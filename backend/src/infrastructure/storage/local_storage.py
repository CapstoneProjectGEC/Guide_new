"""Filesystem document storage service with SHA-256 calculation and PyMuPDF page count."""

import hashlib
from pathlib import Path
import uuid
import fitz  # PyMuPDF
from backend.src.core.config import get_settings
from backend.src.core.errors import NotFoundError
from backend.src.core.logging import get_logger

logger = get_logger("infrastructure.storage")


class LocalStorageService:
    """Service handling secure file storage and cryptographic hashing."""

    def __init__(self, base_path: str | None = None) -> None:
        settings = get_settings()
        self.base_dir = Path(base_path or settings.DOCUMENT_STORAGE_PATH)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: bytes, original_filename: str) -> tuple[str, str, int, int]:
        """Save file to storage and calculate SHA-256 and page count.

        Returns:
            Tuple of (storage_path, sha256_hash, file_size_bytes, page_count)
        """
        sha256 = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # Parse page count using PyMuPDF
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = doc.page_count
            doc.close()
        except Exception as e:
            logger.warning("could_not_parse_page_count", error=str(e))
            page_count = 1

        # Generate non-colliding UUID filename
        storage_filename = f"{uuid.uuid4().hex}.pdf"
        target_path = self.base_dir / storage_filename

        target_path.write_bytes(content)
        logger.info(
            "file_stored_successfully",
            original=original_filename,
            stored=str(target_path),
            size_bytes=file_size,
            pages=page_count,
            sha256=sha256,
        )

        return str(target_path), sha256, file_size, page_count

    def read_file(self, storage_path: str) -> bytes:
        """Read and return raw file bytes from storage."""
        path = Path(storage_path)
        if not path.exists() or not path.is_file():
            raise NotFoundError(f"Physical file not found on disk at {storage_path}")
        return path.read_bytes()

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from disk."""
        path = Path(storage_path)
        if path.exists() and path.is_file():
            path.unlink()
            logger.info("file_deleted", path=storage_path)
            return True
        return False


_storage_service: LocalStorageService | None = None


def get_storage_service() -> LocalStorageService:
    """Singleton provider for storage service."""
    global _storage_service
    if _storage_service is None:
        _storage_service = LocalStorageService()
    return _storage_service
