"""Local offline speech transcription engine wrapping faster-whisper and CTranslate2."""

import asyncio
import io
import os
import sys
import threading
import time
from typing import Any, BinaryIO
import numpy as np

from backend.src.core.config import get_settings
from backend.src.core.logging import get_logger
from backend.src.domain.voice import TranscriptionResult, TranscriptionSegment, VoiceEngineInfo

logger = get_logger("infrastructure.audio.whisper_engine")


def _setup_cuda_dll_paths() -> None:
    """Discover and register Windows CUDA runtime DLL directories (e.g. from Ollama or CUDA toolkit)."""
    if sys.platform != "win32":
        return

    candidate_paths = []
    # 1. Ollama bundled CUDA v12
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        ollama_cuda12 = os.path.join(local_app_data, "Programs", "Ollama", "lib", "ollama", "cuda_v12")
        candidate_paths.append(ollama_cuda12)
        ollama_cuda13 = os.path.join(local_app_data, "Programs", "Ollama", "lib", "ollama", "cuda_v13")
        candidate_paths.append(ollama_cuda13)

    # 2. Standard CUDA toolkit directories
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        candidate_paths.append(os.path.join(cuda_path, "bin"))

    for path in candidate_paths:
        if os.path.exists(path) and os.path.isdir(path):
            try:
                os.add_dll_directory(path)
                curr_path = os.environ.get("PATH", "")
                if path not in curr_path:
                    os.environ["PATH"] = path + os.pathsep + curr_path
                logger.info("cuda_dll_directory_registered", path=path)
            except Exception as exc:
                logger.warning("cuda_dll_directory_registration_failed", path=path, error=str(exc))


# Run discovery at module import
_setup_cuda_dll_paths()


class WhisperEngine:
    """Thread-safe CTranslate2 Faster-Whisper wrapper with automatic CUDA/CPU fallback."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        cpu_threads: int | None = None,
    ) -> None:
        self.settings = get_settings()
        self.model_name = model_name or self.settings.WHISPER_MODEL_NAME
        self.requested_device = device or self.settings.WHISPER_DEVICE
        self.requested_compute_type = compute_type or self.settings.WHISPER_COMPUTE_TYPE
        self.cpu_threads = cpu_threads or self.settings.WHISPER_CPU_THREADS

        self._lock = threading.Lock()
        self._model: Any = None
        self._active_device: str = "cpu"
        self._active_compute_type: str = "int8"
        self._cuda_device_name: str | None = None

        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize faster-whisper with hardware auto-detection and graceful fallback."""
        import ctranslate2
        import faster_whisper

        use_cuda = False
        cuda_count = 0
        try:
            cuda_count = ctranslate2.get_cuda_device_count()
        except Exception:
            cuda_count = 0

        target_device = self.requested_device.lower()
        if target_device in ("auto", "cuda") and cuda_count > 0:
            use_cuda = True

        if use_cuda:
            comp_type = "float16" if self.requested_compute_type in ("auto", "float16") else self.requested_compute_type
            try:
                logger.info(
                    "whisper_initializing_cuda",
                    model=self.model_name,
                    device="cuda",
                    compute_type=comp_type,
                )
                candidate_model = faster_whisper.WhisperModel(
                    self.model_name,
                    device="cuda",
                    compute_type=comp_type,
                )
                # Probe verification: test transcribing 0.2s of zeros to guarantee cublas64_12.dll is loaded
                dummy_audio = np.zeros(3200, dtype=np.float32)
                _ = list(candidate_model.transcribe(dummy_audio, vad_filter=False)[0])

                self._model = candidate_model
                self._active_device = "cuda"
                self._active_compute_type = comp_type
                try:
                    import torch
                    if torch.cuda.is_available():
                        self._cuda_device_name = torch.cuda.get_device_name(0)
                except Exception:
                    self._cuda_device_name = "NVIDIA CUDA Device"

                logger.info(
                    "whisper_initialized_cuda_success",
                    model=self.model_name,
                    device=self._active_device,
                    compute_type=self._active_compute_type,
                )
                return
            except Exception as exc:
                logger.warning(
                    "whisper_cuda_initialization_failed_fallback_cpu",
                    error=str(exc),
                    model=self.model_name,
                )

        # Fallback to CPU
        comp_type = "int8" if self.requested_compute_type in ("auto", "int8") else self.requested_compute_type
        logger.info(
            "whisper_initializing_cpu",
            model=self.model_name,
            device="cpu",
            compute_type=comp_type,
            cpu_threads=self.cpu_threads,
        )
        self._model = faster_whisper.WhisperModel(
            self.model_name,
            device="cpu",
            compute_type=comp_type,
            cpu_threads=self.cpu_threads,
        )
        self._active_device = "cpu"
        self._active_compute_type = comp_type
        logger.info(
            "whisper_initialized_cpu_success",
            model=self.model_name,
            device=self._active_device,
            compute_type=self._active_compute_type,
        )

    @property
    def active_device(self) -> str:
        return self._active_device

    @property
    def active_compute_type(self) -> str:
        return self._active_compute_type

    def get_info(self) -> VoiceEngineInfo:
        """Return engine metadata and hardware properties."""
        import ctranslate2
        cuda_available = False
        try:
            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            pass

        return VoiceEngineInfo(
            model_name=self.model_name,
            device=self._active_device,
            compute_type=self._active_compute_type,
            is_cuda_available=cuda_available,
            cuda_device_name=self._cuda_device_name,
            supported_formats=["webm", "wav", "mp3", "ogg", "m4a"],
            max_audio_size_bytes=self.settings.MAX_AUDIO_SIZE_BYTES,
            max_audio_duration_seconds=self.settings.MAX_AUDIO_DURATION_SECONDS,
        )

    def transcribe_sync(
        self,
        audio_input: np.ndarray | str | BinaryIO,
        language: str | None = None,
        beam_size: int | None = None,
        vad_filter: bool | None = None,
        word_timestamps: bool = False,
    ) -> TranscriptionResult:
        """Synchronously execute transcription with whisper."""
        t_start = time.perf_counter()

        beam = beam_size or self.settings.WHISPER_BEAM_SIZE
        vad = vad_filter if vad_filter is not None else self.settings.WHISPER_VAD_FILTER

        with self._lock:
            segments_gen, info = self._model.transcribe(
                audio_input,
                language=language,
                beam_size=beam,
                vad_filter=vad,
                vad_parameters=dict(min_silence_duration_ms=500),
                word_timestamps=word_timestamps,
            )
            raw_segments = list(segments_gen)

        latency_ms = int((time.perf_counter() - t_start) * 1000.0)

        domain_segments: list[TranscriptionSegment] = []
        for idx, seg in enumerate(raw_segments):
            words_data = None
            if word_timestamps and hasattr(seg, "words") and seg.words:
                words_data = [
                    {
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 3),
                    }
                    for w in seg.words
                ]

            domain_segments.append(
                TranscriptionSegment(
                    id=idx,
                    start=round(float(seg.start), 2),
                    end=round(float(seg.end), 2),
                    text=seg.text.strip(),
                    avg_logprob=round(float(seg.avg_logprob), 4),
                    no_speech_prob=round(float(seg.no_speech_prob), 4),
                    words=words_data,
                )
            )

        full_text = " ".join(s.text for s in domain_segments).strip()
        is_silent = len(domain_segments) == 0 or len(full_text) == 0

        return TranscriptionResult(
            text=full_text,
            detected_language=info.language,
            language_probability=round(float(info.language_probability), 4),
            duration_seconds=round(float(info.duration), 2),
            is_silent=is_silent,
            device=self._active_device,
            compute_type=self._active_compute_type,
            model_name=self.model_name,
            latency_ms=latency_ms,
            segments=domain_segments,
        )

    async def transcribe(
        self,
        audio_input: np.ndarray | str | BinaryIO,
        language: str | None = None,
        beam_size: int | None = None,
        vad_filter: bool | None = None,
        word_timestamps: bool = False,
        timeout_seconds: float | None = None,
    ) -> TranscriptionResult:
        """Asynchronously execute transcription without blocking the event loop."""
        timeout = timeout_seconds or self.settings.WHISPER_TIMEOUT_SECONDS

        return await asyncio.wait_for(
            asyncio.to_thread(
                self.transcribe_sync,
                audio_input=audio_input,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
            ),
            timeout=timeout,
        )


_engine_singleton: WhisperEngine | None = None
_engine_singleton_lock = threading.Lock()


def get_whisper_engine() -> WhisperEngine:
    """Return cached WhisperEngine singleton."""
    global _engine_singleton
    if _engine_singleton is None:
        with _engine_singleton_lock:
            if _engine_singleton is None:
                _engine_singleton = WhisperEngine()
    return _engine_singleton
