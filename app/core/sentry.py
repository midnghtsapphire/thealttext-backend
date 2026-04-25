"""
Sentry Error Tracking Configuration
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

def init_sentry(dsn: str | None = None, environment: str = "production"):
    """Initialize Sentry error tracking"""
    if not dsn:
        return
    
    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            FastApiIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=environment,
        # Filter out health check errors
        before_send=lambda event, hint: None if "/health" in event.get("request", {}).get("url", "") else event,
    )
