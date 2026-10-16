"""Domain terminology glossary and proper-noun preservation filter for Belur Chennakeshava Temple."""

import re
from backend.src.domain.translation import HeritageTermMapping

# Canonical mapping of Kannada heritage terms to English authoritative terminology
HERITAGE_GLOSSARY: list[HeritageTermMapping] = [
    # Royalty & Patrons
    HeritageTermMapping(
        kannada_term="ವಿಷ್ಣುವರ್ಧನ",
        english_term="King Vishnuvardhana",
        category="patron",
        synonyms=["ವಿಷ್ಣುವರ್ಧನ ಮಹಾರಾಜ", "ಬಿಟ್ಟಿದೇವ", "ಹೊಯ್ಸಳ ವಿಷ್ಣುವರ್ಧನ"],
    ),
    HeritageTermMapping(
        kannada_term="ಶಾಂತಲಾ ದೇವಿ",
        english_term="Queen Shantala Devi",
        category="patron",
        synonyms=["ಶಾಂತಲೆ", "ಶಾಂತಲಾ", "ರಾಣಿ ಶಾಂತಲಾ"],
    ),
    HeritageTermMapping(
        kannada_term="ಹೊಯ್ಸಳ",
        english_term="Hoysala",
        category="dynasty",
        synonyms=["ಹೊಯ್ಸಳರು", "ಹೊಯ್ಸಳ ಸಾಮ್ರಾಜ್ಯ", "ಹೊಯ್ಸಳ ರಾಜವಂಶ"],
    ),
    # Temples & Complexes
    HeritageTermMapping(
        kannada_term="ಬೇಲೂರು",
        english_term="Belur",
        category="location",
        synonyms=["ಬೇಲೂರಿನ", "ಬೇಲೂರು ದೇವಾಲಯ"],
    ),
    HeritageTermMapping(
        kannada_term="ಚೆನ್ನಕೇಶವ",
        english_term="Chennakeshava",
        category="temple",
        synonyms=["ಚೆನ್ನಕೇಶವ ದೇವಾಲಯ", "ಚೆನ್ನಕೇಶವಸ್ವಾಮಿ", "ವಿಜಯನಾರಾಯಣ", "ವಿಜಯ ನಾರಾಯಣ"],
    ),
    HeritageTermMapping(
        kannada_term="ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ",
        english_term="Kappe Chennigaraya",
        category="temple",
        synonyms=["ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ದೇವಾಲಯ", "ಚೆನ್ನಿಗರಾಯ"],
    ),
    HeritageTermMapping(
        kannada_term="ಸೌಮ್ಯನಾಯಕಿ",
        english_term="Soumyanayaki",
        category="temple",
        synonyms=["ಸೌಮ್ಯನಾಯಕಿ ಅಮ್ಮನವರ ದೇವಾಲಯ"],
    ),
    HeritageTermMapping(
        kannada_term="ರಂಗನಾಯಕಿ",
        english_term="Ranganayaki",
        category="temple",
        synonyms=["ರಂಗನಾಯಕಿ ದೇವಾಲಯ"],
    ),
    HeritageTermMapping(
        kannada_term="ಪುಷ್ಕರಣಿ",
        english_term="Pushkarani",
        category="architecture",
        synonyms=["ಕಲ್ಯಾಣಿ", "ಹೊಂಡ", "ವಾಪೀ"],
    ),
    HeritageTermMapping(
        kannada_term="ಯಾಗಶಾಲೆ",
        english_term="Yagashala",
        category="architecture",
        synonyms=[],
    ),
    # Sculptures & Art
    HeritageTermMapping(
        kannada_term="ಮದನಿಕಾ",
        english_term="Madanika",
        category="sculpture",
        synonyms=["ಮದನಿಕೆ", "ಮದನಿಕೆಯರು", "ಶಿಲಾಬಾಲಿಕೆ", "ಶಿಲಾಬಾಲಿಕೆಯರು"],
    ),
    HeritageTermMapping(
        kannada_term="ದರ್ಪಣ ಸುಂದರಿ",
        english_term="Darpana Sundari",
        category="sculpture",
        synonyms=["ಕನ್ನಡಿ ಸುಂದರಿ"],
    ),
    HeritageTermMapping(
        kannada_term="ನಾಟ್ಯ ಮೋಹಿನಿ",
        english_term="Natya Mohini",
        category="sculpture",
        synonyms=[],
    ),
    HeritageTermMapping(
        kannada_term="ಶುಕ ಭಾಷಿಣಿ",
        english_term="Shuka Bhashini",
        category="sculpture",
        synonyms=[],
    ),
    HeritageTermMapping(
        kannada_term="ತ್ರಿಭಂಗಿ",
        english_term="Tribhanga",
        category="sculpture",
        synonyms=["ತ್ರಿಭಂಗಿ ಭಂಗಿ"],
    ),
    # Architects & Sculptors
    HeritageTermMapping(
        kannada_term="ಜಕಣಾಚಾರಿ",
        english_term="Jakanachari",
        category="architect",
        synonyms=["ಅಮರಶಿಲ್ಪಿ ಜಕಣಾಚಾರಿ", "ಜಕಣಾಚಾರ್ಯ"],
    ),
    HeritageTermMapping(
        kannada_term="ದಾಸೋಜ",
        english_term="Dasoja",
        category="architect",
        synonyms=["ರೂವಾರಿ ದಾಸೋಜ"],
    ),
    HeritageTermMapping(
        kannada_term="ಚಾವಣ",
        english_term="Chavana",
        category="architect",
        synonyms=[],
    ),
    HeritageTermMapping(
        kannada_term="ಮಲ್ಲಿತಮ್ಮ",
        english_term="Mallitamma",
        category="architect",
        synonyms=[],
    ),
    # Architecture Structures
    HeritageTermMapping(
        kannada_term="ಗರ್ಭಗೃಹ",
        english_term="Garbhagriha",
        category="architecture",
        synonyms=["ಗರ್ಭಗುಡಿ", "ಮೂಲಸ್ಥಾನ"],
    ),
    HeritageTermMapping(
        kannada_term="ನವರಂಗ",
        english_term="Navaranga",
        category="architecture",
        synonyms=["ಮಧ್ಯ ರಂಗ"],
    ),
    HeritageTermMapping(
        kannada_term="ಮಂಟಪ",
        english_term="Mandapa",
        category="architecture",
        synonyms=["ಮುಖಮಂಟಪ", "ಸಭಾಮಂಟಪ"],
    ),
    HeritageTermMapping(
        kannada_term="ದ್ವಾರಪಾಲಕ",
        english_term="Dwarapalaka",
        category="architecture",
        synonyms=["ದ್ವಾರಪಾಲಕರು"],
    ),
    HeritageTermMapping(
        kannada_term="ಗರುಡ ಗಂಭ",
        english_term="Garuda Stambha",
        category="architecture",
        synonyms=["ಗರುಡ ಕಂಬ", "ದೀಪಸ್ತಂಭ"],
    ),
    HeritageTermMapping(
        kannada_term="ಜಗತಿ",
        english_term="Jagati",
        category="architecture",
        synonyms=["ನಕ್ಷತ್ರಾಕಾರದ ಜಗತಿ"],
    ),
    HeritageTermMapping(
        kannada_term="ಸೋಪ್ ಸ್ಟೋನ್",
        english_term="Soapstone",
        category="material",
        synonyms=["ಸೋಪುಗಲ್ಲು", "ಬಳಪದ ಕಲ್ಲು"],
    ),
    # Geography & Related Sites
    HeritageTermMapping(
        kannada_term="ಹಾಸನ",
        english_term="Hassan",
        category="location",
        synonyms=["ಹಾಸನ ಜಿಲ್ಲೆ"],
    ),
    HeritageTermMapping(
        kannada_term="ಯಾಗಚಿ",
        english_term="Yagachi River",
        category="location",
        synonyms=["ಯಾಗಚಿ ನದಿ"],
    ),
    HeritageTermMapping(
        kannada_term="ಹಳೇಬೀಡು",
        english_term="Halebidu",
        category="location",
        synonyms=["ದ್ವಾರಸಮುದ್ರ"],
    ),
    HeritageTermMapping(
        kannada_term="ಸೋಮನಾಥಪುರ",
        english_term="Somanathapura",
        category="location",
        synonyms=[],
    ),
]

# Query intent keywords mapped from Kannada to English retrieval equivalents
INTENT_TERMS_MAP: list[tuple[re.Pattern, str]] = [
    # Construction / Patronage inquiries
    (re.compile(r"(ಯಾರು\s*ಕಟ್ಟಿಸಿದರು|ಯಾರು\s*ನಿರ್ಮಿಸಿದರು|ಕಟ್ಟಿಸಿದವರು\s*ಯಾರು|ನಿರ್ಮಿಸಿದವರು\s*ಯಾರು|ಯಾರು\s*ಕಟ್ಟಿಸಿದ್ದು|ಕಟ್ಟಿಸಿದ\s*ರಾಜ\s*ಯಾರು)", re.IGNORECASE), "who built commissioned constructed"),
    (re.compile(r"(ಯಾವಾಗ\s*ಕಟ್ಟಲಾಯಿತು|ಯಾವಾಗ\s*ನಿರ್ಮಿಸಲಾಯಿತು|ಕಟ್ಟಿದ\s*ವರ್ಷ|ಯಾವ\s*ವರ್ಷ|ಯಾವ\s*ಶತಮಾನ)", re.IGNORECASE), "when was it built construction year century"),
    # Location inquiries
    (re.compile(r"(ಎಲ್ಲಿದೆ|ಯಾವ\s*ಸ್ಥಳ|ಎಲ್ಲಿ\s*ಇದೆ|ಸ್ಥಳ\s*ಯಾವುದು|ಹೇಗೆ\s*ತಲುಪುವುದು)", re.IGNORECASE), "where is located location directions route"),
    # Architectural inquiries
    (re.compile(r"(ವಾಸ್ತುಶಿಲ್ಪ|ವಾಸ್ತುಕಲೆ|ವಾಸ್ತು\s*ಶೈಲಿ|ಶೈಲಿ)", re.IGNORECASE), "architecture architectural style"),
    # Sculpture inquiries
    (re.compile(r"(ಶಿಲ್ಪಗಳು|ಶಿಲ್ಪಕಲೆ|ಕೆತ್ತನೆಗಳು|ವಿಗ್ರಹಗಳು|ವಿಗ್ರಹ|ಕೆತ್ತನೆ)", re.IGNORECASE), "sculptures carvings statues relief work bracket figures"),
    # Practical tourist inquiries
    (re.compile(r"(ಪ್ರವೇಶ\s*ಶುಲ್ಕ|ಟಿಕೆಟ್|ದರ್ಶನ\s*ಶುಲ್ಕ|ಟಿಕೆಟ್\s*ದರ)", re.IGNORECASE), "entry fee ticket price admission"),
    (re.compile(r"(ಸಮಯ|ತೆರೆಯುವ\s*ಸಮಯ|ದರ್ಶನ\s*ಸಮಯ|ಯಾವಾಗ\s*ತೆರೆಯುತ್ತದೆ)", re.IGNORECASE), "temple timings opening hours visiting time"),
    # Historical / Significance inquiries
    (re.compile(r"(ಇತಿಹಾಸ|ಹಿನ್ನೆಲೆ|ಪುರಾಣ|ಕಥೆ)", re.IGNORECASE), "history historical background"),
    (re.compile(r"(ಮಹತ್ವ|ವಿಶೇಷತೆ|ವೈಶಿಷ್ಟ್ಯ|ಪ್ರಸಿದ್ಧಿ)", re.IGNORECASE), "significance unique features importance"),
]


class HeritageGlossary:
    """Manages terminology dictionary, proper-noun masking, and cross-lingual term lookup."""

    def __init__(self) -> None:
        self._kn_to_en: dict[str, str] = {}
        self._en_to_kn: dict[str, str] = {}
        self._sorted_kn_terms: list[str] = []
        self._build_indexes()

    def _build_indexes(self) -> None:
        for item in HERITAGE_GLOSSARY:
            # Primary term
            self._kn_to_en[item.kannada_term] = item.english_term
            self._en_to_kn[item.english_term.lower()] = item.kannada_term

            # Synonyms
            for syn in item.synonyms:
                self._kn_to_en[syn] = item.english_term

        # Sort keys descending by length so longer multi-word terms match before substrings
        self._sorted_kn_terms = sorted(self._kn_to_en.keys(), key=len, reverse=True)

    def extract_heritage_terms(self, text: str) -> list[tuple[str, str]]:
        """Identify heritage terms present in text and return [(kannada_term, english_term)]."""
        matched: list[tuple[str, str]] = []
        for term in self._sorted_kn_terms:
            if term in text:
                matched.append((term, self._kn_to_en[term]))
        return matched

    def mask_heritage_terms(self, text: str) -> tuple[str, dict[str, str]]:
        """Mask heritage entities with placeholder tokens to protect proper nouns during translation."""
        masks: dict[str, str] = {}
        masked_text = text
        counter = 0

        for term in self._sorted_kn_terms:
            if term in masked_text:
                placeholder = f"__HERITAGE_TERM_{counter}__"
                english_val = self._kn_to_en[term]
                masks[placeholder] = english_val
                # Replace exact occurrences
                masked_text = masked_text.replace(term, placeholder)
                counter += 1

        return masked_text, masks

    def unmask_heritage_terms(self, text: str, masks: dict[str, str]) -> str:
        """Replace placeholder tokens with authoritative English heritage terms."""
        result = text
        for placeholder, canonical_term in masks.items():
            result = result.replace(placeholder, canonical_term)
        return result

    def get_intent_expansion(self, text: str) -> list[str]:
        """Match question intent patterns and return English query expansion tokens."""
        expansions: list[str] = []
        for pattern, replacement in INTENT_TERMS_MAP:
            if pattern.search(text):
                expansions.append(replacement)
        return expansions
