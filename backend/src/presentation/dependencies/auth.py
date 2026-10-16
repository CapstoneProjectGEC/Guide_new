"""Authentication dependencies and Role-Based Access Control guards."""

from typing import Callable
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.core.errors import AuthenticationError, PermissionDeniedError
from backend.src.core.security import decode_token
from backend.src.domain.auth import AdminRole, ROLE_HIERARCHY
from backend.src.infrastructure.database.session import get_db_session
from backend.src.infrastructure.models.auth import Admin

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> Admin:
    """Extract and validate JWT access token from request Bearer header."""
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Missing Bearer authorization header.")

    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type. Expected access token.")

    admin_id = payload.get("sub")
    if not admin_id:
        raise AuthenticationError("Token missing subject identifier.")

    stmt = select(Admin).where(Admin.id == admin_id)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise AuthenticationError("Administrator account no longer exists.")

    if not admin.is_active:
        raise AuthenticationError("Administrator account is inactive.")

    return admin


def require_role(minimum_role: AdminRole) -> Callable:
    """Dependency factory enforcing minimum required administrative privilege."""

    async def role_checker(current_admin: Admin = Depends(get_current_admin)) -> Admin:
        admin_role_enum = AdminRole(current_admin.role)
        current_level = ROLE_HIERARCHY.get(admin_role_enum, 0)
        required_level = ROLE_HIERARCHY.get(minimum_role, 0)

        if current_level < required_level:
            raise PermissionDeniedError(
                f"Insufficient privileges. Operation requires {minimum_role.value} or higher."
            )
        return current_admin

    return role_checker
