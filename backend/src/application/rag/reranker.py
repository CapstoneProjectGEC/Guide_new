"""Cross-encoder re-ranking service using ms-marco-MiniLM-L-6-v2."""

from functools import lru_cache
import math
import re
from typing import Any
from sentence_transformers import CrossEncoder
from backend.src.core.config import get_settings
from backend.src.core.logging import get_logger

logger = get_logger("application.rag.reranker")

NOISE_PATTERNS = [
    re.compile(r"^table of contents", re.IGNORECASE),
    re.compile(r"^references\s*$", re.IGNORECASE),
    re.compile(r"^index\s*$", re.IGNORECASE),
]


class CrossEncoderReranker:
    """Re-scores candidate chunks against the query using a cross-encoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        """Lazily load the CrossEncoder model."""
        if self._model is None:
            logger.info("loading_cross_encoder_model", model=self.model_name)
            self._model = CrossEncoder(self.model_name)
        return self._model

    @staticmethod
    def sigmoid(score: float) -> float:
        """Map raw unbounded cross-encoder logit into [0, 1] confidence probability."""
        if score < -40:
            return 0.0
        if score > 40:
            return 1.0
        return 1.0 / (1.0 + math.exp(-score))

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 4,
        threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """Score (query, chunk) pairs, apply sigmoid, filter by threshold, and return top_k."""
        if not candidates or not query.strip():
            return []

        # Filter out obvious boilerplate or empty content
        valid_candidates: list[dict[str, Any]] = []
        pairs: list[tuple[str, str]] = []

        for candidate in candidates:
            content = candidate.get("content", "").strip()
            if not content or len(content) < 15:
                continue

            if any(pat.match(content) for pat in NOISE_PATTERNS):
                continue

            valid_candidates.append(dict(candidate))
            pairs.append((query, content))

        if not pairs:
            return []

        # Predict cross-encoder logits
        raw_scores = self.model.predict(pairs)

        scored_candidates: list[dict[str, Any]] = []
        for cand, raw_score in zip(valid_candidates, raw_scores, strict=True):
            prob = self.sigmoid(float(raw_score))
            cand["rerank_score"] = round(prob, 4)
            cand["raw_rerank_logit"] = round(float(raw_score), 4)

            # Filter against minimum confidence threshold
            if prob >= threshold:
                cand["is_selected"] = True
                scored_candidates.append(cand)
            else:
                cand["is_selected"] = False

        # Sort descending by re-ranking confidence score
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        selected = scored_candidates[:top_k]
        logger.info(
            "cross_encoder_rerank_completed",
            query=query[:40],
            candidates_in=len(candidates),
            candidates_above_threshold=len(scored_candidates),
            final_selected=len(selected),
        )
        return selected


@lru_cache(maxsize=1)
def get_cross_encoder_reranker() -> CrossEncoderReranker:
    """Return cached CrossEncoderReranker singleton."""
    settings = get_settings()
    return CrossEncoderReranker(model_name=settings.CROSS_ENCODER_MODEL_NAME)
