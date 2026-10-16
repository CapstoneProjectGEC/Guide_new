"""Administrative management endpoints for model and translation registry synchronization."""

from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.application.translation.translator import TranslationService
from backend.src.application.voice.tts_service import TextToSpeechService, get_tts_service
from backend.src.core.logging import get_logger
from backend.src.domain.auth import AdminRole
from backend.src.infrastructure.database.session import get_db_session
from backend.src.infrastructure.models.auth import Admin
from backend.src.presentation.dependencies.auth import require_role

logger = get_logger("presentation.api.admin_sync")
router = APIRouter(prefix="/admin/sync", tags=["Admin Management"])


@router.post("/voice", status_code=status.HTTP_200_OK)
async def sync_voice_registry_admin(
    current_admin: Admin = Depends(require_role(AdminRole.OPERATOR)),
    tts_service: TextToSpeechService = Depends(get_tts_service),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Synchronize discovered offline Piper voice models into MySQL voice_registry (OPERATOR+)."""
    records = await tts_service.sync_voice_registry(session=session)
    await session.commit()
    logger.info("admin_voice_registry_synced", admin_id=current_admin.id, count=len(records))
    return {
        "status": "success",
        "synced_by": current_admin.username,
        "synced_voices_count": len(records),
        "voices": [
            {
                "voice_id": r.voice_id,
                "language_code": r.language_code,
                "engine": r.engine,
                "is_active": r.is_active,
            }
            for r in records
        ],
    }


@router.post("/translation", status_code=status.HTTP_200_OK)
async def sync_translation_registry_admin(
    current_admin: Admin = Depends(require_role(AdminRole.OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Synchronize installed Argos neural translation packages into MySQL translation_registry (OPERATOR+)."""
    service = TranslationService()
    records = await service.sync_translation_registry(session=session)
    await session.commit()
    logger.info("admin_translation_registry_synced", admin_id=current_admin.id, count=len(records))
    return {
        "status": "success",
        "synced_by": current_admin.username,
        "synced_packages_count": len(records),
        "packages": [
            {
                "source_language": r.source_language,
                "target_language": r.target_language,
                "package_name": r.package_name,
                "is_installed": r.is_installed,
            }
            for r in records
        ],
    }


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_sync_status(
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    tts_service: TextToSpeechService = Depends(get_tts_service),
) -> dict[str, Any]:
    """Inspect current registry sync status across voice and translation subsystems (VIEWER+)."""
    tts_status = tts_service.get_status()
    translation_service = TranslationService()
    trans_status = translation_service.get_status()

    return {
        "status": "operational",
        "voice": {
            "engine": tts_status.engine_name,
            "installed_voices": tts_status.installed_voices,
            "operational": tts_status.is_operational,
        },
        "translation": {
            "engine": trans_status["engine"],
            "installed_packages_count": trans_status["installed_packages_count"],
            "kn_en_available": trans_status["kn_en_available"],
            "en_kn_available": trans_status["en_kn_available"],
        },
    }
