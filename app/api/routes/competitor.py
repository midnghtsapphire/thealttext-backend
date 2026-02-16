"""
TheAltText Backend — Competitor Alt-Text Comparison Tool
Blue Ocean: Compare your website's alt text compliance against competitors.
A GlowStarLabs product by Audrey Evans.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.scanner import scan_page
from app.services.ai_vision import analyze_existing_alt_text
from app.schemas.schemas import (
    CompetitorCompareRequest, CompetitorCompareResponse, CompetitorImageResult,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def _analyze_site_images(url: str) -> dict:
    """Scan a page and analyze all image alt texts."""
    try:
        result = await scan_page(url)
    except Exception as e:
        logger.error(f"Failed to scan {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to scan URL: {str(e)}",
        )

    total = result.get("total_images", 0)
    with_alt = result.get("images_with_alt", 0)
    compliance = (with_alt / total * 100) if total > 0 else 100.0

    image_results = []
    for img in result.get("images", []):
        alt = img.get("alt", "")
        has_alt = bool(alt and alt.strip())
        if has_alt:
            analysis = await analyze_existing_alt_text(alt)
            quality_score = analysis.get("score", 0)
            issues = analysis.get("issues", [])
        else:
            quality_score = 0.0
            issues = ["Alt text is completely missing"]

        image_results.append(CompetitorImageResult(
            image_url=img.get("src", ""),
            existing_alt=alt if has_alt else None,
            has_alt=has_alt,
            quality_score=quality_score,
            issues=issues,
        ))

    return {
        "total_images": total,
        "images_with_alt": with_alt,
        "compliance_score": round(compliance, 1),
        "images": image_results,
    }


def _generate_recommendations(
    competitor_score: float,
    your_score: Optional[float],
    competitor_total: int,
    your_total: Optional[int],
) -> List[str]:
    """Generate actionable recommendations based on comparison."""
    recs = []

    if your_score is not None:
        diff = your_score - competitor_score
        if diff > 10:
            recs.append(
                f"Your compliance score ({your_score:.1f}%) is {diff:.1f}% higher than "
                f"your competitor. Maintain this advantage."
            )
        elif diff < -10:
            recs.append(
                f"Your competitor's compliance ({competitor_score:.1f}%) exceeds yours "
                f"({your_score:.1f}%). Prioritize adding alt text to close the gap."
            )
        else:
            recs.append("Scores are close. Focus on alt text quality to differentiate.")

    if competitor_score < 70:
        recs.append(
            "Your competitor has poor accessibility. This is an opportunity to "
            "differentiate with superior WCAG compliance."
        )

    if competitor_total > 50:
        recs.append(
            f"Competitor has {competitor_total} images. Ensure all your product "
            "images have descriptive, SEO-optimized alt text."
        )

    recs.append("Use TheAltText's bulk processing to maintain 100% alt text coverage.")
    recs.append("Consider multi-language alt text to reach international audiences.")

    return recs


@router.post(
    "/compare",
    response_model=CompetitorCompareResponse,
    summary="Compare alt text with competitor",
    description="Scan a competitor's website and compare alt text compliance.",
)
async def compare_competitor(
    request: CompetitorCompareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare your website's alt text against a competitor."""
    if not settings.COMPETITOR_COMPARISON_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Competitor comparison is not enabled",
        )

    # Scan competitor
    competitor_data = await _analyze_site_images(request.url)

    # Optionally scan your site
    your_data = None
    if request.your_url:
        your_data = await _analyze_site_images(request.your_url)

    # Determine advantage
    if your_data:
        if your_data["compliance_score"] > competitor_data["compliance_score"] + 5:
            advantage = "you"
        elif competitor_data["compliance_score"] > your_data["compliance_score"] + 5:
            advantage = "competitor"
        else:
            advantage = "tie"
    else:
        advantage = "unknown"

    recommendations = _generate_recommendations(
        competitor_data["compliance_score"],
        your_data["compliance_score"] if your_data else None,
        competitor_data["total_images"],
        your_data["total_images"] if your_data else None,
    )

    return CompetitorCompareResponse(
        competitor_url=request.url,
        your_url=request.your_url,
        competitor_total_images=competitor_data["total_images"],
        competitor_images_with_alt=competitor_data["images_with_alt"],
        competitor_compliance_score=competitor_data["compliance_score"],
        your_total_images=your_data["total_images"] if your_data else None,
        your_images_with_alt=your_data["images_with_alt"] if your_data else None,
        your_compliance_score=your_data["compliance_score"] if your_data else None,
        advantage=advantage,
        recommendations=recommendations,
        competitor_images=competitor_data["images"][:50],  # Limit to 50
    )
