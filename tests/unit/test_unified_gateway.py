"""Automated unit and integration tests for Phase 13: Unified FastAPI Client Gateway."""

import time
from unittest.mock import MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.core.config import get_settings
from backend.src.core.limiter import RateLimiter, get_rate_limiter
from backend.src.core.security import create_access_token
from backend.src.main import app
from backend.src.presentation.router import GATEWAY_TAGS_METADATA, api_v1_router


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state before and after each test."""
    limiter = get_rate_limiter()
    limiter.reset_sync()
    yield
    limiter.reset_sync()


# ---------------------------------------------------------------------------
# 1. Route Inventory & Prefix Organization Tests
# ---------------------------------------------------------------------------


def test_unified_gateway_route_inventory():
    """Verify all tourist, voice, translation, and admin routes are organized under /api/v1."""
    routes = set(app.openapi()["paths"].keys())
    for r in app.routes:
        if hasattr(r, "path"):
            routes.add(r.path)

    # Health probes
    assert "/api/v1/health" in routes
    assert "/api/v1/health/live" in routes
    assert "/api/v1/health/ready" in routes
    assert "/health" in routes  # Root orchestrator alias

    # Tourist chat & voice endpoints (Zero-auth)
    assert "/api/v1/chat/message" in routes
    assert "/api/v1/chat/stream" in routes
    assert "/api/v1/chat/sessions" in routes
    assert "/api/v1/voice/info" in routes
    assert "/api/v1/voice/transcribe" in routes
    assert "/api/v1/voice/chat" in routes
    assert "/api/v1/voice/stream" in routes
    assert "/api/v1/voice/synthesize" in routes
    assert "/api/v1/voice/tts/status" in routes
    assert "/api/v1/voice/tts/voices" in routes

    # Translation endpoints
    assert "/api/v1/translation/status" in routes
    assert "/api/v1/translation/normalize" in routes
    assert "/api/v1/translation/sync" in routes

    # Admin authentication & RBAC endpoints
    assert "/api/v1/auth/login" in routes
    assert "/api/v1/auth/refresh" in routes
    assert "/api/v1/auth/logout" in routes
    assert "/api/v1/auth/me" in routes

    # Admin management endpoints
    assert "/api/v1/admin/documents" in routes
    assert "/api/v1/admin/knowledge/generations" in routes
    assert "/api/v1/admin/diagnostics/retrieval" in routes
    assert "/api/v1/admin/sync/voice" in routes
    assert "/api/v1/admin/sync/translation" in routes
    assert "/api/v1/admin/sync/status" in routes


# ---------------------------------------------------------------------------
# 2. OpenAPI Schema & Documentation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openapi_schema_generation():
    """Verify /openapi.json contains comprehensive metadata, tags, and security schemes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()

        assert "openapi" in schema
        assert schema["info"]["title"] == app.title
        assert "Belur Chennakeshava Temple" in schema["info"]["description"]

        # Security scheme
        components = schema.get("components", {})
        sec_schemes = components.get("securitySchemes", {})
        assert "BearerAuth" in sec_schemes
        assert sec_schemes["BearerAuth"]["scheme"] == "bearer"
        assert sec_schemes["BearerAuth"]["bearerFormat"] == "JWT"

        # Tag groups
        tag_names = [t["name"] for t in schema.get("tags", [])]
        expected_tags = [
            "System Health",
            "Tourist Chat",
            "Tourist Voice",
            "Translation & Cross-Lingual",
            "Admin Authentication",
            "Admin Documents",
            "Admin Knowledge Pipeline",
            "Admin Diagnostics",
            "Admin Management",
        ]
        for tag in expected_tags:
            assert tag in tag_names


# ---------------------------------------------------------------------------
# 3. Tourist Rate Limiting Tests (60 RPM Default)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tourist_rate_limit_enforcement(monkeypatch):
    """Verify anonymous tourist requests enforce configured limit and return 429 when exceeded."""
    limiter = get_rate_limiter()
    # Set limit to 3 for fast test execution
    monkeypatch.setattr(limiter, "tourist_rpm", 3)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Requests 1, 2, 3 must succeed
        for i in range(3):
            resp = await client.get("/api/v1/voice/tts/status")
            assert resp.status_code == 200
            assert resp.headers["x-ratelimit-limit"] == "3"
            assert resp.headers["x-ratelimit-remaining"] == str(2 - i)

        # Request 4 must be rate-limited (HTTP 429)
        resp4 = await client.get("/api/v1/voice/tts/status")
        assert resp4.status_code == 429
        assert resp4.headers["x-ratelimit-remaining"] == "0"
        assert "retry-after" in resp4.headers
        retry_after = int(resp4.headers["retry-after"])
        assert retry_after >= 1

        payload = resp4.json()
        assert payload["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert payload["error"]["details"]["client_type"] == "tourist"
        assert payload["error"]["details"]["limit_requests_per_minute"] == 3


# ---------------------------------------------------------------------------
# 4. Admin Rate Limiting Tests (120 RPM Default)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_rate_limit_higher_quota(monkeypatch):
    """Verify authenticated admin receives higher quota and is not capped at tourist limit."""
    limiter = get_rate_limiter()
    # Configure 2 for tourist, 5 for admin
    monkeypatch.setattr(limiter, "tourist_rpm", 2)
    monkeypatch.setattr(limiter, "admin_rpm", 5)

    admin_token = create_access_token(
        data={"sub": "admin_uuid_123", "role": "SITE_CURATOR", "username": "curator_test"}
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Requests 1, 2, 3, 4, 5 should succeed (exceeding tourist limit of 2)
        for i in range(5):
            resp = await client.get("/api/v1/voice/tts/status", headers=headers)
            assert resp.status_code == 200
            assert resp.headers["x-ratelimit-limit"] == "5"

        # Request 6 must trigger admin rate limit
        resp6 = await client.get("/api/v1/voice/tts/status", headers=headers)
        assert resp6.status_code == 429
        payload = resp6.json()
        assert payload["error"]["details"]["client_type"] == "admin"
        assert payload["error"]["details"]["limit_requests_per_minute"] == 5


# ---------------------------------------------------------------------------
# 5. Security & Anti-Spoofing Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spoofed_admin_role_headers_ignored(monkeypatch):
    """Verify attacker cannot elevate rate limit by injecting spoofed role headers."""
    limiter = get_rate_limiter()
    monkeypatch.setattr(limiter, "tourist_rpm", 2)
    monkeypatch.setattr(limiter, "admin_rpm", 10)

    # Attacker passes spoofed role headers without valid Bearer token
    spoofed_headers = {
        "X-Admin-Role": "SUPER_ADMIN",
        "X-Role": "admin",
        "X-User-Type": "admin",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1st and 2nd pass
        r1 = await client.get("/api/v1/voice/tts/status", headers=spoofed_headers)
        assert r1.status_code == 200
        r2 = await client.get("/api/v1/voice/tts/status", headers=spoofed_headers)
        assert r2.status_code == 200

        # 3rd is blocked because tourist quota (2) applies, not admin quota (10)
        r3 = await client.get("/api/v1/voice/tts/status", headers=spoofed_headers)
        assert r3.status_code == 429
        assert r3.json()["error"]["details"]["client_type"] == "tourist"


@pytest.mark.asyncio
async def test_untrusted_forwarded_for_ignored(monkeypatch):
    """Verify X-Forwarded-For is ignored when request arrives from an untrusted client IP."""
    limiter = get_rate_limiter()
    monkeypatch.setattr(limiter, "tourist_rpm", 2)
    # Configure untrusted proxy list that does NOT include 192.168.1.50
    monkeypatch.setattr(limiter, "trusted_proxies", {"10.0.0.1"})

    mock_req = MagicMock()
    mock_req.method = "GET"
    mock_req.url.path = "/api/v1/chat/message"
    mock_req.headers = {
        "X-Forwarded-For": "203.0.113.195",  # Spoofed public IP
    }
    mock_req.client.host = "192.168.1.50"  # Direct untrusted peer

    client_key, client_type, limit = limiter.extract_client_identifier(mock_req)
    # Must use peer socket IP (192.168.1.50), NOT the spoofed header (203.0.113.195)
    assert client_key == "tourist:192.168.1.50"
    assert client_type == "tourist"


@pytest.mark.asyncio
async def test_trusted_forwarded_for_respected(monkeypatch):
    """Verify X-Forwarded-For is respected when request arrives from a configured trusted proxy."""
    limiter = get_rate_limiter()
    monkeypatch.setattr(limiter, "trusted_proxies", {"127.0.0.1"})

    mock_req = MagicMock()
    mock_req.method = "GET"
    mock_req.url.path = "/api/v1/chat/message"
    mock_req.headers = {
        "X-Forwarded-For": "198.51.100.42, 127.0.0.1",
    }
    mock_req.client.host = "127.0.0.1"  # Trusted proxy

    client_key, client_type, limit = limiter.extract_client_identifier(mock_req)
    assert client_key == "tourist:198.51.100.42"


# ---------------------------------------------------------------------------
# 6. Exemption, Cleanup, and Monotonic Clock Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_and_docs_endpoints_exempt_from_rate_limits(monkeypatch):
    """Verify /health and /openapi.json are never rate-limited even under high traffic."""
    limiter = get_rate_limiter()
    monkeypatch.setattr(limiter, "tourist_rpm", 1)  # Strict limit of 1

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Multiple requests to health and openapi.json must never return 429
        for _ in range(5):
            h_resp = await client.get("/api/v1/health")
            assert h_resp.status_code == 200
            assert "x-ratelimit-limit" not in h_resp.headers

            root_h = await client.get("/health")
            assert root_h.status_code == 200

            doc_resp = await client.get("/openapi.json")
            assert doc_resp.status_code == 200


@pytest.mark.asyncio
async def test_limiter_window_expiration():
    """Verify rate limit window expires and allows new requests after elapsed duration."""
    limiter = RateLimiter()
    limiter.tourist_rpm = 1
    limiter.window_seconds = 1  # 1 second window

    mock_req = MagicMock()
    mock_req.method = "GET"
    mock_req.url.path = "/api/v1/chat/message"
    mock_req.headers = {}
    mock_req.client.host = "127.0.0.1"

    # First request allowed
    res1 = await limiter.check_rate_limit(mock_req)
    assert res1.is_allowed is True

    # Immediate second request blocked
    res2 = await limiter.check_rate_limit(mock_req)
    assert res2.is_allowed is False

    # Wait for window to expire
    time.sleep(1.05)

    # Third request allowed after expiration
    res3 = await limiter.check_rate_limit(mock_req)
    assert res3.is_allowed is True


# ---------------------------------------------------------------------------
# 7. Gateway Streaming & Binary Audio Compatibility Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gateway_sse_stream_compatibility():
    """Verify Server-Sent Events stream passes cleanly through gateway middleware without buffering."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chat/stream",
            json={"content": "Who built the temple?", "preferred_language": "en"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        assert resp.headers.get("x-accel-buffering") == "no"
        # Rate limit header is present on logical request
        assert "x-ratelimit-limit" in resp.headers


@pytest.mark.asyncio
async def test_gateway_audio_wav_compatibility(monkeypatch):
    """Verify audio synthesis WAV binary stream and headers pass cleanly through gateway."""
    mock_wav = b"RIFF" + b"\x00" * 40
    service = app.state.tts_service if hasattr(app.state, "tts_service") else None

    with patch("backend.src.presentation.api.voice.get_tts_service") as mock_get_tts:
        mock_svc = MagicMock()
        from backend.src.domain.voice import SynthesisMetadata
        mock_svc.synthesize = AsyncMock = MagicMock()

        async def fake_synthesize(req):
            return mock_wav, SynthesisMetadata(
                duration_seconds=0.5,
                sample_rate=22050,
                audio_format="wav",
                audio_bytes_length=len(mock_wav),
                latency_ms=10,
                cached=False,
                engine="piper",
                voice="en_US-lessac-medium",
                language="en",
                client_fallback_recommended=False,
            )

        mock_svc.synthesize.side_effect = fake_synthesize
        mock_get_tts.return_value = mock_svc

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/voice/synthesize",
                json={"text": "Test audio through gateway", "language": "en"},
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/wav"
            assert resp.headers["x-tts-engine"] == "piper"
            assert "x-ratelimit-limit" in resp.headers


# ---------------------------------------------------------------------------
# 8. Admin Management Synchronization Security Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_sync_endpoints_require_authentication():
    """Verify /api/v1/admin/sync endpoints reject unauthenticated access with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Voice sync without auth -> 401
        r_voice = await client.post("/api/v1/admin/sync/voice")
        assert r_voice.status_code == 401
        assert r_voice.json()["error"]["code"] == "UNAUTHORIZED"

        # 2. Translation sync without auth -> 401
        r_trans = await client.post("/api/v1/admin/sync/translation")
        assert r_trans.status_code == 401
        assert r_trans.json()["error"]["code"] == "UNAUTHORIZED"

        # 3. Status without auth -> 401
        r_status = await client.get("/api/v1/admin/sync/status")
        assert r_status.status_code == 401
        assert r_status.json()["error"]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# 9. CORS Policy & Credential Security Tests
# ---------------------------------------------------------------------------


def test_cors_policy_rejects_wildcard_with_credentials():
    """Verify security constraint: wildcard origins cannot be used with credentialed access."""
    settings = get_settings()
    # Default settings has specific localhost origins, not wildcard
    assert "*" not in settings.CORS_ORIGINS
    assert settings.cors_allow_credentials is True
