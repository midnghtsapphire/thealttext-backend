"""
TheAltText Backend — Webhook Notifications API
Blue Ocean: Register webhooks for event notifications.
A GlowStarLabs product by Audrey Evans.
"""
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.schemas import WebhookCreate, WebhookResponse, WebhookTestResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory webhook store (use DB in production)
_webhooks: Dict[int, dict] = {}
_webhook_counter = 0

SUPPORTED_EVENTS = [
    "alt_text.generated",
    "alt_text.failed",
    "bulk.started",
    "bulk.completed",
    "bulk.failed",
    "scan.started",
    "scan.completed",
    "scan.failed",
    "subscription.created",
    "subscription.canceled",
    "api_key.created",
    "api_key.revoked",
]


def _sign_payload(payload: str, secret: str) -> str:
    """Create HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


async def deliver_webhook(webhook: dict, event_type: str, data: dict):
    """Deliver a webhook notification with retry logic."""
    payload = json.dumps({
        "event": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "webhook_id": webhook["id"],
    })

    headers = {"Content-Type": "application/json", "X-TheAltText-Event": event_type}
    if webhook.get("secret"):
        headers["X-TheAltText-Signature"] = _sign_payload(payload, webhook["secret"])

    for attempt in range(settings.WEBHOOK_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(webhook["url"], content=payload, headers=headers)
                if response.status_code < 300:
                    webhook["deliveries_count"] = webhook.get("deliveries_count", 0) + 1
                    webhook["last_delivered_at"] = datetime.now(timezone.utc).isoformat()
                    logger.info(f"Webhook {webhook['id']} delivered: {event_type}")
                    return True
                logger.warning(f"Webhook {webhook['id']} got {response.status_code}, attempt {attempt + 1}")
        except Exception as e:
            logger.error(f"Webhook {webhook['id']} delivery failed: {e}, attempt {attempt + 1}")

    return False


async def trigger_webhooks(user_id: int, event_type: str, data: dict):
    """Trigger all matching webhooks for a user event."""
    if not settings.WEBHOOK_ENABLED:
        return

    for wh in _webhooks.values():
        if wh.get("user_id") == user_id and event_type in wh.get("events", []) and wh.get("is_active"):
            await deliver_webhook(wh, event_type, data)


@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a webhook",
    description="Register a webhook endpoint to receive event notifications.",
)
async def create_webhook(
    request: WebhookCreate,
    current_user: User = Depends(get_current_user),
):
    """Register a new webhook endpoint."""
    # Validate events
    invalid = [e for e in request.events if e not in SUPPORTED_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported events: {invalid}. Supported: {SUPPORTED_EVENTS}",
        )

    global _webhook_counter
    _webhook_counter += 1

    webhook = {
        "id": _webhook_counter,
        "user_id": current_user.id,
        "url": request.url,
        "events": request.events,
        "secret": request.secret,
        "is_active": True,
        "deliveries_count": 0,
        "last_delivered_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _webhooks[_webhook_counter] = webhook

    return WebhookResponse(**{k: v for k, v in webhook.items() if k != "secret" and k != "user_id"})


@router.get(
    "/",
    response_model=List[WebhookResponse],
    summary="List webhooks",
    description="List all registered webhooks.",
)
async def list_webhooks(
    current_user: User = Depends(get_current_user),
):
    """List user's webhooks."""
    user_webhooks = [
        WebhookResponse(**{k: v for k, v in wh.items() if k != "secret" and k != "user_id"})
        for wh in _webhooks.values()
        if wh.get("user_id") == current_user.id
    ]
    return user_webhooks


@router.delete(
    "/{webhook_id}",
    summary="Delete a webhook",
    description="Remove a registered webhook.",
)
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a webhook."""
    webhook = _webhooks.get(webhook_id)
    if not webhook or webhook.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del _webhooks[webhook_id]
    return {"message": "Webhook deleted"}


@router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Test a webhook",
    description="Send a test event to a webhook endpoint.",
)
async def test_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
):
    """Send a test event to a webhook."""
    webhook = _webhooks.get(webhook_id)
    if not webhook or webhook.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    start = time.time()
    test_data = {"message": "This is a test event from TheAltText", "test": True}

    try:
        payload = json.dumps({
            "event": "test",
            "data": test_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        headers = {"Content-Type": "application/json", "X-TheAltText-Event": "test"}
        if webhook.get("secret"):
            headers["X-TheAltText-Signature"] = _sign_payload(payload, webhook["secret"])

        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(webhook["url"], content=payload, headers=headers)
            return WebhookTestResponse(
                webhook_id=webhook_id,
                status_code=response.status_code,
                response_time_ms=int((time.time() - start) * 1000),
                success=response.status_code < 300,
            )
    except Exception as e:
        return WebhookTestResponse(
            webhook_id=webhook_id,
            status_code=0,
            response_time_ms=int((time.time() - start) * 1000),
            success=False,
        )


@router.get(
    "/events",
    summary="List supported events",
    description="List all supported webhook event types.",
)
async def list_events():
    """List supported webhook events."""
    return {"events": SUPPORTED_EVENTS}
