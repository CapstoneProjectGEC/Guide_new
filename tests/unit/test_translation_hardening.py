"""Unit and integration tests for Phase 11: Translation Hardening & Cross-Lingual RAG."""

from unittest.mock import MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.application.chat.grounding_guard import CANONICAL_FALLBACK_KN
from backend.src.application.translation.heritage_glossary import HeritageGlossary
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.application.translation.transliteration import transliterate_kannada_to_latin
from backend.src.application.translation.translator import TranslationService
from backend.src.domain.conversation import SendMessageRequest
from backend.src.domain.translation import TranslationStrategy
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.system import TranslationRegistry
from backend.src.infrastructure.translation.argos_engine import ArgosTranslationEngine
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_heritage_glossary_term_extraction_and_masking():
    """Verify that heritage proper nouns are extracted and masked without corruption."""
    glossary = HeritageGlossary()
    text = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ವಿಷ್ಣುವರ್ಧನ ರಾಜನು ನಿರ್ಮಿಸಿದನು."

    # 1. Term extraction
    extracted = glossary.extract_heritage_terms(text)
    extracted_canonical = [eng for _, eng in extracted]
    assert "Belur" in extracted_canonical
    assert "Chennakeshava" in extracted_canonical
    assert "King Vishnuvardhana" in extracted_canonical

    # 2. Masking proper nouns
    masked, masks = glossary.mask_heritage_terms(text)
    assert len(masks) >= 3
    for placeholder in masks:
        assert placeholder in masked

    # 3. Unmasking replaces placeholders with canonical English terms
    unmasked = glossary.unmask_heritage_terms(masked, masks)
    assert "Belur" in unmasked
    assert "Chennakeshava" in unmasked
    assert "King Vishnuvardhana" in unmasked


def test_transliteration_distinguished_from_translation():
    """Verify that phonetic transliteration is strictly distinguished from semantic translation."""
    # Transliteration converts script phonetically
    translit_devalaya = transliterate_kannada_to_latin("ದೇವಾಲಯ")
    assert translit_devalaya in ["devalaya", "deevaalaya"]
    assert translit_devalaya != "temple"  # Must NOT claim that transliteration is translation

    translit_belur = transliterate_kannada_to_latin("ಬೇಲೂರು")
    assert "beeloor" in translit_belur or "belur" in translit_belur


def test_query_normalizer_english_passthrough():
    """Verify English queries undergo zero mutation and pass through with PASSTHROUGH strategy."""
    normalizer = QueryNormalizer()
    query = "Who commissioned the Chennakeshava Temple at Belur?"

    norm = normalizer.normalize_for_retrieval(query, source_lang="en")
    assert norm.retrieval_query == query
    assert norm.translation_applied is False
    assert norm.strategy_used == TranslationStrategy.PASSTHROUGH
    assert norm.preserved_terms == []


def test_query_normalizer_kannada_query_expansion():
    """Verify Kannada query is normalized into high-precision English retrieval query."""
    normalizer = QueryNormalizer()
    query = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"

    norm = normalizer.normalize_for_retrieval(query, source_lang="kn")
    assert norm.translation_applied is True
    assert norm.strategy_used in [TranslationStrategy.DOMAIN_GLOSSARY_EXPANSION, TranslationStrategy.ARGOS_NEURAL]
    assert "Belur" in norm.preserved_terms
    assert "Chennakeshava" in norm.preserved_terms

    # Retrieval query must contain key entities and intent expansion
    retrieval_lower = norm.retrieval_query.lower()
    assert "belur" in retrieval_lower
    assert "chennakeshava" in retrieval_lower
    assert any(w in retrieval_lower for w in ["who", "built", "commissioned", "constructed"])


def test_query_normalizer_mixed_language_query():
    """Verify mixed-language queries are normalized cleanly preserving English terms."""
    normalizer = QueryNormalizer()
    query = "Belur temple ಚೆನ್ನಕೇಶವ architecture ಬಗ್ಗೆ ತಿಳಿಸಿ"

    norm = normalizer.normalize_for_retrieval(query)
    assert norm.translation_applied is True
    retrieval_lower = norm.retrieval_query.lower()
    assert "belur" in retrieval_lower
    assert "chennakeshava" in retrieval_lower
    assert "architecture" in retrieval_lower


def test_query_normalizer_empty_and_malformed_inputs():
    """Verify empty strings and malformed inputs are handled gracefully without exceptions."""
    normalizer = QueryNormalizer()

    # Empty string
    norm_empty = normalizer.normalize_for_retrieval("")
    assert norm_empty.retrieval_query == ""
    assert norm_empty.translation_applied is False

    # Punctuation / whitespace
    norm_spaces = normalizer.normalize_for_retrieval("   ???   ")
    assert norm_spaces.retrieval_query == "???"


def test_argos_engine_graceful_fallback_when_model_unavailable():
    """Verify that when Argos language pair is absent, the engine reports unavailable without crash."""
    engine = ArgosTranslationEngine()
    # Query for pair that is not installed
    is_avail = engine.is_language_pair_available("kn", "en")
    if not is_avail:
        res = engine.translate("ಪರೀಕ್ಷೆ", "kn", "en")
        assert res is None  # Graceful fallback returns None


def test_argos_neural_translation_path_with_mock():
    """Verify neural translation path with proper-noun preservation when model is present."""
    mock_engine = MagicMock(spec=ArgosTranslationEngine)
    mock_engine.is_language_pair_available.return_value = True
    # Return translated text containing placeholder
    mock_engine.translate.return_value = "Who built __HERITAGE_TERM_0__ in __HERITAGE_TERM_1__?"

    normalizer = QueryNormalizer(argos_engine=mock_engine)
    query = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?"

    norm = normalizer.normalize_for_retrieval(query, source_lang="kn")
    assert norm.strategy_used == TranslationStrategy.ARGOS_NEURAL
    assert norm.translation_applied is True
    assert "Chennakeshava" in norm.retrieval_query
    assert "Belur" in norm.retrieval_query


@pytest.mark.anyio
async def test_translation_service_status_and_db_sync():
    """Verify TranslationService reports status and synchronizes with MySQL translation_registry."""
    service = TranslationService()
    status_info = service.get_status()
    assert status_info["engine"] == "argos"
    assert "installed_packages_count" in status_info

    async with get_session_factory()() as db_session:
        synced = await service.sync_translation_registry(session=db_session)
        assert isinstance(synced, list)
        await db_session.commit()

        # Query database directly
        res = await db_session.execute(select(TranslationRegistry))
        rows = res.scalars().all()
        assert len(rows) == len(synced)


@pytest.mark.anyio
async def test_rest_api_translation_endpoints():
    """Verify /api/v1/translation endpoints report valid schemas and respond HTTP 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Status endpoint
        status_res = await client.get("/api/v1/translation/status")
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["engine"] == "argos"

        # 2. Normalize endpoint
        norm_res = await client.post(
            "/api/v1/translation/normalize",
            json={"query": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ"},
        )
        assert norm_res.status_code == 200
        norm_data = norm_res.json()
        assert norm_data["translation_applied"] is True
        assert "Belur" in norm_data["retrieval_query"]
        assert "Chennakeshava" in norm_data["retrieval_query"]

        # 3. Sync endpoint
        sync_res = await client.post("/api/v1/translation/sync")
        assert sync_res.status_code == 200
        assert "synced_count" in sync_res.json()


@pytest.mark.anyio
async def test_kannada_query_end_to_end_grounded_retrieval():
    """Verify that a Kannada query successfully retrieves English chunks with high confidence."""
    async with get_session_factory()() as session:
        manager = ConversationManager(session=session)
        request = SendMessageRequest(
            content="ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
            preferred_language="kn",
        )
        response = await manager.process_message(request)

        # Must succeed and be grounded
        assert response.role == "assistant"
        assert response.detected_language == "kn"
        assert response.is_grounded is True
        assert len(response.citations) > 0

        # Citations must attribute to Belur temple chunks
        top_cit = response.citations[0]
        assert top_cit.relevance_score > 0.35
        assert top_cit.chunk_id is not None


@pytest.mark.anyio
async def test_kannada_irrelevant_query_strict_grounding_fallback():
    """Verify out-of-domain Kannada query triggers canonical fallback without hallucination."""
    async with get_session_factory()() as session:
        manager = ConversationManager(session=session)
        request = SendMessageRequest(
            content="ಮೈಸೂರು ಅರಮನೆಯ ಇತಿಹಾಸವೇನು?",  # Out-of-domain (Mysore palace)
            preferred_language="kn",
        )
        response = await manager.process_message(request)

        # Must NOT be grounded; must return canonical fallback
        assert response.is_grounded is False
        assert len(response.citations) == 0
        assert response.content == CANONICAL_FALLBACK_KN


@pytest.mark.anyio
async def test_kannada_sse_streaming_preserves_contract():
    """Verify Kannada query through SSE stream emits valid citations and token events."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        req_payload = {
            "content": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
            "preferred_language": "kn",
        }
        res = await client.post("/api/v1/chat/stream", json=req_payload)
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        body = res.text
        assert "event: citations" in body
        assert "event: token" in body
        assert "event: done" in body


@pytest.mark.anyio
async def test_paired_english_kannada_polished_pillars_retrieval():
    """Verify that equivalent English and Kannada questions retrieve identical key knowledge."""
    async with get_session_factory()() as session:
        manager = ConversationManager(session=session)

        # 1. English query
        req_en = SendMessageRequest(
            content="Who built the Chennakeshava Temple at Belur and when?",
            preferred_language="en",
        )
        resp_en = await manager.process_message(req_en)
        assert resp_en.is_grounded is True
        assert len(resp_en.citations) > 0
        assert resp_en.citations[0].relevance_score >= 0.35
        en_chunk_ids = [c.chunk_id for c in resp_en.citations]

        # 2. Equivalent Kannada query
        req_kn = SendMessageRequest(
            content="ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?",
            preferred_language="kn",
        )
        resp_kn = await manager.process_message(req_kn)
        assert resp_kn.is_grounded is True
        assert len(resp_kn.citations) > 0
        assert resp_kn.citations[0].relevance_score >= 0.35
        kn_chunk_ids = [c.chunk_id for c in resp_kn.citations]

        # Both queries must retrieve the exact same primary knowledge chunk
        assert en_chunk_ids[0] == kn_chunk_ids[0]
        assert "vishnuvardhana" in resp_en.content.lower() or "vishnuvardhana" in resp_en.citations[0].snippet.lower()


@pytest.mark.anyio
async def test_kannada_pillar_phrasing_variations():
    """Verify that alternative Kannada phrasings of the pillar question retrieve grounded knowledge."""
    phrasings = [
        "ನವರಂಗದ ದುಂಡನೆಯ ಹೊಳಪಿನ ಕಂಬಗಳನ್ನು ಹೇಗೆ ತಯಾರಿಸಿದರು?",
        "ಕಂಬಗಳಿಗೆ ಹೊಳಪು ಮತ್ತು ದುಂಡಗಿನ ಆಕಾರವನ್ನು ಹೇಗೆ ನೀಡಲಾಯಿತು?",
        "ಬೇಲೂರು ಮುಖ್ಯ ಮಂಟಪದ ಹೊಳಪುಳ್ಳ ಕಂಬಗಳನ್ನು ಹೇಗೆ ಮಾಡಿದರು?",
    ]
    normalizer = QueryNormalizer()
    for query in phrasings:
        norm = normalizer.normalize_for_retrieval(query, source_lang="kn")
        retrieval_lower = norm.retrieval_query.lower()
        # Ensure key architectural keywords are preserved
        assert "pillar" in retrieval_lower or "column" in retrieval_lower
        assert "lathe" in retrieval_lower or "turn" in retrieval_lower or "polish" in retrieval_lower


@pytest.mark.anyio
async def test_paired_stone_material_and_sculpture_count():
    """Verify paired Kannada knowledge questions retrieve accurate grounding."""
    async with get_session_factory()() as session:
        manager = ConversationManager(session=session)

        # Stone material query
        req_stone = SendMessageRequest(
            content="ದೇವಾಲಯ ನಿರ್ಮಾಣಕ್ಕೆ ಯಾವ ಕಲ್ಲನ್ನು ಬಳಸಲಾಗಿದೆ?",
            preferred_language="kn",
        )
        resp_stone = await manager.process_message(req_stone)
        assert resp_stone.is_grounded is True
        assert len(resp_stone.citations) > 0

        # Madanika count query
        req_count = SendMessageRequest(
            content="ದೇವಾಲಯದಲ್ಲಿ ಒಟ್ಟು ಎಷ್ಟು ಮದನಿಕಾ ಶಿಲ್ಪಗಳಿವೆ?",
            preferred_language="kn",
        )
        resp_count = await manager.process_message(req_count)
        assert resp_count.is_grounded is True
        assert len(resp_count.citations) > 0


@pytest.mark.anyio
async def test_unsupported_out_of_domain_kannada_truthful_fallback():
    """Verify unsupported out-of-domain Kannada questions consistently yield canonical fallback."""
    unsupported_queries = [
        "ತಾಜ್ ಮಹಲ್ ಎಲ್ಲಿದೆ?",
        "ಬೆಂಗಳೂರಿನ ಹವಾಮಾನ ಹೇಗಿದೆ?",
    ]
    async with get_session_factory()() as session:
        manager = ConversationManager(session=session)
        for q in unsupported_queries:
            req = SendMessageRequest(content=q, preferred_language="kn")
            resp = await manager.process_message(req)
            assert resp.is_grounded is False
            assert len(resp.citations) == 0
            assert resp.content == CANONICAL_FALLBACK_KN
