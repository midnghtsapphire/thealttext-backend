"""
TheAltText — Image Analysis Routes
Single image analysis, bulk upload, and alt text generation.
"""

import base64
import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.image import Image
from app.models.alt_text import AltText
from app.schemas.schemas import AltTextRequest, AltTextResponse, BulkUploadResponse
from app.services.ai_vision import generate_alt_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/images", tags=["Image Analysis"])


def _check_usage_limit(user: User):
    """Check if user has exceeded their monthly usage limit."""
    if user.tier == "free" and user.monthly_usage >= settings.FREE_TIER_MONTHLY_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Free tier limit reached ({settings.FREE_TIER_MONTHLY_LIMIT} images/month). Upgrade to Pro for unlimited access.",
        )


@router.post(
    "/analyze",
    response_model=AltTextResponse,
    summary="Analyze a single image",
    description="Upload an image file or provide a URL to generate WCAG-compliant alt text.",
)
async def analyze_image(
    file: UploadFile = File(None),
    image_url: str = Form(None),
    language: str = Form("en"),
    tone: str = Form("formal"),
    wcag_level: str = Form("AAA"),
    context: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate alt text for a single image (file upload or URL)."""
    _check_usage_limit(current_user)

    if not file and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either an image file or image_url",
        )

    image_base64 = None
    mime_type = "image/jpeg"
    filename = "url_image"
    file_size = 0

    if file:
        # Validate file type
        allowed = settings.ALLOWED_IMAGE_TYPES.split(",")
        if file.content_type not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type: {file.content_type}. Allowed: {', '.join(allowed)}",
            )

        content = await file.read()
        file_size = len(content)

        if file_size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
            )

        image_base64 = base64.b64encode(content).decode("utf-8")
        mime_type = file.content_type
        filename = file.filename or "uploaded_image"

    # Generate alt text
    try:
        alt_text, model_used, confidence, carbon_cost, processing_time = await generate_alt_text(
            image_url=image_url,
            image_base64=image_base64,
            mime_type=mime_type,
            language=language,
            tone=tone,
            wcag_level=wcag_level,
            context=context,
        )
    except Exception as e:
        logger.error(f"Alt text generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alt text generation failed: {str(e)}",
        )

    # Save image record
    image = Image(
        user_id=current_user.id,
        filename=filename,
        original_url=image_url,
        file_size=file_size,
        mime_type=mime_type,
    )
    db.add(image)
    await db.flush()

    # Save alt text record
    alt_record = AltText(
        image_id=image.id,
        generated_text=alt_text,
        language=language,
        tone=tone,
        model_used=model_used,
        confidence_score=confidence,
        wcag_level=wcag_level,
        character_count=len(alt_text),
        carbon_cost_mg=carbon_cost,
        processing_time_ms=processing_time,
    )
    db.add(alt_record)

    # Update usage
    current_user.monthly_usage += 1
    await db.flush()
    await db.refresh(alt_record)

    return AltTextResponse.model_validate(alt_record)


@router.post(
    "/analyze-url",
    response_model=AltTextResponse,
    summary="Analyze image from URL",
    description="Provide a public image URL to generate WCAG-compliant alt text.",
)
async def analyze_image_url(
    request: AltTextRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate alt text from an image URL."""
    _check_usage_limit(current_user)

    if not request.image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="image_url is required",
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
        logger.error(f"Alt text generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Alt text generation failed: {str(e)}",
        )

    image = Image(
        user_id=current_user.id,
        filename="url_image",
        original_url=request.image_url,
        mime_type="image/unknown",
    )
    db.add(image)
    await db.flush()

    alt_record = AltText(
        image_id=image.id,
        generated_text=alt_text,
        language=request.language,
        tone=request.tone,
        model_used=model_used,
        confidence_score=confidence,
        wcag_level=request.wcag_level,
        character_count=len(alt_text),
        carbon_cost_mg=carbon_cost,
        processing_time_ms=processing_time,
    )
    db.add(alt_record)
    current_user.monthly_usage += 1
    await db.flush()
    await db.refresh(alt_record)

    return AltTextResponse.model_validate(alt_record)


@router.post(
    "/bulk-upload",
    response_model=BulkUploadResponse,
    summary="Bulk upload images",
    description="Upload multiple images at once for batch alt text generation.",
)
async def bulk_upload(
    files: List[UploadFile] = File(...),
    language: str = Form("en"),
    tone: str = Form("formal"),
    wcag_level: str = Form("AAA"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple images for batch processing."""
    _check_usage_limit(current_user)

    if len(files) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 images per batch upload",
        )

    remaining = settings.FREE_TIER_MONTHLY_LIMIT - current_user.monthly_usage if current_user.tier == "free" else len(files)
    if current_user.tier == "free" and len(files) > remaining:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Only {remaining} images remaining in your free tier this month",
        )

    job_id = str(uuid.uuid4())
    processed = 0
    errors = []

    for file in files:
        try:
            content = await file.read()
            image_base64 = base64.b64encode(content).decode("utf-8")

            alt_text, model_used, confidence, carbon_cost, processing_time = await generate_alt_text(
                image_base64=image_base64,
                mime_type=file.content_type or "image/jpeg",
                language=language,
                tone=tone,
                wcag_level=wcag_level,
            )

            image = Image(
                user_id=current_user.id,
                filename=file.filename or f"bulk_{processed}",
                file_size=len(content),
                mime_type=file.content_type,
            )
            db.add(image)
            await db.flush()

            alt_record = AltText(
                image_id=image.id,
                generated_text=alt_text,
                language=language,
                tone=tone,
                model_used=model_used,
                confidence_score=confidence,
                wcag_level=wcag_level,
                character_count=len(alt_text),
                carbon_cost_mg=carbon_cost,
                processing_time_ms=processing_time,
            )
            db.add(alt_record)
            current_user.monthly_usage += 1
            processed += 1

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            logger.error(f"Bulk upload error for {file.filename}: {str(e)}")

    await db.flush()

    status_msg = "completed" if not errors else "completed_with_errors"
    message = f"Processed {processed}/{len(files)} images"
    if errors:
        message += f". Errors: {'; '.join(errors[:5])}"

    return BulkUploadResponse(
        job_id=job_id,
        total_images=processed,
        status=status_msg,
        message=message,
    )


@router.get(
    "/history",
    response_model=List[AltTextResponse],
    summary="Get alt text generation history",
    description="Retrieve your previously generated alt texts.",
)
async def get_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's alt text generation history."""
    result = await db.execute(
        select(AltText)
        .join(Image)
        .where(Image.user_id == current_user.id)
        .order_by(AltText.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    records = result.scalars().all()
    return [AltTextResponse.model_validate(r) for r in records]
