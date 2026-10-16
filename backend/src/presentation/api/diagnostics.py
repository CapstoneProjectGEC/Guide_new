"""Administrative diagnostic endpoints for RAG retrieval scoring and latency profiling."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.core.logging import get_logger
from backend.src.domain.auth import AdminRole
from backend.src.domain.rag import RetrievalDiagnosticRequest, RetrievalDiagnosticResponse
from backend.src.infrastructure.database.session import get_db_session
from backend.src.infrastructure.models.auth import Admin
from backend.src.presentation.dependencies.auth import require_role

logger = get_logger("presentation.api.diagnostics")
router = APIRouter(prefix="/admin/diagnostics", tags=["Admin Diagnostics"])


@router.post("/retrieval", response_model=RetrievalDiagnosticResponse, status_code=status.HTTP_200_OK)
async def diagnose_retrieval_post(
    request: RetrievalDiagnosticRequest,
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> RetrievalDiagnosticResponse:
    """Execute hybrid retrieval pipeline and return intermediate dense, sparse, RRF, and cross-encoder scores."""
    retriever = HybridRAGRetriever(session=session)
    return await retriever.diagnose(
        query=request.query,
        top_dense=request.top_dense,
        top_sparse=request.top_sparse,
        top_fused=request.top_fused,
        top_final=request.top_final,
        threshold=request.score_threshold,
    )


@router.get("/retrieval", response_model=RetrievalDiagnosticResponse, status_code=status.HTTP_200_OK)
async def diagnose_retrieval_get(
    query: str = Query(..., min_length=1, max_length=500, description="Test query"),
    current_admin: Admin = Depends(require_role(AdminRole.VIEWER)),
    session: AsyncSession = Depends(get_db_session),
) -> RetrievalDiagnosticResponse:
    """Convenience GET endpoint for query diagnostic testing in browser or curl."""
    retriever = HybridRAGRetriever(session=session)
    return await retriever.diagnose(query=query)
