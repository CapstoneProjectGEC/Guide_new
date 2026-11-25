"""Regression and validation tests for Kannada language response, system prompt protection, and UI localization."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.src.application.chat.grounding_guard import GroundingGuard, CANONICAL_FALLBACK_KN, CANONICAL_FALLBACK_EN
from backend.src.application.translation.heritage_translator import HeritageTranslator
from backend.src.application.translation.translator import TranslationService
from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.domain.conversation import SendMessageRequest
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.models.chat import ChatSession

@pytest.mark.asyncio
async def test_grounding_guard_rejects_system_prompt_echo():
    """Ensure system prompt persona instructions are strictly detected and rejected."""
    guard = GroundingGuard()

    # Kannada system prompt excerpts that previously leaked
    kn_leaks = [
        "ನೀವು ಕರ್ನಾಟಕದ ಬೇಲೂರು ಚನ್ನಕೇಶವ ದೇವಾಲಯದ ಅಧಿಕೃತ ಸ್ಮಾರ್ಟ್ ಪ್ರವಾಸಿ ಮಾರ್ಗದರ್ಶಿ",
        "ನೀವು ಕರ್ನಾಟಕದ ಬೇಲೂರು ಚನ್ನಕೇಶವ ದೇವಾಲಯದ ಅಧಿಕೃತ ಸ್ಮಾರ್ಟ್ ಮಾರ್ಗದರ್ಶಿ",
        "ಮಹತ್ವದ ನಿಯಮಗಳು: ಕೆಳಗಿನ ಸಂದರ್ಭದಲ್ಲಿ",
        "ನಿಮ್ಮ ಸಂಪೂರ್ಣ ಉತ್ತರವು ಕಡ್ಡಾಯವಾಗಿ ಶುದ್ಧ ಕನ್ನಡದಲ್ಲೇ ಇರಬೇಕು",
        "ಮಾರ್ಗದರ್ಶಿಯ ಉತ್ತರ (ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ):",
    ]
    for leak in kn_leaks:
        assert guard.is_system_prompt_echo(leak) is True, f"Failed to reject leak: {leak}"
        is_grounded, text = guard.verify_response(leak, "ಪ್ರಶ್ನೆ", [], language="kn")
        assert is_grounded is False
        assert text == CANONICAL_FALLBACK_KN

    # English system prompt excerpts
    en_leaks = [
        "You are the official Smart Tourist Guide AI for Belur Chennakeshava Temple",
        "CRITICAL GROUNDING RULES: Answer ONLY using the facts",
        "Tourist Question: Who built it?",
    ]
    for leak in en_leaks:
        assert guard.is_system_prompt_echo(leak) is True, f"Failed to reject leak: {leak}"
        is_grounded, text = guard.verify_response(leak, "question", [], language="en")
        assert is_grounded is False
        assert text == CANONICAL_FALLBACK_EN

    # Valid factual answers must NOT be flagged
    valid_kn = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು."
    assert guard.is_system_prompt_echo(valid_kn) is False
    is_grounded, text = guard.verify_response(valid_kn, "ಪ್ರಶ್ನೆ", [], language="kn")
    assert is_grounded is True
    assert text == valid_kn

    valid_en = "The Chennakeshava Temple at Belur was built by Hoysala ruler King Vishnuvardhana in 1117 CE."
    assert guard.is_system_prompt_echo(valid_en) is False
    is_grounded, text = guard.verify_response(valid_en, "question", [], language="en")
    assert is_grounded is True
    assert text == valid_en

def test_heritage_translator_factual_translation():
    """Verify factual English responses translate to natural, accurate Kannada without hallucinations."""
    translator = HeritageTranslator()

    # Builder & Inception
    en_builder = "The Chennakeshava Temple at Belur was built by Hoysala ruler King Vishnuvardhana in 1117 CE."
    kn_builder = translator.translate_en_to_kn(en_builder)
    assert "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು" in kn_builder
    assert "ವಿಷ್ಣುವರ್ಧನನು" in kn_builder
    assert "1117" in kn_builder

    # Material
    en_stone = "The temple in Belur was constructed using fine-grained chloritic schist, commonly known as soapstone."
    kn_stone = translator.translate_en_to_kn(en_stone)
    assert "ಬಳಪದ ಕಲ್ಲಿನಿಂದ" in kn_stone
    assert "ಸೋಪ್‌ಸ್ಟೋನ್" in kn_stone

    # Madanika figures
    en_madanika = "There are 42 Madanika bracket figures in the temple."
    kn_madanika = translator.translate_en_to_kn(en_madanika)
    assert "42" in kn_madanika
    assert "ಮದನಿಕಾ" in kn_madanika

    # Darpana Sundari
    en_darpana = "Darpana Sundari is a renowned Madanika figure representing a maiden admiring herself in a mirror."
    kn_darpana = translator.translate_en_to_kn(en_darpana)
    assert "ದರ್ಪಣ ಸುಂದರಿ" in kn_darpana
    assert "ಕೈಗನ್ನಡಿ" in kn_darpana

    # Fallback
    en_fallback = CANONICAL_FALLBACK_EN
    kn_fallback = translator.translate_en_to_kn(en_fallback)
    assert kn_fallback == CANONICAL_FALLBACK_KN

@pytest.mark.asyncio
async def test_kannada_message_stream_flow():
    """Simulate complete Kannada turn, verifying fast inference, streaming, and no system prompt leakage."""
    session_mock = AsyncMock()
    # Mock existing session query
    mock_chat_session = ChatSession(
        id="test-session-123",
        client_fingerprint="tourist_123",
        preferred_language="kn",
    )
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = mock_chat_session
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalars.return_value.first.return_value = None
    session_mock.execute.return_value = result_mock

    # Mock Retriever returning King Vishnuvardhana chunk
    mock_retriever = AsyncMock()
    candidate = RetrievalCandidate(
        chunk_id="chunk-1",
        document_id="Temple_info.pdf",
        page_number=1,
        section_heading="Section 1: Historical Patronage and Inception",
        content="The Chennakeshava Temple was commissioned by Hoysala ruler King Vishnuvardhana in 1117 CE.",
        dense_score=0.92,
        sparse_score=0.88,
        rerank_score=0.95,
    )
    mock_retriever.retrieve.return_value = [candidate]

    # Mock Ollama generating English response
    mock_ollama = MagicMock()
    async def mock_stream_gen(prompt, system_prompt, **kwargs):
        tokens = ["The ", "Chennakeshava ", "Temple ", "at ", "Belur ", "was ", "built ", "by ", "Hoysala ", "ruler ", "King ", "Vishnuvardhana ", "in ", "1117 ", "CE."]
        for tok in tokens:
            yield tok

    mock_ollama.stream_generate = mock_stream_gen

    # Manager
    manager = ConversationManager(
        session=session_mock,
        retriever=mock_retriever,
        ollama_client=mock_ollama,
    )

    request = SendMessageRequest(
        session_id="test-session-123",
        content="ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?",
        preferred_language="kn",
        input_mode="text",
    )

    events: list[str] = []
    async for raw_sse in manager.process_message_stream(request):
        events.append(raw_sse)

    # 1. First event should be citations
    assert len(events) >= 3
    assert "event: citations" in events[0]
    cit_payload = json.loads(events[0].replace("event: citations\ndata: ", "").strip())
    assert "citations" in cit_payload

    # 2. Subsequent events should be token streaming in Kannada
    tokens = []
    for ev in events[1:-1]:
        if "event: token" in ev:
            data = json.loads(ev.replace("event: token\ndata: ", "").strip())
            tokens.append(data["token"])

    full_response = "".join(tokens).strip()
    # Must be in Kannada
    assert "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು" in full_response
    assert "ವಿಷ್ಣುವರ್ಧನನು" in full_response
    assert "1117" in full_response

    # Must NOT contain system prompt or persona leak
    assert "ನೀವು ಕರ್ನಾಟಕದ ಬೇಲೂರು" not in full_response
    assert "ಅಧಿಕೃತ ಸ್ಮಾರ್ಟ್ ಮಾರ್ಗದರ್ಶಿ" not in full_response
    assert "ಮಹತ್ವದ ನಿಯಮಗಳು" not in full_response

    # 3. Last event must be done event with kn language
    done_ev = events[-1]
    assert "event: done" in done_ev
    done_payload = json.loads(done_ev.replace("event: done\ndata: ", "").strip())
    assert done_payload["detected_language"] == "kn"
    assert done_payload["is_grounded"] is True

