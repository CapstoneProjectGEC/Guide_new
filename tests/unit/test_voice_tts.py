"""Automated unit and integration tests for Phase 12: Offline Text-to-Speech (TTS)."""

import asyncio
import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import wave

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.voice.tts_service import TextToSpeechService, get_tts_service
from backend.src.core.config import get_settings
from backend.src.core.errors import (
    TTSTimeoutError,
    TTSTooLargeError,
    TTSUnavailableError,
    TTSValidationError,
)
from backend.src.domain.voice import SynthesisRequest
from backend.src.infrastructure.audio.piper_engine import PiperEngine, get_piper_engine
from backend.src.infrastructure.audio.tts_cache import TTSAudioCache
from backend.src.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _create_mock_wav_bytes(duration_sec: float = 0.5, sample_rate: int = 22050) -> bytes:
    """Generate minimal valid PCM WAV bytes for deterministic tests."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_f:
        wav_f.setnchannels(1)
        wav_f.setsampwidth(2)
        wav_f.setframerate(sample_rate)
        n_frames = int(sample_rate * duration_sec)
        wav_f.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. LRU Cache Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_cache_operations_lru_and_eviction():
    """Verify cache normalization, key building, bounded capacity, hit/miss, and LRU eviction."""
    cache = TTSAudioCache(max_entries=2, max_text_length=50)

    # Text normalization
    norm_en = cache.normalize_text("  Hello   World!  ", "en")
    assert norm_en == "hello world!"
    norm_kn = cache.normalize_text("  ನಮಸ್ಕಾರ   ಸ್ವಾಗತ  ", "kn")
    assert norm_kn == "ನಮಸ್ಕಾರ ಸ್ವಾಗತ"

    mock_audio_1 = (_create_mock_wav_bytes(), 0.5, 22050)
    mock_audio_2 = (_create_mock_wav_bytes(), 0.6, 22050)
    mock_audio_3 = (_create_mock_wav_bytes(), 0.7, 22050)

    # Miss
    assert await cache.get("Phrase 1", "en", "voice1", 1.0) is None
    assert cache.stats["misses"] == 1

    # Put entry 1 and 2
    await cache.put("Phrase 1", "en", "voice1", 1.0, mock_audio_1)
    await cache.put("Phrase 2", "en", "voice1", 1.0, mock_audio_2)
    assert cache.stats["entries"] == 2

    # Hit entry 1 (makes entry 2 LRU)
    hit = await cache.get("Phrase 1", "en", "voice1", 1.0)
    assert hit is not None
    assert cache.stats["hits"] == 1

    # Put entry 3 (should evict entry 2)
    await cache.put("Phrase 3", "en", "voice1", 1.0, mock_audio_3)
    assert cache.stats["entries"] == 2
    assert cache.stats["evictions"] == 1

    # Entry 1 should still exist; Entry 2 should be gone
    assert await cache.get("Phrase 1", "en", "voice1", 1.0) is not None
    assert await cache.get("Phrase 2", "en", "voice1", 1.0) is None

    # Length ceiling check: text > 50 chars is not cacheable
    long_text = "A" * 60
    assert not cache.is_cacheable(long_text)
    assert await cache.get(long_text, "en", "voice1", 1.0) is None

    await cache.clear()
    assert cache.stats["entries"] == 0


@pytest.mark.asyncio
async def test_tts_cache_concurrent_deduplication():
    """Verify concurrent lock acquisition and deduplication for identical requests."""
    cache = TTSAudioCache(max_entries=10, max_text_length=100)
    text = "Grounded fallback phrase"

    lock1 = await cache.get_or_create_lock(text, "en", "voice1", 1.0)
    lock2 = await cache.get_or_create_lock(text, "en", "voice1", 1.0)
    assert lock1 is lock2

    await cache.cleanup_lock(text, "en", "voice1", 1.0)


# ---------------------------------------------------------------------------
# 2. Piper Engine Adapter Tests
# ---------------------------------------------------------------------------


def test_piper_engine_voice_resolution():
    """Verify resolution of language codes and explicit voice overrides."""
    engine = PiperEngine(models_dir="data/models/piper")

    # English mappings
    assert engine.resolve_voice_id("en", None) == engine.settings.TTS_VOICE_EN
    assert engine.resolve_voice_id("en_US", None) == engine.settings.TTS_VOICE_EN
    assert engine.resolve_voice_id(None, "english") == engine.settings.TTS_VOICE_EN

    # Kannada mappings
    assert engine.resolve_voice_id("kn", None) == engine.settings.TTS_VOICE_KN
    assert engine.resolve_voice_id("kn_IN", None) == engine.settings.TTS_VOICE_KN
    assert engine.resolve_voice_id(None, "kannada") == engine.settings.TTS_VOICE_KN

    # Unsupported language
    with pytest.raises(TTSValidationError) as exc:
        engine.resolve_voice_id("fr", None)
    assert "Unsupported language code" in str(exc.value)


def test_piper_engine_missing_model_raises_unavailable(tmp_path: Path):
    """Verify that attempting to synthesize with missing model files raises TTSUnavailableError."""
    empty_engine = PiperEngine(models_dir=tmp_path)
    with pytest.raises(TTSUnavailableError) as exc:
        empty_engine.get_voice_instance("nonexistent_voice")
    assert "not found" in str(exc.value)


# ---------------------------------------------------------------------------
# 3. Application Service Tests
# ---------------------------------------------------------------------------


def test_tts_service_input_validation():
    """Verify validation guards for empty input and oversized text."""
    service = TextToSpeechService()

    # 1. Reject empty text
    with pytest.raises(TTSValidationError):
        service.validate_request(SynthesisRequest(text=""))

    with pytest.raises(TTSValidationError):
        service.validate_request(SynthesisRequest(text="   \n\t  "))

    # 2. Reject oversized text
    max_len = service.settings.TTS_MAX_TEXT_LENGTH
    oversized = "a" * (max_len + 1)
    with pytest.raises(TTSTooLargeError):
        service.validate_request(SynthesisRequest(text=oversized))


def test_tts_service_language_resolution():
    """Verify language selection with explicit code or Kannada/English auto-detection."""
    service = TextToSpeechService()

    # Explicit
    assert service.resolve_language("Hello", "en") == "en"
    assert service.resolve_language("Hello", "kn") == "kn"

    # Unsupported explicit
    with pytest.raises(TTSValidationError):
        service.resolve_language("Hello", "de")

    # Auto-detection from script
    assert service.resolve_language("This is an English answer", None) == "en"
    assert service.resolve_language("ಇದು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯದ ಇತಿಹಾಸ", None) == "kn"


@pytest.mark.asyncio
async def test_tts_service_disabled_configuration(monkeypatch):
    """Verify that TTSUnavailableError is raised when TTS_ENABLED is False."""
    service = TextToSpeechService()
    monkeypatch.setattr(service.settings, "TTS_ENABLED", False)

    with pytest.raises(TTSUnavailableError) as exc:
        await service.synthesize(SynthesisRequest(text="Test speech"))
    assert "disabled by system configuration" in str(exc.value)


@pytest.mark.asyncio
async def test_tts_service_timeout_handling(monkeypatch):
    """Verify TTSTimeoutError when synthesis exceeds timeout."""
    service = TextToSpeechService()
    monkeypatch.setattr(service.settings, "TTS_TIMEOUT_SECONDS", 0.01)

    def slow_synthesize(*args, **kwargs):
        import time
        time.sleep(0.05)
        return _create_mock_wav_bytes(), 0.5, 22050

    monkeypatch.setattr(service.engine, "synthesize_wav", slow_synthesize)
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: True)
    monkeypatch.setattr(service.engine, "get_voice_instance", lambda _: MagicMock())

    with pytest.raises(TTSTimeoutError):
        await service.synthesize(SynthesisRequest(text="Slow synthesis"))


@pytest.mark.asyncio
async def test_tts_service_mocked_synthesis_and_caching(monkeypatch):
    """Verify end-to-end synthesis flow for English and Kannada with caching."""
    service = TextToSpeechService()

    mock_wav = _create_mock_wav_bytes(duration_sec=1.2, sample_rate=22050)
    monkeypatch.setattr(service.engine, "synthesize_wav", lambda text, voice_id, speed: (mock_wav, 1.2, 22050))
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: True)

    # 1. English synthesis
    req_en = SynthesisRequest(text="Belur temple was built in 1117 AD.", language="en")
    audio_en, meta_en = await service.synthesize(req_en)
    assert len(audio_en) == len(mock_wav)
    assert meta_en.language == "en"
    assert meta_en.cached is False
    assert meta_en.duration_seconds == 1.2

    # 2. Kannada synthesis
    req_kn = SynthesisRequest(text="ಬೇಲೂರು ದೇವಾಲಯವನ್ನು ವಿಷ್ಣುವರ್ಧನ ಕಟ್ಟಿಸಿದನು.", language="kn")
    audio_kn, meta_kn = await service.synthesize(req_kn)
    assert len(audio_kn) == len(mock_wav)
    assert meta_kn.language == "kn"
    assert meta_kn.cached is False

    # 3. Cache hit on repeated short phrase
    repeated_req = SynthesisRequest(text="Short repeated greeting", language="en")
    _, meta_first = await service.synthesize(repeated_req)
    assert meta_first.cached is False

    _, meta_second = await service.synthesize(repeated_req)
    assert meta_second.cached is True
    assert meta_second.latency_ms <= 5


# ---------------------------------------------------------------------------
# 4. REST API Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_synthesize_endpoint_english_success(monkeypatch):
    """Verify POST /api/v1/voice/synthesize returns playable WAV and correct headers."""
    mock_wav = _create_mock_wav_bytes(duration_sec=0.8, sample_rate=22050)
    service = get_tts_service()
    monkeypatch.setattr(service.engine, "synthesize_wav", lambda text, voice_id, speed: (mock_wav, 0.8, 22050))
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"text": "Welcome to Chennakeshava Temple.", "language": "en"}
        resp = await client.post("/api/v1/voice/synthesize", json=payload)

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.headers["x-tts-engine"] == "piper"
        assert resp.headers["x-tts-language"] == "en"
        assert resp.headers["x-tts-cached"] == "false"
        assert "inline; filename=" in resp.headers["content-disposition"]
        assert len(resp.content) == len(mock_wav)

        # Immediate repeat should return cached=true
        resp_cached = await client.post("/api/v1/voice/synthesize", json=payload)
        assert resp_cached.status_code == 200
        assert resp_cached.headers["x-tts-cached"] == "true"


@pytest.mark.asyncio
async def test_api_synthesize_endpoint_kannada_success(monkeypatch):
    """Verify POST /api/v1/voice/synthesize works for Kannada text with auto-detection."""
    mock_wav = _create_mock_wav_bytes(duration_sec=1.0, sample_rate=22050)
    service = get_tts_service()
    monkeypatch.setattr(service.engine, "synthesize_wav", lambda text, voice_id, speed: (mock_wav, 1.0, 22050))
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without explicit language, Kannada script auto-detects 'kn'
        payload = {"text": "ಬೇಲೂರು ದೇವಾಲಯದ ದರ್ಶನಕ್ಕೆ ಸುಸ್ವಾಗತ."}
        resp = await client.post("/api/v1/voice/synthesize", json=payload)

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/wav"
        assert resp.headers["x-tts-language"] == "kn"
        assert resp.headers["x-tts-voice"] == service.settings.TTS_VOICE_KN


@pytest.mark.asyncio
async def test_api_synthesize_validation_errors():
    """Verify structured error envelopes for empty, oversized, and unsupported input."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Empty text -> 400 Bad Request
        resp1 = await client.post("/api/v1/voice/synthesize", json={"text": "   "})
        assert resp1.status_code == 400
        body1 = resp1.json()
        assert body1["error"]["code"] == "TTS_VALIDATION_ERROR"

        # 2. Oversized text -> 413 Content Too Large
        oversized = "x" * 1001
        resp2 = await client.post("/api/v1/voice/synthesize", json={"text": oversized})
        assert resp2.status_code == 413
        body2 = resp2.json()
        assert body2["error"]["code"] == "TTS_TOO_LARGE"

        # 3. Unsupported language -> 400 Bad Request
        resp3 = await client.post("/api/v1/voice/synthesize", json={"text": "Bonjour", "language": "fr"})
        assert resp3.status_code == 400
        body3 = resp3.json()
        assert body3["error"]["code"] == "TTS_VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_api_synthesize_disabled_tts_error(monkeypatch):
    """Verify 503 Service Unavailable when TTS is disabled."""
    service = get_tts_service()
    monkeypatch.setattr(service.settings, "TTS_ENABLED", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/voice/synthesize", json={"text": "Test"})
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "TTS_UNAVAILABLE"


@pytest.mark.asyncio
async def test_api_synthesize_missing_voice_error(monkeypatch):
    """Verify 503 Service Unavailable when requested voice model does not exist."""
    service = get_tts_service()
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: False)

    def raise_missing(*args, **kwargs):
        raise TTSUnavailableError("Model not found on disk")

    monkeypatch.setattr(service.engine, "get_voice_instance", raise_missing)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/voice/synthesize", json={"text": "Test", "voice": "absent_voice"})
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "TTS_UNAVAILABLE"


@pytest.mark.asyncio
async def test_api_tts_status_and_voices_endpoints():
    """Verify GET /api/v1/voice/tts/status and GET /api/v1/voice/tts/voices."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Status endpoint
        status_resp = await client.get("/api/v1/voice/tts/status")
        assert status_resp.status_code == 200
        sdata = status_resp.json()
        assert sdata["engine_name"] == "piper"
        assert sdata["sample_rate"] == 22050
        assert "is_operational" in sdata

        # Voices endpoint
        voices_resp = await client.get("/api/v1/voice/tts/voices")
        assert voices_resp.status_code == 200
        vdata = voices_resp.json()
        assert isinstance(vdata, list)
        assert len(vdata) >= 2


@pytest.mark.asyncio
async def test_tts_service_db_sync_and_endpoint():
    """Verify TextToSpeechService synchronizes recognized voices with MySQL voice_registry table."""
    from backend.src.infrastructure.database.session import get_session_factory
    from backend.src.infrastructure.models.system import VoiceRegistry
    from sqlalchemy import select

    service = get_tts_service()

    async with get_session_factory()() as db_session:
        synced = await service.sync_voice_registry(session=db_session)
        assert isinstance(synced, list)
        assert len(synced) >= 2
        await db_session.commit()

        # Query database directly
        res = await db_session.execute(select(VoiceRegistry))
        rows = res.scalars().all()
        assert len(rows) >= 2

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/voice/tts/sync")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["synced_voices_count"] >= 2


@pytest.mark.asyncio
async def test_tts_concurrent_synthesis(monkeypatch):
    """Verify that multiple concurrent synthesis requests execute without deadlock or corruption."""
    mock_wav = _create_mock_wav_bytes(duration_sec=0.4, sample_rate=22050)
    service = get_tts_service()
    monkeypatch.setattr(service.engine, "synthesize_wav", lambda text, voice_id, speed: (mock_wav, 0.4, 22050))
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [
            client.post("/api/v1/voice/synthesize", json={"text": f"Concurrent test {i}"})
            for i in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        for r in responses:
            assert r.status_code == 200
            assert r.headers["content-type"] == "audio/wav"
            assert len(r.content) == len(mock_wav)


# ---------------------------------------------------------------------------
# 5. Live Local Model Smoke Test (Only runs if real models are present on disk)
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_real_local_piper_english_and_kannada_synthesis():
    """Smoke test executing real Piper neural synthesis on local CPU with downloaded models."""
    models_dir = Path("data/models/piper")
    en_model = models_dir / "en_US-lessac-medium.onnx"
    kn_model = models_dir / "kn_IN-syspin_male-medium.onnx"

    if not en_model.exists() or not kn_model.exists():
        pytest.skip("Local Piper ONNX models not provisioned in data/models/piper; skipping smoke test.")

    engine = PiperEngine(models_dir=models_dir)

    # 1. Real English synthesis
    wav_en, dur_en, sr_en = engine.synthesize_wav("Welcome to Belur.", engine.settings.TTS_VOICE_EN)
    assert len(wav_en) > 1000
    assert dur_en > 0.1
    assert sr_en == 22050

    # 2. Real Kannada synthesis
    wav_kn, dur_kn, sr_kn = engine.synthesize_wav("ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ.", engine.settings.TTS_VOICE_KN)
    assert len(wav_kn) > 1000
    assert dur_kn > 0.1
    assert sr_kn == 22050


# ---------------------------------------------------------------------------
# 6. Preservation of Existing Contracts (STT, Chat, Grounding Guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_existing_stt_endpoints_unaffected():
    """Verify GET /api/v1/voice/info contract is preserved and operational."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/voice/info")
        assert resp.status_code == 200
        info = resp.json()
        assert "model_name" in info
        assert "supported_formats" in info
        assert "is_cuda_available" in info


@pytest.mark.asyncio
async def test_grounding_guard_and_canonical_fallback_preserved_with_tts(monkeypatch):
    """Verify strict GroundingGuard fallback is untouched and passes cleanly to TTS without modification."""
    from backend.src.application.chat.grounding_guard import CANONICAL_FALLBACK_KN
    mock_wav = _create_mock_wav_bytes(duration_sec=0.5, sample_rate=22050)
    service = get_tts_service()
    monkeypatch.setattr(service.engine, "synthesize_wav", lambda text, voice_id, speed: (mock_wav, 0.5, 22050))
    monkeypatch.setattr(service.engine, "is_voice_available", lambda _: True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Chat query triggering canonical fallback
        chat_resp = await client.post(
            "/api/v1/chat/message",
            json={"content": "ಮೈಸೂರು ಅರಮನೆ ಇತಿಹಾಸವೇನು?", "preferred_language": "kn"},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert chat_data["is_grounded"] is False
        assert chat_data["content"] == CANONICAL_FALLBACK_KN

        # 2. Pass exact ungrounded response to TTS synthesis
        tts_resp = await client.post(
            "/api/v1/voice/synthesize",
            json={"text": chat_data["content"], "language": "kn"},
        )
        assert tts_resp.status_code == 200
        assert tts_resp.headers["content-type"] == "audio/wav"
        assert tts_resp.headers["x-tts-language"] == "kn"

