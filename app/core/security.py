"""
Security middleware and utilities for injection prevention.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import re


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request, call_next) -> Response:
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Other security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        return response


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS/injection."""
    if not text:
        return ""
    
    # Remove potential SQL injection characters
    dangerous_patterns = [
        r"['\";--]",  # SQL injection chars
        r"<script",   # XSS attempt
        r"javascript:",  # XSS attempt
        r"on\w+=",   # Event handlers
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    return text.strip()


def validate_file_type(filename: str, allowed_types: list[str]) -> bool:
    """Validate file type to prevent malicious uploads."""
    allowed_extensions = {t.lower().lstrip(".") for t in allowed_types}
    
    if "." not in filename:
        return False
    
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in allowed_extensions


def validate_file_size(size: int, max_size_mb: int = 10) -> bool:
    """Validate file size."""
    return size <= max_size_mb * 1024 * 1024
