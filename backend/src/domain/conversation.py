"""Domain models and contracts for multilingual chat sessions and messages."""

from enum import Enum
from pydantic import BaseModel, Field


class LanguageCode(str, Enum):
    """Supported official language codes."""

    KANNADA = "kn"
    ENGLISH = "en"


class MessageRole(str, Enum):
    """Turn participant roles in conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InputMode(str, Enum):
    """Input modalities for conversation turns."""

    TEXT = "text"
    VOICE = "voice"


class Citation(BaseModel):
    """Attributed source citation linking response to ground truth document chunk."""

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Source document identifier")
    page_number: int = Field(ge=1, description="Origin page number")
    section_heading: str | None = Field(default=None, description="Section heading context")
    relevance_score: float = Field(description="Confidence re-ranking score")
    snippet: str = Field(description="Verbatim excerpt from source chunk")


class ChatMessageResponse(BaseModel):
    """Individual conversational message turn response contract."""

    id: str
    session_id: str
    role: str
    content: str
    detected_language: str
    input_mode: str
    latency_ms: int | None = None
    is_grounded: bool = True
    created_at: str
    citations: list[Citation] = Field(default_factory=list)


class ChatSessionResponse(BaseModel):
    """Conversational session context contract."""

    id: str
    client_fingerprint: str
    preferred_language: str
    created_at: str
    last_active_at: str
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    """Payload to initiate a tourist conversational session."""

    client_fingerprint: str | None = Field(
        default=None,
        description="Optional client-side device or browser fingerprint for session continuity",
    )
    preferred_language: str = Field(
        default="kn",
        description="Initial language preference: 'kn' (Kannada) or 'en' (English)",
    )


class SendMessageRequest(BaseModel):
    """User input payload to send a conversational query."""

    session_id: str | None = Field(
        default=None,
        description="Existing session identifier. If omitted, a session is automatically initialized.",
    )
    client_fingerprint: str | None = Field(
        default=None,
        description="Optional client fingerprint for automatic session resolution.",
    )
    content: str = Field(min_length=1, max_length=2000, description="User question or statement.")
    preferred_language: str | None = Field(
        default=None,
        description="Explicit language override ('kn' or 'en'). If omitted, language is auto-detected.",
    )
    input_mode: str = Field(default="text", description="Input modality: 'text' or 'voice'.")
