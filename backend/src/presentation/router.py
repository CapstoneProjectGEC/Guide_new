"""Unified API router consolidating all tourist and administrative /api/v1 endpoints."""

from fastapi import APIRouter

from backend.src.presentation.api.admin_documents import router as admin_docs_router
from backend.src.presentation.api.admin_knowledge import router as admin_knowledge_router
from backend.src.presentation.api.admin_sync import router as admin_sync_router
from backend.src.presentation.api.auth import router as auth_router
from backend.src.presentation.api.chat import router as chat_router
from backend.src.presentation.api.diagnostics import router as diagnostics_router
from backend.src.presentation.api.health import router as health_router
from backend.src.presentation.api.translation import router as translation_router
from backend.src.presentation.api.voice import router as voice_router

# Gateway router mounting all subsystems under /api/v1
api_v1_router = APIRouter(prefix="/api/v1")

# 1. System Health & Probes
api_v1_router.include_router(health_router)

# 2. Administrative Authentication & RBAC
api_v1_router.include_router(auth_router)

# 3. Administrative Document Management
api_v1_router.include_router(admin_docs_router)

# 4. Administrative Knowledge Base Pipeline
api_v1_router.include_router(admin_knowledge_router)

# 5. Administrative RAG Retrieval Diagnostics
api_v1_router.include_router(diagnostics_router)

# 6. Administrative Registry Management
api_v1_router.include_router(admin_sync_router)

# 7. Frictionless Tourist Chat (RAG, Coreference, SSE Streaming)
api_v1_router.include_router(chat_router)

# 8. Frictionless Tourist Voice (Whisper STT, Piper TTS)
api_v1_router.include_router(voice_router)

# 9. Translation & Cross-Lingual RAG Normalization
api_v1_router.include_router(translation_router)


# Tag metadata for rich OpenAPI documentation
GATEWAY_TAGS_METADATA = [
    {
        "name": "System Health",
        "description": "Liveness, readiness, and subsystem component probes.",
    },
    {
        "name": "Tourist Chat",
        "description": "Frictionless, zero-authentication multi-turn conversational RAG and streaming text exploration for Belur Temple.",
    },
    {
        "name": "Tourist Voice",
        "description": "Multilingual speech-to-text (Whisper STT) and offline neural speech synthesis (Piper TTS).",
    },
    {
        "name": "Translation & Cross-Lingual",
        "description": "Deterministic query normalization, Belur heritage glossary masking, and offline neural translation.",
    },
    {
        "name": "Admin Authentication",
        "description": "Cryptographic authentication with Argon2id and JWT access/refresh token rotation.",
    },
    {
        "name": "Admin Documents",
        "description": "Secure heritage PDF document ingestion, SHA-256 deduplication, and storage lifecycle.",
    },
    {
        "name": "Admin Knowledge Pipeline",
        "description": "PyMuPDF parsing, structural chunking, ChromaDB vector indexing, and zero-rebuild rollback.",
    },
    {
        "name": "Admin Diagnostics",
        "description": "Deep hybrid retrieval diagnostics, dense vs BM25 sparse scores, and cross-encoder weights.",
    },
    {
        "name": "Admin Management",
        "description": "Administrative synchronization of installed voice models and neural translation packages.",
    },
]
