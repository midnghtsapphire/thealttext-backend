"""
TheAltText — Report Model
Compliance reports for scanned websites.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_job_id = Column(Integer, ForeignKey("scan_jobs.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    report_type = Column(String(50), default="compliance", nullable=False)  # compliance, bulk, single
    target_url = Column(Text, nullable=True)
    total_images = Column(Integer, default=0, nullable=False)
    images_with_alt = Column(Integer, default=0, nullable=False)
    images_without_alt = Column(Integer, default=0, nullable=False)
    images_with_poor_alt = Column(Integer, default=0, nullable=False)
    compliance_score = Column(Float, default=0.0, nullable=False)
    wcag_level = Column(String(10), default="AAA", nullable=False)
    summary = Column(Text, nullable=True)
    detailed_results = Column(JSON, nullable=True)
    export_format = Column(String(20), nullable=True)  # pdf, csv, json
    file_path = Column(Text, nullable=True)
    carbon_total_mg = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="reports")
    scan_job = relationship("ScanJob", back_populates="reports")

    def __repr__(self):
        return f"<Report(id={self.id}, score={self.compliance_score})>"
