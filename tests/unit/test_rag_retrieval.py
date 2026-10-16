"""Unit and integration tests for Phase 7: RAG Retrieval Optimization."""

import pytest
from httpx import ASGITransport, AsyncClient
from backend.src.application.rag.bm25 import BM25Index
from backend.src.application.rag.reranker import CrossEncoderReranker
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.core.security import hash_password
from backend.src.domain.rag import RetrievalDiagnosticRequest
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def create_viewer_admin() -> tuple[Admin, str]:
    """Seed a test viewer administrator."""
    import uuid
    session_factory = get_session_factory()
    uid = uuid.uuid4().hex[:6]
    pwd = "ViewerPassword123!"
    admin = Admin(
        username=f"viewer_rag_{uid}",
        email=f"viewer_rag_{uid}@karnatakagov.in",
        password_hash=hash_password(pwd),
        role="VIEWER",
        is_active=True,
    )
    async with session_factory() as session:
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
    return admin, pwd


def test_bm25_lexical_indexing_and_scoring():
    """Verify BM25 Okapi inverted indexing, exact match recall, and term frequency scoring."""
    corpus = [
        {
            "chunk_id": "chunk_0",
            "document_id": "doc_1",
            "page_number": 1,
            "section_heading": "Patronage",
            "content": "King Vishnuvardhana commissioned the Chennakeshava Temple at Belur in 1117 CE.",
        },
        {
            "chunk_id": "chunk_1",
            "document_id": "doc_1",
            "page_number": 1,
            "section_heading": "Architecture",
            "content": "The temple is built from soapstone or chloritic schist with star shaped jagati.",
        },
        {
            "chunk_id": "chunk_2",
            "document_id": "doc_1",
            "page_number": 2,
            "section_heading": "Madanikas",
            "content": "There are 42 Madanika celestial bracket figures including Darpana Sundari.",
        },
    ]

    index = BM25Index(k1=1.5, b=0.75).fit(corpus)

    # 1. Search for unique keyword in chunk 0
    results_0 = index.search(query="Vishnuvardhana 1117", top_k=2)
    assert len(results_0) >= 1
    assert results_0[0]["chunk_id"] == "chunk_0"
    assert results_0[0]["sparse_score"] > 0

    # 2. Search for unique keyword in chunk 2
    results_2 = index.search(query="Darpana Sundari Madanika", top_k=2)
    assert len(results_2) >= 1
    assert results_2[0]["chunk_id"] == "chunk_2"

    # 3. Search for non-existent keyword returns empty
    results_none = index.search(query="aeroplane jet engine", top_k=5)
    assert len(results_none) == 0


def test_cross_encoder_reranker_scoring_and_threshold():
    """Verify cross-encoder pairwise scoring, sigmoid calibration, and threshold cutoff."""
    reranker = CrossEncoderReranker()

    candidates = [
        {
            "chunk_id": "c1",
            "content": "King Vishnuvardhana of Hoysala dynasty commissioned Chennakeshava Temple in 1117 CE.",
        },
        {
            "chunk_id": "c2",
            "content": "The temple wall friezes feature 650 elephants, charging lions, and cavalry horses.",
        },
        {
            "chunk_id": "c3",
            "content": "The weather in Bengaluru is pleasant during October with light rain showers.",
        },
    ]

    query = "Who commissioned the Chennakeshava temple?"
    results = reranker.rerank(query=query, candidates=candidates, top_k=3, threshold=0.35)

    # c1 is highly relevant and should have confidence > 0.8
    assert len(results) >= 1
    top_hit = results[0]
    assert top_hit["chunk_id"] == "c1"
    assert top_hit["rerank_score"] > 0.7
    assert top_hit["is_selected"] is True

    # c3 (weather in Bengaluru) is irrelevant and must be filtered out by threshold
    selected_ids = [r["chunk_id"] for r in results]
    assert "c3" not in selected_ids


@pytest.mark.anyio
async def test_hybrid_retriever_end_to_end_with_live_knowledge_base():
    """Verify dense + sparse retrieval, RRF fusion, and Cross-Encoder ranking on active Belur data."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        retriever = HybridRAGRetriever(session=session)
        query = "Who commissioned the Chennakeshava Temple and in which year?"

        diag = await retriever.diagnose(query=query, top_final=3, threshold=0.35)

        # 1. Verify diagnostic fields
        assert diag.query == query
        assert diag.generation_number >= 1
        assert len(diag.dense_candidates) > 0
        assert len(diag.sparse_candidates) > 0
        assert len(diag.fused_candidates) > 0
        assert len(diag.final_chunks) > 0

        # 2. Check top ranked final chunk
        top_chunk = diag.final_chunks[0]
        assert "Vishnuvardhana" in top_chunk.content
        assert top_chunk.rerank_score is not None
        assert top_chunk.rerank_score >= 0.35

        # 3. Verify provenance
        assert top_chunk.page_number == 1
        assert "Patronage" in (top_chunk.section_heading or "")

        # 4. Verify latency profile (test warm execution speed after model weights are loaded)
        warm_diag = await retriever.diagnose(query=query, top_final=3, threshold=0.35)
        breakdown = warm_diag.latency_breakdown_ms
        assert "dense_ms" in breakdown
        assert "sparse_ms" in breakdown
        assert "rrf_ms" in breakdown
        assert "rerank_ms" in breakdown
        assert "total_ms" in breakdown
        assert breakdown["total_ms"] < 1000.0  # Warm retrieval executes in < 1000ms (typically < 100ms)


@pytest.mark.anyio
async def test_hybrid_retriever_sculpture_query():
    """Verify retrieval precision for Madanika bracket figures and sculptors."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        retriever = HybridRAGRetriever(session=session)
        query = "What are the Madanika bracket figures and Darpana Sundari?"

        chunks = await retriever.retrieve(query=query, top_final=2, threshold=0.35)
        assert len(chunks) >= 1

        top_content = chunks[0].content
        assert "Madanika" in top_content or "Darpana Sundari" in top_content
        assert chunks[0].page_number == 2


@pytest.mark.anyio
async def test_admin_diagnostics_endpoint_and_rbac():
    """Verify admin diagnostics endpoint requires authentication and delivers structured traces."""
    viewer, viewer_pwd = await create_viewer_admin()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated request rejected -> 401 Unauthorized
        unauth = await client.post(
            "/api/v1/admin/diagnostics/retrieval",
            json={"query": "Who built Belur?"},
        )
        assert unauth.status_code == 401

        # 2. Login as viewer
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": viewer.username, "password": viewer_pwd},
        )
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Authenticated POST diagnostics probe
        diag_req = RetrievalDiagnosticRequest(
            query="Who built the temple and who was the sculptor?",
            top_final=2,
            score_threshold=0.30,
        )
        resp = await client.post(
            "/api/v1/admin/diagnostics/retrieval",
            headers=headers,
            json=diag_req.model_dump(),
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["query"] == diag_req.query
        assert "dense_candidates" in data
        assert "sparse_candidates" in data
        assert "fused_candidates" in data
        assert "final_chunks" in data
        assert len(data["final_chunks"]) >= 1
        assert "latency_breakdown_ms" in data

        # 4. Authenticated GET diagnostics probe
        get_resp = await client.get(
            "/api/v1/admin/diagnostics/retrieval?query=chloritic+schist+soapstone",
            headers=headers,
        )
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert len(get_data["final_chunks"]) >= 1
        assert "soapstone" in get_data["final_chunks"][0]["content"].lower()
