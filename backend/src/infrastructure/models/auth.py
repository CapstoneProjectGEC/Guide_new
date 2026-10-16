"""Authentication and administrative models."""

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.src.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Admin(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Administrative user account."""

    __tablename__ = "admins"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(191), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("SUPER_ADMIN", "SITE_CURATOR", "OPERATOR", "VIEWER", name="admin_role_enum"),
        default="OPERATOR",
        index=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
