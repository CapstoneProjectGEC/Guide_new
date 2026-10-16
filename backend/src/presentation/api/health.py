"""Health, liveness, and readiness probe endpoints."""

from datetime import datetime, timezone
import time
from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.src.core.config import Settings, get_settings
from backend.src.infrastructure.database.session import check_database_health

router = APIRouter(tags=["System Health"])

START_TIME = time.time()


class HealthResponse(BaseModel):
    """Comprehensive health probe response schema."""

    status: str = Field(default="healthy", description="Overall system health status: healthy, degraded, or unhealthy")
    version: str = Field(description="Application semantic version")
    profile: str = Field(description="Active deployment profile: dev, standalone, or cloud")
    uptime_seconds: float = Field(description="Total server process uptime in seconds")
    timestamp: str = Field(description="Current UTC timestamp in ISO 8601 format")
    components: dict[str, Any] = Field(default_factory=dict, description="Subsystem health and optional AI model statuses")


class SimpleProbeResponse(BaseModel):
    """Lightweight probe response schema for orchestrator health checks."""

    status: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return application health, version, deployment profile, and component probes.

    Note:
        Application health reflects core API and database operational status.
        Optional local voice models (Whisper STT, Piper TTS) are reported under
        components but do not degrade overall application health if unprovisioned.
    """
    uptime = round(time.time() - START_TIME, 2)
    db_health = await check_database_health()

    # Optional subsystem probes
    voice_stt_info: dict[str, Any] = {"status": "available"}
    voice_tts_info: dict[str, Any] = {"status": "available"}

    try:
        from backend.src.infrastructure.audio.whisper_engine import get_whisper_engine
        stt_info = get_whisper_engine().get_info()
        voice_stt_info = {
            "status": "ready",
            "device": stt_info.device,
            "model": stt_info.model_name,
        }
    except Exception as exc:
        voice_stt_info = {"status": "degraded_or_uninitialized", "error": str(exc)}

    try:
        from backend.src.infrastructure.audio.piper_engine import get_piper_engine
        tts_status = get_piper_engine().get_status()
        voice_tts_info = {
            "status": "ready" if tts_status.is_operational else "models_unprovisioned",
            "device": tts_status.device,
            "installed_voices": tts_status.installed_voices,
        }
    except Exception as exc:
        voice_tts_info = {"status": "uninitialized", "error": str(exc)}

    overall_status = "healthy" if db_health.get("status") == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        profile=settings.APP_PROFILE,
        uptime_seconds=uptime,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components={
            "api": "healthy",
            "database": db_health,
            "speech_to_text": voice_stt_info,
            "text_to_speech": voice_tts_info,
        },
    )


@router.get("/health/live", response_model=SimpleProbeResponse, status_code=status.HTTP_200_OK)
async def get_liveness() -> SimpleProbeResponse:
    """Kubernetes/Container liveness probe verifying process is responsive."""
    return SimpleProbeResponse(status="alive", uptime_seconds=round(time.time() - START_TIME, 2))


@router.get("/health/ready")
async def get_readiness() -> JSONResponse:
    """Kubernetes/Container readiness probe verifying database connectivity."""
    db_health = await check_database_health()
    uptime = round(time.time() - START_TIME, 2)

    if db_health.get("status") == "healthy":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready", "database": "connected", "uptime_seconds": uptime},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "database": "unavailable", "uptime_seconds": uptime},
        )
