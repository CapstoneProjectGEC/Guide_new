"""Application configuration management via pydantic-settings."""

from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = Field(default="AI-Powered Smart Tourist Guide Platform for Karnataka")
    APP_VERSION: str = Field(default="0.1.0")
    APP_PROFILE: Literal["dev", "standalone", "cloud"] = Field(default="dev")
    API_PREFIX: str = Field(default="/api/v1")
    DEBUG: bool = Field(default=False)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    )
    LOG_LEVEL: str = Field(default="INFO")

    # MySQL 8.0 Persistence Configuration
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_USER: str = Field(default="root")
    DB_PASSWORD: str = Field(default="root")
    DB_NAME: str = Field(default="karnataka_tourism")
    DB_POOL_SIZE: int = Field(default=10)
    DB_MAX_OVERFLOW: int = Field(default=20)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_ECHO: bool = Field(default=False)

    # Security & JWT Configuration (Admin Only)
    JWT_SECRET_KEY: str = Field(
        default="karnataka-heritage-belur-secret-key-change-in-prod-2026"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Document Storage & Ingestion Limits
    DOCUMENT_STORAGE_PATH: str = Field(default="data/documents")
    MAX_DOCUMENT_SIZE_BYTES: int = Field(default=52428800)  # 50 MB

    # Vector Storage & Knowledge Base Pipeline Configuration
    CHROMA_PERSIST_DIRECTORY: str = Field(default="data/chroma")
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2")
    EMBEDDING_DIMENSIONS: int = Field(default=384)
    CHUNK_SIZE_TOKENS: int = Field(default=400)
    CHUNK_OVERLAP_TOKENS: int = Field(default=50)

    # Hybrid RAG Retrieval & Re-ranking Configuration
    CROSS_ENCODER_MODEL_NAME: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    RAG_DENSE_TOP_K: int = Field(default=15)
    RAG_SPARSE_TOP_K: int = Field(default=15)
    RAG_FUSED_TOP_K: int = Field(default=10)
    RAG_FINAL_TOP_K: int = Field(default=4)
    RAG_CONFIDENCE_THRESHOLD: float = Field(default=0.35)
    RAG_RRF_K: int = Field(default=60)

    # Local Ollama LLM Inference Configuration (127.0.0.1:11434)
    OLLAMA_BASE_URL: str = Field(default="http://127.0.0.1:11434")
    OLLAMA_MODEL: str = Field(default="gemma3:4b")
    OLLAMA_NUM_CTX: int = Field(default=4096)
    OLLAMA_NUM_PREDICT: int = Field(default=160)
    OLLAMA_TEMPERATURE: float = Field(default=0.1)
    OLLAMA_TOP_K: int = Field(default=20)
    OLLAMA_TOP_P: float = Field(default=0.8)
    OLLAMA_KEEP_ALIVE: str = Field(default="-1")  # -1 keeps resident in GPU VRAM
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=30.0)
    OLLAMA_CONNECT_TIMEOUT_SECONDS: float = Field(default=5.0)
    PROMPT_CONTEXT_CEILING_TOKENS: int = Field(default=1500)

    # Phase 10: Local Speech-To-Text (faster-whisper) Configuration
    WHISPER_MODEL_NAME: str = Field(default="base")
    WHISPER_DEVICE: str = Field(default="auto")  # "auto", "cuda", "cpu"
    WHISPER_COMPUTE_TYPE: str = Field(default="auto")  # "auto", "float16", "int8", "float32"
    WHISPER_CPU_THREADS: int = Field(default=4)
    WHISPER_BEAM_SIZE: int = Field(default=5)
    WHISPER_VAD_FILTER: bool = Field(default=True)
    WHISPER_TIMEOUT_SECONDS: float = Field(default=30.0)
    MAX_AUDIO_SIZE_BYTES: int = Field(default=26214400)  # 25 MB
    MIN_AUDIO_DURATION_SECONDS: float = Field(default=0.3)
    MAX_AUDIO_DURATION_SECONDS: float = Field(default=60.0)
    AUDIO_SILENCE_ENERGY_THRESHOLD: float = Field(default=0.002)

    # Phase 12: Offline Text-To-Speech (TTS / Piper) Configuration
    TTS_ENABLED: bool = Field(default=True)
    TTS_ENGINE: str = Field(default="piper")
    TTS_MODELS_DIR: str = Field(default="data/models/piper")
    TTS_VOICE_EN: str = Field(default="en_US-lessac-medium")
    TTS_VOICE_KN: str = Field(default="kn_IN-syspin_male-medium")
    TTS_DEFAULT_LANGUAGE: str = Field(default="en")
    TTS_MAX_TEXT_LENGTH: int = Field(default=1000)
    TTS_CACHE_MAX_ENTRIES: int = Field(default=128)
    TTS_CACHE_MAX_TEXT_LENGTH: int = Field(default=150)
    TTS_TIMEOUT_SECONDS: float = Field(default=15.0)
    TTS_SAMPLE_RATE: int = Field(default=22050)
    TTS_USE_CUDA: bool = Field(default=False)  # Keep on CPU to preserve VRAM for LLM
    TTS_ALLOW_CLIENT_FALLBACK: bool = Field(default=True)

    # Phase 13: Unified Client Gateway & Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_TOURIST_RPM: int = Field(default=60)
    RATE_LIMIT_ADMIN_RPM: int = Field(default=120)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    RATE_LIMIT_MAX_TRACKED_CLIENTS: int = Field(default=10000)
    TRUSTED_PROXIES: list[str] = Field(default=["127.0.0.1", "::1", "localhost"])

    @property
    def cors_allow_credentials(self) -> bool:
        """Allow credentials only when origins are explicit and do not contain wildcards."""
        return "*" not in self.CORS_ORIGINS

    @property
    def async_database_url(self) -> str:
        """Asynchronous database connection URL using asyncmy."""
        return f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    @property
    def sync_database_url(self) -> str:
        """Synchronous database connection URL using pymysql."""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
