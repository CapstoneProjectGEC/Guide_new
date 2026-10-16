"""Prompt construction and context window budgeting for grounded LLM inference."""

from backend.src.application.chat.grounding_guard import (
    CANONICAL_FALLBACK_EN,
    CANONICAL_FALLBACK_KN,
)
from backend.src.core.config import get_settings
from backend.src.core.logging import get_logger
from backend.src.domain.rag import RetrievalCandidate
from backend.src.infrastructure.models.chat import ChatMessage

logger = get_logger("application.chat.prompt_builder")

SYSTEM_PROMPT_EN = (
    "You are the official Smart Tourist Guide AI for Belur Chennakeshava Temple in Karnataka, India. "
    "Your duty is to deliver strictly factual, accurate, and concise answers based ONLY on the provided context excerpts.\n"
    "CRITICAL GROUNDING RULES:\n"
    "1. Answer ONLY using the facts stated in the Context section below.\n"
    "2. Never extrapolate, guess, or use external knowledge not contained in the Context.\n"
    f"3. If the Context does not contain the complete factual answer, respond EXACTLY with: \"{CANONICAL_FALLBACK_EN}\"\n"
    "4. Answer concisely in English."
)

SYSTEM_PROMPT_KN = (
    "ನೀವು ಕರ್ನಾಟಕದ ಬೇಲೂರು ಚನ್ನಕೇಶವ ದೇವಾಲಯದ ಅಧಿಕೃತ ಸ್ಮಾರ್ಟ್ ಪ್ರವಾಸಿ ಮಾರ್ಗದರ್ಶಿ ಎಐ. "
    "ಕೆಳಗೆ ನೀಡಲಾದ ಮಾಹಿತಿಯ ಆಧಾರದ ಮೇಲೆ ಮಾತ್ರ ನಿಖರವಾದ, ಸತ್ಯವಾದ ಮತ್ತು ಸಂಕ್ಷಿಪ್ತ ಉತ್ತರಗಳನ್ನು ನೀಡುವುದು ನಿಮ್ಮ ಕರ್ತವ್ಯ.\n"
    "ಮಹತ್ವದ ನಿಯಮಗಳು:\n"
    "1. ಕೆಳಗಿನ ಸಂದರ್ಭದಲ್ಲಿ (Context) ನೀಡಲಾದ ಅಂಶಗಳನ್ನು ಆಧರಿಸಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ.\n"
    "2. ಸಂದರ್ಭದಲ್ಲಿ ಇಲ್ಲದ ಯಾವುದೇ ಕಲ್ಪಿತ ಅಥವಾ ಬಾಹ್ಯ ಮಾಹಿತಿಯನ್ನು ನೀಡಬೇಡಿ.\n"
    f"3. ಕೇಳಲಾದ ಪ್ರಶ್ನೆಗೆ ಪೂರ್ಣ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲದಿದ್ದರೆ, ನಿಖರವಾಗಿ ಹೀಗೆ ಉತ್ತರಿಸಿ: \"{CANONICAL_FALLBACK_KN}\"\n"
    "4. ಕನ್ನಡದಲ್ಲೇ ಸಂಕ್ಷಿಪ್ತವಾಗಿ ಉತ್ತರಿಸಿ."
)


class PromptBuilder:
    """Constructs token-budgeted, evidence-grounded prompts for local LLM inference."""

    def __init__(self, context_ceiling_tokens: int | None = None) -> None:
        settings = get_settings()
        self.context_ceiling_tokens = context_ceiling_tokens or settings.PROMPT_CONTEXT_CEILING_TOKENS

    def build_prompt(
        self,
        query: str,
        evidence_chunks: list[RetrievalCandidate],
        language: str = "en",
        history: list[ChatMessage] | None = None,
    ) -> tuple[str, str]:
        """Generate (system_prompt, user_prompt) adhering to context token ceilings."""
        system_prompt = SYSTEM_PROMPT_KN if language == "kn" else SYSTEM_PROMPT_EN

        # Format context excerpts while tracking estimated token budget (~1.3 tokens per word)
        context_parts: list[str] = []
        accumulated_words = 0
        word_budget = int(self.context_ceiling_tokens * 0.7)

        for chunk in evidence_chunks:
            heading = chunk.section_heading or "General"
            part = f"--- [Page {chunk.page_number} | {heading}] ---\n{chunk.content.strip()}"
            words_in_part = len(part.split())
            if accumulated_words + words_in_part > word_budget and context_parts:
                break
            context_parts.append(part)
            accumulated_words += words_in_part

        formatted_context = "\n\n".join(context_parts) if context_parts else "No context available."

        # Format conversation history compactly (last 2 turns only)
        history_parts: list[str] = []
        if history:
            recent_turns = history[-4:]
            for msg in recent_turns:
                prefix = "Tourist" if msg.role == "user" else "Guide"
                history_parts.append(f"{prefix}: {msg.content.strip()}")

        history_block = ""
        if history_parts:
            history_block = "Previous Conversation:\n" + "\n".join(history_parts) + "\n\n"

        user_prompt = (
            f"Context:\n{formatted_context}\n\n"
            f"{history_block}"
            f"Tourist Question: {query}\n\n"
            f"Guide Answer:"
        )

        logger.info(
            "prompt_constructed",
            language=language,
            chunks_used=len(context_parts),
            estimated_words=len(user_prompt.split()),
        )
        return system_prompt, user_prompt
