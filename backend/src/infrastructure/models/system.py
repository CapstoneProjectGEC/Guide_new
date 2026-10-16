"""System telemetry, audit logs, and component registries models."""

from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.src.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class AuditLog(Base):
    """Immutable audit trail of administrative operations."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class SystemLog(Base):
    """Structured application runtime events."""

    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    logger_name: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    context_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class DeploymentHistory(Base):
    """Track applied releases, schema revisions, and deployment modes."""

    __tablename__ = "deployment_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[str] = mapped_column(String(64), nullable=False)
    profile: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)
    deployed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HealthMetric(Base):
    """Periodic system resource utilization snapshots."""

    __tablename__ = "health_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cpu_usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    ram_usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    disk_usage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    mysql_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    chroma_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ollama_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    active_sessions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class ModelRegistry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered LLM, embedding, and transcription model profiles."""

    __tablename__ = "model_registry"

    model_name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    configuration: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class VoiceRegistry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered speech synthesis and recognition voices."""

    __tablename__ = "voice_registry"

    voice_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    engine: Mapped[str] = mapped_column(String(32), default="piper", nullable=False)
    model_path: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TranslationRegistry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered offline neural translation language pairs."""

    __tablename__ = "translation_registry"

    source_language: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_installed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SystemSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Dynamic application configuration key-value storage."""

    __tablename__ = "system_settings"

    setting_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
