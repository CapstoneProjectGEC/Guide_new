"""Persistence foundation and MySQL verification tests."""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from backend.src.infrastructure.database.session import (
    check_database_health,
    get_session_factory,
)
from backend.src.infrastructure.models import (
    Admin,
    AuditLog,
    ChatMessage,
    ChatSession,
    ChunkEmbedding,
    CitationReference,
    DeploymentHistory,
    Document,
    DocumentChunk,
    GenerationStatus,
    HealthMetric,
    KnowledgeGeneration,
    ModelRegistry,
    SystemLog,
    SystemSetting,
    TranslationRegistry,
    VoiceRegistry,
)
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_database_connection_and_ping():
    """Verify check_database_health executes a ping query with low latency."""
    health = await check_database_health()
    assert health["status"] == "healthy"
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0.0


@pytest.mark.asyncio
async def test_async_session_crud_lifecycle():
    """Verify inserting, querying, and deleting a record using async SQLAlchemy."""
    session_factory = get_session_factory()
    test_key = f"test_setting_{uuid.uuid4().hex[:8]}"

    async with session_factory() as session:
        # Create
        setting = SystemSetting(
            setting_key=test_key,
            setting_value="Belur Heritage Mode Enabled",
            description="Integration test setting",
        )
        session.add(setting)
        await session.commit()

    async with session_factory() as session:
        # Read
        stmt = select(SystemSetting).where(SystemSetting.setting_key == test_key)
        result = await session.execute(stmt)
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.setting_value == "Belur Heritage Mode Enabled"
        assert fetched.created_at is not None

        # Delete / Cleanup
        await session.delete(fetched)
        await session.commit()

    async with session_factory() as session:
        # Verify deletion
        stmt = select(SystemSetting).where(SystemSetting.setting_key == test_key)
        result = await session.execute(stmt)
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_health_endpoint_reports_database_healthy():
    """Verify /api/v1/health exposes live database probe status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data["components"]
    assert data["components"]["database"]["status"] == "healthy"
    assert "latency_ms" in data["components"]["database"]


def test_all_17_models_instantiation():
    """Verify all 17 locked models are valid SQLAlchemy ORM entities with mapped tables."""
    models = [
        Admin,
        Document,
        KnowledgeGeneration,
        GenerationStatus,
        DocumentChunk,
        ChunkEmbedding,
        CitationReference,
        ChatSession,
        ChatMessage,
        AuditLog,
        SystemLog,
        DeploymentHistory,
        HealthMetric,
        ModelRegistry,
        VoiceRegistry,
        TranslationRegistry,
        SystemSetting,
    ]
    assert len(models) == 17
    for model_cls in models:
        assert hasattr(model_cls, "__tablename__")
        assert model_cls.__tablename__ is not None
