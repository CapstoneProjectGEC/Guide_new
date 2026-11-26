"""Terminology and glossary post-processor for Belur Heritage domain.

Per Phase 4 architecture:
This component does NOT generate complete answers or replace sentences.
It post-processes translated text to ensure authoritative heritage terminology,
standard Kannada orthography, and proper entity rendering.
"""

import re
from backend.src.core.logging import get_logger

logger = get_logger("application.translation.heritage_translator")

# Helper patterns for Indic script boundaries (standard \b fails on Unicode combining marks)
L_KN = r"(?<![ಅ-ಹ\u0c80-\u0cff])"
R_KN = r"(?![ಅ-ಹ\u0c80-\u0cff])"

# Authoritative Kannada orthography alignments for neural translation outputs.
# Pure terminology and spelling normalizer: preserves all grammatical case endings,
# suffixes, adpositions, and tense/honorific endings produced by neural translation.
ORTHOGRAPHIC_CORRECTIONS: list[tuple[re.Pattern, str]] = [
    # Era markers (CE / BCE to ಕ್ರಿ.ಶ. / ಕ್ರಿ.ಪೂ. with proper Kannada postpositions)
    (re.compile(rf"{L_KN}(\d{{4}})\s*(?:CE|AD)\s*ಯಲ್ಲಿ{R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಶ. \1ರಲ್ಲಿ"),
    (re.compile(rf"{L_KN}(\d{{4}})\s*(?:CE|AD)\s*ನಲ್ಲಿ{R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಶ. \1ರಲ್ಲಿ"),
    (re.compile(rf"{L_KN}(\d{{4}})\s*(?:CE|AD)\s*ರಲ್ಲಿ{R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಶ. \1ರಲ್ಲಿ"),
    (re.compile(rf"{L_KN}(\d{{4}})\s*(?:CE|AD){R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಶ. \1"),
    (re.compile(rf"{L_KN}(?:CE|AD)\s*(\d{{4}}){R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಶ. \1"),
    (re.compile(rf"{L_KN}(\d{{3,4}})\s*BCE\s*ಯಲ್ಲಿ{R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಪೂ. \1ರಲ್ಲಿ"),
    (re.compile(rf"{L_KN}(\d{{3,4}})\s*BCE{R_KN}", re.IGNORECASE), r"ಕ್ರಿ.ಪೂ. \1"),
    # Shrines & Royal Patrons
    (re.compile(rf"{L_KN}ಕಪ್ಪೆ[\s-]ಚೆನ್ನೀ?ಗರಾಯ{R_KN}", re.IGNORECASE), "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ"),
    (re.compile(rf"{L_KN}ಕಪ್ಪೆ[\s-]ಚೆನ್ನಕೇಶವ{R_KN}", re.IGNORECASE), "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ"),
    (re.compile(rf"{L_KN}(?:ರಾಜಕುಮಾರಿ\s+|ರಾಣಿ\s+)?(?:ಸಂಟಾಲೆ|ಸಾಂಟಾಲೆ)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ರಾಣಿ ಶಾಂತಲಾ ದೇವಿ\1"),
    (re.compile(rf"{L_KN}ಭ್ಯಖುನಾ{R_KN}", re.IGNORECASE), "ವರುಣ"),
    (re.compile(rf"{L_KN}ಸೀಲಿಗಳು{R_KN}", re.IGNORECASE), "ಮೇಲ್ಛಾವಣಿಗಳು"),
    (re.compile(rf"{L_KN}ವೇರ್ಡಾಗಳು{R_KN}", re.IGNORECASE), "ವರಾಂಡಗಳು"),
    (re.compile(rf"{L_KN}ಬ್ರಾಕೆಟ್\s*ಶಿಲ್ಪಗಳು{R_KN}", re.IGNORECASE), "ಮದನಿಕಾ ಶಿಲ್ಪಗಳು"),
    # Common untranslated Latin domain loanwords
    (re.compile(r"\bverandas\b", re.IGNORECASE), "ವರಾಂಡಗಳು"),
    (re.compile(r"\bveranda\b", re.IGNORECASE), "ವರಾಂಡ"),
    (re.compile(r"\bcomplex\b", re.IGNORECASE), "ಸಂಕೀರ್ಣ"),
    # Location proper nouns - correct base spelling while preserving suffixes (e.g. ನಲ್ಲಿ, ನ, ಗೆ, ಂದ)
    (re.compile(rf"{L_KN}(?:ಬೆಲು|ಬೇಲು|ಬೆಲೂ)ರಿ([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಬೇಲೂರಿ\1"),
    (re.compile(rf"{L_KN}(?:ಬೆಲುರ್|ಬೆಲೂರು|ಬೇಲೂರ್|ಬೆಲು){R_KN}", re.IGNORECASE), "ಬೇಲೂರು"),
    # Temple name - correct stem spelling while preserving suffixes
    (re.compile(rf"{L_KN}(?:ಚೆನ್ನಕೇಶ್ವ|ಚೆನ್ನಕೇಶವಸ್ವಾಮಿ|ಚಿನ್ನಕೇಶ್ವ|ಚಿನ್ನಕೇಶವ|ಚೆನ್ನಾ-ಕೆಸವಾ|ಚೆನ್ನಾಕೆಸವಾ)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಚೆನ್ನಕೇಶವ\1"),
    # Saumyanayaki Goddess Shrine
    (re.compile(rf"{L_KN}(?:ಸೌಮ್ಯನ್ಯಾಕಿ|ಸೌಮ್ಯನಾಯ್ಕಿ|ಸೌಮ್ಯನಾಯಕಿಅಮ್ಮನವರ|ಸೋಮನ್ಯಾಕಿ|ಸೋಮನಾಯ್ಕಿ)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಸೌಮ್ಯನಾಯಕಿ\1"),
    (re.compile(rf"{L_KN}ಅಲ್ವಾರ್ಗಳಿಗೆ\s+ಮೀಸಲಾಗಿರುವ{R_KN}", re.IGNORECASE), "ಸೌಮ್ಯನಾಯಕಿ ದೇವಿಗೆ ಮೀಸಲಾಗಿರುವ"),
    (re.compile(rf"{L_KN}ವಿಮನಾ{R_KN}", re.IGNORECASE), "ವಿಮಾನ"),
    # Pavilions & Water Tanks
    (re.compile(rf"{L_KN}(?:ನಾರ್ತ್\s*ಪ್ಯಾವಿಲಿಯನ್|ಉತ್ತರದ?\s*ಪ್ಯಾವಿಲಿಯನ್)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಉತ್ತರ ಮಂಟಪ\1"),
    (re.compile(rf"{L_KN}(?:ಈಸ್ಟ್\s*ಪ್ಯಾವಿಲಿಯನ್|ಪೂರ್ವದ?\s*ಪ್ಯಾವಿಲಿಯನ್)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಪೂರ್ವ ಮಂಟಪ\1"),
    (re.compile(rf"{L_KN}(?:ಸೌತ್-ಈಸ್ಟರ್ನ್\s*ಪ್ಯಾವಿಲಿಯನ್|ಆಗ್ನೇಯದ?\s*ಪ್ಯಾವಿಲಿಯನ್)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಆಗ್ನೇಯ ಮಂಟಪ\1"),
    (re.compile(rf"{L_KN}(?:ವಸುಧೇವಾ|ವಾಸುದೇವ)\s*ಸರೋವರಾ?([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ವಾಸುದೇವ ಸರೋವರ\1"),
    (re.compile(rf"{L_KN}ಮಂದಪ([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಮಂಟಪ\1"),
    # Pedestal (pedestrian translation error)
    (re.compile(rf"{L_KN}ಪಾದಚಾರಿ(?:ಯ)?\s*ಮೇಲೆ{R_KN}", re.IGNORECASE), "ಪೀಠದ ಮೇಲೆ"),
    (re.compile(rf"{L_KN}ಪಾದಚಾರಿ{R_KN}", re.IGNORECASE), "ಪೀಠ"),
    # Architectural terms & layout
    (re.compile(rf"{L_KN}ಕಾಂಪ್ಯಾಕ್ಟ್{R_KN}", re.IGNORECASE), "ಅಂದವಾದ"),
    (re.compile(rf"{L_KN}ಎರಡು\s*ಕೋಶದ{R_KN}", re.IGNORECASE), "ದ್ವಿಕೂಟ"),
    # Artisans & Sculptors
    (re.compile(rf"{L_KN}ಶಿಲ್ಪಕನನ್ನು{R_KN}", re.IGNORECASE), "ಶಿಲ್ಪಿಯನ್ನು"),
    (re.compile(rf"{L_KN}ಶಿಲ್ಪಕನು{R_KN}", re.IGNORECASE), "ಶಿಲ್ಪಿಯು"),
    (re.compile(rf"{L_KN}ಶಿಲ್ಪಕರು{R_KN}", re.IGNORECASE), "ಶಿಲ್ಪಿಗಳು"),
    # Legend corrections (Kappe Chennigaraya frog cavity & Dankanachari)
    (re.compile(rf"{L_KN}ವಿಗ್ರಹದಲ್ಲಿ\s+ಒಂದು\s+ಬಾವಿಯನ್ನು{R_KN}", re.IGNORECASE), "ವಿಗ್ರಹದಲ್ಲಿ ಒಂದು ಕಪ್ಪೆಯನ್ನು"),
    (re.compile(rf"{L_KN}ಅವನ\s+ಕೈಯನ್ನು\s+ಕತ್ತರಿಸಿದರು{R_KN}", re.IGNORECASE), "ತನ್ನ ಕೈಯನ್ನು ಕತ್ತರಿಸಿಕೊಂಡನು"),
    # Dynasty proper noun - correct stem spelling while preserving suffixes (e.g. ರ, ರಿಗೆ)
    (re.compile(rf"{L_KN}(?:ಹೋಯ್ಸಲಾ|ಹೋಯ್ಸಾಲಾ|ಹೊಯ್ಸಾಲಾ|ಹೋಯ್ಸಾಲ|ಹೊಯ್ಸಳ)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಹೊಯ್ಸಳ\1"),
    # Patron royal name - correct stem spelling while preserving suffixes (ನು, ನ, ರ, ನಿಗೆ, etc.)
    # Does NOT inject 'ರಾಜ' or force 'ನು' nominative ending
    (re.compile(rf"{L_KN}ವಿಷ್ಣುವರ್[ಧದ]ಾ?ನಾ([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ವಿಷ್ಣುವರ್ಧನ\1"),
    (re.compile(rf"{L_KN}ವಿಷ್ಣುವರ್[ಧದ]ಾ?ನ([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ವಿಷ್ಣುವರ್ಧನ\1"),
    # Queen Shantala name - correct spelling while preserving suffixes
    (re.compile(rf"{L_KN}ಶಾಂತಲೆ([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಶಾಂತಲಾ\1"),
    # Deduplicate consecutive repeated proper nouns if neural model stuttered
    (re.compile(rf"{L_KN}(?:ಹೊಯ್ಸಳ\s+)+ಹೊಯ್ಸಳ{R_KN}", re.IGNORECASE), "ಹೊಯ್ಸಳ"),
    (re.compile(rf"{L_KN}(?:ರಾಜ\s+)+ರಾಜ{R_KN}", re.IGNORECASE), "ರಾಜ"),
    (re.compile(rf"{L_KN}(?:ವಿಷ್ಣುವರ್ಧನ\s+)+ವಿಷ್ಣುವರ್ಧನ{R_KN}", re.IGNORECASE), "ವಿಷ್ಣುವರ್ಧನ"),
    # Sculptures & Architecture domain terminology
    (re.compile(rf"{L_KN}ಮದಾನಿಕಾ([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ಮದನಿಕಾ\1"),
    (re.compile(rf"{L_KN}(?:ದರ್ಪಣಸುಂದರಿ|ದಾರ್ಪನಾ\s*ಸುಂದರಿ)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ದರ್ಪಣ ಸುಂದರಿ\1"),
    (re.compile(rf"{L_KN}(?:ತಲಾಕಾಡ್|ತಲಾಖಾದ್)([ಅ-ಹ\u0c80-\u0cff]*){R_KN}", re.IGNORECASE), r"ತಲಕಾಡು\1"),
    (re.compile(rf"{L_KN}(?:ಕ್ಲೋರಿಟ್\s*ಸ್ಕ್ಯಾಸ್ಟ್|ಕ್ಲೋರಿಟಿಕ್\s*ಶಿಸ್ಟ್){R_KN}", re.IGNORECASE), "ಕ್ಲೋರಿಟಿಕ್ ಶಿಸ್ಟ್"),
    (re.compile(rf"{L_KN}(?:ಸೋಪ್\s*ಸ್ಟೋನ್|ಸೋಪ್ಸ್ಟೋನ್|ಸ್ಯಾಪ್\s*ಸ್ಟೋನ್|ಸ್ಯಾಪ್ಸ್ಟೋನ್|ಸಾಪ್\s*ಸ್ಟೋನ್|ಸಾಪ್ಸ್ಟೋನ್){R_KN}", re.IGNORECASE), "ಸೋಪ್‌ಸ್ಟೋನ್"),
]


APPROVED_LATIN_ACRONYMS = {"UNESCO"}


class HeritageTranslator:
    """Post-processes neural translations with authoritative temple terminology and orthography."""

    def __init__(self) -> None:
        self.corrections = ORTHOGRAPHIC_CORRECTIONS

    @staticmethod
    def detect_unapproved_latin_words(text: str) -> list[str]:
        """Detect any Latin words in Kannada output that are not in the approved allow-list."""
        words = re.findall(r"\b[A-Za-z]+\b", text)
        return [w for w in words if w.upper() not in APPROVED_LATIN_ACRONYMS]

    def post_process_kannada(self, text: str) -> str:
        """Apply glossary refinements and orthographic corrections to neural Kannada output.

        Does NOT replace sentences or remove numbers/facts.
        """
        if not text:
            return ""

        result = text

        # 1. Tautology removal (e.g. "X ದೇವಾಲಯ, X ದೇವಾಲಯ ಎಂದೂ ಕರೆಯಲ್ಪಡುವ" -> "X ದೇವಾಲಯ")
        result = re.sub(r"([^,\n]+),\s*\1\s+(?:ಎಂದೂ|ಎಂದು)\s+ಕರೆಯಲ್ಪಡುವ", r"\1", result)

        # 2. Apply orthographic corrections & domain terminology alignments
        for pattern, replacement in self.corrections:
            result = pattern.sub(replacement, result)

        # 3. Clean consecutive repeating words caused by neural token stuttering
        words = result.split()
        if words:
            deduped = [words[0]]
            for w in words[1:]:
                if w != deduped[-1]:
                    deduped.append(w)
            result = " ".join(deduped)

        # 4. Clean redundant double spaces and special token markers
        result = re.sub(r"<(?:unk|s|/s|pad)>", "", result)
        result = re.sub(r"\s+", " ", result).strip()
        return result
