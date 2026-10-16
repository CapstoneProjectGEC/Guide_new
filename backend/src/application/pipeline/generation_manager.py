"""Knowledge generation pipeline orchestrator and state machine."""

from datetime import datetime
import time
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.pipeline.chunker import SemanticChunker
from backend.src.application.pipeline.extractor import PDFExtractor
from backend.src.core.config import get_settings
from backend.src.core.errors import ConflictError, NotFoundError, ValidationError
from backend.src.core.logging import get_logger
from backend.src.domain.knowledge import (
    GenerationStepResponse,
    KnowledgeGenerationListResponse,
    KnowledgeGenerationResponse,
    PipelineStep,
    StepExecutionStatus,
    TextChunk,
)
from backend.src.infrastructure.database.base import utc_now
from backend.src.infrastructure.models.knowledge import (
    ChunkEmbedding,
    Document,
    DocumentChunk,
    GenerationStatus,
    KnowledgeGeneration,
)
from backend.src.infrastructure.storage.local_storage import LocalStorageService, get_storage_service
from backend.src.infrastructure.vector.chroma_store import (
    ChromaVectorStore,
    EmbeddingService,
    get_embedding_service,
    get_vector_store,
)

logger = get_logger("application.pipeline.generation_manager")


class KnowledgeGenerationManager:
    """Manages immutable knowledge generation builds, validation, promotion, and rollbacks."""

    def __init__(
        self,
        session: AsyncSession,
        storage: LocalStorageService | None = None,
        extractor: PDFExtractor | None = None,
        chunker: SemanticChunker | None = None,
        vector_store: ChromaVectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        settings = get_settings()
        self.session = session
        self.storage = storage or get_storage_service()
        self.extractor = extractor or PDFExtractor()
        self.chunker = chunker or SemanticChunker(
            target_chunk_tokens=settings.CHUNK_SIZE_TOKENS,
            overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
        )
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = embedding_service or get_embedding_service()

    async def build_generation(
        self,
        admin_id: str | None = None,
        document_ids: list[str] | None = None,
        auto_promote: bool = True,
    ) -> KnowledgeGenerationResponse:
        """Execute full end-to-end pipeline: BUILD ➔ PARSE ➔ CHUNK ➔ EMBED ➔ INDEX ➔ VALIDATE ➔ PROMOTE."""
        # 1. Determine next monotonic generation number
        max_num_stmt = select(func.max(KnowledgeGeneration.generation_number))
        result = await self.session.execute(max_num_stmt)
        max_num = result.scalar_one_or_none() or 0
        gen_number = max_num + 1
        collection_name = f"kbase_gen_{gen_number}"

        generation = KnowledgeGeneration(
            generation_number=gen_number,
            status="BUILD",
            chroma_collection_name=collection_name,
            chunk_count=0,
            created_by_id=admin_id,
        )
        self.session.add(generation)
        await self.session.flush()

        # Initialize step execution trackers
        steps = [
            PipelineStep.PARSE,
            PipelineStep.CHUNK,
            PipelineStep.EMBED,
            PipelineStep.INDEX,
            PipelineStep.VALIDATE,
            PipelineStep.PROMOTE,
        ]
        step_records: dict[str, GenerationStatus] = {}
        for step in steps:
            status_row = GenerationStatus(
                generation_id=generation.id,
                step=step.value,
                status=StepExecutionStatus.PENDING.value,
                progress_pct=0.0,
            )
            self.session.add(status_row)
            step_records[step.value] = status_row

        await self.session.commit()
        await self.session.refresh(generation)

        logger.info(
            "knowledge_generation_started",
            generation_id=generation.id,
            generation_number=gen_number,
            collection=collection_name,
        )

        try:
            # ---------------------------------------------------------
            # STEP 1: PARSE
            # ---------------------------------------------------------
            await self._update_step(generation, step_records, PipelineStep.PARSE, StepExecutionStatus.IN_PROGRESS, 10.0)

            # Retrieve target documents
            doc_query = select(Document)
            if document_ids:
                doc_query = doc_query.where(Document.id.in_(document_ids))
            docs_result = await self.session.execute(doc_query)
            target_docs = docs_result.scalars().all()

            if not target_docs:
                raise ValidationError("No valid documents found to build knowledge base.")

            parsed_sections_by_doc: dict[str, list] = {}
            for doc in target_docs:
                pdf_bytes = self.storage.read_file(doc.storage_path)
                sections = self.extractor.extract_from_bytes(pdf_bytes, filename=doc.filename)
                parsed_sections_by_doc[doc.id] = sections

            await self._update_step(generation, step_records, PipelineStep.PARSE, StepExecutionStatus.COMPLETED, 100.0)

            # ---------------------------------------------------------
            # STEP 2: CHUNK
            # ---------------------------------------------------------
            await self._update_step(generation, step_records, PipelineStep.CHUNK, StepExecutionStatus.IN_PROGRESS, 10.0)

            all_domain_chunks: list[TextChunk] = []
            db_chunk_entities: list[DocumentChunk] = []

            for doc in target_docs:
                sections = parsed_sections_by_doc.get(doc.id, [])
                doc_chunks = self.chunker.chunk_sections(sections, document_id=doc.id)
                for chunk in doc_chunks:
                    all_domain_chunks.append(chunk)
                    chunk_entity = DocumentChunk(
                        document_id=doc.id,
                        generation_id=generation.id,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        section_heading=chunk.section_heading,
                        content=chunk.content,
                        token_count=chunk.token_count,
                    )
                    self.session.add(chunk_entity)
                    db_chunk_entities.append(chunk_entity)

            if not all_domain_chunks:
                raise ValidationError("Document parsing and chunking produced zero text chunks.")

            await self.session.flush()
            generation.chunk_count = len(all_domain_chunks)
            await self._update_step(generation, step_records, PipelineStep.CHUNK, StepExecutionStatus.COMPLETED, 100.0)

            # ---------------------------------------------------------
            # STEP 3: EMBED
            # ---------------------------------------------------------
            await self._update_step(generation, step_records, PipelineStep.EMBED, StepExecutionStatus.IN_PROGRESS, 10.0)

            texts_to_embed = [c.content for c in all_domain_chunks]
            embeddings = self.embedding_service.embed_texts(texts_to_embed)

            settings = get_settings()
            for chunk_entity, vec, domain_chunk in zip(db_chunk_entities, embeddings, all_domain_chunks, strict=True):
                vector_id = f"{domain_chunk.document_id}_{domain_chunk.chunk_index}"
                checksum = EmbeddingService.calculate_vector_checksum(vec)
                emb_record = ChunkEmbedding(
                    chunk_id=chunk_entity.id,
                    generation_id=generation.id,
                    model_name=settings.EMBEDDING_MODEL_NAME,
                    dimensions=settings.EMBEDDING_DIMENSIONS,
                    vector_id=vector_id,
                    checksum=checksum,
                )
                self.session.add(emb_record)

            await self.session.flush()
            await self._update_step(generation, step_records, PipelineStep.EMBED, StepExecutionStatus.COMPLETED, 100.0)

            # ---------------------------------------------------------
            # STEP 4: INDEX
            # ---------------------------------------------------------
            await self._update_step(generation, step_records, PipelineStep.INDEX, StepExecutionStatus.IN_PROGRESS, 10.0)

            self.vector_store.index_chunks(
                collection_name=collection_name,
                chunks=all_domain_chunks,
                embeddings=embeddings,
            )
            await self._update_step(generation, step_records, PipelineStep.INDEX, StepExecutionStatus.COMPLETED, 100.0)

            # ---------------------------------------------------------
            # STEP 5: VALIDATE
            # ---------------------------------------------------------
            await self._update_step(generation, step_records, PipelineStep.VALIDATE, StepExecutionStatus.IN_PROGRESS, 10.0)

            chroma_count = self.vector_store.count(collection_name)
            if chroma_count != len(all_domain_chunks):
                raise ValidationError(
                    f"Vector count mismatch: MySQL recorded {len(all_domain_chunks)} chunks, Chroma has {chroma_count}."
                )

            # Perform probe retrieval
            test_vec = self.embedding_service.embed_query("Belur Chennakeshava Temple")
            probe_results = self.vector_store.query_dense(collection_name, test_vec, top_k=2)
            if not probe_results:
                raise ValidationError("Validation probe query against ChromaDB returned empty results.")

            await self._update_step(generation, step_records, PipelineStep.VALIDATE, StepExecutionStatus.COMPLETED, 100.0)

            # ---------------------------------------------------------
            # STEP 6: PROMOTE
            # ---------------------------------------------------------
            if auto_promote:
                await self._update_step(generation, step_records, PipelineStep.PROMOTE, StepExecutionStatus.IN_PROGRESS, 50.0)
                await self._promote_internal(generation)
                await self._update_step(generation, step_records, PipelineStep.PROMOTE, StepExecutionStatus.COMPLETED, 100.0)
            else:
                generation.status = "VALIDATE"

            await self.session.commit()
            await self.session.refresh(generation)

            logger.info(
                "knowledge_generation_completed_successfully",
                generation_id=generation.id,
                generation_number=generation.generation_number,
                chunks=generation.chunk_count,
                status=generation.status,
            )
            return await self._to_response(generation)

        except Exception as exc:
            logger.error(
                "knowledge_generation_failed",
                generation_id=generation.id,
                error=str(exc),
                exc_info=True,
            )
            generation.status = "FAILED"
            # Update currently running step to FAILED
            for record in step_records.values():
                if record.status == StepExecutionStatus.IN_PROGRESS.value:
                    record.status = StepExecutionStatus.FAILED.value
                    record.error_message = str(exc)
            await self.session.commit()
            raise

    async def promote_generation(self, generation_id: str) -> KnowledgeGenerationResponse:
        """Promote an existing validated or archived generation to ACTIVE status."""
        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.id == generation_id)
        result = await self.session.execute(stmt)
        gen = result.scalar_one_or_none()

        if not gen:
            raise NotFoundError(f"Knowledge generation '{generation_id}' not found.")

        if gen.status == "ACTIVE":
            logger.info("generation_already_active", generation_id=generation_id)
            return await self._to_response(gen)

        if gen.status == "FAILED":
            raise ConflictError("Cannot promote a FAILED generation. Rebuild required.")

        await self._promote_internal(gen)
        await self.session.commit()
        await self.session.refresh(gen)

        logger.info("generation_promoted_to_active", generation_id=gen.id, number=gen.generation_number)
        return await self._to_response(gen)

    async def rollback_generation(
        self,
        target_id: str | None = None,
        target_number: int | None = None,
    ) -> KnowledgeGenerationResponse:
        """Fast zero-rebuild rollback (<100ms) to previous or specified generation."""
        start_time = time.perf_counter()

        stmt = select(KnowledgeGeneration)
        if target_id:
            stmt = stmt.where(KnowledgeGeneration.id == target_id)
        elif target_number:
            stmt = stmt.where(KnowledgeGeneration.generation_number == target_number)
        else:
            # Revert to most recent archived generation
            stmt = stmt.where(KnowledgeGeneration.status == "ARCHIVED").order_by(
                desc(KnowledgeGeneration.generation_number)
            )

        result = await self.session.execute(stmt)
        target_gen = result.scalars().first()

        if not target_gen:
            raise NotFoundError("No suitable target generation found for rollback.")

        if target_gen.status == "ACTIVE":
            raise ConflictError(f"Generation {target_gen.generation_number} is already active.")

        if target_gen.chunk_count == 0:
            raise ConflictError(f"Target generation {target_gen.generation_number} contains zero indexed chunks.")

        # Switch active pointer
        await self._promote_internal(target_gen)
        await self.session.commit()
        await self.session.refresh(target_gen)

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            "knowledge_generation_rollback_completed",
            target_id=target_gen.id,
            target_number=target_gen.generation_number,
            latency_ms=f"{latency_ms:.2f}ms",
        )
        return await self._to_response(target_gen)

    async def get_active_generation(self) -> KnowledgeGenerationResponse | None:
        """Retrieve current ACTIVE knowledge generation."""
        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.status == "ACTIVE")
        result = await self.session.execute(stmt)
        gen = result.scalar_one_or_none()
        if not gen:
            return None
        return await self._to_response(gen)

    async def get_generation(self, generation_id: str) -> KnowledgeGenerationResponse:
        """Retrieve details of a specific generation by UUID."""
        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.id == generation_id)
        result = await self.session.execute(stmt)
        gen = result.scalar_one_or_none()
        if not gen:
            raise NotFoundError(f"Knowledge generation '{generation_id}' not found.")
        return await self._to_response(gen)

    async def list_generations(self) -> KnowledgeGenerationListResponse:
        """List all knowledge generations sorted newest first."""
        stmt = select(KnowledgeGeneration).order_by(desc(KnowledgeGeneration.generation_number))
        result = await self.session.execute(stmt)
        generations = result.scalars().all()

        responses = [await self._to_response(g) for g in generations]
        active_id = next((g.id for g in responses if g.status == "ACTIVE"), None)

        return KnowledgeGenerationListResponse(
            generations=responses,
            active_generation_id=active_id,
            total=len(responses),
        )

    async def _promote_internal(self, target_generation: KnowledgeGeneration) -> None:
        """Internal atomic helper to demote any currently active generation and promote target."""
        # Demote all currently active generations to ARCHIVED
        demote_stmt = (
            update(KnowledgeGeneration)
            .where(KnowledgeGeneration.status == "ACTIVE")
            .values(status="ARCHIVED")
        )
        await self.session.execute(demote_stmt)

        # Mark target as ACTIVE
        target_generation.status = "ACTIVE"
        target_generation.promoted_at = utc_now()
        self.session.add(target_generation)

    async def _update_step(
        self,
        generation: KnowledgeGeneration,
        step_records: dict[str, GenerationStatus],
        step: PipelineStep,
        status: StepExecutionStatus,
        progress_pct: float,
    ) -> None:
        """Update step progress record and sync generation status."""
        record = step_records.get(step.value)
        if record:
            record.status = status.value
            record.progress_pct = progress_pct
            self.session.add(record)

        generation.status = step.value if status == StepExecutionStatus.IN_PROGRESS else generation.status
        self.session.add(generation)
        await self.session.flush()

    async def _to_response(self, gen: KnowledgeGeneration) -> KnowledgeGenerationResponse:
        """Serialize KnowledgeGeneration model to domain response contract."""
        status_stmt = select(GenerationStatus).where(GenerationStatus.generation_id == gen.id)
        status_result = await self.session.execute(status_stmt)
        steps = status_result.scalars().all()

        return KnowledgeGenerationResponse(
            id=gen.id,
            generation_number=gen.generation_number,
            status=gen.status,
            chroma_collection_name=gen.chroma_collection_name,
            chunk_count=gen.chunk_count,
            created_by_id=gen.created_by_id,
            created_at=gen.created_at.isoformat() if gen.created_at else "",
            promoted_at=gen.promoted_at.isoformat() if gen.promoted_at else None,
            steps=[
                GenerationStepResponse(
                    step=s.step,
                    status=s.status,
                    progress_pct=s.progress_pct,
                    error_message=s.error_message,
                )
                for s in steps
            ],
        )
