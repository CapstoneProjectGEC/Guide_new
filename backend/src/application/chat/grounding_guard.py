"""Strict Grounding Guard enforcing evidence verification and deterministic fallbacks."""

import re
from pydantic import BaseModel, Field
from backend.src.domain.rag import RetrievalCandidate

CANONICAL_FALLBACK_EN = "Information is not available in the knowledge base."
CANONICAL_FALLBACK_KN = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."


class GroundingEvaluation(BaseModel):
    """Result of grounding verification against retrieved chunks."""

    is_grounded: bool
    fallback_message: str | None = None
    selected_chunks: list[RetrievalCandidate] = Field(default_factory=list)
    top_confidence: float = 0.0


class GroundingGuard:
    """Evaluates whether retrieved evidence is sufficient to answer user query without hallucinations."""

    def __init__(self, confidence_threshold: float = 0.35) -> None:
        self.confidence_threshold = confidence_threshold

    def evaluate(
        self,
        candidates: list[RetrievalCandidate],
        language: str = "kn",
    ) -> GroundingEvaluation:
        """Inspect candidate chunks and enforce canonical fallback if evidence is insufficient."""
        fallback = CANONICAL_FALLBACK_KN if language == "kn" else CANONICAL_FALLBACK_EN

        if not candidates:
            return GroundingEvaluation(
                is_grounded=False,
                fallback_message=fallback,
                selected_chunks=[],
                top_confidence=0.0,
            )

        # Top candidate confidence check
        top_cand = candidates[0]
        top_score = top_cand.rerank_score or 0.0

        if top_score < self.confidence_threshold:
            return GroundingEvaluation(
                is_grounded=False,
                fallback_message=fallback,
                selected_chunks=[],
                top_confidence=top_score,
            )

        # Filter candidates meeting threshold
        valid_chunks = [c for c in candidates if (c.rerank_score or 0.0) >= self.confidence_threshold]

        if not valid_chunks:
            return GroundingEvaluation(
                is_grounded=False,
                fallback_message=fallback,
                selected_chunks=[],
                top_confidence=top_score,
            )

        return GroundingEvaluation(
            is_grounded=True,
            fallback_message=None,
            selected_chunks=valid_chunks,
            top_confidence=top_score,
        )

    @staticmethod
    def is_query_echo(text: str, query: str) -> bool:
        """Detect whether text merely repeats the user question or query."""
        clean_t = "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()
        clean_q = "".join(c.lower() for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_t or not clean_q:
            return False
        if clean_t == clean_q:
            return True
        if clean_t.startswith(clean_q):
            remainder = clean_t[len(clean_q):].strip().split()
            if len(remainder) <= 2:
                return True
        return False

    @staticmethod
    def is_heading_only(text: str, chunks: list[RetrievalCandidate]) -> bool:
        """Detect whether text is merely a section heading without substantive facts."""
        clean_t = "".join(c.lower() for c in text if c.isalnum() or c.isspace()).strip()
        for chunk in chunks:
            heading = chunk.section_heading or ""
            clean_h = "".join(c.lower() for c in heading if c.isalnum() or c.isspace()).strip()
            if clean_h and clean_t == clean_h:
                return True
        return False

    @staticmethod
    def is_system_prompt_echo(text: str) -> bool:
        """Detect whether text echoes system prompts, persona instructions, or role definitions."""
        system_signatures = [
            "ನೀವು ಕರ್ನಾಟಕದ ಬೇಲೂರು",
            "ಚೆನ್ನಕೇಶವ ದೇವಾಲಯದ ಅಧಿಕೃತ",
            "ಚನ್ನಕೇಶವ ದೇವಾಲಯದ ಅಧಿಕೃತ",
            "ಸ್ಮಾರ್ಟ್ ಪ್ರವಾಸಿ ಮಾರ್ಗದರ್ಶಿ",
            "ಅಧಿಕೃತ ಸ್ಮಾರ್ಟ್ ಮಾರ್ಗದರ್ಶಿ",
            "ಮಹತ್ವದ ನಿಯಮಗಳು",
            "ಶುದ್ಧ ಕನ್ನಡದಲ್ಲೇ",
            "ಸಂದರ್ಭದಲ್ಲಿ ನೀಡಲಾದ",
            "you are the official smart tourist guide",
            "belur chennakeshava temple in karnataka",
            "critical grounding rules",
            "answer only using the facts",
            "never extrapolate, guess",
            "tourist question:",
            "guide answer:",
            "ಪ್ರವಾಸಿಗರ ಪ್ರಶ್ನೆ:",
            "ಮಾರ್ಗದರ್ಶಿಯ ಉತ್ತರ",
        ]
        lower_text = text.lower()
        for sig in system_signatures:
            if sig.lower() in lower_text:
                return True
        return False

    def verify_response(
        self,
        response_text: str,
        query: str,
        evidence_chunks: list[RetrievalCandidate],
        language: str = "en",
    ) -> tuple[bool, str]:
        """Verify generated answer quality and grounding.

        Returns:
            tuple[bool, str]: (is_grounded, verified_or_fallback_text)
        """
        fallback = CANONICAL_FALLBACK_KN if language == "kn" else CANONICAL_FALLBACK_EN
        stripped = response_text.strip()

        # 1. Reject empty or whitespace
        if not stripped:
            return False, fallback

        # 2. Reject canonical fallback text
        if stripped in (CANONICAL_FALLBACK_EN, CANONICAL_FALLBACK_KN):
            return False, fallback

        # 3. Reject system prompt and persona instruction echoes
        if self.is_system_prompt_echo(stripped):
            return False, fallback

        # 4. Reject query echoes
        if self.is_query_echo(stripped, query):
            return False, fallback

        # 5. Reject heading-only responses
        if self.is_heading_only(stripped, evidence_chunks):
            return False, fallback

        # 6. Require meaningful content (at least 4 words)
        words = stripped.split()
        if len(words) < 4:
            return False, fallback

        # 7. Evidence substantiation check: Ensure English answer is factually grounded in evidence chunks
        if evidence_chunks and language == "en":
            all_evidence_text = " ".join(c.content.lower() for c in evidence_chunks)
            common_fillers = {
                "the", "and", "was", "were", "with", "from", "that", "this", "have", "has", "had",
                "been", "also", "about", "into", "over", "after", "before", "their", "there", "which",
                "these", "those", "under", "where", "while", "during", "built", "known", "called",
                "located", "temple", "belur", "karnataka", "india"
            }
            ans_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", stripped.lower())) - common_fillers
            if ans_tokens:
                ev_tokens = set(re.findall(r"\b[a-zA-Z]{4,}\b", all_evidence_text))
                supported_ratio = len(ans_tokens & ev_tokens) / len(ans_tokens)
                if supported_ratio < 0.30:
                    return False, fallback

        return True, stripped
