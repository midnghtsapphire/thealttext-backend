"""
TheAltText Backend — Bulk Processing API
Blue Ocean: Process up to 100 images in a single batch.
A GlowStarLabs product by Audrey Evans.
"""
import asyncio
import logging
import time
import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.ai_vision import generate_alt_text, analyze_existing_alt_text
from app.schemas.schemas import BulkJobResponse, BulkJobItemResult

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job store (use Redis in production)
_bulk_jobs: Dict[str, dict] = {}


@router.post(
    "/process",
    response_model=BulkJobResponse,
    summary="Start bulk image processing",
    description="Upload up to 100 images for batch alt text generation.",
)
async def start_bulk_processing(
    files: List[UploadFile] = File(...),
    language: str = Form(default="en"),
    tone: str = Form(default="formal"),
    wcag_level: str = Form(default="AAA"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process multiple images in bulk."""
    if len(files) > settings.BULK_MAX_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.BULK_MAX_IMAGES} images per batch",
        )

    # Check tier limits
    if current_user.tier == "free":
        remaining = settings.FREE_TIER_MONTHLY_LIMIT - current_user.monthly_usage
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly limit reached. Upgrade for bulk processing.",
            )
        if len(files) > remaining:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Only {remaining} images remaining in your monthly quota.",
            )

    job_id = f"bulk_{uuid.uuid4().hex[:12]}"
    results: List[BulkJobItemResult] = []
    errors = 0
    start_time = time.time()

    for idx, file in enumerate(files):
        try:
            content = await file.read()
            import base64
            b64 = base64.b64encode(content).decode()
            mime = file.content_type or "image/jpeg"
            data_url = f"data:{mime};base64,{b64}"

            alt_text, model_used, confidence, carbon_cost, proc_time = await generate_alt_text(
                image_base64=data_url,
                language=language,
                tone=tone,
                wcag_level=wcag_level,
            )

            wcag_result = await analyze_existing_alt_text(alt_text, wcag_level=wcag_level)

            results.append(BulkJobItemResult(
                image_index=idx,
                file_name=file.filename or f"image_{idx}",
                alt_text=alt_text,
                confidence=confidence,
                wcag_score=wcag_result.get("score", 0),
                error=None,
                processing_time_ms=proc_time,
            ))

            current_user.monthly_usage += 1

        except Exception as e:
            logger.error(f"Bulk item {idx} failed: {str(e)}")
            errors += 1
            results.append(BulkJobItemResult(
                image_index=idx,
                file_name=file.filename or f"image_{idx}",
                alt_text=None,
                confidence=None,
                wcag_score=None,
                error=str(e),
                processing_time_ms=None,
            ))

    await db.flush()

    total_time = int((time.time() - start_time) * 1000)
    completed = len(results) - errors

    response = BulkJobResponse(
        job_id=job_id,
        total=len(files),
        completed=completed,
        errors=errors,
        status="completed",
        results=results,
    )

    _bulk_jobs[job_id] = response.model_dump()
    logger.info(f"Bulk job {job_id}: {completed}/{len(files)} completed in {total_time}ms")

    return response


@router.get(
    "/status/{job_id}",
    response_model=BulkJobResponse,
    summary="Get bulk job status",
    description="Check the status of a bulk processing job.",
)
async def get_bulk_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get status of a bulk processing job."""
    job = _bulk_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Bulk job not found")
    return BulkJobResponse(**job)
