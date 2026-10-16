"""Domain schemas and models for hybrid RAG retrieval and diagnostics."""

from pydantic import BaseModel, Field


class RetrievalCandidate(BaseModel):
    """Candidate document chunk evaluated through retrieval pipeline stages."""

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Source document identifier")
    page_number: int = Field(ge=1, description="Source page number")
    section_heading: str | None = Field(default=None, description="Section heading context")
    content: str = Field(description="Normalized chunk text")
    dense_rank: int | None = Field(default=None, description="1-indexed rank from ChromaDB dense retrieval")
    dense_score: float | None = Field(default=None, description="Cosine similarity score from dense search")
    sparse_rank: int | None = Field(default=None, description="1-indexed rank from BM25 sparse retrieval")
    sparse_score: float | None = Field(default=None, description="BM25 lexical matching score")
    rrf_score: float = Field(default=0.0, description="Reciprocal Rank Fusion score")
    rerank_score: float | None = Field(default=None, description="Cross-Encoder relevance confidence score")
    is_selected: bool = Field(default=False, description="Whether chunk passed confidence filter into final context")


class RetrievalDiagnosticRequest(BaseModel):
    """Input payload to trigger a retrieval diagnostic probe."""

    query: str = Field(min_length=1, max_length=500, description="Tourist or test search query")
    top_dense: int = Field(default=15, ge=1, le=50, description="Candidate count for dense Chroma search")
    top_sparse: int = Field(default=15, ge=1, le=50, description="Candidate count for sparse BM25 search")
    top_fused: int = Field(default=10, ge=1, le=30, description="Candidate count after RRF fusion")
    top_final: int = Field(default=4, ge=1, le=10, description="Final context chunks after re-ranking")
    score_threshold: float = Field(default=0.35, ge=0.0, le=1.0, description="Minimum cross-encoder confidence cutoff")


class RetrievalDiagnosticResponse(BaseModel):
    """Diagnostic trace showing intermediate scores across all retrieval stages."""

    query: str
    generation_id: str
    generation_number: int
    dense_candidates: list[RetrievalCandidate]
    sparse_candidates: list[RetrievalCandidate]
    fused_candidates: list[RetrievalCandidate]
    reranked_candidates: list[RetrievalCandidate]
    final_chunks: list[RetrievalCandidate]
    latency_breakdown_ms: dict[str, float]
