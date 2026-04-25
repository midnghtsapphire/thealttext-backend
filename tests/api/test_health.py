"""
Tests for Health Endpoints
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    """Test basic health endpoint"""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_liveness_check(client):
    """Test liveness probe"""
    response = await client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_check(client):
    """Test readiness probe"""
    response = await client.get("/api/health/ready")
    # May be 200 or 503 depending on DB
    assert response.status_code in [200, 503]
