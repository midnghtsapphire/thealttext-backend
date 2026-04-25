"""
Rate Limiting Middleware
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter with IP-based rate limiting
limiter = Limiter(key_func=get_remote_address)

# Default rate limits
DEFAULT_RATE_LIMIT = "10/minute"
AUTH_RATE_LIMIT = "5/minute"
GENERATE_RATE_LIMIT = "20/minute"
