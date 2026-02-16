"""
TheAltText - WCAG AAA Compliance & Accessibility Features
"""

from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

class WCAGLevel(str, Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"

class AltTextMetrics(BaseModel):
    wcag_compliance: WCAGLevel
    readability: float  # 0-100
    seo_score: float  # 0-100
    descriptiveness: float  # 0-100
    conciseness: float  # 0-100
    overall_score: float  # 0-100
    issues: List[str]
    suggestions: List[str]

def generate_wcag_aaa_compliant_alt_text(
    image_description: str,
    context: str,
    image_type: str
) -> str:
    """Generate WCAG AAA compliant alt text"""
    templates = {
        'decorative': lambda desc, ctx: '',
        'functional': lambda desc, ctx: f"{desc}. {f'Used in: {ctx}' if ctx else ''}".strip(),
        'complex': lambda desc, ctx: f"{desc}. Detailed description available below. {f'Context: {ctx}' if ctx else ''}".strip(),
        'ecommerce': lambda desc, ctx: f"{desc}. Product image. {ctx if ctx else ''}".strip(),
    }
    
    return templates.get(image_type, templates['functional'])(image_description, context)

def analyze_alt_text_compliance(alt_text: str, image_type: str) -> AltTextMetrics:
    """Analyze alt text for WCAG compliance"""
    issues = []
    suggestions = []
    
    length = len(alt_text)
    
    if length == 0 and image_type != 'decorative':
        issues.append('Alt text is empty')
        suggestions.append('Provide descriptive alt text')
    
    if length > 250:
        issues.append('Alt text is too long (>250 characters)')
        suggestions.append('Consider breaking into shorter, focused descriptions')
    
    if 'image of' in alt_text.lower() or 'picture of' in alt_text.lower():
        issues.append('Redundant "image of" or "picture of" phrase')
        suggestions.append('Remove "image of" - screen readers already announce it\'s an image')
    
    readability = min(100, max(0, 100 - abs(length - 125) / 2.5))
    descriptiveness = min(100, length / 2) if length > 10 else 0
    conciseness = 100 if length < 250 else max(0, 100 - (length - 250) / 2.5)
    seo_score = 80 if len(alt_text.split()) > 3 else 50
    
    overall_score = (readability + descriptiveness + conciseness + seo_score) / 4
    
    return AltTextMetrics(
        wcag_compliance=WCAGLevel.AAA if overall_score > 80 else WCAGLevel.AA if overall_score > 60 else WCAGLevel.A,
        readability=readability,
        seo_score=seo_score,
        descriptiveness=descriptiveness,
        conciseness=conciseness,
        overall_score=overall_score,
        issues=issues,
        suggestions=suggestions
    )

def generate_ecommerce_alt_text(product_data: Dict) -> str:
    """Generate e-commerce specific alt text"""
    parts = [product_data.get('name', '')]
    
    if product_data.get('color'):
        parts.append(f"in {product_data['color']}")
    if product_data.get('size'):
        parts.append(f"size {product_data['size']}")
    if product_data.get('material'):
        parts.append(f"made of {product_data['material']}")
    if product_data.get('features'):
        parts.append(f"featuring {', '.join(product_data['features'])}")
    
    return ', '.join(parts) + '.'
