"""Fact-preservation validator ensuring translation integrity of years, numbers, and named entities."""

import re
from backend.src.core.logging import get_logger

logger = get_logger("application.translation.fact_validator")

# Canonical Kannada transliterations and accepted variants for key heritage entities
ENTITY_KANNADA_VARIANTS: dict[str, list[str]] = {
    "Vishnuvardhana": ["ವಿಷ್ಣುವರ್ಧನ", "ವಿಷ್ಣುವರ್ದಾನಾ", "ವಿಷ್ಣುವರ್ದನ", "ವಿಷ್ಣುವರ್ಧನನು"],
    "Hoysala": ["ಹೊಯ್ಸಳ", "ಹೋಯ್ಸಲಾ", "ಹೊಯ್ಸಳರು", "ಹೋಯ್ಸಾಲಾ"],
    "Chennakeshava": ["ಚೆನ್ನಕೇಶವ", "ಚೆನ್ನಕೇಶ್ವ", "ಚೆನ್ನಕೇಶವಸ್ವಾಮಿ", "ವಿಜಯನಾರಾಯಣ"],
    "Belur": ["ಬೇಲೂರು", "ಬೇಲೂರಿನ", "ಬೆಲುರ್", "ಬೆಲುರಿನಲ್ಲಿ", "ಬೇಲೂರಿನಲ್ಲಿ"],
    "Shantala Devi": ["ಶಾಂತಲಾ ದೇವಿ", "ಶಾಂತಲಾ", "ಶಾಂತಲೆ"],
    "Darpana Sundari": ["ದರ್ಪಣ ಸುಂದರಿ", "ದರ್ಪಣಸುಂದರಿ"],
    "Garbhagriha": ["ಗರ್ಭಗೃಹ", "ಗರ್ಭಗುಡಿ", "ಪವಿತ್ರಸ್ಥಾನ"],
    "Talakad": ["ತಲಕಾಡು", "ತಲಾಕಾಡ್"],
    "Mallitamma": ["ಮಲ್ಲಿತಮ್ಮ"],
    "Dasoja": ["ದಾಸೋಜ"],
    "UNESCO": ["ಯುನೆಸ್ಕೋ", "UNESCO"],
    "Kappe Chennigaraya": ["ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ", "ಕಪ್ಪೆ-ಚೆನ್ನಿಗರಾಯ", "ಚೆನ್ನಿಗರಾಯ"],
}


class FactPreservationValidator:
    """Verifies that all factual years, counts, and proper entities from English text are retained in Kannada."""

    @staticmethod
    def extract_facts(text: str) -> dict[str, list[str]]:
        """Extract verifiable factual tokens from English text."""
        # 1. Historical years (e.g. 1117, 2023)
        years = re.findall(r"\b(1\d{3}|20\d{2})\b", text)

        # 2. Key counts and numerical statistics
        # Exclude numbers already captured as years
        all_numbers = re.findall(r"\b\d+\b", text)
        counts = [n for n in all_numbers if n not in years]

        # 3. Known domain entities
        entities: list[str] = []
        for ent in ENTITY_KANNADA_VARIANTS:
            if re.search(r"\b" + re.escape(ent) + r"\b", text, re.IGNORECASE):
                entities.append(ent)

        return {
            "years": list(dict.fromkeys(years)),
            "counts": list(dict.fromkeys(counts)),
            "entities": list(dict.fromkeys(entities)),
        }

    @staticmethod
    def validate(english_text: str, kannada_text: str) -> tuple[bool, list[str]]:
        """Validate factual completeness.

        Returns:
            tuple[bool, list[str]]: (is_valid, list_of_missing_facts)
        """
        facts = FactPreservationValidator.extract_facts(english_text)
        missing: list[str] = []

        # 0. Reject unk token artifacts
        if "<unk>" in kannada_text:
            missing.append("UnkToken <unk>")

        # 1. Validate Years
        for year in facts["years"]:
            kn_digits = "".join("೦೧೨೩೪೫೬೭೮೯"[int(d)] for d in year)
            if year not in kannada_text and kn_digits not in kannada_text:
                missing.append(f"Year {year}")

        # 2. Validate Numerical Counts
        for num in facts["counts"]:
            kn_digits = "".join("೦೧೨೩೪೫೬೭೮೯"[int(d)] for d in num)
            if num not in kannada_text and kn_digits not in kannada_text:
                missing.append(f"Number {num}")

        # 3. Validate Named Entities
        for ent in facts["entities"]:
            variants = ENTITY_KANNADA_VARIANTS.get(ent, [])
            if not any(v in kannada_text for v in variants):
                missing.append(f"Entity {ent}")

        is_valid = len(missing) == 0
        if not is_valid:
            logger.warning(
                "fact_preservation_validation_failed",
                missing=missing,
                english_sample=english_text[:80],
                kannada_sample=kannada_text[:80],
            )
        else:
            logger.info("fact_preservation_validation_passed", facts_verified=facts)

        return is_valid, missing

