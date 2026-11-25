"""Administrative REST API endpoints for knowledge base generation lifecycle."""

from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.pipeline.generation_manager import KnowledgeGenerationManager
from backend.src.core.errors import NotFoundError
from backend.src.core.logging import get_logger
from backend.src.domain.auth import AdminRole
from backend.src.domain.knowledge import (
    BuildGenerationRequest,
    KnowledgeGenerationListResponse,
    KnowledgeGenerationResponse,
    RollbackRequest,
)
from backend.src.infrastructure.database.session import get_db_session
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.system import AuditLog
from backend.src.presentation.dependencies.auth import require_role

logger = get_logger("presentation.api.admin_knowledge")
router = APIRouter(prefix="/admin/knowledge/generations", tags=["Admin Knowledge Base"])


@router.post("/build", response_model=KnowledgeGenerationResponse, status_code=status.HTTP_201_CREATED)
async def build_generation(
    request: BuildGenerationRequest = BuildGenerationRequest(),
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeGenerationResponse:
    """Trigger the end-to-end knowledge generation build pipeline."""
    manager = KnowledgeGenerationManager(session=session)
    response = await manager.build_generation(
        admin_id=current_admin.id,
        document_ids=request.document_ids,
        auto_promote=request.auto_promote,
    )

    # Log action to audit trail
    audit = AuditLog(
        admin_id=current_admin.id,
        action="GEN_BUILD",
        resource_type="knowledge_generation",
        resource_id=response.id,
        payload={"generation_number": response.generation_number, "chunks": response.chunk_count},
    )
    session.add(audit)
    await session.commit()

    return response


@router.delete("/failed", status_code=status.HTTP_200_OK)
async def cleanup_failed_generations(
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Clean up orphaned FAILED generations that have 0 chunks (SITE_CURATOR+)."""
    manager = KnowledgeGenerationManager(session=session)
    result = await manager.cleanup_failed_generations()

    audit = AuditLog(
        admin_id=current_admin.id,
        action="GEN_CLEANUP_FAILED",
        resource_type="knowledge_generation",
        resource_id="batch",
        payload={"deleted_count": result["deleted_count"]},
    )
    session.add(audit)
    await session.commit()

    return result


@router.get("", response_model=KnowledgeGenerationListResponse)
async def list_generations(
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeGenerationListResponse:
    """List all knowledge generations in chronological reverse order."""
    manager = KnowledgeGenerationManager(session=session)
    return await manager.list_generations()


@router.get("/active", response_model=KnowledgeGenerationResponse)
async def get_active_generation(
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeGenerationResponse:
    """Retrieve the currently active knowledge generation."""
    manager = KnowledgeGenerationManager(session=session)
    active = await manager.get_active_generation()
    if not active:
        raise NotFoundError("No knowledge generation is currently marked ACTIVE.")
    return active


@router.get("/{generation_id}", response_model=KnowledgeGenerationResponse)
async def get_generation_by_id(
    generation_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeGenerationResponse:
    """Retrieve details and execution progress of a specific generation."""
    manager = KnowledgeGenerationManager(session=session)
    return await manager.get_generation(generation_id)


@router.post("/{generation_id}/promote", response_model=KnowledgeGenerationResponse)
async def promote_generation(
    generation_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeGenerationResponse:
    """Manually promote an existing generation to ACTIVE status."""
    manager = KnowledgeGenerationManager(session=session)
    response = await manager.promote_generation(generation_id)

    audit = AuditLog(
        admin_id=current_admin.id,
        action="GEN_PROMOTE",
        resource_type="knowledge_generation",
        resource_id=response.id,
        payload={"generation_number": response.generation_number},
    )
    session.add(audit)
    await session.commit()

    return response


@router.post("/rollback", response_model=KnowledgeGenerationResponse)
async def rollback_generation(
    request: RollbackRequest = RollbackRequest(),
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeGenerationResponse:
    """Instantly roll back the active generation pointer (<100ms) to a previous generation."""
    manager = KnowledgeGenerationManager(session=session)
    response = await manager.rollback_generation(
        target_id=request.target_generation_id,
        target_number=request.target_generation_number,
    )

    audit = AuditLog(
        admin_id=current_admin.id,
        action="GEN_ROLLBACK",
        resource_type="knowledge_generation",
        resource_id=response.id,
        payload={"generation_number": response.generation_number},
    )
    session.add(audit)
    await session.commit()

    return response
