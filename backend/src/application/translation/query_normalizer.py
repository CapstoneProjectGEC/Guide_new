"""Cross-lingual query normalization service uniting neural translation, domain glossaries, and intent expansion."""

import re
from backend.src.application.chat.language_detector import LanguageDetector
from backend.src.application.translation.heritage_glossary import HeritageGlossary
from backend.src.application.translation.transliteration import transliterate_kannada_to_latin
from backend.src.core.logging import get_logger
from backend.src.domain.translation import NormalizedQuery, TranslationStrategy
from backend.src.infrastructure.translation.argos_engine import ArgosTranslationEngine, get_argos_engine

logger = get_logger("application.translation.query_normalizer")

# Common Kannada lexical terms translated to English domain equivalents for RAG retrieval
COMMON_KANNADA_TERMS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(ದೇವಾಲಯ|ಗುಡಿ|ಕೋವಿಲ್|ಮಂದಿರ)", re.IGNORECASE), "temple"),
    (re.compile(r"(ಅರಮನೆ|ಕೋಟೆ)", re.IGNORECASE), "palace fort"),
    (re.compile(r"(ರಾಜ|ಮಹಾರಾಜ|ದೊರೆ)", re.IGNORECASE), "king ruler"),
    (re.compile(r"(ರಾಣಿ|ಮಹಾರಾಣಿ)", re.IGNORECASE), "queen"),
    (re.compile(r"(ಶಿಲ್ಪಿ|ಶಿಲ್ಪಿಗಳು|ರೂವಾರಿ)", re.IGNORECASE), "sculptor architect"),
    (re.compile(r"(ಕೆತ್ತನೆ|ಕೆತ್ತನೆಗಳು)", re.IGNORECASE), "carvings sculptures"),
    (re.compile(r"(ಕಂಬ|ಕಂಬಗಳು|ಸ್ತಂಭ)", re.IGNORECASE), "pillar column"),
    (re.compile(r"(ಬಗ್ಗೆ|ಕುರಿತು)", re.IGNORECASE), "about details"),
    (re.compile(r"(ತಿಳಿಸಿ|ಹೇಳಿ|ವಿವರಿಸಿ)", re.IGNORECASE), "explain describe information"),
    (re.compile(r"(ವಿಗ್ರಹ|ಮೂರ್ತಿ)", re.IGNORECASE), "idol deity statue"),
    (re.compile(r"(ವರ್ಷ|ಶತಮಾನ)", re.IGNORECASE), "year century"),
    (re.compile(r"(ಸ್ಥಳ|ಜಿಲ್ಲೆ)", re.IGNORECASE), "place location district"),
]

KANNADA_UNICODE_PATTERN = re.compile(r"[\u0c80-\u0cff]")


class QueryNormalizer:
    """Normalizes multilingual tourist queries for dense and sparse retrieval while preserving original context."""

    def __init__(
        self,
        argos_engine: ArgosTranslationEngine | None = None,
        glossary: HeritageGlossary | None = None,
        language_detector: LanguageDetector | None = None,
    ) -> None:
        self.argos_engine = argos_engine or get_argos_engine()
        self.glossary = glossary or HeritageGlossary()
        self.language_detector = language_detector or LanguageDetector()

    def normalize_for_retrieval(
        self,
        query: str,
        source_lang: str | None = None,
        target_lang: str = "en",
    ) -> NormalizedQuery:
        """Translate or expand a non-English query into an optimal English retrieval query."""
        clean_query = query.strip()
        if not clean_query:
            return NormalizedQuery(
                original_query=query,
                retrieval_query="",
                detected_language="en",
                preserved_terms=[],
                translation_applied=False,
                strategy_used=TranslationStrategy.PASSTHROUGH,
            )

        # 1. Detect language if not explicitly provided
        has_kannada_script = bool(KANNADA_UNICODE_PATTERN.search(clean_query))
        det_lang = source_lang or ("kn" if has_kannada_script else "en")

        # 2. English passthrough optimization: if purely English, return immediately with zero overhead
        if not has_kannada_script and det_lang == "en":
            return NormalizedQuery(
                original_query=query,
                retrieval_query=clean_query,
                detected_language="en",
                preserved_terms=[],
                translation_applied=False,
                strategy_used=TranslationStrategy.PASSTHROUGH,
            )

        # 3. Identify and preserve heritage entities (e.g. Belur, Vishnuvardhana, Madanika)
        matched_heritage = self.glossary.extract_heritage_terms(clean_query)
        preserved_terms = [eng for _, eng in matched_heritage]

        # 4. Attempt neural translation via Argos Translate if installed and available
        if self.argos_engine.is_language_pair_available(det_lang, target_lang):
            masked_text, masks = self.glossary.mask_heritage_terms(clean_query)
            translated = self.argos_engine.translate(masked_text, det_lang, target_lang)
            if translated:
                unmasked = self.glossary.unmask_heritage_terms(translated, masks)
                logger.info(
                    "query_normalized_argos_neural",
                    original=clean_query,
                    retrieval_query=unmasked,
                    preserved=preserved_terms,
                )
                return NormalizedQuery(
                    original_query=query,
                    retrieval_query=unmasked.strip(),
                    detected_language=det_lang,
                    preserved_terms=preserved_terms,
                    translation_applied=True,
                    strategy_used=TranslationStrategy.ARGOS_NEURAL,
                )

        # 5. Deterministic Domain Translation & Intent Expansion Strategy
        # Used when neural model package is unavailable offline or fails
        query_working = clean_query

        # A. Replace matched heritage terms with canonical English representations
        for kn_term, en_term in matched_heritage:
            query_working = query_working.replace(kn_term, f" {en_term} ")

        # B. Match question intent patterns (who built, when, where, architecture, ticket, etc.)
        intents = self.glossary.get_intent_expansion(clean_query)

        # C. Translate common architectural and inquiry terms
        for pat, replacement in COMMON_KANNADA_TERMS:
            query_working = pat.sub(f" {replacement} ", query_working)

        # D. Clean extra spaces and assemble retrieval query
        transliterated = transliterate_kannada_to_latin(clean_query)
        retrieval_tokens: list[str] = []

        # Process words from query_working
        raw_words = [w for w in re.split(r"\s+", query_working) if w]
        for w in raw_words:
            if KANNADA_UNICODE_PATTERN.search(w):
                # Unmapped Kannada words are transliterated phonetically to Latin
                # This ensures out-of-domain entities (e.g. Mysore, palace) retain lexical presence
                latin_w = transliterate_kannada_to_latin(w)
                clean_latin = re.sub(r"[^\w]", "", latin_w).strip()
                if clean_latin and clean_latin.lower() not in [t.lower() for t in retrieval_tokens]:
                    retrieval_tokens.append(clean_latin)
            else:
                clean_eng = re.sub(r"[^\w\-]", "", w).strip()
                if clean_eng and clean_eng.lower() not in [t.lower() for t in retrieval_tokens]:
                    retrieval_tokens.append(clean_eng)

        # Add intent expansions (e.g. 'who built commissioned constructed', 'history historical background')
        if intents:
            for it in intents:
                for token in it.split():
                    if token.lower() not in [t.lower() for t in retrieval_tokens]:
                        retrieval_tokens.append(token)

        if not retrieval_tokens:
            retrieval_tokens.append(transliterated)

        retrieval_query = " ".join(retrieval_tokens).strip()

        logger.info(
            "query_normalized_domain_expansion",
            original=clean_query,
            retrieval_query=retrieval_query,
            preserved=preserved_terms,
        )

        return NormalizedQuery(
            original_query=query,
            retrieval_query=retrieval_query,
            detected_language=det_lang,
            preserved_terms=preserved_terms,
            translation_applied=True,
            strategy_used=TranslationStrategy.DOMAIN_GLOSSARY_EXPANSION,
            transliterated_query=transliterated,
        )
