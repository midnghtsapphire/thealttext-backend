"""
TheAltText — Developer API Routes
Public API endpoints for third-party integrations.
Authenticated via API keys.
"""

import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.api_key import APIKey
from app.schemas.schemas import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreatedResponse,
    DevAPIRequest,
    DevAPIResponse,
)
from app.services.ai_vision import generate_alt_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/developer", tags=["Developer API"])


def _hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


async def _get_user_from_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate a request using an API key."""
    key_hash = _hash_key(x_api_key)
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Update usage stats
    api_key.last_used_at = datetime.now(timezone.utc)
    api_key.requests_count += 1

    # Get the user
    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


# ── API Key Management ────────────────────────────────────────────────────────

@router.post(
    "/keys",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an API key",
    description="Generate a new API key for programmatic access to TheAltText.",
)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key."""
    # Generate key
    raw_key = f"tat_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    key_prefix = raw_key[:12]

    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=request.name,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    response = APIKeyCreatedResponse(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        is_active=api_key.is_active,
        requests_count=api_key.requests_count,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        full_key=raw_key,
    )
    return response


@router.get(
    "/keys",
    response_model=List[APIKeyResponse],
    summary="List API keys",
    description="List all your API keys.",
)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's API keys."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [APIKeyResponse.model_validate(k) for k in keys]


@router.delete(
    "/keys/{key_id}",
    summary="Revoke an API key",
    description="Permanently deactivate an API key.",
)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    await db.flush()
    return {"message": "API key revoked"}


# ── Public API Endpoint ──────────────────────────────────────────────────────

@router.post(
    "/v1/alt-text",
    response_model=DevAPIResponse,
    summary="Generate alt text (API)",
    description="Generate WCAG-compliant alt text for an image. Authenticate with X-API-Key header.",
)
async def generate_alt_text_api(
    request: DevAPIRequest,
    user: User = Depends(_get_user_from_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Public API endpoint for alt text generation."""
    # Check usage limits
    if user.tier == "free" and user.monthly_usage >= settings.FREE_TIER_MONTHLY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly limit reached. Upgrade to Pro for unlimited access.",
        )

    try:
        alt_text, model_used, confidence, carbon_cost, processing_time = await generate_alt_text(
            image_url=request.image_url,
            language=request.language,
            tone=request.tone,
            wcag_level=request.wcag_level,
            context=request.context,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )

    user.monthly_usage += 1
    await db.flush()

    return DevAPIResponse(
        alt_text=alt_text,
        language=request.language,
        tone=request.tone,
        wcag_level=request.wcag_level,
        confidence=confidence,
        model=model_used,
        carbon_cost_mg=carbon_cost,
        processing_time_ms=processing_time,
    )
