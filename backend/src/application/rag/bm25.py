"""In-memory BM25 Okapi lexical sparse retriever."""

import math
import re
from typing import Any
from backend.src.core.logging import get_logger

logger = get_logger("application.rag.bm25")

# Regex supporting both Latin words and Unicode scripts including Kannada (\u0C80-\u0CFF)
TOKEN_PATTERN = re.compile(r"[\w\u0c80-\u0cff]+", re.UNICODE)


class BM25Index:
    """In-memory BM25Okapi inverted index built over document chunks."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus: list[dict[str, Any]] = []
        self.doc_lengths: list[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: dict[str, int] = {}
        self.term_freqs: list[dict[str, int]] = []
        self.idf_cache: dict[str, float] = {}
        self.num_docs: int = 0

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase lexical terms supporting Kannada and English."""
        if not text:
            return []
        return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]

    def fit(self, chunks: list[dict[str, Any]]) -> "BM25Index":
        """Index a collection of chunk records: [{chunk_id, document_id, page_number, section_heading, content}]."""
        self.corpus = chunks
        self.num_docs = len(chunks)
        self.doc_lengths = []
        self.doc_freqs = {}
        self.term_freqs = []
        self.idf_cache = {}

        if self.num_docs == 0:
            self.avg_doc_len = 0.0
            return self

        total_length = 0

        for chunk in chunks:
            tokens = self.tokenize(chunk.get("content", ""))
            length = len(tokens)
            self.doc_lengths.append(length)
            total_length += length

            tf: dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            self.term_freqs.append(tf)

            for token in tf:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_len = total_length / self.num_docs

        # Precompute IDF values for all observed terms
        for term, freq in self.doc_freqs.items():
            # BM25Okapi smoothed IDF formula
            idf = math.log((self.num_docs - freq + 0.5) / (freq + 0.5) + 1.0)
            self.idf_cache[term] = max(0.0, idf)

        logger.info(
            "bm25_index_fitted",
            num_docs=self.num_docs,
            unique_terms=len(self.doc_freqs),
            avg_doc_len=f"{self.avg_doc_len:.1f}",
        )
        return self

    def search(self, query: str, top_k: int = 15) -> list[dict[str, Any]]:
        """Compute BM25 Okapi lexical scores for the query terms."""
        if self.num_docs == 0 or not query.strip():
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores: list[float] = [0.0] * self.num_docs

        for token in query_tokens:
            if token not in self.doc_freqs:
                continue

            idf = self.idf_cache.get(token, 0.0)
            if idf <= 0.0:
                continue

            for doc_idx, tf_dict in enumerate(self.term_freqs):
                freq = tf_dict.get(token, 0)
                if freq == 0:
                    continue

                doc_len = self.doc_lengths[doc_idx]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[doc_idx] += idf * (numerator / denominator)

        # Pair scores with chunk documents
        scored_results: list[tuple[int, float]] = [
            (idx, score) for idx, score in enumerate(scores) if score > 0.0
        ]
        scored_results.sort(key=lambda x: x[1], reverse=True)

        top_candidates = scored_results[:top_k]
        output: list[dict[str, Any]] = []

        for rank, (doc_idx, score) in enumerate(top_candidates, start=1):
            chunk_data = dict(self.corpus[doc_idx])
            chunk_data["sparse_rank"] = rank
            chunk_data["sparse_score"] = float(score)
            output.append(chunk_data)

        return output
