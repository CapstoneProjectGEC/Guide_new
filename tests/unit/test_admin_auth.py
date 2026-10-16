"""Unit and integration tests for Phase 4: Admin Authentication & RBAC."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from backend.src.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.system import AuditLog
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_test_admin(role: str = "SUPER_ADMIN", password: str = "SuperSecret123!") -> Admin:
    """Helper to seed an admin record for testing."""
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    admin = Admin(
        username=f"admin_{uid}",
        email=f"admin_{uid}@karnatakagov.in",
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin


async def delete_test_admin(admin_id: str) -> None:
    """Helper to remove a test admin."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(Admin).where(Admin.id == admin_id)
        res = await session.execute(stmt)
        obj = res.scalar_one_or_none()
        if obj:
            await session.delete(obj)
            await session.commit()


def test_argon2id_hashing_and_verification():
    """Verify Argon2id password hashing strength and verification logic."""
    raw_pwd = "BelurHeritagePassword2026!"
    hashed = hash_password(raw_pwd)

    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False


def test_jwt_token_lifecycle():
    """Verify JWT access token creation and decoding."""
    payload = {"sub": "test-admin-uuid", "role": "OPERATOR"}
    token = create_access_token(payload)

    decoded = decode_token(token)
    assert decoded["sub"] == "test-admin-uuid"
    assert decoded["role"] == "OPERATOR"
    assert decoded["type"] == "access"
    assert "exp" in decoded
    assert "jti" in decoded


@pytest.mark.asyncio
async def test_admin_login_success_and_audit():
    """Verify valid login returns token pair and generates an audit record."""
    raw_password = "ValidPassword123!"
    admin = await create_test_admin(role="SUPER_ADMIN", password=raw_password)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": admin.username, "password": raw_password},
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["role"] == "SUPER_ADMIN"
        assert data["token_type"] == "bearer"

        # Verify audit log record
        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = (
                select(AuditLog)
                .where(AuditLog.admin_id == admin.id, AuditLog.action == "ADMIN_LOGIN_SUCCESS")
                .order_by(AuditLog.created_at.desc())
            )
            res = await session.execute(stmt)
            audit_entry = res.scalar_one_or_none()
            assert audit_entry is not None
            assert audit_entry.action == "ADMIN_LOGIN_SUCCESS"
    finally:
        await delete_test_admin(admin.id)


@pytest.mark.asyncio
async def test_admin_login_failure_and_audit():
    """Verify invalid login returns HTTP 401 and records failed audit event."""
    transport = ASGITransport(app=app)
    bad_username = f"nonexistent_{uuid.uuid4().hex[:6]}"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": bad_username, "password": "WrongPassword999!"},
        )

    assert response.status_code == 401
    err = response.json()["error"]
    assert err["code"] == "UNAUTHORIZED"

    # Verify failed audit log
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == "ADMIN_LOGIN_FAILED")
            .order_by(AuditLog.created_at.desc())
        )
        res = await session.execute(stmt)
        audit_entry = res.scalars().first()
        assert audit_entry is not None
        assert audit_entry.payload["attempted_username"] == bad_username


@pytest.mark.asyncio
async def test_token_refresh_rotation():
    """Verify rotating refresh token exchange."""
    raw_password = "RotatePassword123!"
    admin = await create_test_admin(role="SITE_CURATOR", password=raw_password)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_res = await client.post(
                "/api/v1/auth/login",
                json={"username": admin.username, "password": raw_password},
            )
            refresh_tok = login_res.json()["refresh_token"]

            refresh_res = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_tok},
            )

        assert refresh_res.status_code == 200
        rotated_data = refresh_res.json()
        assert "access_token" in rotated_data
        assert "refresh_token" in rotated_data
        assert rotated_data["refresh_token"] != refresh_tok
    finally:
        await delete_test_admin(admin.id)


@pytest.mark.asyncio
async def test_role_based_access_control():
    """Verify RBAC role hierarchy enforcement using /api/v1/auth/curator-zone."""
    pwd = "RbacPassword123!"
    super_admin = await create_test_admin(role="SUPER_ADMIN", password=pwd)
    viewer_admin = await create_test_admin(role="VIEWER", password=pwd)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Login as VIEWER
            v_login = await client.post(
                "/api/v1/auth/login",
                json={"username": viewer_admin.username, "password": pwd},
            )
            v_token = v_login.json()["access_token"]

            # Attempt to access curator gate with VIEWER token -> Expect 403 Forbidden
            v_access = await client.get(
                "/api/v1/auth/curator-zone",
                headers={"Authorization": f"Bearer {v_token}"},
            )
            assert v_access.status_code == 403
            assert v_access.json()["error"]["code"] == "FORBIDDEN"

            # 2. Login as SUPER_ADMIN
            s_login = await client.post(
                "/api/v1/auth/login",
                json={"username": super_admin.username, "password": pwd},
            )
            s_token = s_login.json()["access_token"]

            # Attempt to access curator gate with SUPER_ADMIN token -> Expect 200 OK
            s_access = await client.get(
                "/api/v1/auth/curator-zone",
                headers={"Authorization": f"Bearer {s_token}"},
            )
            assert s_access.status_code == 200
            assert s_access.json()["authorized"] is True
    finally:
        await delete_test_admin(super_admin.id)
        await delete_test_admin(viewer_admin.id)


@pytest.mark.asyncio
async def test_tourist_public_endpoints_require_zero_auth():
    """Verify public endpoints remain completely open with zero authentication headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
