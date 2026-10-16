"""Application-level offline Text-to-Speech service orchestrating Piper, caching, and language safety."""

import asyncio
import time
from typing import Any

from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.core.config import get_settings
from backend.src.core.errors import (
    TTSTimeoutError,
    TTSTooLargeError,
    TTSUnavailableError,
    TTSValidationError,
)
from backend.src.core.logging import get_logger
from backend.src.domain.voice import (
    SynthesisMetadata,
    SynthesisRequest,
    TTSEngineStatus,
    TTSVoiceInfo,
)
from backend.src.infrastructure.audio.piper_engine import PiperEngine, get_piper_engine
from backend.src.infrastructure.audio.tts_cache import TTSAudioCache

logger = get_logger("application.voice.tts_service")


class TextToSpeechService:
    """Orchestrates multilingual offline speech synthesis with in-memory caching and bounded threads."""

    def __init__(
        self,
        piper_engine: PiperEngine | None = None,
        language_detector: LanguageDetector | None = None,
        cache: TTSAudioCache | None = None,
    ) -> None:
        self.settings = get_settings()
        self.engine = piper_engine or get_piper_engine()
        self.language_detector = language_detector or LanguageDetector()
        self.cache = cache or TTSAudioCache(
            max_entries=self.settings.TTS_CACHE_MAX_ENTRIES,
            max_text_length=self.settings.TTS_CACHE_MAX_TEXT_LENGTH,
        )

    def validate_request(self, request: SynthesisRequest) -> None:
        """Validate input payload boundaries and character limits."""
        text = request.text.strip() if request.text else ""
        if not text:
            raise TTSValidationError(
                "Text content for synthesis cannot be empty or pure whitespace.",
                details={"text_length": 0},
            )

        if len(text) > self.settings.TTS_MAX_TEXT_LENGTH:
            raise TTSTooLargeError(
                f"Synthesis text length ({len(text)} characters) exceeds maximum limit of {self.settings.TTS_MAX_TEXT_LENGTH} characters.",
                details={
                    "character_count": len(text),
                    "max_limit": self.settings.TTS_MAX_TEXT_LENGTH,
                },
            )

    def resolve_language(self, text: str, requested_lang: str | None) -> str:
        """Determine language ('kn' or 'en') using explicit preference or script auto-detection."""
        if requested_lang and requested_lang.strip():
            clean = requested_lang.strip().lower()
            if clean in ("kn", "kn_in", "kannada"):
                return "kn"
            elif clean in ("en", "en_us", "english"):
                return "en"
            else:
                raise TTSValidationError(
                    f"Unsupported language code '{requested_lang}'. Only 'kn' (Kannada) and 'en' (English) are supported.",
                    details={"requested_language": requested_lang, "supported_languages": ["kn", "en"]},
                )

        # Fall back to script-level Unicode language detection
        detection = self.language_detector.detect(text, fallback_language=self.settings.TTS_DEFAULT_LANGUAGE)
        return "kn" if detection.language == "kn" else "en"

    async def synthesize(self, request: SynthesisRequest) -> tuple[bytes, SynthesisMetadata]:
        """Synthesize text into playable WAV audio buffer asynchronously.

        Returns:
            tuple[bytes, SynthesisMetadata]: raw WAV bytes and associated metadata.
        """
        # 1. Check global toggle
        if not self.settings.TTS_ENABLED:
            raise TTSUnavailableError(
                "Offline Text-to-Speech synthesis is disabled by system configuration.",
                details={"config_flag": "TTS_ENABLED"},
            )

        # 2. Validate request
        self.validate_request(request)
        clean_text = request.text.strip()

        # 3. Resolve target language
        target_lang = self.resolve_language(clean_text, request.language)

        # 4. Resolve voice ID
        voice_id = self.engine.resolve_voice_id(language=target_lang, requested_voice=request.voice)

        # 5. Check cache for quick hit
        speed = round(request.speed, 2)
        cached_result = await self.cache.get(text=clean_text, language=target_lang, voice=voice_id, speed=speed)
        if cached_result is not None:
            audio_bytes, duration_sec, sample_rate = cached_result
            metadata = SynthesisMetadata(
                duration_seconds=duration_sec,
                sample_rate=sample_rate,
                audio_format="wav",
                audio_bytes_length=len(audio_bytes),
                latency_ms=1,  # Sub-millisecond cache hit
                cached=True,
                engine=self.settings.TTS_ENGINE,
                voice=voice_id,
                language=target_lang,
                client_fallback_recommended=False,
            )
            logger.info(
                "tts_synthesis_cache_hit",
                language=target_lang,
                voice=voice_id,
                text_len=len(clean_text),
                bytes_len=len(audio_bytes),
            )
            return audio_bytes, metadata

        # 6. Deduplicate concurrent requests for identical short phrases
        lock = await self.cache.get_or_create_lock(text=clean_text, language=target_lang, voice=voice_id, speed=speed)
        try:
            async with lock:
                # Double-check cache inside lock in case earlier concurrent request populated it
                cached_result = await self.cache.get(text=clean_text, language=target_lang, voice=voice_id, speed=speed)
                if cached_result is not None:
                    audio_bytes, duration_sec, sample_rate = cached_result
                    metadata = SynthesisMetadata(
                        duration_seconds=duration_sec,
                        sample_rate=sample_rate,
                        audio_format="wav",
                        audio_bytes_length=len(audio_bytes),
                        latency_ms=2,
                        cached=True,
                        engine=self.settings.TTS_ENGINE,
                        voice=voice_id,
                        language=target_lang,
                        client_fallback_recommended=False,
                    )
                    return audio_bytes, metadata

                # 7. Offload CPU synthesis to bounded thread pool with timeout guard
                t0 = time.perf_counter()
                try:
                    audio_bytes, duration_sec, sample_rate = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.engine.synthesize_wav,
                            text=clean_text,
                            voice_id=voice_id,
                            speed=speed,
                        ),
                        timeout=self.settings.TTS_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "tts_synthesis_timed_out",
                        language=target_lang,
                        voice=voice_id,
                        timeout=self.settings.TTS_TIMEOUT_SECONDS,
                    )
                    raise TTSTimeoutError(
                        f"Speech synthesis operation timed out after {self.settings.TTS_TIMEOUT_SECONDS}s.",
                        details={"timeout_seconds": self.settings.TTS_TIMEOUT_SECONDS},
                    )

                latency_ms = int((time.perf_counter() - t0) * 1000)

                # 8. Store into cache if text is eligible
                await self.cache.put(
                    text=clean_text,
                    language=target_lang,
                    voice=voice_id,
                    speed=speed,
                    audio_data=(audio_bytes, duration_sec, sample_rate),
                )

                metadata = SynthesisMetadata(
                    duration_seconds=duration_sec,
                    sample_rate=sample_rate,
                    audio_format="wav",
                    audio_bytes_length=len(audio_bytes),
                    latency_ms=latency_ms,
                    cached=False,
                    engine=self.settings.TTS_ENGINE,
                    voice=voice_id,
                    language=target_lang,
                    client_fallback_recommended=False,
                )

                logger.info(
                    "tts_synthesis_completed",
                    language=target_lang,
                    voice=voice_id,
                    text_len=len(clean_text),
                    duration_s=duration_sec,
                    bytes_len=len(audio_bytes),
                    latency_ms=latency_ms,
                )

                return audio_bytes, metadata

        finally:
            await self.cache.cleanup_lock(text=clean_text, language=target_lang, voice=voice_id, speed=speed)

    def get_status(self) -> TTSEngineStatus:
        """Get composite runtime status for the TTS engine and cache."""
        status = self.engine.get_status()
        cache_stats = self.cache.stats
        status.cache_entries = cache_stats["entries"]
        status.cache_hits = cache_stats["hits"]
        status.cache_misses = cache_stats["misses"]
        return status

    def get_available_voices(self) -> list[TTSVoiceInfo]:
        """List registered and discovered local voices."""
        return self.engine.get_installed_voices()

    async def sync_voice_registry(self, session: Any) -> list[Any]:
        """Synchronize recognized offline voice models into the relational voice_registry table."""
        from sqlalchemy import select
        from backend.src.infrastructure.models.system import VoiceRegistry

        voices = self.get_available_voices()
        stmt = select(VoiceRegistry)
        result = await session.execute(stmt)
        existing_rows = {r.voice_id: r for r in result.scalars().all()}

        synced_records: list[VoiceRegistry] = []
        for v in voices:
            if v.voice_id in existing_rows:
                record = existing_rows[v.voice_id]
                record.language_code = v.language_code
                record.engine = v.engine
                record.model_path = v.model_path
                record.is_active = v.is_available
                session.add(record)
                synced_records.append(record)
            else:
                new_record = VoiceRegistry(
                    voice_id=v.voice_id,
                    language_code=v.language_code,
                    engine=v.engine,
                    model_path=v.model_path,
                    is_active=v.is_available,
                )
                session.add(new_record)
                synced_records.append(new_record)

        await session.flush()
        logger.info("voice_registry_synchronized", count=len(synced_records))
        return synced_records


_tts_service_singleton: TextToSpeechService | None = None


def get_tts_service() -> TextToSpeechService:
    """Return cached TextToSpeechService singleton."""
    global _tts_service_singleton
    if _tts_service_singleton is None:
        _tts_service_singleton = TextToSpeechService()
    return _tts_service_singleton
