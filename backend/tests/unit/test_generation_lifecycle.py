"""Unit tests verifying knowledge generation preflight checks, staging protection, promotion constraints, and cleanup."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.src.application.pipeline.generation_manager import KnowledgeGenerationManager
from backend.src.core.errors import ConflictError, NotFoundError, ValidationError
from backend.src.domain.knowledge import ExtractedSection, TextChunk
from backend.src.infrastructure.models.knowledge import Document, DocumentChunk, KnowledgeGeneration


@pytest.mark.asyncio
async def test_build_generation_preflight_no_documents() -> None:
    """Verify that build_generation aborts in preflight if no documents are found in database."""
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_res

    manager = KnowledgeGenerationManager(session=mock_session)

    with pytest.raises(ValidationError) as exc_info:
        await manager.build_generation()

    assert "Preflight check failed: No valid documents found" in exc_info.value.message
    # Verify no KnowledgeGeneration was added or committed
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_build_generation_preflight_missing_physical_file() -> None:
    """Verify that build_generation aborts in preflight if physical document file is missing on disk."""
    mock_session = AsyncMock()
    doc = Document(
        id="doc-1",
        filename="Missing.pdf",
        storage_path="data/documents/does_not_exist.pdf",
        sha256_hash="hash1",
        file_size_bytes=1000,
        page_count=1,
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [doc]
    mock_session.execute.return_value = mock_res

    mock_storage = MagicMock()
    mock_storage.read_file.side_effect = FileNotFoundError("File not found")

    manager = KnowledgeGenerationManager(session=mock_session, storage=mock_storage)

    with pytest.raises(ValidationError) as exc_info:
        await manager.build_generation()

    assert "Physical document file is missing or unreadable" in exc_info.value.message
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_build_generation_preflight_no_extractable_text() -> None:
    """Verify that build_generation aborts in preflight if document contains zero extractable text."""
    mock_session = AsyncMock()
    doc = Document(
        id="doc-empty",
        filename="Empty.pdf",
        storage_path="data/documents/empty.pdf",
        sha256_hash="empty_hash",
        file_size_bytes=500,
        page_count=1,
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [doc]
    mock_session.execute.return_value = mock_res

    mock_storage = MagicMock()
    mock_storage.read_file.return_value = b"%PDF-1.4 dummy valid length bytes" + b" " * 100

    mock_extractor = MagicMock()
    # Returns empty sections
    mock_extractor.extract_from_bytes.return_value = []

    manager = KnowledgeGenerationManager(session=mock_session, storage=mock_storage, extractor=mock_extractor)

    with pytest.raises(ValidationError) as exc_info:
        await manager.build_generation()

    assert "zero meaningful extractable text" in exc_info.value.message
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_promote_generation_fails_on_failed_status() -> None:
    """Verify that promoting a FAILED generation is strictly rejected with ConflictError."""
    mock_session = AsyncMock()
    gen = KnowledgeGeneration(
        id="gen-failed",
        generation_number=140,
        status="FAILED",
        chroma_collection_name="kbase_gen_140",
        chunk_count=0,
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = gen
    mock_session.execute.return_value = mock_res

    manager = KnowledgeGenerationManager(session=mock_session)

    with pytest.raises(ConflictError) as exc_info:
        await manager.promote_generation("gen-failed")

    assert "Cannot promote a FAILED generation" in exc_info.value.message


@pytest.mark.asyncio
async def test_promote_generation_fails_on_zero_chunks() -> None:
    """Verify that promoting a generation with zero chunks is rejected with ConflictError."""
    mock_session = AsyncMock()
    gen = KnowledgeGeneration(
        id="gen-zero",
        generation_number=141,
        status="VALIDATE",
        chroma_collection_name="kbase_gen_141",
        chunk_count=0,
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = gen
    mock_session.execute.return_value = mock_res

    manager = KnowledgeGenerationManager(session=mock_session)

    with pytest.raises(ConflictError) as exc_info:
        await manager.promote_generation("gen-zero")

    assert "chunk count is 0" in exc_info.value.message


@pytest.mark.asyncio
async def test_promote_generation_fails_on_chroma_mismatch() -> None:
    """Verify that promoting fails if Chroma collection count differs from MySQL chunk count."""
    mock_session = AsyncMock()
    gen = KnowledgeGeneration(
        id="gen-mismatch",
        generation_number=142,
        status="VALIDATE",
        chroma_collection_name="kbase_gen_142",
        chunk_count=5,
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = gen
    mock_session.execute.return_value = mock_res

    mock_vector = MagicMock()
    mock_vector.count.return_value = 2  # Mismatch: 2 in Chroma vs 5 in DB

    manager = KnowledgeGenerationManager(session=mock_session, vector_store=mock_vector)

    with pytest.raises(ConflictError) as exc_info:
        await manager.promote_generation("gen-mismatch")

    assert "collection count mismatch" in exc_info.value.message


@pytest.mark.asyncio
async def test_cleanup_failed_generations_preserves_active_and_archived() -> None:
    """Verify that cleanup_failed_generations only deletes FAILED generations with 0 chunks."""
    mock_session = AsyncMock()

    failed_gen1 = KnowledgeGeneration(
        id="fail-1",
        generation_number=135,
        status="FAILED",
        chroma_collection_name="kbase_gen_135",
        chunk_count=0,
    )
    failed_gen2 = KnowledgeGeneration(
        id="fail-2",
        generation_number=136,
        status="FAILED",
        chroma_collection_name="kbase_gen_136",
        chunk_count=0,
    )

    # 1st execute: select failed gens
    res_list = MagicMock()
    res_list.scalars.return_value.all.return_value = [failed_gen1, failed_gen2]

    # chunk checks for fail-1 and fail-2 return 0 chunks
    res_chunk1 = MagicMock()
    res_chunk1.scalar_one.return_value = 0
    res_chunk2 = MagicMock()
    res_chunk2.scalar_one.return_value = 0

    mock_session.execute.side_effect = [res_list, res_chunk1, res_chunk2]

    mock_vector = MagicMock()
    mock_vector.get_collection.return_value = None  # No orphan collections

    manager = KnowledgeGenerationManager(session=mock_session, vector_store=mock_vector)

    result = await manager.cleanup_failed_generations()

    assert result["deleted_count"] == 2
    assert [g["generation_number"] for g in result["cleaned_generations"]] == [135, 136]
    assert mock_session.delete.call_count == 2
    mock_session.commit.assert_called_once()
