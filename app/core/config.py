"""
TheAltText Backend — Configuration
Standalone settings with Stripe dual-mode (test/live) toggle.
Includes Blue Ocean enhancements: bulk processing, e-commerce SEO,
multi-language, webhooks, API key management, competitor comparison.
A GlowStarLabs product by Audrey Evans.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "TheAltText"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://thealttext:changeme@db:5432/thealttext"

    # ── Auth / JWT ───────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── OpenRouter AI ────────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    VISION_MODELS_FREE: str = "google/gemini-2.0-flash-exp:free,meta-llama/llama-4-maverick:free"
    VISION_MODELS_PAID: str = "google/gemini-2.5-flash,openai/gpt-4.1-mini"

    # ── Stripe Dual-Mode Billing ─────────────────────────────────────────
    STRIPE_MODE: str = "test"  # "test" or "live"

    # Test mode keys
    STRIPE_TEST_SECRET_KEY: str = ""
    STRIPE_TEST_PUBLISHABLE_KEY: str = ""
    STRIPE_TEST_WEBHOOK_SECRET: str = ""
    STRIPE_TEST_PRO_PRICE_ID: str = ""
    STRIPE_TEST_ENTERPRISE_PRICE_ID: str = ""

    # Live mode keys
    STRIPE_LIVE_SECRET_KEY: str = ""
    STRIPE_LIVE_PUBLISHABLE_KEY: str = ""
    STRIPE_LIVE_WEBHOOK_SECRET: str = ""
    STRIPE_LIVE_PRO_PRICE_ID: str = ""
    STRIPE_LIVE_ENTERPRISE_PRICE_ID: str = ""

    # Legacy single-mode keys (backward compat)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""

    # ── Rate Limits ──────────────────────────────────────────────────────
    FREE_TIER_MONTHLY_LIMIT: int = 50
    PRO_TIER_MONTHLY_LIMIT: int = -1  # unlimited

    # ── File Upload ──────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_IMAGE_TYPES: str = (
        "image/jpeg,image/png,image/webp,image/gif,"
        "image/svg+xml,image/bmp,image/tiff"
    )

    # ── Redis (for Celery task queue) ────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── Carbon Tracking ──────────────────────────────────────────────────
    CARBON_TRACKING_ENABLED: bool = True

    # ── Blue Ocean: Bulk Processing ──────────────────────────────────────
    BULK_MAX_IMAGES: int = 100
    BULK_CONCURRENT_WORKERS: int = 5

    # ── Blue Ocean: E-commerce SEO ───────────────────────────────────────
    ECOMMERCE_MODE_ENABLED: bool = True
    SEO_KEYWORD_BOOST: bool = True

    # ── Blue Ocean: Multi-Language ───────────────────────────────────────
    SUPPORTED_LANGUAGES: str = (
        "en,es,fr,de,ja,ko,zh,ar,pt,it,nl,ru,hi,haw"
    )
    AUTO_DETECT_LOCALE: bool = True

    # ── Blue Ocean: Webhooks ─────────────────────────────────────────────
    WEBHOOK_ENABLED: bool = True
    WEBHOOK_MAX_RETRIES: int = 3
    WEBHOOK_TIMEOUT_SECONDS: int = 10

    # ── Blue Ocean: Competitor Comparison ────────────────────────────────
    COMPETITOR_COMPARISON_ENABLED: bool = True

    # ── Branding ─────────────────────────────────────────────────────────
    BRAND_NAME: str = "GlowStarLabs"
    BRAND_URL: str = "https://meetaudreyevans.com"
    BRAND_AUTHOR: str = "Audrey Evans"

    # ── Stripe Helper Properties ─────────────────────────────────────────
    @property
    def active_stripe_secret_key(self) -> str:
        if self.STRIPE_MODE == "live":
            return self.STRIPE_LIVE_SECRET_KEY or self.STRIPE_SECRET_KEY
        return self.STRIPE_TEST_SECRET_KEY or self.STRIPE_SECRET_KEY

    @property
    def active_stripe_publishable_key(self) -> str:
        if self.STRIPE_MODE == "live":
            return self.STRIPE_LIVE_PUBLISHABLE_KEY or self.STRIPE_PUBLISHABLE_KEY
        return self.STRIPE_TEST_PUBLISHABLE_KEY or self.STRIPE_PUBLISHABLE_KEY

    @property
    def active_stripe_webhook_secret(self) -> str:
        if self.STRIPE_MODE == "live":
            return self.STRIPE_LIVE_WEBHOOK_SECRET or self.STRIPE_WEBHOOK_SECRET
        return self.STRIPE_TEST_WEBHOOK_SECRET or self.STRIPE_WEBHOOK_SECRET

    @property
    def active_stripe_pro_price_id(self) -> str:
        if self.STRIPE_MODE == "live":
            return self.STRIPE_LIVE_PRO_PRICE_ID or self.STRIPE_PRO_PRICE_ID
        return self.STRIPE_TEST_PRO_PRICE_ID or self.STRIPE_PRO_PRICE_ID

    @property
    def active_stripe_enterprise_price_id(self) -> str:
        if self.STRIPE_MODE == "live":
            return self.STRIPE_LIVE_ENTERPRISE_PRICE_ID
        return self.STRIPE_TEST_ENTERPRISE_PRICE_ID

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
