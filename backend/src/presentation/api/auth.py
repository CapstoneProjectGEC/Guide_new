"""Authentication and admin account management routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.core.config import get_settings
from backend.src.core.errors import AuthenticationError
from backend.src.core.logging import get_logger
from backend.src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
    verify_password,
)
from backend.src.domain.auth import (
    AdminProfileResponse,
    AdminRole,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from backend.src.infrastructure.database.session import get_db_session
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.system import AuditLog
from backend.src.presentation.dependencies.auth import get_current_admin, require_role

logger = get_logger("presentation.api.auth")
router = APIRouter(prefix="/auth", tags=["Admin Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate administrator, write audit trail, and issue rotating JWT tokens."""
    settings = get_settings()
    ip_addr = request.client.host if request.client else None

    stmt = select(Admin).where(
        or_(Admin.username == payload.username, Admin.email == payload.username)
    )
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(payload.password, admin.password_hash):
        # Log failed attempt in audit log
        audit = AuditLog(
            action="ADMIN_LOGIN_FAILED",
            resource_type="auth",
            resource_id=None,
            payload={"attempted_username": payload.username},
            ip_address=ip_addr,
        )
        session.add(audit)
        await session.commit()
        logger.warning("admin_login_failed", username=payload.username, ip=ip_addr)
        raise AuthenticationError("Invalid administrative credentials.")

    if not admin.is_active:
        logger.warning("admin_account_inactive", username=admin.username)
        raise AuthenticationError("Administrative account is inactive.")

    # Generate JWT token pair
    token_claims = {"sub": admin.id, "username": admin.username, "role": admin.role}
    access_token = create_access_token(token_claims)
    refresh_token = create_refresh_token(token_claims)

    # Record successful login in audit log
    audit = AuditLog(
        admin_id=admin.id,
        action="ADMIN_LOGIN_SUCCESS",
        resource_type="auth",
        resource_id=admin.id,
        payload={"username": admin.username, "role": admin.role},
        ip_address=ip_addr,
    )
    session.add(audit)
    await session.commit()

    logger.info("admin_login_success", username=admin.username, role=admin.role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=admin.role,
        username=admin.username,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Validate refresh token and issue rotated access and refresh token pair."""
    settings = get_settings()
    claims = decode_token(payload.refresh_token)

    if claims.get("type") != "refresh":
        raise AuthenticationError("Invalid token type. Expected refresh token.")

    admin_id = claims.get("sub")
    stmt = select(Admin).where(Admin.id == admin_id)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin or not admin.is_active:
        raise AuthenticationError("Administrator account no longer active.")

    token_claims = {"sub": admin.id, "username": admin.username, "role": admin.role}
    new_access_token = create_access_token(token_claims)
    new_refresh_token = create_refresh_token(token_claims)

    # Invalidate rotated refresh token server-side
    if claims.get("jti"):
        revoke_token(claims["jti"])

    audit = AuditLog(
        admin_id=admin.id,
        action="TOKEN_ROTATED",
        resource_type="auth",
        resource_id=admin.id,
        payload={"username": admin.username},
    )
    session.add(audit)
    await session.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=admin.role,
        username=admin.username,
    )


@router.post("/logout")
async def logout(
    request: Request,
    payload: RefreshTokenRequest | None = None,
    current_admin: Admin = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Log out administrator, invalidate active tokens server-side, and record audit event."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        access_tok = auth_header[7:].strip()
        try:
            acc_claims = decode_token(access_tok, check_revocation=False)
            if acc_claims.get("jti"):
                revoke_token(acc_claims["jti"])
        except Exception:
            pass

    if payload and payload.refresh_token:
        try:
            ref_claims = decode_token(payload.refresh_token, check_revocation=False)
            if ref_claims.get("jti"):
                revoke_token(ref_claims["jti"])
        except Exception:
            pass

    audit = AuditLog(
        admin_id=current_admin.id,
        action="ADMIN_LOGOUT",
        resource_type="auth",
        resource_id=current_admin.id,
        payload={"username": current_admin.username},
    )
    session.add(audit)
    await session.commit()
    logger.info("admin_logged_out", username=current_admin.username)
    return {"message": "Administrator logged out successfully."}


@router.get("/me", response_model=AdminProfileResponse)
async def get_my_profile(
    current_admin: Admin = Depends(get_current_admin),
) -> AdminProfileResponse:
    """Return authenticated administrator profile."""
    return AdminProfileResponse(
        id=current_admin.id,
        username=current_admin.username,
        email=current_admin.email,
        role=current_admin.role,
        is_active=current_admin.is_active,
        created_at=current_admin.created_at.isoformat(),
    )


@router.get("/curator-zone")
async def get_curator_zone(
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
) -> dict[str, str | bool]:
    """Endpoint guarded by SITE_CURATOR role or higher."""
    return {"authorized": True, "user": current_admin.username, "role": current_admin.role}
