###############################################################################
# TheAltText Backend — Dockerfile
# Standalone FastAPI server with PostgreSQL 16 support.
# A GlowStarLabs product by Audrey Evans
# https://meetaudreyevans.com
###############################################################################

FROM python:3.11-slim

LABEL maintainer="Audrey Evans <audrey@glowstarlabs.com>"
LABEL description="TheAltText Backend — AI-Powered Alt Text Generator API"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
