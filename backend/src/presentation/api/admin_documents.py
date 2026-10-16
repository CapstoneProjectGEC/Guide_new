"""Administrative endpoints for PDF document ingestion and lifecycle management."""

import hashlib
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.core.config import get_settings
from backend.src.core.errors import ConflictError, NotFoundError
from backend.src.core.logging import get_logger
from backend.src.domain.auth import AdminRole
from backend.src.domain.document import (
    DocumentListResponse,
    DocumentResponse,
    validate_pdf_content,
)
from backend.src.infrastructure.database.session import get_db_session
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import Document
from backend.src.infrastructure.models.system import AuditLog
from backend.src.infrastructure.storage.local_storage import get_storage_service
from backend.src.presentation.dependencies.auth import require_role

logger = get_logger("presentation.api.admin_documents")
router = APIRouter(prefix="/admin/documents", tags=["Admin Documents"])


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Upload, validate, deduplicate, and securely store a heritage PDF document."""
    settings = get_settings()
    storage = get_storage_service()

    content = await file.read()
    filename = file.filename or "unknown.pdf"

    # 1. Validate size, format, and magic bytes
    validate_pdf_content(content, filename, settings.MAX_DOCUMENT_SIZE_BYTES)

    # 2. SHA-256 deduplication check
    sha256 = hashlib.sha256(content).hexdigest()
    stmt = select(Document).where(Document.sha256_hash == sha256)
    result = await session.execute(stmt)
    existing_doc = result.scalar_one_or_none()

    if existing_doc:
        logger.warning("duplicate_document_upload_rejected", sha256=sha256, filename=filename)
        raise ConflictError(
            f"Document with identical SHA-256 hash already exists: '{existing_doc.filename}' (ID: {existing_doc.id})."
        )

    # 3. Store file to secure filesystem
    storage_path, computed_hash, file_size, page_count = storage.save_file(content, filename)

    # 4. Insert Document record into MySQL
    doc = Document(
        filename=filename,
        storage_path=storage_path,
        sha256_hash=computed_hash,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/pdf",
        page_count=page_count,
        uploaded_by_id=current_admin.id,
    )
    session.add(doc)
    await session.flush()
    await session.refresh(doc)

    # 5. Record action in Audit Log
    audit = AuditLog(
        admin_id=current_admin.id,
        action="DOC_UPLOAD",
        resource_type="document",
        resource_id=doc.id,
        payload={"filename": doc.filename, "sha256": doc.sha256_hash, "size": doc.file_size_bytes, "pages": doc.page_count},
    )
    session.add(audit)
    await session.commit()

    logger.info("document_ingested_successfully", doc_id=doc.id, filename=doc.filename, pages=doc.page_count)
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        sha256_hash=doc.sha256_hash,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        page_count=doc.page_count,
        uploaded_by_id=doc.uploaded_by_id,
        created_at=doc.created_at.isoformat(),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentListResponse:
    """Retrieve paginated list of all ingested documents."""
    total_stmt = select(func.count(Document.id))
    total_result = await session.execute(total_stmt)
    total = total_result.scalar_one()

    stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    docs = result.scalars().all()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                filename=d.filename,
                sha256_hash=d.sha256_hash,
                file_size_bytes=d.file_size_bytes,
                mime_type=d.mime_type,
                page_count=d.page_count,
                uploaded_by_id=d.uploaded_by_id,
                created_at=d.created_at.isoformat(),
            )
            for d in docs
        ],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> DocumentResponse:
    """Retrieve metadata for a specific ingested document."""
    stmt = select(Document).where(Document.id == document_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found.")

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        sha256_hash=doc.sha256_hash,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        page_count=doc.page_count,
        uploaded_by_id=doc.uploaded_by_id,
        created_at=doc.created_at.isoformat(),
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Stream raw PDF file content for download."""
    storage = get_storage_service()
    stmt = select(Document).where(Document.id == document_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found.")

    file_bytes = storage.read_file(doc.storage_path)
    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_admin: Admin = Depends(require_role(AdminRole.SITE_CURATOR)),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete document from MySQL and physical filesystem."""
    storage = get_storage_service()
    stmt = select(Document).where(Document.id == document_id)
    result = await session.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        raise NotFoundError(f"Document with ID '{document_id}' not found.")

    # Remove file from disk
    storage.delete_file(doc.storage_path)

    # Delete record from MySQL
    await session.delete(doc)

    # Record deletion audit log
    audit = AuditLog(
        admin_id=current_admin.id,
        action="DOC_DELETE",
        resource_type="document",
        resource_id=document_id,
        payload={"filename": doc.filename, "sha256": doc.sha256_hash},
    )
    session.add(audit)
    await session.commit()

    logger.info("document_deleted_successfully", doc_id=document_id, filename=doc.filename)
    return {"message": f"Document '{doc.filename}' deleted successfully."}
