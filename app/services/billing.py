"""
TheAltText Backend — Billing Service
Stripe dual-mode (test/live) integration for subscription management.
A GlowStarLabs product by Audrey Evans.
"""
import logging
from typing import Optional

import stripe

from app.core.config import settings

logger = logging.getLogger(__name__)


def _init_stripe():
    """Initialize Stripe with the active mode key."""
    stripe.api_key = settings.active_stripe_secret_key
    logger.info(f"Stripe initialized in {settings.STRIPE_MODE.upper()} mode")


_init_stripe()


def get_stripe_mode() -> str:
    """Return the current Stripe mode."""
    return settings.STRIPE_MODE


async def create_customer(email: str, name: Optional[str] = None) -> str:
    """Create a Stripe customer and return the customer ID."""
    _init_stripe()
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                "app": "thealttext",
                "ecosystem": "glowstarlabs",
                "stripe_mode": settings.STRIPE_MODE,
            },
        )
        return customer.id
    except stripe.error.StripeError as e:
        logger.error(f"Stripe customer creation failed: {str(e)}")
        raise


async def create_checkout_session(
    customer_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a Stripe Checkout session for subscription."""
    _init_stripe()

    # Resolve price ID based on plan
    if plan == "enterprise":
        price_id = settings.active_stripe_enterprise_price_id
    else:
        price_id = settings.active_stripe_pro_price_id

    if not price_id:
        raise ValueError(f"No price ID configured for plan '{plan}' in {settings.STRIPE_MODE} mode")

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "app": "thealttext",
                "plan": plan,
                "stripe_mode": settings.STRIPE_MODE,
            },
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout creation failed: {str(e)}")
        raise


async def cancel_subscription(subscription_id: str) -> dict:
    """Cancel a Stripe subscription at period end."""
    _init_stripe()
    try:
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )
        return {
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe cancellation failed: {str(e)}")
        raise


async def get_subscription(subscription_id: str) -> dict:
    """Get subscription details from Stripe."""
    _init_stripe()
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        return {
            "id": subscription.id,
            "status": subscription.status,
            "plan": subscription.plan.id if subscription.plan else None,
            "current_period_end": subscription.current_period_end,
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe subscription retrieval failed: {str(e)}")
        raise


def handle_webhook_event(payload: bytes, sig_header: str) -> dict:
    """Process a Stripe webhook event using the active webhook secret."""
    _init_stripe()
    webhook_secret = settings.active_stripe_webhook_secret
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise ValueError("Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid signature")
    return {"type": event.type, "data": event.data.object}
