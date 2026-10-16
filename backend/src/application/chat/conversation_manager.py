"""Multilingual conversation engine, session state tracker, and grounding orchestrator."""

import json
from datetime import datetime
import re
import time
import uuid
from typing import AsyncGenerator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.chat.grounding_guard import GroundingGuard
from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.chat.prompt_builder import PromptBuilder
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.core.errors import NotFoundError
from backend.src.core.logging import get_logger
from backend.src.domain.conversation import (
    ChatMessageResponse,
    ChatSessionResponse,
    Citation,
    SendMessageRequest,
)
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.database.base import utc_now
from backend.src.infrastructure.llm.ollama_client import OllamaClient, get_ollama_client
from backend.src.infrastructure.models.chat import ChatMessage, ChatSession
from backend.src.infrastructure.models.knowledge import CitationReference, DocumentChunk

logger = get_logger("application.chat.conversation_manager")

PRONOUN_PATTERN = re.compile(
    r"\b(it|this|that|these|those|they|them|he|she|him|her|its|there|here|who built it|what is it|why)\b",
    re.IGNORECASE,
)


class ConversationManager:
    """Orchestrates session lifecycle, language detection, multi-turn context, and grounded responses."""

    def __init__(
        self,
        session: AsyncSession,
        retriever: HybridRAGRetriever | None = None,
        language_detector: LanguageDetector | None = None,
        grounding_guard: GroundingGuard | None = None,
        ollama_client: OllamaClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        query_normalizer: QueryNormalizer | None = None,
    ) -> None:
        self.session = session
        self.retriever = retriever or HybridRAGRetriever(session=session)
        self.language_detector = language_detector or LanguageDetector()
        self.grounding_guard = grounding_guard or GroundingGuard()
        self.ollama = ollama_client or get_ollama_client()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.query_normalizer = query_normalizer or QueryNormalizer()

    async def get_or_create_session(
        self,
        session_id: str | None = None,
        client_fingerprint: str | None = None,
        preferred_language: str = "kn",
    ) -> ChatSession:
        """Fetch existing chat session or allocate a new frictionless tourist session."""
        if session_id:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.last_active_at = utc_now()
                self.session.add(existing)
                return existing

        # Allocate new session
        fingerprint = client_fingerprint or f"tourist_{uuid.uuid4().hex[:12]}"
        new_session = ChatSession(
            client_fingerprint=fingerprint,
            preferred_language=preferred_language,
            created_at=utc_now(),
            last_active_at=utc_now(),
        )
        self.session.add(new_session)
        await self.session.flush()
        await self.session.refresh(new_session)
        return new_session

    async def process_message(self, request: SendMessageRequest) -> ChatMessageResponse:
        """Process incoming user message turn through multi-turn resolution, retrieval, and grounding."""
        t_start = time.perf_counter()

        # 1. Resolve or create chat session
        chat_session = await self.get_or_create_session(
            session_id=request.session_id,
            client_fingerprint=request.client_fingerprint,
            preferred_language=request.preferred_language or "kn",
        )

        # 2. Language Auto-Detection
        detection = self.language_detector.detect(
            text=request.content,
            fallback_language=chat_session.preferred_language,
        )
        active_language = request.preferred_language or detection.language

        # Update preferred language on session if detected
        chat_session.preferred_language = active_language
        chat_session.last_active_at = utc_now()
        self.session.add(chat_session)

        # 3. Fetch recent turn history for coreference awareness
        history = await self._get_recent_history(chat_session.id, limit=6)

        # 4. Context Query Reformulation
        reformulated_query = self._reformulate_query(request.content, history)

        # 5. Record User Turn
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=request.content,
            detected_language=active_language,
            input_mode=request.input_mode,
            is_grounded=True,
            created_at=utc_now(),
        )
        self.session.add(user_msg)
        await self.session.flush()

        # 6. Cross-Lingual Query Normalization for Knowledge Retrieval
        retrieval_query = reformulated_query
        if active_language == "kn" or self.language_detector.detect(reformulated_query).is_mixed:
            normalized = self.query_normalizer.normalize_for_retrieval(reformulated_query, source_lang=active_language)
            retrieval_query = normalized.retrieval_query

        # 7. Execute Hybrid RAG Retrieval
        candidates = await self.retriever.retrieve(
            query=retrieval_query,
            top_final=4,
            threshold=0.35,
        )

        # 7. Evaluate Strict Grounding Guard
        grounding_result = self.grounding_guard.evaluate(candidates, language=active_language)

        # 8. Synthesize Response Text & Attributed Citations
        if not grounding_result.is_grounded:
            assistant_content = grounding_result.fallback_message or ""
            is_grounded = False
            selected_chunks = []
        else:
            is_grounded = True
            selected_chunks = grounding_result.selected_chunks
            assistant_content = self._format_grounded_answer(selected_chunks, active_language)

        latency_ms = int((time.perf_counter() - t_start) * 1000.0)

        # 9. Record Assistant Turn
        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content=assistant_content,
            detected_language=active_language,
            input_mode=request.input_mode,
            latency_ms=latency_ms,
            is_grounded=is_grounded,
            created_at=utc_now(),
        )
        self.session.add(assistant_msg)
        await self.session.flush()

        # 10. Map Citations & Relational References
        domain_citations: list[Citation] = []
        if is_grounded and selected_chunks:
            domain_citations = await self._record_citations(assistant_msg.id, selected_chunks)

        await self.session.commit()
        await self.session.refresh(assistant_msg)

        logger.info(
            "chat_turn_completed",
            session_id=chat_session.id,
            user_msg_id=user_msg.id,
            assistant_msg_id=assistant_msg.id,
            language=active_language,
            is_grounded=is_grounded,
            citations=len(domain_citations),
            latency_ms=latency_ms,
        )

        return ChatMessageResponse(
            id=assistant_msg.id,
            session_id=chat_session.id,
            role="assistant",
            content=assistant_msg.content,
            detected_language=assistant_msg.detected_language,
            input_mode=assistant_msg.input_mode,
            latency_ms=assistant_msg.latency_ms,
            is_grounded=assistant_msg.is_grounded,
            created_at=assistant_msg.created_at.isoformat(),
            citations=domain_citations,
        )

    async def process_message_stream(self, request: SendMessageRequest) -> AsyncGenerator[str, None]:
        """Stream conversational response tokens over SSE while preserving grounding and citation guarantees."""
        t_start = time.perf_counter()

        # 1. Resolve or create chat session
        chat_session = await self.get_or_create_session(
            session_id=request.session_id,
            client_fingerprint=request.client_fingerprint,
            preferred_language=request.preferred_language or "kn",
        )

        # 2. Language Auto-Detection
        detection = self.language_detector.detect(
            text=request.content,
            fallback_language=chat_session.preferred_language,
        )
        active_language = request.preferred_language or detection.language
        chat_session.preferred_language = active_language
        chat_session.last_active_at = utc_now()
        self.session.add(chat_session)

        # 3. Fetch recent turn history for coreference awareness
        history = await self._get_recent_history(chat_session.id, limit=6)

        # 4. Context Query Reformulation
        reformulated_query = self._reformulate_query(request.content, history)

        # 5. Record User Turn
        user_msg = ChatMessage(
            session_id=chat_session.id,
            role="user",
            content=request.content,
            detected_language=active_language,
            input_mode=request.input_mode,
            is_grounded=True,
            created_at=utc_now(),
        )
        self.session.add(user_msg)
        await self.session.flush()

        # 6. Cross-Lingual Query Normalization for Knowledge Retrieval
        retrieval_query = reformulated_query
        if active_language == "kn" or self.language_detector.detect(reformulated_query).is_mixed:
            normalized = self.query_normalizer.normalize_for_retrieval(reformulated_query, source_lang=active_language)
            retrieval_query = normalized.retrieval_query

        # 7. Execute Hybrid RAG Retrieval
        candidates = await self.retriever.retrieve(
            query=retrieval_query,
            top_final=4,
            threshold=0.35,
        )

        # 7. Evaluate Strict Grounding Guard
        grounding_result = self.grounding_guard.evaluate(candidates, language=active_language)

        if not grounding_result.is_grounded:
            fallback = grounding_result.fallback_message or ""
            latency_ms = int((time.perf_counter() - t_start) * 1000.0)

            assistant_msg = ChatMessage(
                session_id=chat_session.id,
                role="assistant",
                content=fallback,
                detected_language=active_language,
                input_mode=request.input_mode,
                latency_ms=latency_ms,
                is_grounded=False,
                created_at=utc_now(),
            )
            self.session.add(assistant_msg)
            await self.session.commit()
            await self.session.refresh(assistant_msg)

            # Stream empty citations event
            yield f"event: citations\ndata: {json.dumps({'citations': []}, ensure_ascii=False)}\n\n"

            # Stream fallback text
            for word in fallback.split():
                yield f"event: token\ndata: {json.dumps({'token': word + ' '}, ensure_ascii=False)}\n\n"

            # Stream terminal done event
            done_payload = {
                "message_id": assistant_msg.id,
                "session_id": chat_session.id,
                "is_grounded": False,
                "detected_language": active_language,
                "latency_ms": latency_ms,
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
            return

        # Evidence is grounded!
        selected_chunks = grounding_result.selected_chunks

        assistant_msg = ChatMessage(
            session_id=chat_session.id,
            role="assistant",
            content="",
            detected_language=active_language,
            input_mode=request.input_mode,
            latency_ms=None,
            is_grounded=True,
            created_at=utc_now(),
        )
        self.session.add(assistant_msg)
        await self.session.flush()

        # Record citations and stream citation metadata immediately
        domain_citations = await self._record_citations(assistant_msg.id, selected_chunks)
        citations_data = [cit.model_dump() for cit in domain_citations]
        yield f"event: citations\ndata: {json.dumps({'citations': citations_data}, ensure_ascii=False)}\n\n"

        # Build grounded prompt
        system_prompt, user_prompt = self.prompt_builder.build_prompt(
            query=request.content,
            evidence_chunks=selected_chunks,
            language=active_language,
            history=history,
        )

        tokens_accum: list[str] = []
        try:
            async for token in self.ollama.stream_generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
            ):
                tokens_accum.append(token)
                yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

        except Exception as exc:
            logger.warning("ollama_stream_generation_fallback", error=str(exc))
            # If Ollama service is unavailable or times out, fallback to verified ground truth chunks directly
            grounded_fallback = self._format_grounded_answer(selected_chunks, active_language)
            tokens_accum = [grounded_fallback]
            for word in grounded_fallback.split():
                yield f"event: token\ndata: {json.dumps({'token': word + ' '}, ensure_ascii=False)}\n\n"

        final_content = "".join(tokens_accum).strip()
        if not final_content:
            final_content = self._format_grounded_answer(selected_chunks, active_language)

        latency_ms = int((time.perf_counter() - t_start) * 1000.0)
        assistant_msg.content = final_content
        assistant_msg.latency_ms = latency_ms
        self.session.add(assistant_msg)
        await self.session.commit()
        await self.session.refresh(assistant_msg)

        done_payload = {
            "message_id": assistant_msg.id,
            "session_id": chat_session.id,
            "is_grounded": True,
            "detected_language": active_language,
            "latency_ms": latency_ms,
        }
        yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    async def get_session_history(self, session_id: str) -> ChatSessionResponse:
        """Fetch full message turn history for a chat session."""
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            raise NotFoundError(f"Chat session '{session_id}' not found.")

        msg_stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        msg_result = await self.session.execute(msg_stmt)
        messages = msg_result.scalars().all()

        # Load citations for assistant messages
        response_messages: list[ChatMessageResponse] = []
        for msg in messages:
            citations: list[Citation] = []
            if msg.role == "assistant":
                citations = await self._get_citations_for_message(msg.id)

            response_messages.append(
                ChatMessageResponse(
                    id=msg.id,
                    session_id=msg.session_id,
                    role=msg.role,
                    content=msg.content,
                    detected_language=msg.detected_language,
                    input_mode=msg.input_mode,
                    latency_ms=msg.latency_ms,
                    is_grounded=msg.is_grounded,
                    created_at=msg.created_at.isoformat(),
                    citations=citations,
                )
            )

        return ChatSessionResponse(
            id=chat_session.id,
            client_fingerprint=chat_session.client_fingerprint,
            preferred_language=chat_session.preferred_language,
            created_at=chat_session.created_at.isoformat(),
            last_active_at=chat_session.last_active_at.isoformat(),
            messages=response_messages,
        )

    async def _get_recent_history(self, session_id: str, limit: int = 6) -> list[ChatMessage]:
        """Fetch chronological turns for coreference context."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        return list(reversed(messages))

    @staticmethod
    def _reformulate_query(query: str, history: list[ChatMessage]) -> str:
        """Reformulate query using prior conversational turns when coreferences/pronouns are detected."""
        if not history or len(query.split()) > 12:
            return query

        # Detect pronouns or vague follow-ups
        has_pronoun = bool(PRONOUN_PATTERN.search(query))
        is_short_question = len(query.split()) <= 4 and query.strip().endswith("?")

        if has_pronoun or is_short_question:
            # Extract key nouns/topics from previous user query
            previous_user_turns = [m.content for m in history if m.role == "user"]
            if previous_user_turns:
                last_user_query = previous_user_turns[-1]
                # Combine last subject with current question for grounded search
                reformulated = f"{last_user_query} {query}".strip()
                logger.info(
                    "query_reformulated_with_history",
                    original=query,
                    reformulated=reformulated,
                )
                return reformulated

        return query

    @staticmethod
    def _format_grounded_answer(chunks: list[RetrievalCandidate], language: str) -> str:
        """Format response text grounded directly on retrieved evidence chunks."""
        if not chunks:
            return "Information is not available in the knowledge base."

        # Aggregate evidence content cleanly
        excerpts = [c.content.strip() for c in chunks[:2]]
        combined_text = "\n\n".join(excerpts)
        return combined_text

    async def _record_citations(
        self, message_id: str, candidates: list[RetrievalCandidate]
    ) -> list[Citation]:
        """Record CitationReference rows in MySQL and return domain Citation models."""
        citations: list[Citation] = []

        for cand in candidates:
            # Lookup underlying DocumentChunk by document_id and page/content
            stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.document_id == cand.document_id)
                .where(DocumentChunk.page_number == cand.page_number)
            )
            result = await self.session.execute(stmt)
            chunk_entity = result.scalars().first()

            if chunk_entity:
                cit_ref = CitationReference(
                    message_id=message_id,
                    chunk_id=chunk_entity.id,
                    relevance_score=cand.rerank_score or 0.0,
                    created_at=utc_now(),
                )
                self.session.add(cit_ref)

                citations.append(
                    Citation(
                        chunk_id=chunk_entity.id,
                        document_id=cand.document_id,
                        page_number=cand.page_number,
                        section_heading=cand.section_heading,
                        relevance_score=cand.rerank_score or 0.0,
                        snippet=cand.content[:160] + ("..." if len(cand.content) > 160 else ""),
                    )
                )

        return citations

    async def _get_citations_for_message(self, message_id: str) -> list[Citation]:
        """Query citation_references joined with document_chunks for a message turn."""
        stmt = (
            select(CitationReference, DocumentChunk)
            .join(DocumentChunk, CitationReference.chunk_id == DocumentChunk.id)
            .where(CitationReference.message_id == message_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        citations: list[Citation] = []
        for cit_ref, chunk in rows:
            citations.append(
                Citation(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    relevance_score=cit_ref.relevance_score,
                    snippet=chunk.content[:160] + ("..." if len(chunk.content) > 160 else ""),
                )
            )
        return citations
