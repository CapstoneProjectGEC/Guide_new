"""Unit tests for Phase 2 - Backend Foundation."""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.src.core.config import Settings
from backend.src.core.errors import NotFoundError
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_check_returns_200():
    """Verify GET /api/v1/health returns HTTP 200 with required schema."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["profile"] in ["dev", "standalone", "cloud"]
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert data["components"]["api"] == "healthy"


@pytest.mark.asyncio
async def test_correlation_id_generated_when_missing():
    """Verify X-Correlation-ID is generated and returned when not supplied by client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    cid = response.headers.get("X-Correlation-ID")
    assert cid is not None
    assert len(cid) > 10
    assert "X-Process-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_correlation_id_preserved_when_supplied():
    """Verify client-supplied X-Correlation-ID passes through cleanly."""
    custom_cid = "client-trace-12345"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health", headers={"X-Correlation-ID": custom_cid})

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == custom_cid


@pytest.mark.asyncio
async def test_domain_exception_returns_standard_envelope():
    """Verify domain exceptions are formatted into standard ErrorEnvelope."""
    # Temporarily attach test route throwing NotFoundError
    @app.get("/api/v1/test-error")
    async def trigger_error():
        raise NotFoundError("The requested temple monument was not found.", details={"id": "belur-404"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/test-error")

    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    err = body["error"]
    assert err["code"] == "NOT_FOUND"
    assert err["message"] == "The requested temple monument was not found."
    assert err["details"]["id"] == "belur-404"
    assert "correlation_id" in err


def test_settings_defaults():
    """Verify Settings object initialization and default properties."""
    settings = Settings()
    assert settings.APP_NAME == "AI-Powered Smart Tourist Guide Platform for Karnataka"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.API_PREFIX == "/api/v1"
    assert settings.APP_PROFILE in ["dev", "standalone", "cloud"]
