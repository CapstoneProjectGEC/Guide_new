"""Cryptographic security utilities: Argon2id password hashing and JWT issuance."""

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
import argon2
from argon2.exceptions import VerifyMismatchError
import jwt
from backend.src.core.config import get_settings
from backend.src.core.errors import AuthenticationError
from backend.src.core.logging import get_logger

logger = get_logger("core.security")

# OWASP recommended Argon2id parameters
_hasher = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate a signed JWT access token with unique jti claim."""
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate a signed JWT refresh token with unique jti claim for rotation."""
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# In-memory revocation registry for revoked token JTIs (logout and refresh rotation)
_revoked_token_jtis: set[str] = set()


def revoke_token(jti: str) -> None:
    """Register a token JTI as revoked."""
    if jti:
        _revoked_token_jtis.add(jti)


def is_token_revoked(jti: str) -> bool:
    """Check if token JTI has been revoked."""
    return jti in _revoked_token_jtis


def clear_revoked_tokens() -> None:
    """Clear revoked token registry (primarily for test fixture resets)."""
    _revoked_token_jtis.clear()


def decode_token(token: str, check_revocation: bool = True) -> dict[str, Any]:
    """Decode, validate, and check revocation status of a signed JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if check_revocation and payload.get("jti") and is_token_revoked(payload["jti"]):
            raise AuthenticationError("Authentication token has been revoked.")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Authentication token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid authentication token.")
