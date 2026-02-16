"""
TheAltText Backend — Billing Routes
Stripe dual-mode (test/live) subscription management endpoints.
A GlowStarLabs product by Audrey Evans.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.subscription import Subscription
from app.schemas.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionResponse,
)
from app.services.billing import (
    create_customer,
    create_checkout_session,
    cancel_subscription,
    handle_webhook_event,
    get_stripe_mode,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_plan_prices() -> dict:
    """Get plan prices based on active Stripe mode."""
    return {
        "pro": settings.active_stripe_pro_price_id,
        "enterprise": settings.active_stripe_enterprise_price_id,
    }


@router.get(
    "/config",
    summary="Get billing config",
    description="Get the current Stripe configuration (publishable key and mode).",
)
async def get_billing_config():
    """Return the publishable key and mode for frontend Stripe.js."""
    return {
        "stripe_mode": settings.STRIPE_MODE,
        "publishable_key": settings.active_stripe_publishable_key,
        "plans": {
            "pro": {"price_id": settings.active_stripe_pro_price_id},
            "enterprise": {"price_id": settings.active_stripe_enterprise_price_id},
        },
    }


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
    description="Create a Stripe Checkout session for subscription upgrade.",
)
async def create_checkout(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for subscription upgrade."""
    plan_prices = _get_plan_prices()

    if request.plan not in plan_prices:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan: {request.plan}. Available: {list(plan_prices.keys())}",
        )

    price_id = plan_prices[request.plan]
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Stripe is not configured for plan '{request.plan}' in {settings.STRIPE_MODE} mode.",
        )

    # Create Stripe customer if needed
    if not current_user.stripe_customer_id:
        customer_id = await create_customer(
            email=current_user.email,
            name=current_user.full_name,
        )
        current_user.stripe_customer_id = customer_id
        await db.flush()

    session = await create_checkout_session(
        customer_id=current_user.stripe_customer_id,
        plan=request.plan,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
    )
    return CheckoutResponse(**session)


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get current subscription",
    description="Get the current user's subscription details.",
)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's active subscription."""
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status.in_(["active", "trialing"]),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return SubscriptionResponse(
            id=0,
            plan="free",
            status="active",
            current_period_start=None,
            current_period_end=None,
            cancel_at_period_end=False,
            created_at=current_user.created_at,
        )
    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/cancel",
    summary="Cancel subscription",
    description="Cancel your subscription at the end of the current billing period.",
)
async def cancel_sub(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel the current subscription."""
    result = await db.execute(
        select(Subscription)
        .where(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()

    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    result = await cancel_subscription(subscription.stripe_subscription_id)
    subscription.cancel_at_period_end = True
    await db.flush()

    return {"message": "Subscription will be canceled at the end of the billing period", **result}


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events (works for both test and live modes)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = handle_webhook_event(payload, sig_header)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event["type"]
    data = event["data"]

    logger.info(f"Stripe webhook ({settings.STRIPE_MODE}): {event_type}")

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")

        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.tier = "pro"
            sub = Subscription(
                user_id=user.id,
                stripe_subscription_id=subscription_id,
                plan="pro",
                status="active",
            )
            db.add(sub)
            await db.flush()

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "canceled"
            result2 = await db.execute(select(User).where(User.id == sub.user_id))
            user = result2.scalar_one_or_none()
            if user:
                user.tier = "free"
            await db.flush()

    return {"status": "ok"}
