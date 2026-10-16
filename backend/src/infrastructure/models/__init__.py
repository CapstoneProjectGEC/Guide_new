"""Models package aggregating all 17 database entities."""

from backend.src.infrastructure.database.base import Base
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import (
    CitationReference,
    ChunkEmbedding,
    Document,
    DocumentChunk,
    GenerationStatus,
    KnowledgeGeneration,
)
from backend.src.infrastructure.models.chat import ChatMessage, ChatSession
from backend.src.infrastructure.models.system import (
    AuditLog,
    DeploymentHistory,
    HealthMetric,
    ModelRegistry,
    SystemLog,
    SystemSetting,
    TranslationRegistry,
    VoiceRegistry,
)

__all__ = [
    "Base",
    "Admin",
    "Document",
    "KnowledgeGeneration",
    "GenerationStatus",
    "DocumentChunk",
    "ChunkEmbedding",
    "CitationReference",
    "ChatSession",
    "ChatMessage",
    "AuditLog",
    "SystemLog",
    "DeploymentHistory",
    "HealthMetric",
    "ModelRegistry",
    "VoiceRegistry",
    "TranslationRegistry",
    "SystemSetting",
]
