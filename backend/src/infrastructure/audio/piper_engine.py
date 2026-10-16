"""Piper TTS infrastructure engine adapter managing local offline ONNX models."""

import io
import os
from pathlib import Path
import threading
import time
import wave
from typing import Any

from backend.src.core.config import get_settings
from backend.src.core.errors import TTSUnavailableError, TTSValidationError
from backend.src.core.logging import get_logger
from backend.src.domain.voice import TTSEngineStatus, TTSVoiceInfo

logger = get_logger("infrastructure.audio.piper_engine")


class PiperEngine:
    """Thread-safe local neural speech synthesizer adapter wrapping Piper."""

    def __init__(self, models_dir: str | Path | None = None) -> None:
        self.settings = get_settings()
        self.models_dir = Path(models_dir or self.settings.TTS_MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self._loaded_voices: dict[str, Any] = {}
        self._voice_locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        self._is_piper_installed = False

        self._check_piper_installation()

    def _check_piper_installation(self) -> None:
        """Check whether the piper library is installed and importable."""
        try:
            import piper  # noqa: F401
            self._is_piper_installed = True
            logger.info("piper_engine_module_available", models_dir=str(self.models_dir))
        except ImportError:
            self._is_piper_installed = False
            logger.warning("piper_module_not_installed", hint="Install via: pip install piper-tts")

    def resolve_voice_id(self, language: str | None, requested_voice: str | None) -> str:
        """Resolve canonical voice model ID from language hint or explicit voice request."""
        if requested_voice and requested_voice.strip():
            v = requested_voice.strip()
            # If given a short code or full voice id, normalize
            if v in ("kn", "kn_IN", "kannada"):
                return self.settings.TTS_VOICE_KN
            if v in ("en", "en_US", "english"):
                return self.settings.TTS_VOICE_EN
            return v

        lang = (language or self.settings.TTS_DEFAULT_LANGUAGE).lower().strip()
        if lang in ("kn", "kn_in", "kannada"):
            return self.settings.TTS_VOICE_KN
        elif lang in ("en", "en_us", "english"):
            return self.settings.TTS_VOICE_EN
        else:
            raise TTSValidationError(
                f"Unsupported language code '{language}'. Supported languages are 'kn' (Kannada) and 'en' (English).",
                details={"supported_languages": ["kn", "en"]},
            )

    def get_voice_file_paths(self, voice_id: str) -> tuple[Path, Path]:
        """Get expected paths for the model ONNX file and JSON config."""
        clean_id = voice_id.removesuffix(".onnx").removesuffix(".json")
        onnx_path = self.models_dir / f"{clean_id}.onnx"
        json_path = self.models_dir / f"{clean_id}.onnx.json"
        return onnx_path, json_path

    def is_voice_available(self, voice_id: str) -> bool:
        """Check whether both .onnx model and .onnx.json config files exist locally."""
        onnx_path, json_path = self.get_voice_file_paths(voice_id)
        return onnx_path.exists() and json_path.exists() and onnx_path.stat().st_size > 1000

    def is_language_available(self, language: str) -> bool:
        """Check if a voice model for the requested language is provisioned on disk."""
        try:
            voice_id = self.resolve_voice_id(language=language, requested_voice=None)
            return self.is_voice_available(voice_id)
        except Exception:
            return False

    def get_voice_instance(self, voice_id: str) -> Any:
        """Lazy-load and return cached thread-safe PiperVoice instance."""
        if not self._is_piper_installed:
            raise TTSUnavailableError(
                "Piper TTS library is not installed in the runtime environment.",
                details={"engine": "piper"},
            )

        onnx_path, json_path = self.get_voice_file_paths(voice_id)
        if not onnx_path.exists() or not json_path.exists():
            raise TTSUnavailableError(
                f"Voice model '{voice_id}' not found at '{onnx_path}'. Please provision model files before inference.",
                details={
                    "voice_id": voice_id,
                    "expected_onnx": str(onnx_path),
                    "expected_json": str(json_path),
                },
            )

        with self._global_lock:
            if voice_id not in self._voice_locks:
                self._voice_locks[voice_id] = threading.Lock()

            if voice_id in self._loaded_voices:
                return self._loaded_voices[voice_id]

            logger.info("loading_piper_voice_model", voice_id=voice_id, path=str(onnx_path))
            try:
                from piper import PiperVoice

                t0 = time.perf_counter()
                voice_instance = PiperVoice.load(
                    model_path=str(onnx_path),
                    config_path=str(json_path),
                    use_cuda=self.settings.TTS_USE_CUDA,
                )
                load_ms = round((time.perf_counter() - t0) * 1000, 2)
                logger.info("piper_voice_loaded_successfully", voice_id=voice_id, latency_ms=load_ms)

                self._loaded_voices[voice_id] = voice_instance
                return voice_instance
            except Exception as exc:
                logger.error("piper_voice_load_failed", voice_id=voice_id, error=str(exc))
                raise TTSUnavailableError(
                    f"Failed to load Piper voice model '{voice_id}': {exc}",
                    details={"voice_id": voice_id, "error": str(exc)},
                )

    def synthesize_wav(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> tuple[bytes, float, int]:
        """Synthesize text into WAV audio bytes using the requested Piper voice.

        Returns:
            tuple[bytes, float, int]: (wav_bytes, duration_seconds, sample_rate)
        """
        voice = self.get_voice_instance(voice_id)
        voice_lock = self._voice_locks[voice_id]

        from piper.config import SynthesisConfig

        # Map speed factor to length_scale: higher speed = shorter duration (lower length_scale)
        length_scale = 1.0 / max(0.5, min(2.0, speed))
        syn_config = SynthesisConfig(length_scale=length_scale)

        with voice_lock:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_file:
                voice.synthesize_wav(text=text, wav_file=wav_file, syn_config=syn_config)

            wav_bytes = buf.getvalue()

        # Extract WAV audio duration and sample rate
        with wave.open(io.BytesIO(wav_bytes), "rb") as r:
            sample_rate = r.getframerate()
            n_frames = r.getnframes()
            duration_seconds = round(n_frames / float(sample_rate), 3) if sample_rate > 0 else 0.0

        return wav_bytes, duration_seconds, sample_rate

    def get_installed_voices(self) -> list[TTSVoiceInfo]:
        """Inspect models directory and return list of all recognized voices."""
        voices: list[TTSVoiceInfo] = []

        # Check default configured voices first
        en_id = self.settings.TTS_VOICE_EN
        kn_id = self.settings.TTS_VOICE_KN

        en_onnx, _ = self.get_voice_file_paths(en_id)
        voices.append(
            TTSVoiceInfo(
                voice_id=en_id,
                language_code="en",
                engine="piper",
                model_path=str(en_onnx),
                is_available=self.is_voice_available(en_id),
                sample_rate=self.settings.TTS_SAMPLE_RATE,
            )
        )

        kn_onnx, _ = self.get_voice_file_paths(kn_id)
        voices.append(
            TTSVoiceInfo(
                voice_id=kn_id,
                language_code="kn",
                engine="piper",
                model_path=str(kn_onnx),
                is_available=self.is_voice_available(kn_id),
                sample_rate=self.settings.TTS_SAMPLE_RATE,
            )
        )

        # Also scan models_dir for any other .onnx files
        if self.models_dir.exists():
            for f in self.models_dir.glob("*.onnx"):
                base_name = f.stem
                if base_name in (en_id, kn_id):
                    continue
                lang_code = "kn" if "kn" in base_name.lower() else "en"
                voices.append(
                    TTSVoiceInfo(
                        voice_id=base_name,
                        language_code=lang_code,
                        engine="piper",
                        model_path=str(f),
                        is_available=self.is_voice_available(base_name),
                        sample_rate=self.settings.TTS_SAMPLE_RATE,
                    )
                )

        return voices

    def get_status(self) -> TTSEngineStatus:
        """Return operational status and metadata for the TTS subsystem."""
        installed = [v.voice_id for v in self.get_installed_voices() if v.is_available]
        supported_langs = []
        if self.is_language_available("en"):
            supported_langs.append("en")
        if self.is_language_available("kn"):
            supported_langs.append("kn")

        is_operational = self._is_piper_installed and len(installed) > 0
        device = "cuda" if self.settings.TTS_USE_CUDA else "cpu"

        return TTSEngineStatus(
            is_enabled=self.settings.TTS_ENABLED,
            is_operational=is_operational,
            engine_name="piper",
            device=device,
            sample_rate=self.settings.TTS_SAMPLE_RATE,
            installed_voices=installed,
            supported_languages=supported_langs,
            client_fallback_recommended=not is_operational,
        )

    def close(self) -> None:
        """Clean up loaded voice models."""
        with self._global_lock:
            self._loaded_voices.clear()
            self._voice_locks.clear()
            logger.info("piper_engine_shutdown")


_piper_singleton: PiperEngine | None = None
_piper_singleton_lock = threading.Lock()


def get_piper_engine() -> PiperEngine:
    """Return cached PiperEngine singleton."""
    global _piper_singleton
    if _piper_singleton is None:
        with _piper_singleton_lock:
            if _piper_singleton is None:
                _piper_singleton = PiperEngine()
    return _piper_singleton
