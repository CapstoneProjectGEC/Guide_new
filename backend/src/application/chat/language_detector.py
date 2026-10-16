"""Fast, deterministic language auto-detection for Kannada, English, and mixed scripts."""

import re
from pydantic import BaseModel, Field

KANNADA_PATTERN = re.compile(r"[\u0c80-\u0cff]")
LATIN_PATTERN = re.compile(r"[a-zA-Z]")


class LanguageDetectionResult(BaseModel):
    """Result payload from script inspection."""

    language: str = Field(description="Detected language code: 'kn' or 'en'")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence score")
    is_mixed: bool = Field(default=False, description="Whether query contains both Kannada and Latin scripts")
    kannada_chars: int = Field(default=0)
    latin_chars: int = Field(default=0)


class LanguageDetector:
    """Detects Kannada and English script usage in conversational inputs."""

    def detect(self, text: str, fallback_language: str = "kn") -> LanguageDetectionResult:
        """Inspect Unicode code points and determine primary language code."""
        if not text or not text.strip():
            return LanguageDetectionResult(
                language=fallback_language,
                confidence=1.0,
                is_mixed=False,
                kannada_chars=0,
                latin_chars=0,
            )

        kannada_count = len(KANNADA_PATTERN.findall(text))
        latin_count = len(LATIN_PATTERN.findall(text))
        total_letters = kannada_count + latin_count

        if total_letters == 0:
            # Query has no letters (e.g., numbers or punctuation only)
            return LanguageDetectionResult(
                language=fallback_language,
                confidence=0.5,
                is_mixed=False,
                kannada_chars=0,
                latin_chars=0,
            )

        is_mixed = kannada_count > 0 and latin_count > 0

        # If any significant Kannada script is present, prioritize Kannada
        if kannada_count > 0 and (kannada_count >= latin_count * 0.25):
            confidence = round(kannada_count / total_letters, 3)
            return LanguageDetectionResult(
                language="kn",
                confidence=max(0.6, confidence),
                is_mixed=is_mixed,
                kannada_chars=kannada_count,
                latin_chars=latin_count,
            )

        # Primarily English
        confidence = round(latin_count / total_letters, 3)
        return LanguageDetectionResult(
            language="en",
            confidence=max(0.6, confidence),
            is_mixed=is_mixed,
            kannada_chars=kannada_count,
            latin_chars=latin_count,
        )
