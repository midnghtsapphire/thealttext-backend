# TheAltText Backend

**AI-Powered Alt Text Generator — FastAPI Server**

A [GlowStarLabs](https://glowstarlabs.com) product by [Audrey Evans](https://meetaudreyevans.com)

---

## Overview

TheAltText Backend is a fully standalone FastAPI application that powers AI-driven WCAG-compliant alt text generation. It connects to OpenRouter for vision AI models, PostgreSQL 16 for data persistence, Stripe for billing, and Redis for task queuing.

## Features

| Feature | Description |
|---|---|
| **AI Alt Text Generation** | Free-first model stack with automatic fallback to paid models |
| **Bulk Processing API** | Process up to 100 images in a single batch request |
| **E-commerce SEO Optimization** | Product catalog with SEO-optimized alt text generation |
| **Multi-Language Alt Text** | 14+ languages with auto-detect locale support |
| **Webhook Notifications** | Register endpoints for event-driven notifications with HMAC signing |
| **API Key Management** | B2B API keys with usage tracking and rate limiting |
| **Competitor Comparison Tool** | Compare your alt text compliance against any competitor |
| **Website Scanner** | Crawl websites to audit image accessibility (1-5 pages deep) |
| **Compliance Reports** | Generate and export reports in JSON, CSV, or PDF |
| **Stripe Dual-Mode Billing** | Test/live mode toggle with separate key sets |
| **Carbon Tracking** | Monitor environmental impact of AI operations |
| **WCAG Analysis** | Score existing alt text against WCAG A/AA/AAA standards |

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.109 |
| Runtime | Python 3.11 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| AI | OpenRouter (Gemini, LLaMA, GPT-4.1) |
| Payments | Stripe (dual test/live mode) |
| Task Queue | Celery + Redis 7 |
| Auth | JWT (python-jose) + bcrypt |
| HTTP Client | httpx (async) |
| Reports | WeasyPrint + Jinja2 |
| Containerization | Docker + Docker Compose |

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Redis 7 (optional, for task queue)
- OpenRouter API key

### Development

```bash
# Clone the repo
git clone https://github.com/MIDNGHTSAPPHIRE/thealttext-backend.git
cd thealttext-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your keys

# Run database migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs at `http://localhost:8000/api/docs`

### Docker

```bash
# Copy environment config
cp .env.example .env
# Edit .env with your keys

# Build and run (includes PostgreSQL 16 + Redis)
docker compose up --build

# Or build manually
docker build -t thealttext-backend .
docker run -p 8000:8000 --env-file .env thealttext-backend
```

## API Endpoints

### Core

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and get JWT token |
| GET | `/api/auth/me` | Get current user profile |
| POST | `/api/images/analyze-url` | Generate alt text from URL |
| POST | `/api/images/analyze` | Generate alt text from file upload |
| POST | `/api/scanner/scan` | Scan a website for accessibility |
| GET | `/api/reports/` | List compliance reports |
| GET | `/api/dashboard/stats` | Get dashboard statistics |

### Blue Ocean

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/bulk/process` | Bulk process up to 100 images |
| GET | `/api/bulk/status/{job_id}` | Check bulk job status |
| POST | `/api/ecommerce/products` | Add product for SEO alt text |
| POST | `/api/ecommerce/products/{id}/seo-alt` | Regenerate SEO alt text |
| POST | `/api/webhooks/` | Register a webhook endpoint |
| POST | `/api/webhooks/{id}/test` | Test a webhook |
| GET | `/api/webhooks/events` | List supported events |
| POST | `/api/competitor/compare` | Compare alt text vs competitor |
| GET | `/api/gallery` | Browse processed images |
| POST | `/api/developer/v1/alt-text` | Public API (X-API-Key auth) |

### Billing

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/billing/checkout` | Create Stripe checkout session |
| GET | `/api/billing/subscription` | Get subscription status |
| POST | `/api/billing/cancel` | Cancel subscription |

## Stripe Dual-Mode Billing

The backend supports both Stripe **test** and **live** modes via `STRIPE_MODE`:

```env
# Toggle mode
STRIPE_MODE=test  # or "live"

# Test keys
STRIPE_TEST_SECRET_KEY=sk_test_xxxx
STRIPE_TEST_PUBLISHABLE_KEY=pk_test_xxxx
STRIPE_TEST_WEBHOOK_SECRET=whsec_test_xxxx
STRIPE_TEST_PRO_PRICE_ID=price_test_xxxx
STRIPE_TEST_ENTERPRISE_PRICE_ID=price_test_xxxx

# Live keys
STRIPE_LIVE_SECRET_KEY=sk_live_xxxx
STRIPE_LIVE_PUBLISHABLE_KEY=pk_live_xxxx
STRIPE_LIVE_WEBHOOK_SECRET=whsec_live_xxxx
STRIPE_LIVE_PRO_PRICE_ID=price_live_xxxx
STRIPE_LIVE_ENTERPRISE_PRICE_ID=price_live_xxxx
```

The health endpoint reports the active Stripe mode.

## Webhook Events

Register webhooks to receive notifications for:

| Event | Description |
|---|---|
| `alt_text.generated` | Alt text successfully generated |
| `alt_text.failed` | Alt text generation failed |
| `bulk.started` | Bulk processing job started |
| `bulk.completed` | Bulk processing job completed |
| `scan.started` | Website scan started |
| `scan.completed` | Website scan completed |
| `subscription.created` | New subscription created |
| `subscription.canceled` | Subscription canceled |
| `api_key.created` | New API key generated |
| `api_key.revoked` | API key revoked |

Webhooks include HMAC-SHA256 signatures via `X-TheAltText-Signature` header.

## Project Structure

```
thealttext-backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py          # Authentication
│   │       ├── images.py        # Image analysis
│   │       ├── scanner.py       # Website scanner
│   │       ├── reports.py       # Compliance reports
│   │       ├── dashboard.py     # Dashboard stats
│   │       ├── billing.py       # Stripe billing
│   │       ├── developer.py     # API key management
│   │       ├── bulk.py          # Bulk processing
│   │       ├── ecommerce.py     # E-commerce SEO
│   │       ├── webhooks.py      # Webhook notifications
│   │       ├── competitor.py    # Competitor comparison
│   │       └── gallery.py       # Image gallery
│   ├── core/
│   │   ├── config.py            # Settings (Stripe dual-mode)
│   │   ├── database.py          # PostgreSQL async engine
│   │   └── security.py          # JWT auth
│   ├── models/                  # SQLAlchemy models
│   ├── schemas/                 # Pydantic schemas
│   ├── services/
│   │   ├── ai_vision.py         # OpenRouter AI
│   │   ├── billing.py           # Stripe service
│   │   └── scanner.py           # Web scanner
│   └── utils/
│       └── carbon.py            # Carbon tracking
├── alembic/                     # Database migrations
├── tests/                       # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## License

Proprietary — GlowStarLabs / Audrey Evans

## Links

- **Hub**: [meetaudreyevans.com](https://meetaudreyevans.com)
- **Frontend**: [thealttext-frontend](https://github.com/MIDNGHTSAPPHIRE/thealttext-frontend)
- **Original**: [thealttext](https://github.com/MIDNGHTSAPPHIRE/thealttext)
