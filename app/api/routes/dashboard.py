"""
TheAltText — Dashboard Routes
User dashboard stats and carbon tracking.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.image import Image
from app.models.alt_text import AltText
from app.models.scan_job import ScanJob
from app.models.report import Report
from app.schemas.schemas import DashboardStats
from app.utils.carbon import format_carbon_savings

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Get aggregated statistics for the current user's dashboard.",
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's dashboard statistics."""
    # Total images processed
    img_count = await db.execute(
        select(func.count(Image.id)).where(Image.user_id == current_user.id)
    )
    total_images = img_count.scalar() or 0

    # Total alt texts generated
    alt_count = await db.execute(
        select(func.count(AltText.id))
        .join(Image)
        .where(Image.user_id == current_user.id)
    )
    total_alt_texts = alt_count.scalar() or 0

    # Total scans
    scan_count = await db.execute(
        select(func.count(ScanJob.id)).where(ScanJob.user_id == current_user.id)
    )
    total_scans = scan_count.scalar() or 0

    # Average compliance score
    avg_score = await db.execute(
        select(func.avg(Report.compliance_score)).where(Report.user_id == current_user.id)
    )
    compliance_avg = avg_score.scalar() or 0.0

    # Total carbon
    carbon_sum = await db.execute(
        select(func.sum(AltText.carbon_cost_mg))
        .join(Image)
        .where(Image.user_id == current_user.id)
    )
    carbon_total = carbon_sum.scalar() or 0.0

    monthly_limit = (
        settings.FREE_TIER_MONTHLY_LIMIT if current_user.tier == "free"
        else -1  # unlimited
    )

    return DashboardStats(
        total_images_processed=total_images,
        total_alt_texts_generated=total_alt_texts,
        total_scans=total_scans,
        monthly_usage=current_user.monthly_usage,
        monthly_limit=monthly_limit,
        compliance_score_avg=round(compliance_avg, 1),
        carbon_saved_mg=round(carbon_total, 2),
        tier=current_user.tier,
    )


@router.get(
    "/carbon",
    summary="Get carbon tracking data",
    description="Get detailed carbon footprint tracking for your usage.",
)
async def get_carbon_tracking(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get carbon tracking details."""
    carbon_sum = await db.execute(
        select(func.sum(AltText.carbon_cost_mg))
        .join(Image)
        .where(Image.user_id == current_user.id)
    )
    carbon_total = carbon_sum.scalar() or 0.0

    return {
        "tracking_enabled": settings.CARBON_TRACKING_ENABLED,
        **format_carbon_savings(carbon_total),
    }
