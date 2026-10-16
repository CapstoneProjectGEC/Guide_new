"""Domain models, validation rules, and schemas for document management."""

from pydantic import BaseModel, Field
from backend.src.core.errors import ValidationError


class DocumentResponse(BaseModel):
    """Document representation contract."""

    id: str
    filename: str
    sha256_hash: str
    file_size_bytes: int
    mime_type: str
    page_count: int
    uploaded_by_id: str | None
    created_at: str


class DocumentListResponse(BaseModel):
    """Paginated document list contract."""

    documents: list[DocumentResponse]
    total: int


def validate_pdf_content(content: bytes, filename: str, max_size_bytes: int) -> None:
    """Validate uploaded document for size, extension, and PDF magic bytes."""
    if len(content) == 0:
        raise ValidationError("Uploaded file is empty.")

    if len(content) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(f"File size exceeds maximum allowed threshold of {max_mb:.0f}MB.")

    if not filename.lower().endswith(".pdf"):
        raise ValidationError("File extension must be .pdf.")

    # Validate standard PDF magic bytes: %PDF-
    if not content.startswith(b"%PDF-"):
        raise ValidationError("Invalid file format. Header lacks authentic %PDF- magic bytes.")
