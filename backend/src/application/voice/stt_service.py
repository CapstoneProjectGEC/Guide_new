"""Application service coordinating audio validation, normalization, and offline transcription."""

import asyncio
import io
import time
from typing import BinaryIO
import numpy as np

from backend.src.core.config import get_settings
from backend.src.core.errors import AudioTimeoutError, AudioTooLargeError, AudioValidationError
from backend.src.core.logging import get_logger
from backend.src.domain.voice import TranscriptionResult
from backend.src.infrastructure.audio.whisper_engine import WhisperEngine, get_whisper_engine

logger = get_logger("application.voice.stt_service")

ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".ogg", ".m4a"}
ALLOWED_MIME_TYPES = {
    "audio/webm",
    "video/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "application/ogg",
    "audio/m4a",
    "audio/mp4",
    "audio/x-m4a",
    "application/octet-stream",  # Often sent by browsers for binary audio blobs
}


class SpeechToTextService:
    """Coordinates audio payload verification, format normalization, and Whisper transcription."""

    def __init__(self, whisper_engine: WhisperEngine | None = None) -> None:
        self.settings = get_settings()
        self.whisper_engine = whisper_engine or get_whisper_engine()

    def validate_payload_meta(self, filename: str | None, content_type: str | None, size_bytes: int) -> None:
        """Validate audio metadata before reading or decoding full stream."""
        if size_bytes > self.settings.MAX_AUDIO_SIZE_BYTES:
            raise AudioTooLargeError(
                f"Audio payload size ({size_bytes} bytes) exceeds maximum allowable limit of {self.settings.MAX_AUDIO_SIZE_BYTES} bytes."
            )

        if size_bytes < 32:
            raise AudioValidationError("Audio payload is empty or too small to contain valid audio data.")

        # Validate extension if filename is provided
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext and ext not in ALLOWED_AUDIO_EXTENSIONS:
                raise AudioValidationError(
                    f"Unsupported audio extension '{ext}'. Supported formats: {sorted(ALLOWED_AUDIO_EXTENSIONS)}."
                )

        # Validate mime type if provided and not generic octet-stream
        if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
            raise AudioValidationError(
                f"Unsupported audio MIME type '{content_type}'. Allowed types: WebM, WAV, MP3, OGG, M4A."
            )

    def decode_and_normalize(self, audio_bytes: bytes) -> np.ndarray:
        """Decode incoming audio buffer into 16kHz mono float32 PCM numpy array."""
        import av
        from faster_whisper.audio import decode_audio

        try:
            buffer = io.BytesIO(audio_bytes)
            audio_array = decode_audio(buffer, sampling_rate=16000)
        except (av.error.InvalidDataError, av.error.FFmpegError, ValueError) as exc:
            logger.warning("audio_decode_failed", error=str(exc))
            raise AudioValidationError(f"Malformed or corrupt audio data: {str(exc)}") from exc
        except Exception as exc:
            logger.warning("audio_decode_unhandled_failure", error=str(exc))
            raise AudioValidationError(f"Could not parse audio container: {str(exc)}") from exc

        if not isinstance(audio_array, np.ndarray) or len(audio_array) == 0:
            raise AudioValidationError("Audio decoding yielded an empty signal.")

        return audio_array

    def validate_signal_properties(self, audio_array: np.ndarray) -> tuple[float, float, bool]:
        """Verify audio duration and detect pure silence via RMS signal energy."""
        duration_seconds = len(audio_array) / 16000.0

        if duration_seconds < self.settings.MIN_AUDIO_DURATION_SECONDS:
            raise AudioValidationError(
                f"Audio duration ({duration_seconds:.2f}s) is below the minimum threshold of {self.settings.MIN_AUDIO_DURATION_SECONDS}s."
            )

        if duration_seconds > self.settings.MAX_AUDIO_DURATION_SECONDS:
            raise AudioValidationError(
                f"Audio duration ({duration_seconds:.2f}s) exceeds the maximum allowed duration of {self.settings.MAX_AUDIO_DURATION_SECONDS}s."
            )

        # Calculate Root-Mean-Square (RMS) signal energy
        rms_energy = float(np.sqrt(np.mean(np.square(audio_array))))
        peak_energy = float(np.max(np.abs(audio_array)))

        is_silent = rms_energy < self.settings.AUDIO_SILENCE_ENERGY_THRESHOLD or peak_energy < 0.001

        return duration_seconds, rms_energy, is_silent

    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        filename: str | None = None,
        content_type: str | None = None,
        language: str | None = None,
        word_timestamps: bool = False,
    ) -> TranscriptionResult:
        """Complete speech-to-text pipeline: validate, decode, check silence, and transcribe."""
        t_start = time.perf_counter()

        # 1. Metadata check
        self.validate_payload_meta(filename=filename, content_type=content_type, size_bytes=len(audio_bytes))

        # 2. Decoding & resampling to 16kHz float32
        audio_array = self.decode_and_normalize(audio_bytes)

        # 3. Signal property check (duration & silence)
        duration_sec, rms_energy, is_silent = self.validate_signal_properties(audio_array)

        # 4. Immediate shortcut on pure silence
        if is_silent:
            latency_ms = int((time.perf_counter() - t_start) * 1000.0)
            logger.info("audio_silence_detected", duration=duration_sec, rms_energy=rms_energy, latency_ms=latency_ms)
            return TranscriptionResult(
                text="",
                detected_language=language or "kn",
                language_probability=0.0,
                duration_seconds=round(duration_sec, 2),
                is_silent=True,
                device=self.whisper_engine.active_device,
                compute_type=self.whisper_engine.active_compute_type,
                model_name=self.whisper_engine.model_name,
                latency_ms=latency_ms,
                segments=[],
            )

        # 5. Whisper inference with timeout protection
        try:
            result = await self.whisper_engine.transcribe(
                audio_input=audio_array,
                language=language,
                word_timestamps=word_timestamps,
                timeout_seconds=self.settings.WHISPER_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            logger.error("audio_transcription_timeout", duration=duration_sec)
            raise AudioTimeoutError(
                f"Audio transcription timed out after {self.settings.WHISPER_TIMEOUT_SECONDS}s."
            ) from exc

        # Total latency including decoding and validation
        total_latency_ms = int((time.perf_counter() - t_start) * 1000.0)
        result.latency_ms = total_latency_ms

        logger.info(
            "speech_transcription_completed",
            language=result.detected_language,
            prob=result.language_probability,
            duration=result.duration_seconds,
            latency_ms=result.latency_ms,
            device=result.device,
            char_len=len(result.text),
        )
        return result
