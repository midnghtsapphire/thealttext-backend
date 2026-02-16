"""
TheAltText Backend — Main Application
Standalone FastAPI server with all Blue Ocean enhancements.
A GlowStarLabs product by Audrey Evans.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import (
    auth, images, scanner, reports, dashboard,
    billing, developer,
    # Blue Ocean routes
    bulk, ecommerce, webhooks, competitor, gallery,
)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Stripe mode: {settings.STRIPE_MODE.upper()}")
    logger.info(f"Carbon tracking: {'ON' if settings.CARBON_TRACKING_ENABLED else 'OFF'}")
    logger.info(f"E-commerce mode: {'ON' if settings.ECOMMERCE_MODE_ENABLED else 'OFF'}")
    logger.info(f"Webhooks: {'ON' if settings.WEBHOOK_ENABLED else 'OFF'}")
    logger.info(f"Competitor comparison: {'ON' if settings.COMPETITOR_COMPARISON_ENABLED else 'OFF'}")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered WCAG-compliant alt text generator API. "
        "Includes bulk processing, e-commerce SEO, multi-language support, "
        "webhook notifications, API key management, and competitor comparison. "
        "A GlowStarLabs product by Audrey Evans."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Core Routes ──────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(images.router, prefix="/api/images", tags=["Image Analysis"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["Website Scanner"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(developer.router, prefix="/api/developer", tags=["Developer API"])

# ── Blue Ocean Routes ────────────────────────────────────────────────────────
app.include_router(bulk.router, prefix="/api/bulk", tags=["Bulk Processing"])
app.include_router(ecommerce.router, prefix="/api/ecommerce", tags=["E-commerce SEO"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])
app.include_router(competitor.router, prefix="/api/competitor", tags=["Competitor Comparison"])
app.include_router(gallery.router, prefix="/api/gallery", tags=["Gallery"])


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "stripe_mode": settings.STRIPE_MODE,
        "carbon_tracking": settings.CARBON_TRACKING_ENABLED,
        "ecommerce_mode": settings.ECOMMERCE_MODE_ENABLED,
        "webhooks": settings.WEBHOOK_ENABLED,
        "competitor_comparison": settings.COMPETITOR_COMPARISON_ENABLED,
    }


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "brand": settings.BRAND_NAME,
        "author": settings.BRAND_AUTHOR,
        "url": settings.BRAND_URL,
    }
