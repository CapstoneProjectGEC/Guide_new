"""Structural semantic chunking service respecting section boundaries and token budgets."""

import re
from backend.src.core.logging import get_logger
from backend.src.domain.knowledge import ExtractedSection, TextChunk

logger = get_logger("application.pipeline.chunker")


class SemanticChunker:
    """Chunks structured text into semantic segments with provenance tracking."""

    def __init__(self, target_chunk_tokens: int = 400, overlap_tokens: int = 50) -> None:
        self.target_chunk_tokens = target_chunk_tokens
        self.overlap_tokens = overlap_tokens

    @staticmethod
    def estimate_token_count(text: str) -> int:
        """Estimate token count based on whitespace and punctuation heuristics (~1.33 tokens per word)."""
        words = text.split()
        if not words:
            return 0
        # Standard BPE heuristic: word count * 1.33 plus punctuation count
        punct_count = len(re.findall(r"[,.!?;:()\[\]\"']", text))
        estimated = int(len(words) * 1.25 + (punct_count * 0.1))
        return max(1, estimated)

    def chunk_sections(self, sections: list[ExtractedSection], document_id: str) -> list[TextChunk]:
        """Split a list of extracted sections into semantically bounded TextChunk instances."""
        chunks: list[TextChunk] = []
        chunk_idx = 0

        for section in sections:
            content = section.content.strip()
            if not content:
                continue

            est_tokens = self.estimate_token_count(content)

            # If section fits comfortably within the target + overlap envelope, keep as a single chunk
            if est_tokens <= (self.target_chunk_tokens + self.overlap_tokens):
                chunks.append(
                    TextChunk(
                        document_id=document_id,
                        chunk_index=chunk_idx,
                        page_number=section.page_number,
                        section_heading=section.section_heading,
                        content=content,
                        token_count=est_tokens,
                    )
                )
                chunk_idx += 1
            else:
                # Section exceeds target size, split into sub-chunks respecting paragraph/sentence boundaries
                sub_chunks = self._split_large_section(section, document_id, chunk_idx)
                chunks.extend(sub_chunks)
                chunk_idx += len(sub_chunks)

        logger.info(
            "semantic_chunking_completed",
            document_id=document_id,
            sections_count=len(sections),
            total_chunks=len(chunks),
        )
        return chunks

    def _split_large_section(
        self, section: ExtractedSection, document_id: str, starting_idx: int
    ) -> list[TextChunk]:
        """Split an oversized section into overlapping chunks."""
        # 1. Break into paragraph units
        paragraphs = [p.strip() for p in section.content.split("\n\n") if p.strip()]
        
        # 2. Break down into sentence units if paragraphs are too large
        units: list[str] = []
        for p in paragraphs:
            if self.estimate_token_count(p) > self.target_chunk_tokens:
                sentences = re.split(r"(?<=[.!?])\s+", p)
                units.extend([s.strip() for s in sentences if s.strip()])
            else:
                units.append(p)

        sub_chunks: list[TextChunk] = []
        current_units: list[str] = []
        current_tokens = 0
        current_idx = starting_idx

        for unit in units:
            unit_tokens = self.estimate_token_count(unit)
            if current_tokens + unit_tokens > self.target_chunk_tokens and current_units:
                # Flush current buffer
                chunk_text = "\n\n".join(current_units).strip()
                sub_chunks.append(
                    TextChunk(
                        document_id=document_id,
                        chunk_index=current_idx,
                        page_number=section.page_number,
                        section_heading=section.section_heading,
                        content=chunk_text,
                        token_count=current_tokens,
                    )
                )
                current_idx += 1

                # Retain overlap from end of current units
                overlap_units: list[str] = []
                overlap_tokens_accum = 0
                for prev_unit in reversed(current_units):
                    p_tokens = self.estimate_token_count(prev_unit)
                    if overlap_tokens_accum + p_tokens <= self.overlap_tokens:
                        overlap_units.insert(0, prev_unit)
                        overlap_tokens_accum += p_tokens
                    else:
                        break

                current_units = overlap_units
                current_tokens = overlap_tokens_accum

            current_units.append(unit)
            current_tokens += unit_tokens

        # Flush final remaining buffer
        if current_units:
            chunk_text = "\n\n".join(current_units).strip()
            sub_chunks.append(
                TextChunk(
                    document_id=document_id,
                    chunk_index=current_idx,
                    page_number=section.page_number,
                    section_heading=section.section_heading,
                    content=chunk_text,
                    token_count=current_tokens,
                )
            )

        return sub_chunks
