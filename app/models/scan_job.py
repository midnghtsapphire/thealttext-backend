"""
TheAltText — ScanJob Model
Website scanning jobs for compliance checking.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_url = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, running, completed, failed
    scan_depth = Column(Integer, default=1, nullable=False)  # How many levels deep to crawl
    pages_scanned = Column(Integer, default=0, nullable=False)
    images_found = Column(Integer, default=0, nullable=False)
    images_missing_alt = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    results = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="scan_jobs")
    images = relationship("Image", back_populates="scan_job")
    reports = relationship("Report", back_populates="scan_job")

    def __repr__(self):
        return f"<ScanJob(id={self.id}, url='{self.target_url}', status='{self.status}')>"
