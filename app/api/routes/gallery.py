"""
TheAltText Backend — Gallery API
Blue Ocean: Browse and manage all processed images.
A GlowStarLabs product by Audrey Evans.
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.image import Image
from app.models.alt_text import AltText
from app.services.ai_vision import analyze_existing_alt_text
from app.schemas.schemas import GalleryItemResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "",
    response_model=List[GalleryItemResponse],
    summary="List gallery images",
    description="Browse all processed images with WCAG scores.",
)
async def list_gallery(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all processed images for the current user."""
    result = await db.execute(
        select(Image)
        .where(Image.user_id == current_user.id)
        .order_by(Image.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    images = result.scalars().all()

    gallery_items = []
    for img in images:
        # Get the latest alt text for this image
        alt_result = await db.execute(
            select(AltText)
            .where(AltText.image_id == img.id)
            .order_by(AltText.created_at.desc())
            .limit(1)
        )
        alt = alt_result.scalar_one_or_none()

        wcag_score = None
        if alt and alt.generated_text:
            wcag_score = await analyze_existing_alt_text(alt.generated_text)

        gallery_items.append(GalleryItemResponse(
            id=img.id,
            image_url=img.source_url or "",
            original_alt=img.original_alt,
            generated_alt=alt.generated_text if alt else None,
            wcag_score=wcag_score,
            language=alt.language if alt else "en",
            tone=alt.tone if alt else "formal",
            file_name=img.file_name,
            file_size=img.file_size,
            created_at=img.created_at,
        ))

    return gallery_items


@router.get(
    "/{image_id}",
    response_model=GalleryItemResponse,
    summary="Get gallery image details",
    description="Get details for a specific processed image.",
)
async def get_gallery_item(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single gallery image with details."""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == current_user.id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    alt_result = await db.execute(
        select(AltText)
        .where(AltText.image_id == img.id)
        .order_by(AltText.created_at.desc())
        .limit(1)
    )
    alt = alt_result.scalar_one_or_none()

    wcag_score = None
    if alt and alt.generated_text:
        wcag_score = await analyze_existing_alt_text(alt.generated_text)

    return GalleryItemResponse(
        id=img.id,
        image_url=img.source_url or "",
        original_alt=img.original_alt,
        generated_alt=alt.generated_text if alt else None,
        wcag_score=wcag_score,
        language=alt.language if alt else "en",
        tone=alt.tone if alt else "formal",
        file_name=img.file_name,
        file_size=img.file_size,
        created_at=img.created_at,
    )


@router.delete(
    "/{image_id}",
    summary="Delete a gallery image",
    description="Remove an image from the gallery.",
)
async def delete_gallery_item(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an image from the gallery."""
    result = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == current_user.id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    await db.delete(img)
    await db.flush()
    return {"message": "Image deleted from gallery"}
