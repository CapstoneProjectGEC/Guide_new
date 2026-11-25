"""Unit tests verifying document deletion idempotency, storage error handling, and active generation protection."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.src.core.errors import ConflictError, NotFoundError, StorageError
from backend.src.infrastructure.models.auth import Admin
from backend.src.infrastructure.models.knowledge import Document, DocumentChunk, KnowledgeGeneration
from backend.src.infrastructure.storage.local_storage import LocalStorageService
from backend.src.presentation.api.admin_documents import delete_document


def test_local_storage_delete_existing_file(tmp_path: Path) -> None:
    """Verify that deleting an existing file unlinks it and returns True."""
    svc = LocalStorageService(base_path=str(tmp_path))
    test_file = tmp_path / "test_doc.pdf"
    test_file.write_bytes(b"%PDF-1.4 test content")

    assert test_file.exists()
    result = svc.delete_file(str(test_file))
    assert result is True
    assert not test_file.exists()


def test_local_storage_delete_missing_file_is_idempotent(tmp_path: Path) -> None:
    """Verify that deleting a non-existent file returns False without raising an exception."""
    svc = LocalStorageService(base_path=str(tmp_path))
    missing_file = tmp_path / "does_not_exist.pdf"

    assert not missing_file.exists()
    result = svc.delete_file(str(missing_file))
    assert result is False


def test_local_storage_delete_permission_error(tmp_path: Path) -> None:
    """Verify that PermissionError during unlink is caught and raised as typed StorageError."""
    svc = LocalStorageService(base_path=str(tmp_path))
    test_file = tmp_path / "locked.pdf"
    test_file.write_bytes(b"content")

    with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
        with pytest.raises(StorageError) as exc_info:
            svc.delete_file(str(test_file))
        assert "Permission denied" in exc_info.value.message


def test_local_storage_delete_os_error(tmp_path: Path) -> None:
    """Verify that generic OSError during unlink is caught and raised as typed StorageError."""
    svc = LocalStorageService(base_path=str(tmp_path))
    test_file = tmp_path / "io_err.pdf"
    test_file.write_bytes(b"content")

    with patch.object(Path, "unlink", side_effect=OSError("Disk failure")):
        with pytest.raises(StorageError) as exc_info:
            svc.delete_file(str(test_file))
        assert "Filesystem error" in exc_info.value.message


@pytest.mark.asyncio
async def test_delete_document_not_found() -> None:
    """Verify that attempting to delete a non-existent document ID raises NotFoundError (404)."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    admin = Admin(id="admin-1", username="curator", role="SITE_CURATOR")

    with pytest.raises(NotFoundError) as exc_info:
        await delete_document(document_id="non-existent-id", current_admin=admin, session=mock_session)
    assert "not found" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_delete_document_blocked_by_active_generation() -> None:
    """Verify that deleting a document referenced by an ACTIVE generation is blocked with ConflictError (409)."""
    mock_session = AsyncMock()
    doc = Document(
        id="doc-active",
        filename="Belur_Temple.pdf",
        storage_path="data/documents/belur.pdf",
        sha256_hash="abc123",
        file_size_bytes=1000,
        page_count=2,
    )

    # 1st execute: fetch doc
    result_doc = MagicMock()
    result_doc.scalar_one_or_none.return_value = doc

    # 2nd execute: active generation check returns [133]
    result_active = MagicMock()
    result_active.scalars.return_value.all.return_value = [133]

    mock_session.execute.side_effect = [result_doc, result_active]

    admin = Admin(id="admin-1", username="curator", role="SITE_CURATOR")

    with pytest.raises(ConflictError) as exc_info:
        await delete_document(document_id="doc-active", current_admin=admin, session=mock_session)

    assert "actively used in generation(s): #133" in exc_info.value.message
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_document_preserves_shared_storage_path(tmp_path: Path) -> None:
    """Verify that if another Document record shares the storage_path, the file on disk is preserved."""
    shared_path = str(tmp_path / "shared.pdf")
    (tmp_path / "shared.pdf").write_bytes(b"shared pdf content")

    mock_session = AsyncMock()
    doc = Document(
        id="doc-1",
        filename="Doc1.pdf",
        storage_path=shared_path,
        sha256_hash="hash1",
        file_size_bytes=500,
        page_count=1,
    )

    # 1. fetch doc
    res_doc = MagicMock()
    res_doc.scalar_one_or_none.return_value = doc
    # 2. active gen check -> none
    res_active = MagicMock()
    res_active.scalars.return_value.all.return_value = []
    # 3. shared storage check -> count = 1 (another doc exists)
    res_shared = MagicMock()
    res_shared.scalar_one.return_value = 1

    mock_session.execute.side_effect = [res_doc, res_active, res_shared]

    admin = Admin(id="admin-1", username="curator", role="SITE_CURATOR")

    with patch("backend.src.presentation.api.admin_documents.get_storage_service") as mock_storage_factory:
        mock_storage = MagicMock()
        mock_storage_factory.return_value = mock_storage

        res = await delete_document(document_id="doc-1", current_admin=admin, session=mock_session)

        # File should NOT be deleted from disk because it's shared
        mock_storage.delete_file.assert_not_called()
        # But DB row is deleted
        mock_session.delete.assert_called_once_with(doc)
        assert "deleted successfully" in res["message"]


@pytest.mark.asyncio
async def test_delete_document_idempotent_with_missing_disk_file() -> None:
    """Verify that if the physical file is already missing on disk, DB deletion still succeeds cleanly."""
    mock_session = AsyncMock()
    doc = Document(
        id="doc-stale",
        filename="Stale_Doc.pdf",
        storage_path="data/documents/already_missing.pdf",
        sha256_hash="stale_hash",
        file_size_bytes=500,
        page_count=1,
    )

    res_doc = MagicMock()
    res_doc.scalar_one_or_none.return_value = doc
    res_active = MagicMock()
    res_active.scalars.return_value.all.return_value = []
    res_shared = MagicMock()
    res_shared.scalar_one.return_value = 0

    mock_session.execute.side_effect = [res_doc, res_active, res_shared]

    admin = Admin(id="admin-1", username="curator", role="SITE_CURATOR")

    with patch("backend.src.presentation.api.admin_documents.get_storage_service") as mock_storage_factory:
        mock_storage = MagicMock()
        mock_storage.delete_file.return_value = False  # File was missing
        mock_storage_factory.return_value = mock_storage

        res = await delete_document(document_id="doc-stale", current_admin=admin, session=mock_session)

        mock_storage.delete_file.assert_called_once_with("data/documents/already_missing.pdf")
        mock_session.delete.assert_called_once_with(doc)
        mock_session.commit.assert_called_once()
        assert "deleted successfully" in res["message"]
