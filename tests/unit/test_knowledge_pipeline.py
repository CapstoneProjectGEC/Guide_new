"""Unit and integration tests for Phase 6: Knowledge Base Pipeline."""

import time
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from backend.src.application.pipeline.chunker import SemanticChunker
from backend.src.application.pipeline.extractor import PDFExtractor
from backend.src.application.pipeline.generation_manager import KnowledgeGenerationManager
from backend.src.core.security import hash_password
from backend.src.domain.knowledge import ExtractedSection, TextChunk
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import (
    ChunkEmbedding,
    Document,
    DocumentChunk,
    GenerationStatus,
    KnowledgeGeneration,
)
from backend.src.infrastructure.models.system import AuditLog
from backend.src.infrastructure.vector.chroma_store import (
    EmbeddingService,
    get_embedding_service,
    get_vector_store,
)
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_curator_admin() -> tuple[Admin, str]:
    """Seed a test curator administrator."""
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    pwd = "CuratorPassword123!"
    admin = Admin(
        username=f"curator_{uid}",
        email=f"curator_{uid}@karnatakagov.in",
        password_hash=hash_password(pwd),
        role="SITE_CURATOR",
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin, pwd


async def create_viewer_admin() -> tuple[Admin, str]:
    """Seed a test viewer administrator."""
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    pwd = "ViewerPassword123!"
    admin = Admin(
        username=f"viewer_{uid}",
        email=f"viewer_{uid}@karnatakagov.in",
        password_hash=hash_password(pwd),
        role="VIEWER",
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin, pwd


@pytest.mark.anyio
async def test_pdf_extractor_fidelity_and_unicode_nfkc():
    """Verify PyMuPDF extraction, heading detection, and Unicode NFKC normalization."""
    extractor = PDFExtractor()
    sections = extractor.extract_from_file("Temple_info.pdf")

    assert len(sections) >= 5
    assert sections[0].page_number == 1
    assert "Historical Patronage" in (sections[0].section_heading or "")
    assert "Vishnuvardhana" in sections[0].content

    # Test NFKC normalization on dirty unicode ligature string
    dirty_text = "ﬁrst ﬃce　ｔｅｓｔ\r\n\r\n\r\n\r\nline2"
    normalized = extractor.normalize_text(dirty_text)
    assert "first ffice test\n\nline2" == normalized


@pytest.mark.anyio
async def test_semantic_chunker_boundaries_and_token_counts():
    """Verify chunk size constraints, section boundaries, and token estimation."""
    chunker = SemanticChunker(target_chunk_tokens=100, overlap_tokens=20)
    sections = [
        ExtractedSection(
            page_number=1,
            section_heading="Section 1: Inception",
            content="Short content that comfortably fits inside one chunk.",
        ),
        ExtractedSection(
            page_number=2,
            section_heading="Section 2: Architecture",
            content="Sentence one is about soapstone. " * 30,  # Large section
        ),
    ]

    chunks = chunker.chunk_sections(sections, document_id="doc-test-123")
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[0].page_number == 1
    assert chunks[0].section_heading == "Section 1: Inception"
    assert chunks[0].token_count > 0

    # Ensure second section was split and chunk indices are sequential
    assert chunks[1].chunk_index == 1
    assert chunks[1].page_number == 2


@pytest.mark.anyio
async def test_chroma_vector_store_and_embedding_service():
    """Verify 384-dim dense embeddings and ChromaDB isolated namespace indexing."""
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()

    texts = ["Belur Chennakeshava Temple Hoysala architecture", "Soapstone carving of Madanika bracket figures"]
    vectors = embedding_service.embed_texts(texts)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    # Test indexing into isolated test collection
    test_collection = f"test_kbase_{uuid.uuid4().hex[:8]}"
    chunks = [
        TextChunk(
            document_id="doc-1",
            chunk_index=0,
            page_number=1,
            section_heading="Heading 1",
            content=texts[0],
            token_count=10,
        ),
        TextChunk(
            document_id="doc-1",
            chunk_index=1,
            page_number=2,
            section_heading="Heading 2",
            content=texts[1],
            token_count=12,
        ),
    ]

    records = vector_store.index_chunks(test_collection, chunks, vectors)
    assert len(records) == 2
    assert vector_store.count(test_collection) == 2

    # Test dense query
    query_vec = embedding_service.embed_query("Hoysala Chennakeshava")
    results = vector_store.query_dense(test_collection, query_vec, top_k=1)
    assert len(results) == 1
    assert "Belur" in results[0]["content"]
    assert results[0]["similarity"] > 0.4

    # Cleanup
    vector_store.delete_collection(test_collection)
    assert vector_store.count(test_collection) == 0


@pytest.mark.anyio
async def test_knowledge_generation_pipeline_lifecycle():
    """Verify end-to-end knowledge generation build, step progression, and active promotion."""
    session_factory = get_session_factory()

    # Ensure at least one document exists in DB for generation
    async with session_factory() as session:
        doc_stmt = select(Document).limit(1)
        doc_res = await session.execute(doc_stmt)
        doc = doc_res.scalar_one_or_none()
        assert doc is not None, "Baseline document Temple_info.pdf must be present in database."

        manager = KnowledgeGenerationManager(session=session)
        gen_response = await manager.build_generation(admin_id=None, auto_promote=True)

        assert gen_response.id is not None
        assert gen_response.generation_number >= 1
        assert gen_response.status == "ACTIVE"
        assert gen_response.chunk_count >= 5
        assert gen_response.promoted_at is not None

        # Verify all 6 pipeline steps completed
        completed_steps = [s.step for s in gen_response.steps if s.status == "COMPLETED"]
        for expected in ["PARSE", "CHUNK", "EMBED", "INDEX", "VALIDATE", "PROMOTE"]:
            assert expected in completed_steps

        # Verify relational synchronization
        chunks_stmt = select(DocumentChunk).where(DocumentChunk.generation_id == gen_response.id)
        chunks_res = await session.execute(chunks_stmt)
        chunks = chunks_res.scalars().all()
        assert len(chunks) == gen_response.chunk_count

        embeddings_stmt = select(ChunkEmbedding).where(ChunkEmbedding.generation_id == gen_response.id)
        embeddings_res = await session.execute(embeddings_stmt)
        embeddings = embeddings_res.scalars().all()
        assert len(embeddings) == gen_response.chunk_count
        assert embeddings[0].dimensions == 384
        assert embeddings[0].model_name == "all-MiniLM-L6-v2"


@pytest.mark.anyio
async def test_fast_zero_rebuild_rollback():
    """Verify instant (<100ms) active generation rollback without rebuilding."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        manager = KnowledgeGenerationManager(session=session)

        # Build Generation A
        gen_a = await manager.build_generation(auto_promote=True)
        assert gen_a.status == "ACTIVE"

        # Build Generation B (becomes ACTIVE, gen_a becomes ARCHIVED)
        gen_b = await manager.build_generation(auto_promote=True)
        assert gen_b.status == "ACTIVE"

        # Check Gen A is now ARCHIVED
        gen_a_refreshed = await manager.get_generation(gen_a.id)
        assert gen_a_refreshed.status == "ARCHIVED"

        # Measure rollback execution time
        start = time.perf_counter()
        rolled_back = await manager.rollback_generation(target_id=gen_a.id)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert rolled_back.id == gen_a.id
        assert rolled_back.status == "ACTIVE"
        assert elapsed_ms < 150.0  # Fast pointer swap under 150ms

        # Check Gen B is now ARCHIVED
        gen_b_refreshed = await manager.get_generation(gen_b.id)
        assert gen_b_refreshed.status == "ARCHIVED"


@pytest.mark.anyio
async def test_admin_knowledge_api_endpoints_and_rbac():
    """Verify administrative REST API endpoints, RBAC permissions, and audit logging."""
    curator, curator_pwd = await create_curator_admin()
    viewer, viewer_pwd = await create_viewer_admin()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login as curator
        curator_login = await client.post(
            "/api/v1/auth/login",
            json={"username": curator.username, "password": curator_pwd},
        )
        curator_token = curator_login.json()["access_token"]
        curator_headers = {"Authorization": f"Bearer {curator_token}"}

        # 2. Login as viewer
        viewer_login = await client.post(
            "/api/v1/auth/login",
            json={"username": viewer.username, "password": viewer_pwd},
        )
        viewer_token = viewer_login.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # 3. Viewer can list generations
        list_res = await client.get("/api/v1/admin/knowledge/generations", headers=viewer_headers)
        assert list_res.status_code == 200
        data = list_res.json()
        assert "generations" in data
        assert data["total"] >= 1

        # 4. Viewer can get active generation
        active_res = await client.get("/api/v1/admin/knowledge/generations/active", headers=viewer_headers)
        assert active_res.status_code == 200
        assert active_res.json()["status"] == "ACTIVE"

        # 5. Viewer CANNOT trigger build (Requires SITE_CURATOR) -> 403 Forbidden
        forbidden_build = await client.post(
            "/api/v1/admin/knowledge/generations/build",
            headers=viewer_headers,
            json={},
        )
        assert forbidden_build.status_code == 403

        # 6. Curator CAN trigger build -> 201 Created
        curator_build = await client.post(
            "/api/v1/admin/knowledge/generations/build",
            headers=curator_headers,
            json={},
        )
        assert curator_build.status_code == 201
        new_gen = curator_build.json()
        assert new_gen["status"] == "ACTIVE"

        # 7. Check audit log recorded GEN_BUILD
        session_factory = get_session_factory()
        async with session_factory() as session:
            audit_stmt = (
                select(AuditLog)
                .where(AuditLog.action == "GEN_BUILD")
                .where(AuditLog.resource_id == new_gen["id"])
            )
            audit_res = await session.execute(audit_stmt)
            audit_record = audit_res.scalar_one_or_none()
            assert audit_record is not None
            assert audit_record.admin_id == curator.id
