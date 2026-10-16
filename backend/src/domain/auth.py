"""Domain models, enums, and schemas for authentication and RBAC."""

from enum import Enum
from pydantic import BaseModel, Field


class AdminRole(str, Enum):
    """Role-Based Access Control roles."""

    SUPER_ADMIN = "SUPER_ADMIN"
    SITE_CURATOR = "SITE_CURATOR"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


# Numeric privilege hierarchy: higher value indicates greater privilege
ROLE_HIERARCHY: dict[AdminRole, int] = {
    AdminRole.VIEWER: 1,
    AdminRole.OPERATOR: 2,
    AdminRole.SITE_CURATOR: 3,
    AdminRole.SUPER_ADMIN: 4,
}


class LoginRequest(BaseModel):
    """Admin login request contract."""

    username: str = Field(min_length=3, max_length=64, description="Admin username or email")
    password: str = Field(min_length=6, max_length=128, description="Plaintext password")


class TokenResponse(BaseModel):
    """JWT token pair response contract."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    role: str
    username: str


class RefreshTokenRequest(BaseModel):
    """Token rotation request contract."""

    refresh_token: str = Field(description="Active JWT refresh token")


class AdminProfileResponse(BaseModel):
    """Public administrator profile contract."""

    id: str
    username: str
    email: str = Field(description="Administrator email address")
    role: str
    is_active: bool
    created_at: str
