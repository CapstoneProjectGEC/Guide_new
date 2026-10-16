"""Strict Grounding Guard enforcing evidence verification and deterministic fallbacks."""

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
