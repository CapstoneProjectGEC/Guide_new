"""Multilingual conversation engine, session state tracker, and grounding orchestrator."""

import json
from datetime import datetime
from pathlib import Path
import re
import time
import uuid
from typing import AsyncGenerator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.application.chat.grounding_guard import (
    GroundingGuard,
    CANONICAL_FALLBACK_EN,
    CANONICAL_FALLBACK_KN,
)
from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.chat.prompt_builder import PromptBuilder
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.application.translation.fact_validator import FactPreservationValidator
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.application.translation.translator import TranslationService
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
        translation_service: TranslationService | None = None,
    ) -> None:
        self.session = session
        self.retriever = retriever or HybridRAGRetriever(session=session)
        self.language_detector = language_detector or LanguageDetector()
        self.grounding_guard = grounding_guard or GroundingGuard()
        self.ollama = ollama_client or get_ollama_client()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.query_normalizer = query_normalizer or QueryNormalizer()
        self.translation_service = translation_service or TranslationService()

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
        llm_question_en = reformulated_query
        if active_language == "kn" or self.language_detector.detect(reformulated_query).is_mixed:
            normalized = self.query_normalizer.normalize_for_retrieval(reformulated_query, source_lang=active_language)
            retrieval_query = normalized.retrieval_query
            translated_q = self.translation_service.translate_text(reformulated_query, "kn", "en")
            if translated_q and len(translated_q.split()) >= 3:
                llm_question_en = translated_q
            else:
                llm_question_en = retrieval_query

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

            # Prompt Ollama in English for high-speed factual grounding
            system_prompt, user_prompt = self.prompt_builder.build_prompt(
                query=llm_question_en if active_language == "kn" else request.content,
                evidence_chunks=selected_chunks,
                language="en",
                history=history,
            )
            raw_answer = ""
            try:
                raw_answer = await self.ollama.generate(prompt=user_prompt, system_prompt=system_prompt)
            except Exception as exc:
                logger.warning("ollama_generate_fallback", error=str(exc))
                raw_answer = self._format_grounded_answer(selected_chunks, "en")

            cleaned = raw_answer.strip()
            for prefix in ("Guide Answer (1-2 sentences):", "Guide Answer:", "Guide:", "Tourist Question:", "ಮಾರ್ಗದರ್ಶಿ:", "ಉತ್ತರ:"):
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):].strip()

            # Verify English response against evidence chunks before translating
            is_grounded, verified_content = self.grounding_guard.verify_response(
                response_text=cleaned,
                query=request.content,
                evidence_chunks=selected_chunks,
                language="en",
            )
            if not is_grounded:
                assistant_content = CANONICAL_FALLBACK_KN if active_language == "kn" else CANONICAL_FALLBACK_EN
                selected_chunks = []
            else:
                if active_language == "kn":
                    translated_kn = self.translation_service.translate_text(cleaned, "en", "kn")
                    valid, missing = FactPreservationValidator.validate(cleaned, translated_kn)
                    if not valid:
                        logger.warning("retrying_translation_due_to_missing_facts", missing=missing)
                        translated_kn = self.translation_service.translate_text(cleaned, "en", "kn")
                        valid, missing = FactPreservationValidator.validate(cleaned, translated_kn)
                    assistant_content = translated_kn
                else:
                    assistant_content = verified_content

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

        # 10. Map Citations & Relational References with strict claim-to-evidence matching
        domain_citations: list[Citation] = []
        if is_grounded and selected_chunks:
            supported_chunks = self._select_relevant_citations(selected_chunks, f"{request.content} {assistant_content}")
            domain_citations = await self._record_citations(assistant_msg.id, supported_chunks)

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
        stage_timings: dict[str, float] = {}

        # 1. Resolve or create chat session
        chat_session = await self.get_or_create_session(
            session_id=request.session_id,
            client_fingerprint=request.client_fingerprint,
            preferred_language=request.preferred_language or "kn",
        )

        # 2. Language Auto-Detection
        t_lang = time.perf_counter()
        detection = self.language_detector.detect(
            text=request.content,
            fallback_language=chat_session.preferred_language,
        )
        stage_timings["language_detection_ms"] = round((time.perf_counter() - t_lang) * 1000.0, 2)
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
        t_qtrans = time.perf_counter()
        retrieval_query = reformulated_query
        if active_language == "kn" or self.language_detector.detect(reformulated_query).is_mixed:
            normalized = self.query_normalizer.normalize_for_retrieval(reformulated_query, source_lang=active_language)
            retrieval_query = normalized.retrieval_query
        stage_timings["query_translation_ms"] = round((time.perf_counter() - t_qtrans) * 1000.0, 2)

        # 7. Execute Hybrid RAG Retrieval
        t_retrieval = time.perf_counter()
        candidates = await self.retriever.retrieve(
            query=retrieval_query,
            top_final=4,
            threshold=0.35,
        )
        stage_timings["retrieval_ms"] = round((time.perf_counter() - t_retrieval) * 1000.0, 2)

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

        # Determine English query for high-speed factual Ollama generation (~400ms)
        llm_query = request.content
        if active_language == "kn":
            norm = self.query_normalizer.normalize_for_retrieval(
                reformulated_query, source_lang="kn", target_lang="en"
            )
            llm_query = norm.retrieval_query or retrieval_query

        # Filter citations to only relevant evidence chunks using token, number, and concept overlap
        citation_context = f"{request.content} {llm_query}"
        relevant_chunks = self._select_relevant_citations(selected_chunks, citation_context)
        if not relevant_chunks:
            relevant_chunks = selected_chunks

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

        # Record and stream relevant citations
        domain_citations = await self._record_citations(assistant_msg.id, relevant_chunks)
        citations_data = [cit.model_dump() for cit in domain_citations]
        yield f"event: citations\ndata: {json.dumps({'citations': citations_data}, ensure_ascii=False)}\n\n"

        # Build grounded prompt
        # We always prompt Ollama in English for high-speed factual precision (~500ms),
        # preventing the 14-second repetition loop that occurs when prompting 3B models in Kannada.
        system_prompt, user_prompt = self.prompt_builder.build_prompt(
            query=llm_query,
            evidence_chunks=relevant_chunks,
            language="en",
            history=history,
        )

        tokens_accum: list[str] = []
        t_llm_start = time.perf_counter()
        first_token_seen = False

        if active_language == "en":
            try:
                async for token in self.ollama.stream_generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                ):
                    if not first_token_seen:
                        stage_timings["llm_ttft_ms"] = round((time.perf_counter() - t_llm_start) * 1000.0, 2)
                        first_token_seen = True
                    tokens_accum.append(token)
                    yield f"event: token\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

            except Exception as exc:
                logger.warning("ollama_stream_generation_fallback", error=str(exc))
                grounded_fallback = self._format_grounded_answer(relevant_chunks, "en")
                tokens_accum = [grounded_fallback]
                for word in grounded_fallback.split():
                    yield f"event: token\ndata: {json.dumps({'token': word + ' '}, ensure_ascii=False)}\n\n"

            stage_timings["llm_generation_ms"] = round((time.perf_counter() - t_llm_start) * 1000.0, 2)
            raw_final_content = "".join(tokens_accum).strip()
            cleaned_content = raw_final_content
            for prefix in ("Guide Answer (1-2 sentences):", "Guide Answer:", "Guide:", "Tourist Question:"):
                if cleaned_content.startswith(prefix):
                    cleaned_content = cleaned_content[len(prefix):].strip()

            is_grounded, verified_content = self.grounding_guard.verify_response(
                response_text=cleaned_content,
                query=request.content,
                evidence_chunks=relevant_chunks,
                language="en",
            )

            if not is_grounded:
                if verified_content != CANONICAL_FALLBACK_EN:
                    grounded_body = self._format_grounded_answer(relevant_chunks, "en")
                    is_grounded, verified_content = self.grounding_guard.verify_response(
                        response_text=grounded_body,
                        query=request.content,
                        evidence_chunks=relevant_chunks,
                        language="en",
                    )
                if verified_content != cleaned_content and verified_content != CANONICAL_FALLBACK_EN:
                    yield f"event: token\ndata: {json.dumps({'token': ' ' + verified_content}, ensure_ascii=False)}\n\n"

        else:
            # active_language == "kn"
            try:
                async for token in self.ollama.stream_generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                ):
                    if not first_token_seen:
                        stage_timings["llm_ttft_ms"] = round((time.perf_counter() - t_llm_start) * 1000.0, 2)
                        first_token_seen = True
                    tokens_accum.append(token)
            except Exception as exc:
                logger.warning("ollama_stream_generation_fallback", error=str(exc))
                grounded_fallback = self._format_grounded_answer(relevant_chunks, "en")
                tokens_accum = [grounded_fallback]

            stage_timings["llm_generation_ms"] = round((time.perf_counter() - t_llm_start) * 1000.0, 2)
            raw_final_content = "".join(tokens_accum).strip()
            cleaned_en = raw_final_content
            for prefix in ("Guide Answer (1-2 sentences):", "Guide Answer:", "Guide:", "Tourist Question:"):
                if cleaned_en.startswith(prefix):
                    cleaned_en = cleaned_en[len(prefix):].strip()

            # Ensure clean sentence boundary before translation to prevent mid-sentence cuts
            match = re.search(r"^(.*[.!?])(?:\s+[^.!?]*)$", cleaned_en, re.DOTALL)
            if match and match.group(1).strip():
                cleaned_en = match.group(1).strip()

            # Verify English output against evidence chunks before translating
            is_grounded, verified_content = self.grounding_guard.verify_response(
                response_text=cleaned_en,
                query=request.content,
                evidence_chunks=relevant_chunks,
                language="en",
            )
            if not is_grounded:
                verified_content = CANONICAL_FALLBACK_KN
            else:
                # Translate factual English answer to authentic Kannada
                t_ans_trans = time.perf_counter()
                translated_kn = self.translation_service.translate_text(
                    text=cleaned_en,
                    source_language="en",
                    target_language="kn",
                )
                stage_timings["answer_translation_ms"] = round((time.perf_counter() - t_ans_trans) * 1000.0, 2)

                # Fact-preservation check
                t_fact = time.perf_counter()
                is_fact_valid, missing_facts = FactPreservationValidator.validate(cleaned_en, translated_kn)
                if not is_fact_valid:
                    logger.warning("fact_preservation_issue", missing=missing_facts)
                    # Production retry path for fact preservation
                    retry_kn = self.translation_service.translate_text(cleaned_en, "en", "kn")
                    is_retry_valid, retry_missing = FactPreservationValidator.validate(cleaned_en, retry_kn)
                    if is_retry_valid:
                        translated_kn = retry_kn
                        logger.info("fact_preservation_retry_succeeded")
                    else:
                        logger.warning("fact_preservation_retry_still_missing", missing=retry_missing)
                stage_timings["fact_validation_ms"] = round((time.perf_counter() - t_fact) * 1000.0, 2)
                verified_content = translated_kn

            # Stream the verified Kannada response tokens to the client
            t_sse = time.perf_counter()
            for word in verified_content.split():
                yield f"event: token\ndata: {json.dumps({'token': word + ' '}, ensure_ascii=False)}\n\n"
            stage_timings["sse_serialization_ms"] = round((time.perf_counter() - t_sse) * 1000.0, 2)

        latency_ms = int((time.perf_counter() - t_start) * 1000.0)
        stage_timings["total_ms"] = latency_ms
        assistant_msg.content = verified_content
        assistant_msg.is_grounded = is_grounded
        assistant_msg.latency_ms = latency_ms

        # Log structured request timing entry
        try:
            timing_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "query": request.content,
                "language": active_language,
                "is_grounded": is_grounded,
                "stage_timings": stage_timings,
            }
            log_f = Path("logs/request_timings.jsonl")
            log_f.parent.mkdir(parents=True, exist_ok=True)
            with open(log_f, "a", encoding="utf-8") as f:
                f.write(json.dumps(timing_log, ensure_ascii=False) + "\n")
        except Exception:
            pass

        # If ungrounded or fallback, delete any recorded citation references so ungrounded turns are not falsely verified
        if not is_grounded:
            delete_cit_stmt = (
                select(CitationReference)
                .where(CitationReference.message_id == assistant_msg.id)
            )
            cit_res = await self.session.execute(delete_cit_stmt)
            for cit_obj in cit_res.scalars().all():
                await self.session.delete(cit_obj)

        self.session.add(assistant_msg)
        await self.session.commit()
        await self.session.refresh(assistant_msg)

        done_payload = {
            "message_id": assistant_msg.id,
            "session_id": chat_session.id,
            "is_grounded": is_grounded,
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

    def _format_grounded_answer(self, chunks: list[RetrievalCandidate], language: str) -> str:
        """Format response text grounded directly on retrieved evidence chunks."""
        fallback = CANONICAL_FALLBACK_KN if language == "kn" else CANONICAL_FALLBACK_EN
        if not chunks:
            return fallback

        # Aggregate evidence content cleanly, stripping duplicate leading headings
        body_parts: list[str] = []
        for c in chunks[:2]:
            lines = c.content.strip().splitlines()
            if len(lines) > 1 and c.section_heading and lines[0].strip().lower() == c.section_heading.strip().lower():
                body = "\n".join(lines[1:]).strip()
            else:
                body = c.content.strip()
            if body:
                body_parts.append(body)

        combined_text = "\n\n".join(body_parts).strip()
        if len(combined_text.split()) < 4:
            return fallback

        if language == "kn":
            return self.translation_service.translate_text(combined_text, "en", "kn")
        return combined_text

    @staticmethod
    def _select_relevant_citations(
        candidates: list[RetrievalCandidate],
        context_text: str,
    ) -> list[RetrievalCandidate]:
        """Filter citations to only include chunks that factually support claims in context_text.

        Uses token and number overlap across English/Kannada terms and architectural concepts,
        ensuring multi-part queries cite all relevant chunks while single-topic queries isolate
        to their exact evidence chunk.
        """
        if not candidates or not context_text.strip():
            return []

        if context_text in (CANONICAL_FALLBACK_EN, CANONICAL_FALLBACK_KN):
            return []

        ctx_lower = context_text.lower()
        supported: list[RetrievalCandidate] = []

        STEM_MAP: dict[str, set[str]] = {
            "built": {"built", "commissioned", "commission", "inception", "construct", "builder", "ನಿರ್ಮಿಸಿದ", "ಕಟ್ಟಿಸಿದ", "ಕಟ್ಟಿಸಿದರು"},
            "patron": {"king", "ruler", "patron", "vishnuvardhana", "victory", "talakad", "chola", "ದೊರೆ", "ರಾಜ", "ವಿಷ್ಣುವರ್ಧನ", "ತಲಕಾಡು", "ಚೋಳ"},
            "date": {"1117", "103", "year", "date", "century", "ಯಾವಾಗ", "ವರ್ಷ", "೧೧೧೭"},
            "deity": {"deity", "idol", "lord", "vishnu", "god", "shankha", "chakra", "gada", "padma", "ವಿಗ್ರಹ", "ದೇವರು", "ದೇವತೆ", "ಶಂಖ", "ಚಕ್ರ"},
            "sanctum": {"sanctum", "garbhagriha", "black stone", "ಗರ್ಭಗೃಹ", "ಗರ್ಭಗುಡಿ", "ಪವಿತ್ರಸ್ಥಾನ", "ಕೃಷ್ಣಶಿಲೆ"},
            "pillar": {"pillar", "pillars", "lathe", "stambha", "narasimha pillar", "mohar", "ಕಂಬಗಳು", "ಖಂಬ", "ಸ್ತಂಭ"},
            "madanika": {"madanika", "bracket", "salabhanjika", "darpana", "sundari", "42", "38", "ಮದನಿಕಾ", "ಶಿಲಾಬಾಲಿಕೆ", "ದರ್ಪಣ", "೪೨", "೩೮"},
            "frieze": {"frieze", "friezes", "elephant", "relief", "tier", "horse", "lion", "650", "ಸಾಲಿನ", "ಆನೆ", "೬೫೦"},
            "material": {"soapstone", "chloritic", "schist", "metamorphic", "stellate", "jagati", "ಬಳಪದ", "ಸೋಪ್", "ಜಗತಿ", "ನಕ್ಷತ್ರಾಕಾರ"},
        }

        # Stop words that should not drive citation overlap
        stops = {
            "the", "and", "was", "were", "for", "with", "from", "that", "this", "over", "into",
            "what", "who", "when", "where", "how", "temple", "belur", "chennakeshava", "ಮತ್ತು",
            "ಇದೆ", "ನಲ್ಲಿ", "ಆಗಿದೆ", "are", "which", "about", "tell", "explain", "details"
        }

        ctx_tokens = set(re.findall(r"[a-zA-Z0-9\u0c80-\u0cff]{3,}", ctx_lower)) - stops
        ctx_nums = set(re.findall(r"\b\d+\b", ctx_lower))

        for cand in candidates:
            cand_lower = (cand.content + " " + (cand.section_heading or "")).lower()
            cand_tokens = set(re.findall(r"[a-zA-Z0-9\u0c80-\u0cff]{3,}", cand_lower)) - stops
            cand_nums = set(re.findall(r"\b\d+\b", cand_lower))

            # 1. Number / Year exact overlap
            if ctx_nums and (ctx_nums & cand_nums):
                supported.append(cand)
                continue

            # 2. Distinctive token overlap (>= 2 significant non-stopwords)
            overlap = ctx_tokens & cand_tokens
            if len(overlap) >= 2:
                supported.append(cand)
                continue

            # 3. Conceptual stem matching with word-boundary isolation
            for _, terms in STEM_MAP.items():
                ctx_has_concept = any(
                    bool(re.search(r"(?:^|[\s\W])" + re.escape(term) + r"(?:$|[\s\W])", ctx_lower))
                    for term in terms
                )
                cand_has_concept = any(
                    bool(re.search(r"(?:^|[\s\W])" + re.escape(term) + r"(?:$|[\s\W])", cand_lower))
                    for term in terms
                )
                if ctx_has_concept and cand_has_concept:
                    supported.append(cand)
                    break

        # Fallback to top-ranked candidate if none specifically matched
        if not supported and candidates:
            supported = [candidates[0]]

        # Preserve uniqueness while preserving order
        seen_chunks: set[str] = set()
        deduped: list[RetrievalCandidate] = []
        for cand in supported:
            if cand.chunk_id not in seen_chunks:
                seen_chunks.add(cand.chunk_id)
                deduped.append(cand)

        return deduped

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
