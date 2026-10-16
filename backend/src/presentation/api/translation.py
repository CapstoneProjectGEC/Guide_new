"""REST API endpoints for translation registry management and cross-lingual query normalization."""

from typing import Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.application.translation.translator import TranslationService
from backend.src.core.logging import get_logger
from backend.src.domain.translation import NormalizedQuery
from backend.src.infrastructure.database.session import get_db_session

logger = get_logger("presentation.api.translation")
router = APIRouter(prefix="/translation", tags=["Translation & Cross-Lingual"])


class NormalizeQueryRequest(BaseModel):
    """Payload to normalize and expand query for knowledge base retrieval."""

    query: str = Field(min_length=1, max_length=1000, description="Tourist inquiry string")
    source_language: str | None = Field(default=None, description="Optional source language code ('kn' or 'en')")


class TranslationStatusResponse(BaseModel):
    """Status metadata for offline translation runtime and registered language pairs."""

    engine: str
    installed_packages_count: int
    packages: list[dict[str, Any]]
    kn_en_available: bool
    en_kn_available: bool


@router.get("/status", response_model=TranslationStatusResponse, status_code=status.HTTP_200_OK)
async def get_translation_status() -> TranslationStatusResponse:
    """Retrieve operational status of offline Argos engine and available language models."""
    service = TranslationService()
    status_data = service.get_status()
    return TranslationStatusResponse(**status_data)


@router.post("/normalize", response_model=NormalizedQuery, status_code=status.HTTP_200_OK)
async def normalize_query(request: NormalizeQueryRequest) -> NormalizedQuery:
    """Normalize and expand a multilingual query into an English retrieval query."""
    normalizer = QueryNormalizer()
    return normalizer.normalize_for_retrieval(
        query=request.query,
        source_lang=request.source_language,
    )


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_registry(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Synchronize installed offline packages with MySQL translation_registry table."""
    service = TranslationService()
    synced = await service.sync_translation_registry(session=session)
    await session.commit()
    return {
        "status": "success",
        "synced_count": len(synced),
        "synced_records": [
            {
                "id": r.id,
                "source_language": r.source_language,
                "target_language": r.target_language,
                "package_name": r.package_name,
                "is_installed": r.is_installed,
            }
            for r in synced
        ],
    }
