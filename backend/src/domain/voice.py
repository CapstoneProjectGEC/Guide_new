"""Domain models and contracts for offline speech-to-text transcription."""

from typing import Any
from pydantic import BaseModel, Field
from backend.src.domain.conversation import ChatMessageResponse


class TranscriptionSegment(BaseModel):
    """Timestamped segment transcribed by Whisper."""

    id: int = Field(description="Segment sequence index")
    start: float = Field(description="Segment start offset in seconds")
    end: float = Field(description="Segment end offset in seconds")
    text: str = Field(description="Transcribed text for this segment")
    avg_logprob: float = Field(default=0.0, description="Average log probability (confidence metric)")
    no_speech_prob: float = Field(default=0.0, description="Probability that segment contains no speech")
    words: list[dict[str, Any]] | None = Field(default=None, description="Optional word-level timestamps")


class TranscriptionResult(BaseModel):
    """Transcription response payload for voice endpoints."""

    text: str = Field(description="Full concatenated speech transcript")
    detected_language: str = Field(description="Detected language code ('kn', 'en', etc.)")
    language_probability: float = Field(description="Confidence of language detection (0.0 to 1.0)")
    duration_seconds: float = Field(description="Total audio duration in seconds")
    is_silent: bool = Field(default=False, description="Flag indicating silence or lack of speech")
    device: str = Field(description="Inference device used ('cuda' or 'cpu')")
    compute_type: str = Field(description="Precision compute type used ('float16', 'int8', etc.)")
    model_name: str = Field(description="Whisper model name used (e.g. 'base')")
    latency_ms: int = Field(description="Transcription execution latency in milliseconds")
    segments: list[TranscriptionSegment] = Field(default_factory=list, description="Individual transcribed segments")


class VoiceChatResponse(BaseModel):
    """Composite response uniting speech transcript with conversational RAG answer."""

    transcription: TranscriptionResult = Field(description="Audio transcription result")
    chat_response: ChatMessageResponse = Field(description="Grounded conversational assistant response")


class VoiceEngineInfo(BaseModel):
    """Metadata describing the offline Whisper engine status and capabilities."""

    model_name: str
    device: str
    compute_type: str
    is_cuda_available: bool
    cuda_device_name: str | None = None
    supported_formats: list[str] = Field(default_factory=list)
    max_audio_size_bytes: int
    max_audio_duration_seconds: float


class SynthesisRequest(BaseModel):
    """Request payload for text-to-speech synthesis."""

    text: str = Field(description="Text content to synthesize into speech (max 1000 chars)")
    language: str | None = Field(default=None, description="Optional language code ('kn', 'en', 'kn_IN', 'en_US')")
    voice: str | None = Field(default=None, description="Optional specific voice identifier")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Playback speech rate multiplier")


class SynthesisMetadata(BaseModel):
    """Synthesis execution and audio metadata."""

    duration_seconds: float = Field(description="Synthesized audio duration in seconds")
    sample_rate: int = Field(default=22050, description="Audio sample rate in Hz")
    audio_format: str = Field(default="wav", description="Audio container format")
    audio_bytes_length: int = Field(description="Size of output audio in bytes")
    latency_ms: int = Field(description="Synthesis processing latency in milliseconds")
    cached: bool = Field(default=False, description="Whether audio was served from LRU cache")
    engine: str = Field(default="piper", description="TTS engine name")
    voice: str = Field(description="Voice model identifier used")
    language: str = Field(description="Target language code ('kn' or 'en')")
    client_fallback_recommended: bool = Field(default=False, description="Flag indicating frontend should fall back to Web Speech API")


class TTSVoiceInfo(BaseModel):
    """Information regarding a registered TTS voice."""

    voice_id: str = Field(description="Unique voice model ID")
    language_code: str = Field(description="Supported language code ('kn' or 'en')")
    engine: str = Field(default="piper", description="TTS engine name")
    model_path: str = Field(description="Local model file path")
    is_available: bool = Field(description="Whether model files are present on disk")
    sample_rate: int = Field(default=22050, description="Sampling rate in Hz")


class TTSEngineStatus(BaseModel):
    """Offline TTS subsystem health and runtime status."""

    is_enabled: bool = Field(description="Whether TTS service is globally enabled")
    is_operational: bool = Field(description="Whether at least one voice model is operational")
    engine_name: str = Field(default="piper", description="Primary TTS engine")
    device: str = Field(default="cpu", description="Inference compute device ('cpu' or 'cuda')")
    sample_rate: int = Field(default=22050, description="Default audio sample rate in Hz")
    installed_voices: list[str] = Field(default_factory=list, description="IDs of installed voice models")
    supported_languages: list[str] = Field(default_factory=list, description="Supported language codes")
    cache_entries: int = Field(default=0, description="Number of items in LRU cache")
    cache_hits: int = Field(default=0, description="Cache hit count")
    cache_misses: int = Field(default=0, description="Cache miss count")
    client_fallback_recommended: bool = Field(default=False, description="Whether client should prefer Web Speech API")
