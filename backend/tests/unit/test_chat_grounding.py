"""Unit tests verifying chat answer grounding, echo rejection, heading-only detection, and citation integrity."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.application.chat.grounding_guard import (
    CANONICAL_FALLBACK_EN,
    CANONICAL_FALLBACK_KN,
    GroundingEvaluation,
    GroundingGuard,
)
from backend.src.domain.conversation import SendMessageRequest
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.models.chat import ChatMessage, ChatSession


def test_grounding_guard_detects_query_echo() -> None:
    """Verify that is_query_echo accurately identifies queries echoed verbatim or with minimal variance."""
    guard = GroundingGuard()

    # Exact echo
    assert guard.is_query_echo("Darpana Sundari", "Darpana Sundari") is True
    # Case & punctuation variance
    assert guard.is_query_echo("darpana sundari?", "Darpana Sundari") is True
    assert guard.is_query_echo("Who built Belur Temple?", "Who built Belur Temple?") is True
    # Minimal prefix echo
    assert guard.is_query_echo("Darpana Sundari.", "Darpana Sundari") is True

    # Real answer is NOT an echo
    assert guard.is_query_echo("Darpana Sundari is a celebrated bracket figure depicting a woman admiring her mirror.", "Darpana Sundari") is False


def test_grounding_guard_detects_heading_only() -> None:
    """Verify that is_heading_only identifies responses that merely output chunk section headings."""
    guard = GroundingGuard()
    cand = RetrievalCandidate(
        document_id="doc-1",
        chunk_id="chk-1",
        chunk_index=0,
        page_number=1,
        section_heading="Madanika Bracket Figures (Darpana Sundari)",
        content="Madanika Bracket Figures (Darpana Sundari)\nFull factual content about sculptures.",
        dense_score=0.9,
        sparse_score=1.0,
        rrf_score=0.5,
        rerank_score=0.95,
    )

    assert guard.is_heading_only("Madanika Bracket Figures (Darpana Sundari)", [cand]) is True
    assert guard.is_heading_only("madanika bracket figures (darpana sundari)", [cand]) is True
    assert guard.is_heading_only("One of the crowning glories is the 42 bracket figures.", [cand]) is False


def test_verify_response_rejects_empty_echo_and_heading() -> None:
    """Verify that verify_response rejects ungrounded, empty, echo, and heading-only candidates."""
    guard = GroundingGuard()
    cand = RetrievalCandidate(
        document_id="doc-1",
        chunk_id="chk-1",
        chunk_index=0,
        page_number=1,
        section_heading="Architecture & Material",
        content="The temple was constructed using chloritic schist (soapstone).",
        dense_score=0.9,
        sparse_score=1.0,
        rrf_score=0.5,
        rerank_score=0.95,
    )

    # Empty
    ok, text = guard.verify_response("", "Soapstone", [cand], "en")
    assert ok is False
    assert text == CANONICAL_FALLBACK_EN

    # Query echo
    ok, text = guard.verify_response("Soapstone", "Soapstone", [cand], "en")
    assert ok is False
    assert text == CANONICAL_FALLBACK_EN

    # Heading-only
    ok, text = guard.verify_response("Architecture & Material", "What material?", [cand], "en")
    assert ok is False
    assert text == CANONICAL_FALLBACK_EN

    # Canonical fallback input
    ok, text = guard.verify_response(CANONICAL_FALLBACK_EN, "Where is it?", [cand], "en")
    assert ok is False
    assert text == CANONICAL_FALLBACK_EN

    # Valid factual grounded response
    factual_text = "The temple was constructed using chloritic schist soapstone."
    ok, text = guard.verify_response(factual_text, "What material was used?", [cand], "en")
    assert ok is True
    assert text == factual_text


@pytest.mark.asyncio
async def test_process_message_stream_unsupported_query_sets_not_grounded() -> None:
    """Verify that an unsupported query (yielding 0 chunks) sets is_grounded: False in done event."""
    mock_session = AsyncMock()

    # Session exists
    chat_sess = ChatSession(id="sess-1", client_fingerprint="fp1", preferred_language="en")
    res_sess = MagicMock()
    res_sess.scalar_one_or_none.return_value = chat_sess
    # No history
    res_hist = MagicMock()
    res_hist.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [res_sess, res_hist]

    mock_retriever = AsyncMock()
    mock_retriever.retrieve.return_value = []  # Zero candidates for unsupported query

    manager = ConversationManager(session=mock_session, retriever=mock_retriever)

    req = SendMessageRequest(session_id="sess-1", content="Tell me about the Eiffel Tower")

    events = []
    async for event_str in manager.process_message_stream(req):
        events.append(event_str)

    full_output = "".join(events)
    assert "event: done" in full_output
    assert '"is_grounded": false' in full_output

    import json
    tokens = []
    for line in full_output.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            if "token" in payload:
                tokens.append(payload["token"])

    assembled = "".join(tokens).strip()
    assert assembled == CANONICAL_FALLBACK_EN
