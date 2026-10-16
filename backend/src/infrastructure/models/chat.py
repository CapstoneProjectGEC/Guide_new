"""Conversational chat session and message turn models."""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.src.infrastructure.database.base import Base, UUIDPrimaryKeyMixin, utc_now


class ChatSession(Base, UUIDPrimaryKeyMixin):
    """Tourist or admin conversational session context."""

    __tablename__ = "chat_sessions"

    client_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="kn", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base, UUIDPrimaryKeyMixin):
    """Individual conversational query or response turn."""

    __tablename__ = "chat_messages"

    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(Enum("user", "assistant", "system", name="message_role_enum"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    detected_language: Mapped[str] = mapped_column(String(10), default="kn", nullable=False)
    input_mode: Mapped[str] = mapped_column(Enum("text", "voice", name="input_mode_enum"), default="text", nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_grounded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
