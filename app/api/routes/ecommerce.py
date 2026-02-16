"""
TheAltText Backend — E-commerce SEO API
Blue Ocean: Product catalog management with SEO-optimized alt text.
A GlowStarLabs product by Audrey Evans.
"""
import logging
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.ai_vision import generate_alt_text
from app.schemas.schemas import (
    EcommerceProductCreate, EcommerceProductResponse,
    EcommerceProductImageResponse, SeoAltResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory product store (use DB in production)
_products: dict = {}
_product_counter = 0


def _seo_optimize_alt(alt_text: str, product_name: str, category: str) -> str:
    """Enhance alt text with SEO keywords from product context."""
    # Inject product name and category for SEO
    seo_parts = []
    if product_name.lower() not in alt_text.lower():
        seo_parts.append(product_name)
    seo_parts.append(alt_text)
    if category.lower() not in alt_text.lower() and category != "General":
        seo_parts.append(f"in {category}")
    return " - ".join(seo_parts)


def _calculate_seo_score(alt_text: str, product_name: str, category: str) -> float:
    """Calculate SEO score based on keyword presence and alt text quality."""
    score = 50.0
    if alt_text and len(alt_text) > 20:
        score += 10
    if product_name.lower() in alt_text.lower():
        score += 15
    if category.lower() in alt_text.lower():
        score += 10
    if len(alt_text) <= 125:
        score += 5
    if not alt_text.startswith(("image", "photo", "picture")):
        score += 10
    return min(100.0, score)


@router.post(
    "/products",
    response_model=EcommerceProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product for SEO alt text",
    description="Add a product with images for SEO-optimized alt text generation.",
)
async def add_product(
    request: EcommerceProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a product and generate initial alt text for its images."""
    global _product_counter
    _product_counter += 1
    product_id = _product_counter

    images = []
    for idx, url in enumerate(request.image_urls):
        try:
            alt_text, model, confidence, carbon, proc_time = await generate_alt_text(
                image_url=url,
                language="en",
                tone="formal",
                wcag_level="AAA",
            )
            seo_alt = _seo_optimize_alt(alt_text, request.product_name, request.category)
            wcag_score = 85.0 if len(alt_text) > 20 else 50.0
            seo_score = _calculate_seo_score(seo_alt, request.product_name, request.category)
        except Exception as e:
            logger.error(f"Failed to generate alt for product image {idx}: {e}")
            alt_text = None
            seo_alt = None
            wcag_score = 0.0
            seo_score = 0.0

        images.append(EcommerceProductImageResponse(
            id=product_id * 100 + idx,
            image_url=url,
            current_alt=None,
            generated_alt=alt_text,
            seo_optimized_alt=seo_alt,
            wcag_score=wcag_score,
            seo_score=seo_score,
        ))

    avg_seo = sum(i.seo_score for i in images) / len(images) if images else 0

    product = EcommerceProductResponse(
        id=product_id,
        sku=request.sku,
        product_name=request.product_name,
        category=request.category,
        seo_score=avg_seo,
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        images=[i.model_dump() for i in images],
    )

    _products[product_id] = product.model_dump()
    return product


@router.get(
    "/products",
    response_model=List[EcommerceProductResponse],
    summary="List products",
    description="List all products with their SEO alt text scores.",
)
async def list_products(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
):
    """List all products."""
    products = list(_products.values())[skip:skip + limit]
    return [EcommerceProductResponse(**p) for p in products]


@router.post(
    "/products/{product_id}/seo-alt",
    response_model=SeoAltResponse,
    summary="Regenerate SEO alt text",
    description="Regenerate SEO-optimized alt text for all product images.",
)
async def regenerate_seo_alt(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate SEO-optimized alt text for a product."""
    product = _products.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    images_processed = 0
    total_seo = 0.0

    for img in product["images"]:
        try:
            alt_text, _, _, _, _ = await generate_alt_text(
                image_url=img["image_url"],
                language="en",
                tone="formal",
                wcag_level="AAA",
            )
            seo_alt = _seo_optimize_alt(alt_text, product["product_name"], product["category"])
            seo_score = _calculate_seo_score(seo_alt, product["product_name"], product["category"])
            img["generated_alt"] = alt_text
            img["seo_optimized_alt"] = seo_alt
            img["seo_score"] = seo_score
            total_seo += seo_score
            images_processed += 1
        except Exception as e:
            logger.error(f"SEO regeneration failed for image: {e}")

    avg_seo = total_seo / images_processed if images_processed > 0 else 0
    product["seo_score"] = avg_seo

    return SeoAltResponse(
        product_id=product_id,
        images_processed=images_processed,
        avg_seo_score=avg_seo,
        message=f"SEO alt text regenerated for {images_processed} images",
    )
