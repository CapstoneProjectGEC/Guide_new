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
    document_id: str = Field(default="BELUR-KB-001", description="Source document identifier")
    page_number: int = Field(default=1, ge=1, description="Origin page number")
    section_heading: str | None = Field(default=None, description="Section heading context")
    section_id: str | None = Field(default=None, description="Canonical Section ID e.g. BELUR-KB-001-S04.1")
    source_page_title: str | None = Field(default=None, description="Human readable source page title")
    source_url: str | None = Field(default=None, description="Original source webpage URL")
    relevance_score: float = Field(default=1.0, description="Confidence re-ranking score")
    snippet: str = Field(default="", description="Verbatim excerpt from source chunk")


class ImageCard(BaseModel):
    """Catalogued temple image card with attribution and caption hedges."""

    image_id: str
    display_url: str | None = None
    original_url: str = ""
    caption: str = ""
    raw_caption: str = ""
    uncertain_caption: bool = False
    source_site: str = ""
    source_page_url: str = ""
    section_id: str = ""
    width: int | None = None
    height: int | None = None
    is_local: bool = False


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
    has_timing_uncertainty: bool = False
    created_at: str
    citations: list[Citation] = Field(default_factory=list)
    images: list[ImageCard] = Field(default_factory=list)


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
