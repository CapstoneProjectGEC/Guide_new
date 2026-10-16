"""PDF text extraction and Unicode NFKC normalization service."""

import re
import unicodedata
from pathlib import Path
import pymupdf
from backend.src.core.errors import ValidationError
from backend.src.core.logging import get_logger
from backend.src.domain.knowledge import ExtractedSection

logger = get_logger("application.pipeline.extractor")

HEADING_PATTERNS = [
    re.compile(r"^(Section\s+\d+\s*:\s*.+)$", re.IGNORECASE),
    re.compile(r"^(Chapter\s+\d+\s*:\s*.+)$", re.IGNORECASE),
    re.compile(r"^([A-Z0-9\s\-:,\.]{4,80})$"),
]


class PDFExtractor:
    """Extracts structured text with heading awareness and Unicode NFKC normalization."""

    def extract_from_bytes(self, content: bytes, filename: str = "document.pdf") -> list[ExtractedSection]:
        """Extract sections from in-memory PDF bytes."""
        if not content:
            raise ValidationError(f"Document content for '{filename}' is empty.")

        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
        except Exception as exc:
            logger.error("pymupdf_open_failed", filename=filename, error=str(exc))
            raise ValidationError(f"Failed to open PDF document '{filename}': {exc}") from exc

        try:
            return self._extract_from_document(doc, filename)
        finally:
            doc.close()

    def extract_from_file(self, file_path: str | Path) -> list[ExtractedSection]:
        """Extract sections from a local filesystem PDF path."""
        path = Path(file_path)
        if not path.is_file():
            raise ValidationError(f"PDF file not found at path: {path}")

        try:
            doc = pymupdf.open(str(path))
        except Exception as exc:
            logger.error("pymupdf_open_failed", path=str(path), error=str(exc))
            raise ValidationError(f"Failed to open PDF file at '{path}': {exc}") from exc

        try:
            return self._extract_from_document(doc, path.name)
        finally:
            doc.close()

    def _extract_from_document(self, doc: pymupdf.Document, filename: str) -> list[ExtractedSection]:
        """Iterate through document pages and extract structured sections."""
        extracted: list[ExtractedSection] = []
        current_heading: str | None = None

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]

            # Extract blocks from PyMuPDF: (x0, y0, x1, y1, text, block_no, block_type)
            # block_type == 0 indicates text block
            blocks = page.get_text("blocks")
            page_buffer: list[str] = []

            for block in blocks:
                if len(block) < 5:
                    continue
                block_type = block[6] if len(block) > 6 else 0
                if block_type != 0:
                    continue

                raw_text = block[4]
                normalized_block = self.normalize_text(raw_text)
                if not normalized_block:
                    continue

                # Check if block is a heading candidate
                lines = [line.strip() for line in normalized_block.splitlines() if line.strip()]
                if not lines:
                    continue

                first_line = lines[0]
                is_heading = self._is_heading_candidate(first_line)

                if is_heading:
                    # Flush accumulated page buffer under previous heading
                    if page_buffer:
                        combined_content = "\n\n".join(page_buffer).strip()
                        if combined_content:
                            extracted.append(
                                ExtractedSection(
                                    page_number=page_num,
                                    section_heading=current_heading,
                                    content=combined_content,
                                )
                            )
                        page_buffer.clear()

                    current_heading = first_line
                    # Remaining lines belong to body
                    remaining_body = "\n".join(lines[1:]).strip()
                    if remaining_body:
                        page_buffer.append(remaining_body)
                else:
                    page_buffer.append(normalized_block)

            # Flush any remaining buffer for the page
            if page_buffer:
                combined_content = "\n\n".join(page_buffer).strip()
                if combined_content:
                    extracted.append(
                        ExtractedSection(
                            page_number=page_num,
                            section_heading=current_heading,
                            content=combined_content,
                        )
                    )
                page_buffer.clear()

        logger.info(
            "pdf_extraction_completed",
            filename=filename,
            pages=len(doc),
            sections_extracted=len(extracted),
        )
        return extracted

    @staticmethod
    def normalize_text(text: str) -> str:
        """Apply Unicode NFKC normalization and clean whitespace."""
        if not text:
            return ""

        # 1. Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Normalize whitespace and newlines
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        # Replace non-breaking spaces and tabs
        normalized = normalized.replace("\xa0", " ").replace("\t", " ")

        # 3. Collapse excessive horizontal spaces
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]

        # 4. Collapse more than 2 consecutive blank lines
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _is_heading_candidate(line: str) -> bool:
        """Determine whether a line qualifies as a section heading."""
        trimmed = line.strip()
        if len(trimmed) < 3 or len(trimmed) > 120:
            return False

        # Explicit section label
        if re.match(r"^Section\s+\d+\s*:\s*.+", trimmed, re.IGNORECASE):
            return True

        if re.match(r"^Chapter\s+\d+\s*:\s*.+", trimmed, re.IGNORECASE):
            return True

        # All uppercase heading of reasonable length without sentence punctuation ending
        if trimmed.isupper() and not trimmed.endswith((".", "?", "!")):
            return True

        return False
