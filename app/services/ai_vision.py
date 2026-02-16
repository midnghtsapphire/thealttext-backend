"""
TheAltText — AI Vision Service
OpenRouter integration with free-first model stack.
Tries free models first, escalates to paid only when needed.
"""

import base64
import time
import logging
from typing import Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Estimated carbon cost per API call in milligrams CO2
CARBON_COST_PER_CALL = {
    "free": 0.5,
    "paid": 2.0,
}

TONE_PROMPTS = {
    "formal": "Use formal, professional language suitable for corporate or government websites.",
    "casual": "Use casual, friendly language suitable for blogs and social media.",
    "technical": "Use precise technical language with specific details about visual elements.",
    "simple": "Use simple, clear language at a 6th-grade reading level. Avoid jargon.",
}

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "es": "Respond in Spanish (Español).",
    "fr": "Respond in French (Français).",
    "de": "Respond in German (Deutsch).",
    "pt": "Respond in Portuguese (Português).",
    "ja": "Respond in Japanese (日本語).",
    "ko": "Respond in Korean (한국어).",
    "zh": "Respond in Chinese (中文).",
    "ar": "Respond in Arabic (العربية).",
    "hi": "Respond in Hindi (हिन्दी).",
    "it": "Respond in Italian (Italiano).",
    "nl": "Respond in Dutch (Nederlands).",
    "ru": "Respond in Russian (Русский).",
    "haw": "Respond in Hawaiian (ʻŌlelo Hawaiʻi).",
}


def _build_system_prompt(language: str, tone: str, wcag_level: str, context: Optional[str] = None) -> str:
    """Build the system prompt for alt text generation."""
    lang_instruction = LANGUAGE_INSTRUCTIONS.get(language, f"Respond in the language with ISO code: {language}.")
    tone_instruction = TONE_PROMPTS.get(tone, TONE_PROMPTS["formal"])

    prompt = f"""You are TheAltText, an expert accessibility specialist that generates WCAG {wcag_level} compliant alt text for images.

Your task: Generate a single, concise, descriptive alt text for the provided image.

Rules:
1. {lang_instruction}
2. {tone_instruction}
3. WCAG {wcag_level} compliance requirements:
   - Describe the meaningful content and function of the image
   - Keep alt text between 50-150 characters for most images
   - For complex images (charts, infographics), provide detailed descriptions up to 250 characters
   - Do NOT start with "Image of" or "Picture of" — describe the content directly
   - If the image is decorative, respond with exactly: ""
   - Include relevant colors, text, actions, and spatial relationships
4. Be specific: "Golden retriever catching a red frisbee in a park" not "Dog playing"
5. Include text visible in the image
6. Describe the emotional tone or mood when relevant
7. For product images, include key product details

{f"Additional context: {context}" if context else ""}

Respond with ONLY the alt text string. No quotes, no explanation, no prefix."""

    return prompt


async def generate_alt_text(
    image_url: Optional[str] = None,
    image_base64: Optional[str] = None,
    mime_type: str = "image/jpeg",
    language: str = "en",
    tone: str = "formal",
    wcag_level: str = "AAA",
    context: Optional[str] = None,
) -> Tuple[str, Optional[str], Optional[float], float, int]:
    """
    Generate alt text for an image using OpenRouter vision models.
    Free-first strategy: tries free models, then escalates to paid.

    Returns: (alt_text, model_used, confidence_score, carbon_cost_mg, processing_time_ms)
    """
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    system_prompt = _build_system_prompt(language, tone, wcag_level, context)

    # Build image content
    if image_url:
        image_content = {"type": "image_url", "image_url": {"url": image_url}}
    elif image_base64:
        image_content = {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
        }
    else:
        raise ValueError("Either image_url or image_base64 must be provided")

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                image_content,
                {"type": "text", "text": "Generate WCAG-compliant alt text for this image."},
            ],
        },
    ]

    # Free-first model stack
    free_models = [m.strip() for m in settings.VISION_MODELS_FREE.split(",") if m.strip()]
    paid_models = [m.strip() for m in settings.VISION_MODELS_PAID.split(",") if m.strip()]
    all_models = [(m, "free") for m in free_models] + [(m, "paid") for m in paid_models]

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.BRAND_URL,
        "X-Title": settings.APP_NAME,
    }

    last_error = None
    async with httpx.AsyncClient(timeout=60.0) as client:
        for model_name, tier in all_models:
            start_time = time.time()
            try:
                logger.info(f"Trying model: {model_name} (tier: {tier})")
                response = await client.post(
                    f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json={
                        "model": model_name,
                        "messages": messages,
                        "max_tokens": 300,
                        "temperature": 0.3,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    alt_text = data["choices"][0]["message"]["content"].strip()
                    # Clean up any quotes
                    alt_text = alt_text.strip('"').strip("'")
                    processing_time = int((time.time() - start_time) * 1000)
                    carbon_cost = CARBON_COST_PER_CALL.get(tier, 1.0)
                    confidence = 0.92 if tier == "paid" else 0.85

                    logger.info(f"Success with {model_name}: {len(alt_text)} chars, {processing_time}ms")
                    return alt_text, model_name, confidence, carbon_cost, processing_time

                elif response.status_code == 429:
                    logger.warning(f"Rate limited on {model_name}, trying next model")
                    last_error = f"Rate limited: {response.text}"
                    continue
                else:
                    logger.warning(f"Error {response.status_code} from {model_name}: {response.text}")
                    last_error = f"{response.status_code}: {response.text}"
                    continue

            except Exception as e:
                logger.error(f"Exception with {model_name}: {str(e)}")
                last_error = str(e)
                continue

    raise RuntimeError(f"All vision models failed. Last error: {last_error}")


async def analyze_existing_alt_text(
    alt_text: str,
    image_url: Optional[str] = None,
    wcag_level: str = "AAA",
) -> dict:
    """
    Analyze existing alt text for WCAG compliance quality.
    Returns a compliance assessment.
    """
    issues = []
    score = 100.0

    if not alt_text or alt_text.strip() == "":
        return {
            "score": 0.0,
            "status": "missing",
            "issues": ["Alt text is completely missing"],
            "recommendation": "Add descriptive alt text that conveys the image content and purpose",
        }

    # Check common issues
    if alt_text.lower().startswith(("image of", "picture of", "photo of", "img")):
        issues.append("Starts with redundant prefix (e.g., 'Image of')")
        score -= 15

    if len(alt_text) < 10:
        issues.append(f"Too short ({len(alt_text)} chars) — may not be descriptive enough")
        score -= 25

    if len(alt_text) > 250:
        issues.append(f"Too long ({len(alt_text)} chars) — consider using longdesc for complex images")
        score -= 10

    if alt_text.lower() in ("image", "photo", "picture", "icon", "logo", "graphic", "banner", "placeholder"):
        issues.append("Generic/non-descriptive alt text")
        score -= 40

    if any(ext in alt_text.lower() for ext in (".jpg", ".png", ".gif", ".svg", ".webp", ".bmp")):
        issues.append("Contains filename instead of description")
        score -= 50

    if alt_text == alt_text.upper() and len(alt_text) > 5:
        issues.append("All uppercase text — poor readability for screen readers")
        score -= 10

    score = max(0.0, score)
    status = "compliant" if score >= 80 else "poor" if score >= 40 else "non_compliant"

    return {
        "score": round(score, 1),
        "status": status,
        "issues": issues if issues else ["Alt text meets basic compliance standards"],
        "recommendation": (
            "Alt text is acceptable" if score >= 80
            else "Consider improving alt text to better describe the image content"
        ),
    }
