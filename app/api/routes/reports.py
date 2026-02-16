"""
TheAltText — Reports Routes
Compliance report generation and export.
"""

import json
import csv
import io
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.report import Report
from app.schemas.schemas import ReportResponse, ReportExportRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/",
    response_model=List[ReportResponse],
    summary="List compliance reports",
    description="Get all your compliance reports.",
)
async def list_reports(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's compliance reports."""
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report details",
    description="Get detailed information for a specific compliance report.",
)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report's details."""
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.get(
    "/{report_id}/export/{format}",
    summary="Export report",
    description="Export a compliance report in JSON, CSV, or PDF format.",
)
async def export_report(
    report_id: int,
    format: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a report in the specified format."""
    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if format == "json":
        return _export_json(report)
    elif format == "csv":
        return _export_csv(report)
    elif format == "pdf":
        return _export_pdf_placeholder(report)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Use json, csv, or pdf.",
        )


def _export_json(report: Report) -> JSONResponse:
    """Export report as JSON."""
    data = {
        "report": {
            "id": report.id,
            "title": report.title,
            "type": report.report_type,
            "target_url": report.target_url,
            "compliance_score": report.compliance_score,
            "wcag_level": report.wcag_level,
            "total_images": report.total_images,
            "images_with_alt": report.images_with_alt,
            "images_without_alt": report.images_without_alt,
            "images_with_poor_alt": report.images_with_poor_alt,
            "summary": report.summary,
            "carbon_total_mg": report.carbon_total_mg,
            "created_at": report.created_at.isoformat(),
        },
        "detailed_results": report.detailed_results,
        "generated_by": "TheAltText by GlowStarLabs",
        "website": "https://meetaudreyevans.com",
    }
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="thealttext_report_{report.id}.json"'
        },
    )


def _export_csv(report: Report) -> StreamingResponse:
    """Export report as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Image URL", "Page URL", "Has Alt Text", "Alt Text",
        "Status", "Compliance"
    ])

    # Data from detailed results
    if report.detailed_results and "page_results" in report.detailed_results:
        for page in report.detailed_results["page_results"]:
            for img in page.get("images", []):
                writer.writerow([
                    img.get("src", ""),
                    img.get("page_url", ""),
                    "Yes" if img.get("status") == "has_alt" else "No",
                    img.get("alt", ""),
                    img.get("status", "unknown"),
                    "Compliant" if img.get("status") == "has_alt" else "Non-compliant",
                ])

    # Summary row
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Images", report.total_images])
    writer.writerow(["Images with Alt", report.images_with_alt])
    writer.writerow(["Images without Alt", report.images_without_alt])
    writer.writerow(["Compliance Score", f"{report.compliance_score}%"])
    writer.writerow(["Generated by", "TheAltText by GlowStarLabs"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="thealttext_report_{report.id}.csv"'
        },
    )


def _export_pdf_placeholder(report: Report) -> JSONResponse:
    """PDF export placeholder — returns report data for client-side PDF generation."""
    return JSONResponse(
        content={
            "message": "PDF generation available in Pro tier. Use JSON or CSV export, or generate PDF client-side.",
            "report_data": {
                "title": report.title,
                "compliance_score": report.compliance_score,
                "total_images": report.total_images,
                "images_with_alt": report.images_with_alt,
                "images_without_alt": report.images_without_alt,
                "summary": report.summary,
            },
        }
    )
