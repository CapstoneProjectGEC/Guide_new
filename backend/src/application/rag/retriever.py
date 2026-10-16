"""Hybrid dense + sparse RAG retriever with Reciprocal Rank Fusion and Cross-Encoder re-ranking."""

import time
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.rag.bm25 import BM25Index
from backend.src.application.rag.reranker import CrossEncoderReranker, get_cross_encoder_reranker
from backend.src.core.config import get_settings
from backend.src.core.errors import NotFoundError
from backend.src.core.logging import get_logger
from backend.src.domain.rag import RetrievalCandidate, RetrievalDiagnosticResponse
from backend.src.infrastructure.models.knowledge import DocumentChunk, KnowledgeGeneration
from backend.src.infrastructure.vector.chroma_store import (
    ChromaVectorStore,
    EmbeddingService,
    get_embedding_service,
    get_vector_store,
)

logger = get_logger("application.rag.retriever")


class HybridRAGRetriever:
    """Orchestrates dense Chroma search, sparse BM25 search, RRF fusion, and cross-encoder re-ranking."""

    # In-memory cached BM25 index keyed by generation_id
    _bm25_cache: dict[str, BM25Index] = {}

    def __init__(
        self,
        session: AsyncSession,
        vector_store: ChromaVectorStore | None = None,
        embedding_service: EmbeddingService | None = None,
        reranker: CrossEncoderReranker | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.vector_store = vector_store or get_vector_store()
        self.embedding_service = embedding_service or get_embedding_service()
        self.reranker = reranker or get_cross_encoder_reranker()

    async def retrieve(
        self,
        query: str,
        top_dense: int | None = None,
        top_sparse: int | None = None,
        top_fused: int | None = None,
        top_final: int | None = None,
        threshold: float | None = None,
    ) -> list[RetrievalCandidate]:
        """Execute hybrid retrieval pipeline and return the final filtered candidate chunks."""
        diag = await self.diagnose(
            query=query,
            top_dense=top_dense,
            top_sparse=top_sparse,
            top_fused=top_fused,
            top_final=top_final,
            threshold=threshold,
        )
        return diag.final_chunks

    async def diagnose(
        self,
        query: str,
        top_dense: int | None = None,
        top_sparse: int | None = None,
        top_fused: int | None = None,
        top_final: int | None = None,
        threshold: float | None = None,
    ) -> RetrievalDiagnosticResponse:
        """Execute hybrid retrieval pipeline with comprehensive intermediate diagnostic metrics."""
        t_start = time.perf_counter()

        limit_dense = top_dense or self.settings.RAG_DENSE_TOP_K
        limit_sparse = top_sparse or self.settings.RAG_SPARSE_TOP_K
        limit_fused = top_fused or self.settings.RAG_FUSED_TOP_K
        limit_final = top_final or self.settings.RAG_FINAL_TOP_K
        cutoff_threshold = threshold if threshold is not None else self.settings.RAG_CONFIDENCE_THRESHOLD
        rrf_k = self.settings.RAG_RRF_K

        # 1. Fetch current active generation
        active_gen = await self._get_active_generation()
        if not active_gen:
            raise NotFoundError("No knowledge generation is currently marked ACTIVE. Please build or promote a generation.")

        # Ensure in-memory BM25 index is prepared for this generation
        bm25_index = await self._get_or_build_bm25_index(active_gen.id)

        # -------------------------------------------------------------
        # STAGE 1: Dense Retrieval via ChromaDB
        # -------------------------------------------------------------
        t_dense_start = time.perf_counter()
        query_vector = self.embedding_service.embed_query(query)
        chroma_hits = self.vector_store.query_dense(
            collection_name=active_gen.chroma_collection_name,
            query_vector=query_vector,
            top_k=limit_dense,
        )
        dense_ms = (time.perf_counter() - t_dense_start) * 1000.0

        dense_candidates: list[dict[str, Any]] = []
        for rank, hit in enumerate(chroma_hits, start=1):
            meta = hit.get("metadata", {})
            dense_candidates.append(
                {
                    "chunk_id": hit["vector_id"],
                    "document_id": meta.get("document_id", ""),
                    "page_number": int(meta.get("page_number", 1)),
                    "section_heading": meta.get("section_heading") or None,
                    "content": hit.get("content", ""),
                    "dense_rank": rank,
                    "dense_score": round(float(hit.get("similarity", 0.0)), 4),
                }
            )

        # -------------------------------------------------------------
        # STAGE 2: Sparse Retrieval via BM25
        # -------------------------------------------------------------
        t_sparse_start = time.perf_counter()
        sparse_hits = bm25_index.search(query=query, top_k=limit_sparse)
        sparse_ms = (time.perf_counter() - t_sparse_start) * 1000.0

        sparse_candidates: list[dict[str, Any]] = []
        for hit in sparse_hits:
            sparse_candidates.append(
                {
                    "chunk_id": hit["chunk_id"],
                    "document_id": hit.get("document_id", ""),
                    "page_number": int(hit.get("page_number", 1)),
                    "section_heading": hit.get("section_heading") or None,
                    "content": hit.get("content", ""),
                    "sparse_rank": hit.get("sparse_rank"),
                    "sparse_score": round(float(hit.get("sparse_score", 0.0)), 4),
                }
            )

        # -------------------------------------------------------------
        # STAGE 3: Reciprocal Rank Fusion (RRF with k=60)
        # -------------------------------------------------------------
        t_rrf_start = time.perf_counter()
        fused_map: dict[str, dict[str, Any]] = {}

        # Merge dense candidates
        for c in dense_candidates:
            cid = c["chunk_id"]
            rrf_val = 1.0 / (rrf_k + c["dense_rank"])
            fused_map[cid] = {
                **c,
                "sparse_rank": None,
                "sparse_score": None,
                "rrf_score": rrf_val,
            }

        # Merge sparse candidates
        for c in sparse_candidates:
            cid = c["chunk_id"]
            rrf_val = 1.0 / (rrf_k + c["sparse_rank"])
            if cid in fused_map:
                fused_map[cid]["sparse_rank"] = c["sparse_rank"]
                fused_map[cid]["sparse_score"] = c["sparse_score"]
                fused_map[cid]["rrf_score"] += rrf_val
            else:
                fused_map[cid] = {
                    **c,
                    "dense_rank": None,
                    "dense_score": None,
                    "rrf_score": rrf_val,
                }

        # Sort descending by fused RRF score
        fused_list = list(fused_map.values())
        fused_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        top_fused_candidates = fused_list[:limit_fused]
        rrf_ms = (time.perf_counter() - t_rrf_start) * 1000.0

        # -------------------------------------------------------------
        # STAGE 4: Cross-Encoder Re-Ranking & Thresholding
        # -------------------------------------------------------------
        t_rerank_start = time.perf_counter()
        reranked = self.reranker.rerank(
            query=query,
            candidates=top_fused_candidates,
            top_k=limit_final,
            threshold=cutoff_threshold,
        )
        rerank_ms = (time.perf_counter() - t_rerank_start) * 1000.0
        total_ms = (time.perf_counter() - t_start) * 1000.0

        logger.info(
            "hybrid_retrieval_completed",
            query=query[:40],
            dense_count=len(dense_candidates),
            sparse_count=len(sparse_candidates),
            fused_count=len(top_fused_candidates),
            selected_count=len(reranked),
            total_ms=f"{total_ms:.1f}ms",
        )

        return RetrievalDiagnosticResponse(
            query=query,
            generation_id=active_gen.id,
            generation_number=active_gen.generation_number,
            dense_candidates=[RetrievalCandidate(**c) for c in dense_candidates],
            sparse_candidates=[RetrievalCandidate(**c) for c in sparse_candidates],
            fused_candidates=[RetrievalCandidate(**c) for c in top_fused_candidates],
            reranked_candidates=[RetrievalCandidate(**c) for c in reranked],
            final_chunks=[RetrievalCandidate(**c) for c in reranked],
            latency_breakdown_ms={
                "dense_ms": round(dense_ms, 2),
                "sparse_ms": round(sparse_ms, 2),
                "rrf_ms": round(rrf_ms, 2),
                "rerank_ms": round(rerank_ms, 2),
                "total_ms": round(total_ms, 2),
            },
        )

    async def _get_active_generation(self) -> KnowledgeGeneration | None:
        """Fetch the currently active KnowledgeGeneration entity."""
        stmt = select(KnowledgeGeneration).where(KnowledgeGeneration.status == "ACTIVE")
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_or_build_bm25_index(self, generation_id: str) -> BM25Index:
        """Fetch cached BM25 index or initialize from relational document_chunks."""
        if generation_id in self._bm25_cache:
            return self._bm25_cache[generation_id]

        stmt = select(DocumentChunk).where(DocumentChunk.generation_id == generation_id)
        result = await self.session.execute(stmt)
        chunks = result.scalars().all()

        chunk_records = [
            {
                "chunk_id": f"{c.document_id}_{c.chunk_index}",
                "document_id": c.document_id,
                "page_number": c.page_number,
                "section_heading": c.section_heading,
                "content": c.content,
            }
            for c in chunks
        ]

        index = BM25Index().fit(chunk_records)
        self._bm25_cache[generation_id] = index
        return index

    @classmethod
    def invalidate_bm25_cache(cls, generation_id: str | None = None) -> None:
        """Clear BM25 in-memory index cache."""
        if generation_id and generation_id in cls._bm25_cache:
            del cls._bm25_cache[generation_id]
        elif generation_id is None:
            cls._bm25_cache.clear()
