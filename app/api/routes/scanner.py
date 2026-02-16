"""
TheAltText — Scanner Routes
Website URL scanning for ADA/WCAG compliance checking.
"""

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.scan_job import ScanJob
from app.models.image import Image
from app.models.report import Report
from app.schemas.schemas import ScanRequest, ScanJobResponse, ReportResponse
from app.services.scanner import full_site_scan
from app.services.ai_vision import generate_alt_text, analyze_existing_alt_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scanner", tags=["Website Scanner"])


@router.post(
    "/scan",
    response_model=ScanJobResponse,
    summary="Scan a website for alt text compliance",
    description="Crawl a website to find all images and check their alt text status against WCAG standards.",
)
async def scan_website(
    request: ScanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan a website for image alt text compliance."""
    # Create scan job
    scan_job = ScanJob(
        user_id=current_user.id,
        target_url=request.url,
        scan_depth=request.scan_depth,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(scan_job)
    await db.flush()

    try:
        # Perform the scan
        results = await full_site_scan(
            url=request.url,
            scan_depth=request.scan_depth,
        )

        # Update scan job with results
        scan_job.pages_scanned = results["pages_scanned"]
        scan_job.images_found = results["total_images"]
        scan_job.images_missing_alt = results["images_missing_alt"]
        scan_job.results = results
        scan_job.status = "completed"
        scan_job.completed_at = datetime.now(timezone.utc)

        # Save image records from scan
        for page_result in results.get("page_results", []):
            for img_data in page_result.get("images", []):
                image = Image(
                    user_id=current_user.id,
                    filename=img_data["src"].split("/")[-1][:500] if img_data["src"] else "unknown",
                    original_url=img_data["src"],
                    existing_alt_text=img_data.get("alt"),
                    source_page_url=img_data.get("page_url"),
                    scan_job_id=scan_job.id,
                )
                db.add(image)

        # Generate compliance report
        report = Report(
            user_id=current_user.id,
            scan_job_id=scan_job.id,
            title=f"Compliance Scan: {request.url}",
            report_type="compliance",
            target_url=request.url,
            total_images=results["total_images"],
            images_with_alt=results["images_with_alt"],
            images_without_alt=results["images_missing_alt"],
            images_with_poor_alt=results.get("images_empty_alt", 0),
            compliance_score=results["compliance_score"],
            wcag_level="AAA",
            summary=f"Scanned {results['pages_scanned']} pages, found {results['total_images']} images. "
                    f"Compliance score: {results['compliance_score']}%",
            detailed_results=results,
        )
        db.add(report)
        await db.flush()
        await db.refresh(scan_job)

    except Exception as e:
        scan_job.status = "failed"
        scan_job.error_message = str(e)
        scan_job.completed_at = datetime.now(timezone.utc)
        await db.flush()
        logger.error(f"Scan failed for {request.url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}",
        )

    return ScanJobResponse.model_validate(scan_job)


@router.get(
    "/jobs",
    response_model=List[ScanJobResponse],
    summary="List scan jobs",
    description="Get all your website scan jobs and their status.",
)
async def list_scan_jobs(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's scan jobs."""
    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.user_id == current_user.id)
        .order_by(ScanJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    jobs = result.scalars().all()
    return [ScanJobResponse.model_validate(j) for j in jobs]


@router.get(
    "/jobs/{job_id}",
    response_model=ScanJobResponse,
    summary="Get scan job details",
    description="Get detailed results for a specific scan job.",
)
async def get_scan_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific scan job's details."""
    result = await db.execute(
        select(ScanJob).where(
            ScanJob.id == job_id,
            ScanJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return ScanJobResponse.model_validate(job)
