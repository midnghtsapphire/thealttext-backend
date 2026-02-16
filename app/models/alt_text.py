"""
TheAltText — AltText Model
Stores generated alt text with metadata.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class AltText(Base):
    __tablename__ = "alt_texts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_text = Column(Text, nullable=False)
    language = Column(String(10), default="en", nullable=False)
    tone = Column(String(50), default="formal", nullable=False)  # formal, casual, technical, simple
    model_used = Column(String(255), nullable=True)
    confidence_score = Column(Float, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    wcag_level = Column(String(10), default="AAA", nullable=False)  # A, AA, AAA
    character_count = Column(Integer, nullable=True)
    carbon_cost_mg = Column(Float, nullable=True)  # estimated carbon cost in milligrams CO2
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    image = relationship("Image", back_populates="alt_texts")

    def __repr__(self):
        return f"<AltText(id={self.id}, image_id={self.image_id}, lang='{self.language}')>"
