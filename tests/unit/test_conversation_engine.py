"""Unit and integration tests for Phase 8: Multilingual Conversation Engine."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from backend.src.application.chat.grounding_guard import (
    CANONICAL_FALLBACK_EN,
    CANONICAL_FALLBACK_KN,
    GroundingGuard,
)
from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.domain.conversation import SendMessageRequest
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.chat import ChatMessage, ChatSession
from backend.src.infrastructure.models.knowledge import CitationReference
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_language_detector_kannada_english_mixed():
    """Verify Kannada script, English, and mixed multilingual input detection."""
    detector = LanguageDetector()

    # 1. Pure Kannada
    kn_text = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"
    res_kn = detector.detect(kn_text)
    assert res_kn.language == "kn"
    assert res_kn.confidence > 0.8
    assert res_kn.is_mixed is False

    # 2. Pure English
    en_text = "Who commissioned the Belur Chennakeshava Temple?"
    res_en = detector.detect(en_text)
    assert res_en.language == "en"
    assert res_en.confidence > 0.8
    assert res_en.is_mixed is False

    # 3. Mixed script
    mixed_text = "Belur ದೇವಾಲಯದ ಶಿಲ್ಪಿ ಯಾರು?"
    res_mixed = detector.detect(mixed_text)
    assert res_mixed.is_mixed is True
    assert res_mixed.language in ["kn", "en"]


def test_strict_grounding_guard_fallback():
    """Verify strict Grounding Guard triggers deterministic canonical fallbacks when evidence is absent."""
    guard = GroundingGuard(confidence_threshold=0.35)

    # 1. Empty candidates -> English fallback
    eval_en = guard.evaluate([], language="en")
    assert eval_en.is_grounded is False
    assert eval_en.fallback_message == CANONICAL_FALLBACK_EN

    # 2. Empty candidates -> Kannada fallback
    eval_kn = guard.evaluate([], language="kn")
    assert eval_kn.is_grounded is False
    assert eval_kn.fallback_message == CANONICAL_FALLBACK_KN

    # 3. Candidates with low confidence below threshold
    low_cand = [
        RetrievalCandidate(
            chunk_id="test_low",
            document_id="doc_1",
            page_number=1,
            content="Irrelevant text snippet",
            rerank_score=0.12,  # < 0.35 threshold
        )
    ]
    eval_low = guard.evaluate(low_cand, language="en")
    assert eval_low.is_grounded is False
    assert eval_low.fallback_message == CANONICAL_FALLBACK_EN

    # 4. Valid candidate above threshold
    high_cand = [
        RetrievalCandidate(
            chunk_id="test_high",
            document_id="doc_1",
            page_number=1,
            content="Grounded historical facts",
            rerank_score=0.88,
        )
    ]
    eval_high = guard.evaluate(high_cand, language="en")
    assert eval_high.is_grounded is True
    assert eval_high.fallback_message is None
    assert len(eval_high.selected_chunks) == 1


@pytest.mark.anyio
async def test_tourist_public_endpoints_require_zero_auth():
    """Verify that general tourists can interact with zero authentication barriers or tokens."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Initialize session without any auth headers
        session_res = await client.post(
            "/api/v1/chat/sessions",
            json={"preferred_language": "en"},
        )
        assert session_res.status_code == 201
        session_data = session_res.json()
        session_id = session_data["id"]
        assert session_id is not None

        # 2. Send message turn with zero authentication
        msg_res = await client.post(
            "/api/v1/chat/message",
            json={
                "session_id": session_id,
                "content": "Who commissioned the Chennakeshava Temple at Belur?",
            },
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assert msg_data["session_id"] == session_id
        assert msg_data["role"] == "assistant"
        assert msg_data["is_grounded"] is True
        assert len(msg_data["citations"]) >= 1

        # 3. Retrieve conversation history with zero authentication
        history_res = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert history_res.status_code == 200
        history_data = history_res.json()
        assert len(history_data["messages"]) == 2  # 1 user + 1 assistant


@pytest.mark.anyio
async def test_multi_turn_coreference_resolution():
    """Verify multi-turn conversation retains context across turns (resolving pronouns like 'Who built it?')."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Turn 1: State the subject
        turn1_res = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "Tell me about the Belur Chennakeshava Temple architecture.",
                "preferred_language": "en",
            },
        )
        assert turn1_res.status_code == 200
        session_id = turn1_res.json()["session_id"]

        # Turn 2: Follow-up with pronoun reference
        turn2_res = await client.post(
            "/api/v1/chat/message",
            json={
                "session_id": session_id,
                "content": "Who built it and in what year?",
            },
        )
        assert turn2_res.status_code == 200
        turn2_data = turn2_res.json()

        # Turn 2 must resolve context and be grounded in King Vishnuvardhana
        assert turn2_data["is_grounded"] is True
        assert "Vishnuvardhana" in turn2_data["content"]
        assert len(turn2_data["citations"]) >= 1


@pytest.mark.anyio
async def test_out_of_domain_query_triggers_canonical_fallback():
    """Verify completely out-of-domain questions return canonical fallback string and zero hallucination."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Out-of-domain query
        res = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "What is the capital city of France and who is the president?",
                "preferred_language": "en",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_grounded"] is False
        assert data["content"] == CANONICAL_FALLBACK_EN
        assert len(data["citations"]) == 0

        # Kannada out-of-domain query
        res_kn = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಯಾವುದು?",
                "preferred_language": "kn",
            },
        )
        assert res_kn.status_code == 200
        data_kn = res_kn.json()
        assert data_kn["is_grounded"] is False
        assert data_kn["content"] == CANONICAL_FALLBACK_KN


@pytest.mark.anyio
async def test_citation_references_relational_persistence():
    """Verify that grounded turns insert persistent rows into citation_references table in MySQL."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        msg_res = await client.post(
            "/api/v1/chat/message",
            json={
                "content": "What material was used for the Hoysala temples in Belur?",
                "preferred_language": "en",
            },
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assistant_msg_id = msg_data["id"]

        # Inspect MySQL database directly
        session_factory = get_session_factory()
        async with session_factory() as session:
            stmt = select(CitationReference).where(CitationReference.message_id == assistant_msg_id)
            result = await session.execute(stmt)
            cit_rows = result.scalars().all()

            assert len(cit_rows) >= 1
            assert cit_rows[0].relevance_score > 0.35
            assert cit_rows[0].chunk_id is not None
