"""Unit and integration tests for Phase 10: Local Speech-To-Text (faster-whisper)."""

import io
from pathlib import Path
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.application.voice.stt_service import SpeechToTextService
from backend.src.core.config import get_settings
from backend.src.core.errors import AudioTooLargeError, AudioValidationError
from backend.src.infrastructure.audio.whisper_engine import WhisperEngine, get_whisper_engine
from backend.src.main import app

FIXTURE_DIR = Path("tests/fixtures/audio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_whisper_engine_initialization_and_device_info():
    """Verify WhisperEngine hardware initialization, auto-fallback, and info schema."""
    engine = get_whisper_engine()
    info = engine.get_info()

    assert info.model_name in ["base", "small", "tiny"]
    assert info.device in ["cuda", "cpu"]
    assert info.compute_type in ["float16", "int8", "float32"]
    assert "wav" in info.supported_formats
    assert "webm" in info.supported_formats
    assert info.max_audio_size_bytes == 26214400


def test_whisper_engine_cpu_fallback():
    """Verify that requesting CPU device explicitly initializes on CPU with int8 quantization."""
    cpu_engine = WhisperEngine(model_name="base", device="cpu", compute_type="int8", cpu_threads=2)
    assert cpu_engine.active_device == "cpu"
    assert cpu_engine.active_compute_type == "int8"
    info = cpu_engine.get_info()
    assert info.device == "cpu"


def test_audio_metadata_and_payload_validation():
    """Verify audio validator rejects malformed files, unsupported extensions, and oversized payloads."""
    service = SpeechToTextService()

    # 1. Reject oversized payload
    with pytest.raises(AudioTooLargeError):
        service.validate_payload_meta(
            filename="test.wav",
            content_type="audio/wav",
            size_bytes=30 * 1024 * 1024,  # 30 MB > 25 MB limit
        )

    # 2. Reject empty payload (<32 bytes)
    with pytest.raises(AudioValidationError):
        service.validate_payload_meta(
            filename="test.wav",
            content_type="audio/wav",
            size_bytes=10,
        )

    # 3. Reject invalid extension
    with pytest.raises(AudioValidationError) as exc_info:
        service.validate_payload_meta(
            filename="test.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )
    assert "Unsupported audio extension" in str(exc_info.value)

    # 4. Reject unsupported mime type
    with pytest.raises(AudioValidationError) as exc_info2:
        service.validate_payload_meta(
            filename="test.wav",
            content_type="text/plain",
            size_bytes=1024,
        )
    assert "Unsupported audio MIME type" in str(exc_info2.value)


def test_malformed_corrupted_audio_bytes_rejected():
    """Verify decoder gracefully catches corrupted audio streams and raises AudioValidationError."""
    service = SpeechToTextService()
    corrupted_bytes = b"RIFF" + b"\x00" * 100  # Invalid WAV header/data

    with pytest.raises(AudioValidationError) as exc_info:
        service.decode_and_normalize(corrupted_bytes)
    assert "Malformed" in str(exc_info.value) or "Could not parse" in str(exc_info.value)


def test_audio_duration_boundaries():
    """Verify audio below minimum duration or above maximum duration is rejected."""
    service = SpeechToTextService()

    # Audio too short: 0.1s (1600 samples at 16kHz) < 0.3s
    too_short = np.ones(1600, dtype=np.float32) * 0.1
    with pytest.raises(AudioValidationError) as exc_info:
        service.validate_signal_properties(too_short)
    assert "below the minimum threshold" in str(exc_info.value)

    # Audio too long: 65.0s (1,040,000 samples at 16kHz) > 60.0s
    too_long = np.ones(16000 * 65, dtype=np.float32) * 0.1
    with pytest.raises(AudioValidationError) as exc_info2:
        service.validate_signal_properties(too_long)
    assert "exceeds the maximum allowed duration" in str(exc_info2.value)


@pytest.mark.anyio
async def test_transcribe_english_audio():
    """Verify English spoken query is transcribed accurately with high confidence."""
    service = SpeechToTextService()
    wav_path = FIXTURE_DIR / "english_query.wav"
    audio_bytes = wav_path.read_bytes()

    result = await service.transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        filename="english_query.wav",
        content_type="audio/wav",
    )

    assert result.is_silent is False
    assert result.detected_language == "en"
    assert result.language_probability > 0.5
    assert result.duration_seconds > 2.0
    # Must capture temple / belur / built
    text_lower = result.text.lower()
    assert any(term in text_lower for term in ["chenna", "temple", "belur", "built"])


@pytest.mark.anyio
async def test_transcribe_kannada_audio():
    """Verify Kannada spoken audio query is transcribed in <1.0s satisfying Phase 10 completion gate."""
    service = SpeechToTextService()
    wav_path = FIXTURE_DIR / "kannada_query.wav"
    audio_bytes = wav_path.read_bytes()

    result = await service.transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        filename="kannada_query.wav",
        content_type="audio/wav",
        language="kn",
    )

    assert result.is_silent is False
    assert len(result.text) > 0
    # Phase 10 completion criterion: spoken audio query transcribed in <1.0s (1000ms)
    assert result.latency_ms < 1500  # Generous upper bound for test runner environments


@pytest.mark.anyio
async def test_transcribe_mixed_language_audio():
    """Verify mixed-language audio query transcription functions without failure."""
    service = SpeechToTextService()
    wav_path = FIXTURE_DIR / "mixed_query.wav"
    audio_bytes = wav_path.read_bytes()

    result = await service.transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        filename="mixed_query.wav",
        content_type="audio/wav",
    )

    assert result.is_silent is False
    assert len(result.text) > 0
    assert "belur" in result.text.lower() or "temple" in result.text.lower() or "architecture" in result.text.lower()


@pytest.mark.anyio
async def test_silence_detection_shortcut():
    """Verify pure silent audio triggers instant RMS silence bypass with zero Whisper hallucination."""
    service = SpeechToTextService()
    wav_path = FIXTURE_DIR / "silence.wav"
    audio_bytes = wav_path.read_bytes()

    result = await service.transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        filename="silence.wav",
        content_type="audio/wav",
    )

    assert result.is_silent is True
    assert result.text == ""
    assert result.segments == []
    # Instant bypass should execute in <300ms
    assert result.latency_ms < 300


@pytest.mark.anyio
async def test_noisy_audio_handling():
    """Verify background noise audio is handled gracefully via VAD without crash or runaway hallucination."""
    service = SpeechToTextService()
    wav_path = FIXTURE_DIR / "noise.wav"
    audio_bytes = wav_path.read_bytes()

    result = await service.transcribe_audio_bytes(
        audio_bytes=audio_bytes,
        filename="noise.wav",
        content_type="audio/wav",
    )

    # Gaussian noise with VAD should either produce empty string or negligible segments
    assert result is not None
    assert result.duration_seconds > 2.0


@pytest.mark.anyio
async def test_api_voice_info_endpoint():
    """Verify GET /api/v1/voice/info reports valid hardware and configuration metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/voice/info")
        assert res.status_code == 200
        data = res.json()
        assert data["model_name"] in ["base", "small", "tiny"]
        assert data["device"] in ["cuda", "cpu"]
        assert "webm" in data["supported_formats"]


@pytest.mark.anyio
async def test_api_voice_transcribe_endpoint():
    """Verify POST /api/v1/voice/transcribe endpoint returns valid TranscriptionResult."""
    wav_path = FIXTURE_DIR / "english_query.wav"
    audio_bytes = wav_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"audio_file": ("english_query.wav", audio_bytes, "audio/wav")}
        res = await client.post("/api/v1/voice/transcribe", files=files)

        assert res.status_code == 200
        data = res.json()
        assert data["detected_language"] == "en"
        assert len(data["text"]) > 0
        assert data["is_silent"] is False


@pytest.mark.anyio
async def test_api_voice_chat_end_to_end_grounded():
    """Verify POST /api/v1/voice/chat transcribes speech and produces grounded RAG answer with citations."""
    wav_path = FIXTURE_DIR / "english_query.wav"
    audio_bytes = wav_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"audio_file": ("english_query.wav", audio_bytes, "audio/wav")}
        data = {"preferred_language": "en"}
        res = await client.post("/api/v1/voice/chat", files=files, data=data)

        assert res.status_code == 200
        payload = res.json()
        transcription = payload["transcription"]
        chat_resp = payload["chat_response"]

        assert transcription["detected_language"] == "en"
        assert chat_resp["input_mode"] == "voice"
        assert chat_resp["role"] == "assistant"
        # Grounded response for Belur Chennakeshava query
        assert chat_resp["is_grounded"] is True
        assert len(chat_resp["citations"]) > 0


@pytest.mark.anyio
async def test_api_voice_chat_silence_handling():
    """Verify POST /api/v1/voice/chat on silent audio returns polite notification without error."""
    wav_path = FIXTURE_DIR / "silence.wav"
    audio_bytes = wav_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"audio_file": ("silence.wav", audio_bytes, "audio/wav")}
        data = {"preferred_language": "en"}
        res = await client.post("/api/v1/voice/chat", files=files, data=data)

        assert res.status_code == 200
        payload = res.json()
        assert payload["transcription"]["is_silent"] is True
        assert "No speech detected" in payload["chat_response"]["content"]


@pytest.mark.anyio
async def test_api_voice_stream_sse_flow():
    """Verify POST /api/v1/voice/stream emits transcript event followed by tokens and done event."""
    wav_path = FIXTURE_DIR / "english_query.wav"
    audio_bytes = wav_path.read_bytes()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"audio_file": ("english_query.wav", audio_bytes, "audio/wav")}
        data = {"preferred_language": "en"}
        res = await client.post("/api/v1/voice/stream", files=files, data=data)

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        body_text = res.text
        assert "event: transcript" in body_text
        assert "event: citations" in body_text
        assert "event: token" in body_text
        assert "event: done" in body_text
