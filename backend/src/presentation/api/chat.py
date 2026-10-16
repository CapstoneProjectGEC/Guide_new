"""Public conversational REST API endpoints for tourist exploration."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.core.logging import get_logger
from backend.src.domain.conversation import (
    ChatMessageResponse,
    ChatSessionResponse,
    CreateSessionRequest,
    SendMessageRequest,
)
from backend.src.infrastructure.database.session import get_db_session

logger = get_logger("presentation.api.chat")
router = APIRouter(prefix="/chat", tags=["Tourist Chat"])


@router.post("/message", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def send_message(
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChatMessageResponse:
    """Public tourist chat endpoint (Strictly zero authentication required)."""
    manager = ConversationManager(session=session)
    return await manager.process_message(request)


@router.post("/stream")
async def send_message_stream(
    request: SendMessageRequest,
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Server-Sent Events (SSE) streaming endpoint for low-latency tourist conversation."""
    manager = ConversationManager(session=session)
    generator = manager.process_message_stream(request)

    return StreamingResponse(
        generator,
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest = CreateSessionRequest(),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionResponse:
    """Initialize a new frictionless conversational session for a tourist."""
    manager = ConversationManager(session=session)
    chat_session = await manager.get_or_create_session(
        client_fingerprint=request.client_fingerprint,
        preferred_language=request.preferred_language,
    )
    await session.commit()
    return await manager.get_session_history(chat_session.id)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse, status_code=status.HTTP_200_OK)
async def get_session(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionResponse:
    """Retrieve turn history and source citations for an active session."""
    manager = ConversationManager(session=session)
    return await manager.get_session_history(session_id)


@router.get("/kb/info", status_code=status.HTTP_200_OK)
async def get_kb_info():
    """Return Belur knowledge base metadata, crawl manifest, and extraction limitations."""
    from backend.src.application.rag.belur_kb_service import get_belur_kb_service
    return get_belur_kb_service().get_info()


@router.get("/kb/sections/{section_id}", status_code=status.HTTP_200_OK)
async def get_kb_section(section_id: str):
    """Retrieve complete raw section details from the Belur Knowledge Base."""
    from backend.src.application.rag.belur_kb_service import get_belur_kb_service
    sec = get_belur_kb_service().get_section(section_id)
    if not sec:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found.")
    return sec


@router.get("/kb/images", status_code=status.HTTP_200_OK)
async def get_kb_images(image_ids: str):
    """Retrieve compliant image cards for a comma-separated list of image IDs."""
    from backend.src.application.rag.belur_kb_service import get_belur_kb_service
    ids_list = [iid.strip() for iid in image_ids.split(",") if iid.strip()]
    return get_belur_kb_service().get_images(ids_list)
