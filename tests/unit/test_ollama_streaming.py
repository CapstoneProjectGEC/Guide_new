"""Unit and integration tests for Phase 9: Local Ollama LLM Integration and SSE Streaming."""

import json
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from backend.src.application.chat.grounding_guard import (
    CANONICAL_FALLBACK_EN,
    CANONICAL_FALLBACK_KN,
)
from backend.src.application.chat.prompt_builder import PromptBuilder
from backend.src.core.config import get_settings
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.llm.ollama_client import OllamaClient
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_ollama_config_and_defaults():
    """Verify Ollama configuration parameters match approved low-latency settings."""
    settings = get_settings()
    assert settings.OLLAMA_BASE_URL == "http://127.0.0.1:11434"
    assert settings.OLLAMA_MODEL == "gemma3:4b"
    assert settings.OLLAMA_NUM_CTX == 4096
    assert settings.OLLAMA_NUM_PREDICT == 160
    assert settings.OLLAMA_TEMPERATURE == 0.1
    assert settings.OLLAMA_TOP_K == 20
    assert settings.OLLAMA_TOP_P == 0.8
    assert settings.OLLAMA_KEEP_ALIVE == "-1"
    assert settings.PROMPT_CONTEXT_CEILING_TOKENS == 1500


def test_prompt_builder_en_and_kn():
    """Verify PromptBuilder enforces canonical fallbacks, heading provenance, and context boundaries."""
    builder = PromptBuilder(context_ceiling_tokens=500)
    evidence = [
        RetrievalCandidate(
            chunk_id="chunk_1",
            document_id="doc_1",
            page_number=1,
            section_heading="Historical Patronage",
            content="King Vishnuvardhana commissioned the temple in 1117 CE.",
            rerank_score=0.95,
        )
    ]

    # 1. English Prompt
    sys_en, user_en = builder.build_prompt("Who built it?", evidence, language="en")
    assert CANONICAL_FALLBACK_EN in sys_en
    assert "Page 1 | Historical Patronage" in user_en
    assert "King Vishnuvardhana" in user_en
    assert "Tourist Question: Who built it?" in user_en

    # 2. Kannada Prompt
    sys_kn, user_kn = builder.build_prompt("ಯಾರು ಕಟ್ಟಿಸಿದರು?", evidence, language="kn")
    assert CANONICAL_FALLBACK_KN in sys_kn
    assert "Page 1 | Historical Patronage" in user_kn


@pytest.mark.anyio
async def test_mocked_ollama_streaming_happy_path():
    """Verify SSE streaming delivers tokens, citations, and terminal done event without buffer delay."""
    simulated_tokens = ["King ", "Vishnuvardhana ", "commissioned ", "the ", "temple ", "in ", "1117 CE."]

    async def mock_stream_generate(*args, **kwargs):
        for tok in simulated_tokens:
            yield tok

    with patch.object(OllamaClient, "stream_generate", side_effect=mock_stream_generate):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/stream",
                json={
                    "content": "Who commissioned the Chennakeshava Temple at Belur?",
                    "preferred_language": "en",
                },
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            lines = response.text.split("\n\n")
            events = []
            tokens = []
            citations = []
            done_payload = None

            for block in lines:
                if not block.strip():
                    continue
                block_lines = block.split("\n")
                evt_type = ""
                data_val = ""
                for line in block_lines:
                    if line.startswith("event:"):
                        evt_type = line.replace("event:", "").strip()
                    elif line.startswith("data:"):
                        data_val = line.replace("data:", "").strip()

                events.append(evt_type)
                if evt_type == "token":
                    tokens.append(json.loads(data_val)["token"])
                elif evt_type == "citations":
                    citations = json.loads(data_val)["citations"]
                elif evt_type == "done":
                    done_payload = json.loads(data_val)

            assert "citations" in events
            assert "token" in events
            assert "done" in events
            assert len(tokens) == len(simulated_tokens)
            assert "".join(tokens) == "".join(simulated_tokens)
            assert len(citations) >= 1
            assert done_payload is not None
            assert done_payload["is_grounded"] is True
            assert done_payload["latency_ms"] is not None


@pytest.mark.anyio
async def test_mocked_ollama_unsupported_query_immediate_fallback():
    """Verify unsupported queries bypass LLM inference and stream canonical fallback with zero tokens wasted."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "content": "How do I make chocolate ice cream at home?",
                "preferred_language": "en",
            },
        )
        assert response.status_code == 200

        lines = response.text.split("\n\n")
        tokens = []
        done_payload = None

        for block in lines:
            if not block.strip():
                continue
            for line in block.split("\n"):
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.replace("data:", "").strip())
                        if "token" in data:
                            tokens.append(data["token"])
                        if "is_grounded" in data:
                            done_payload = data
                    except Exception:
                        pass

        full_streamed_text = "".join(tokens).strip()
        assert CANONICAL_FALLBACK_EN == full_streamed_text
        assert done_payload is not None
        assert done_payload["is_grounded"] is False


@pytest.mark.anyio
async def test_mocked_ollama_kannada_unicode_streaming():
    """Verify Kannada script tokens stream with proper UTF-8 decoding and zero Unicode corruption."""
    kannada_tokens = ["ಹೊಯ್ಸಳ ", "ರಾಜ ", "ವಿಷ್ಣುವರ್ಧನನು ", "ಈ ", "ದೇವಾಲಯವನ್ನು ", "ನಿರ್ಮಿಸಿದನು."]

    async def mock_stream_kn(*args, **kwargs):
        for tok in kannada_tokens:
            yield tok

    with patch.object(OllamaClient, "stream_generate", side_effect=mock_stream_kn):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/stream",
                json={
                    "content": "Who commissioned the Chennakeshava Temple at Belur?",
                    "preferred_language": "kn",
                },
            )
            assert response.status_code == 200

            text = response.text
            assert "ವಿಷ್ಣುವರ್ಧನ" in text
            assert "event: done" in text


@pytest.mark.anyio
async def test_kannada_unsupported_query_immediate_fallback_stream():
    """Verify out-of-domain Kannada queries stream canonical Kannada fallback text cleanly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/chat/stream",
            json={
                "content": "ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಯಾವುದು?",
                "preferred_language": "kn",
            },
        )
        assert response.status_code == 200
        lines = response.text.split("\n\n")
        tokens = []
        for block in lines:
            for line in block.split("\n"):
                if line.startswith("data:"):
                    try:
                        data = json.loads(line.replace("data:", "").strip())
                        if "token" in data:
                            tokens.append(data["token"])
                    except Exception:
                        pass
        full_text = "".join(tokens).strip()
        assert CANONICAL_FALLBACK_KN in full_text
        assert "event: done" in response.text


@pytest.mark.anyio
async def test_ollama_upstream_unavailable_graceful_fallback():
    """Verify that when Ollama is unreachable, system gracefully serves grounded context excerpts without error."""
    # When OllamaClient stream_generate errors out or connection fails
    async def mock_failing_stream(*args, **kwargs):
        raise ConnectionRefusedError("Connection refused by Ollama daemon")
        yield "token"

    with patch.object(OllamaClient, "stream_generate", side_effect=mock_failing_stream):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/chat/stream",
                json={
                    "content": "Who commissioned the Chennakeshava Temple at Belur?",
                    "preferred_language": "en",
                },
            )
            assert response.status_code == 200
            # Should have fallen back to verified chunk content
            assert "Vishnuvardhana" in response.text
            assert "event: done" in response.text
