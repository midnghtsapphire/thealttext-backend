"""
TheAltText Backend — Pydantic Schemas
All request/response models including Blue Ocean enhancements.
A GlowStarLabs product by Audrey Evans.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Auth ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (min 8 chars)")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    organization: Optional[str]
    tier: str
    monthly_usage: int
    preferred_language: Optional[str]
    preferred_tone: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    organization: Optional[str] = None
    preferred_language: Optional[str] = None
    preferred_tone: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Alt Text Generation ──────────────────────────────────────────────────────
class AltTextRequest(BaseModel):
    image_url: Optional[str] = None
    language: str = Field(default="en", description="ISO 639-1 language code")
    tone: str = Field(default="formal", description="Tone: formal, casual, technical, simple")
    wcag_level: str = Field(default="AAA", description="Target WCAG level: A, AA, AAA")
    context: Optional[str] = Field(default=None, description="Additional context about the image")


class AltTextResponse(BaseModel):
    id: int
    image_id: int
    generated_text: str
    language: str
    tone: str
    model_used: Optional[str]
    confidence_score: Optional[float]
    wcag_level: str
    character_count: Optional[int]
    carbon_cost_mg: Optional[float]
    processing_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class BulkUploadResponse(BaseModel):
    job_id: str
    total_images: int
    status: str
    message: str


# ── URL Scanning ─────────────────────────────────────────────────────────────
class ScanRequest(BaseModel):
    url: str = Field(description="URL to scan for images and alt text compliance")
    scan_depth: int = Field(default=1, ge=1, le=5, description="Crawl depth (1-5 pages deep)")
    generate_alt: bool = Field(default=False, description="Auto-generate alt text for missing images")
    language: str = Field(default="en")
    tone: str = Field(default="formal")


class ScanJobResponse(BaseModel):
    id: int
    target_url: str
    status: str
    scan_depth: int
    pages_scanned: int
    images_found: int
    images_missing_alt: int
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScanResultItem(BaseModel):
    image_url: str
    page_url: str
    existing_alt: Optional[str]
    has_alt: bool
    generated_alt: Optional[str]
    compliance_status: str


# ── Reports ──────────────────────────────────────────────────────────────────
class ReportResponse(BaseModel):
    id: int
    title: str
    report_type: str
    target_url: Optional[str]
    total_images: int
    images_with_alt: int
    images_without_alt: int
    images_with_poor_alt: int
    compliance_score: float
    wcag_level: str
    summary: Optional[str]
    carbon_total_mg: float
    created_at: datetime

    class Config:
        from_attributes = True


class ReportExportRequest(BaseModel):
    report_id: int
    format: str = Field(default="json", description="Export format: json, csv, pdf")


# ── API Keys ─────────────────────────────────────────────────────────────────
class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class APIKeyResponse(BaseModel):
    id: int
    key_prefix: str
    name: str
    is_active: bool
    requests_count: int
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(APIKeyResponse):
    full_key: str


# ── Subscription ─────────────────────────────────────────────────────────────
class SubscriptionResponse(BaseModel):
    id: int
    plan: str
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CheckoutRequest(BaseModel):
    plan: str = Field(description="Plan to subscribe to: pro, enterprise")
    success_url: str
    cancel_url: str
    stripe_mode: Optional[str] = Field(default=None, description="Override stripe mode: test, live")


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


# ── Dashboard / Stats ────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_images_processed: int
    total_alt_texts_generated: int
    total_scans: int
    monthly_usage: int
    monthly_limit: int
    compliance_score_avg: float
    carbon_saved_mg: float
    tier: str


# ── Health ───────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    stripe_mode: str
    carbon_tracking: bool


# ── Developer API ────────────────────────────────────────────────────────────
class DevAPIRequest(BaseModel):
    image_url: str = Field(description="Public URL of the image to analyze")
    language: str = Field(default="en")
    tone: str = Field(default="formal")
    wcag_level: str = Field(default="AAA")
    context: Optional[str] = None


class DevAPIResponse(BaseModel):
    alt_text: str
    language: str
    tone: str
    wcag_level: str
    confidence: Optional[float]
    model: Optional[str]
    carbon_cost_mg: Optional[float]
    processing_time_ms: Optional[int]


# ══════════════════════════════════════════════════════════════════════════════
# BLUE OCEAN SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

# ── Bulk Processing ──────────────────────────────────────────────────────────
class BulkJobCreate(BaseModel):
    language: str = Field(default="en")
    tone: str = Field(default="formal")
    wcag_level: str = Field(default="AAA")


class BulkJobItemResult(BaseModel):
    image_index: int
    file_name: str
    alt_text: Optional[str]
    confidence: Optional[float]
    wcag_score: Optional[float]
    error: Optional[str]
    processing_time_ms: Optional[int]


class BulkJobResponse(BaseModel):
    job_id: str
    total: int
    completed: int
    errors: int
    status: str  # queued, processing, completed, failed
    results: List[BulkJobItemResult]


# ── E-commerce SEO ───────────────────────────────────────────────────────────
class EcommerceProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    product_name: str = Field(min_length=1, max_length=500)
    category: str = Field(default="General")
    image_urls: List[str] = Field(default_factory=list)


class EcommerceProductImageResponse(BaseModel):
    id: int
    image_url: str
    current_alt: Optional[str]
    generated_alt: Optional[str]
    seo_optimized_alt: Optional[str]
    wcag_score: float
    seo_score: float


class EcommerceProductResponse(BaseModel):
    id: int
    sku: str
    product_name: str
    category: str
    seo_score: float
    created_at: datetime
    images: List[EcommerceProductImageResponse]

    class Config:
        from_attributes = True


class SeoAltResponse(BaseModel):
    product_id: int
    images_processed: int
    avg_seo_score: float
    message: str


# ── Webhooks ─────────────────────────────────────────────────────────────────
class WebhookCreate(BaseModel):
    url: str = Field(description="Webhook endpoint URL (HTTPS)")
    events: List[str] = Field(
        default=["alt_text.generated", "bulk.completed", "scan.completed"],
        description="Events to subscribe to",
    )
    secret: Optional[str] = Field(default=None, description="Shared secret for HMAC signature")


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    deliveries_count: int
    last_delivered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    webhook_id: int
    status_code: int
    response_time_ms: int
    success: bool


# ── Competitor Comparison ────────────────────────────────────────────────────
class CompetitorCompareRequest(BaseModel):
    url: str = Field(description="Competitor website URL to compare")
    your_url: Optional[str] = Field(default=None, description="Your website URL for comparison")


class CompetitorImageResult(BaseModel):
    image_url: str
    existing_alt: Optional[str]
    has_alt: bool
    quality_score: float
    issues: List[str]


class CompetitorCompareResponse(BaseModel):
    competitor_url: str
    your_url: Optional[str]
    competitor_total_images: int
    competitor_images_with_alt: int
    competitor_compliance_score: float
    your_total_images: Optional[int]
    your_images_with_alt: Optional[int]
    your_compliance_score: Optional[float]
    advantage: str  # "you", "competitor", "tie"
    recommendations: List[str]
    competitor_images: List[CompetitorImageResult]


# ── Gallery ──────────────────────────────────────────────────────────────────
class GalleryItemResponse(BaseModel):
    id: int
    image_url: str
    original_alt: Optional[str]
    generated_alt: Optional[str]
    wcag_score: Optional[dict]
    language: str
    tone: str
    file_name: Optional[str]
    file_size: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Multi-Language ───────────────────────────────────────────────────────────
class MultiLanguageRequest(BaseModel):
    image_url: str
    languages: List[str] = Field(
        default=["en", "es", "fr"],
        description="List of ISO 639-1 language codes",
    )
    tone: str = Field(default="formal")
    wcag_level: str = Field(default="AAA")


class MultiLanguageResult(BaseModel):
    language: str
    language_name: str
    alt_text: str
    confidence: Optional[float]


class MultiLanguageResponse(BaseModel):
    image_url: str
    results: List[MultiLanguageResult]
    total_languages: int
    processing_time_ms: int
