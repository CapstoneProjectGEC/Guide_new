"""Application service managing translation operations, glossary filters, and database registry synchronization."""

import re
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.application.chat.grounding_guard import (
    CANONICAL_FALLBACK_EN,
    CANONICAL_FALLBACK_KN,
)
from backend.src.application.translation.heritage_glossary import HeritageGlossary
from backend.src.application.translation.heritage_translator import HeritageTranslator
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.core.logging import get_logger
from backend.src.infrastructure.models.system import TranslationRegistry
from backend.src.infrastructure.translation.argos_engine import ArgosTranslationEngine, get_argos_engine
from backend.src.infrastructure.translation.nllb_engine import NllbTranslationEngine, get_nllb_engine

logger = get_logger("application.translation.translator")


class TranslationService:
    """Coordinates offline translation, proper-noun glossary preservation, and registry persistence."""

    def __init__(
        self,
        nllb_engine: NllbTranslationEngine | None = None,
        argos_engine: ArgosTranslationEngine | None = None,
        glossary: HeritageGlossary | None = None,
        normalizer: QueryNormalizer | None = None,
        heritage_translator: HeritageTranslator | None = None,
    ) -> None:
        self.nllb_engine = nllb_engine or get_nllb_engine()
        self.argos_engine = argos_engine or get_argos_engine()
        self.glossary = glossary or HeritageGlossary()
        self.normalizer = normalizer or QueryNormalizer(argos_engine=self.argos_engine, glossary=self.glossary)
        self.heritage_translator = heritage_translator or HeritageTranslator()
        self._trans_cache: dict[tuple[str, str, str], str] = {}

    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_heritage: bool = True,
    ) -> str:
        """Translate text between languages using offline neural machine translation and domain glossary."""
        clean_text = text.strip()
        if not clean_text or source_language == target_language:
            return text

        cache_key = (clean_text, source_language, target_language)
        if cache_key in self._trans_cache:
            return self._trans_cache[cache_key]

        # 1. Canonical fallback preservation
        if clean_text == CANONICAL_FALLBACK_EN and target_language == "kn":
            return CANONICAL_FALLBACK_KN
        if clean_text == CANONICAL_FALLBACK_KN and target_language == "en":
            return CANONICAL_FALLBACK_EN

        # 2. Offline Neural Translation with NLLB-200 (CTranslate2 INT8)
        if self.nllb_engine.is_available():
            if source_language == "kn" and target_language == "en" and preserve_heritage:
                masked_text, masks = self.glossary.mask_heritage_terms(clean_text)
                if masks:
                    raw_translated = self.nllb_engine.translate(masked_text, source_language, target_language)
                    unmasked = self.glossary.unmask_heritage_terms(raw_translated, masks)
                    en_fixed = re.sub(r"\bBeirut\b", "Belur", unmasked, flags=re.IGNORECASE)
                    en_fixed = re.sub(r"\bChennaikeshava\b", "Chennakeshava", en_fixed, flags=re.IGNORECASE)
                    res = en_fixed
                else:
                    raw_translated = self.nllb_engine.translate(clean_text, source_language, target_language)
                    en_fixed = re.sub(r"\bBeirut\b", "Belur", raw_translated, flags=re.IGNORECASE)
                    en_fixed = re.sub(r"\bChennaikeshava\b", "Chennakeshava", en_fixed, flags=re.IGNORECASE)
                    res = en_fixed
                # Reject out-of-domain biblical hallucinations
                if any(bad in res.lower() for bad in ["jehovah", "church", "bible", "mosque"]):
                    norm = self.normalizer.normalize_for_retrieval(clean_text, source_lang="kn", target_lang="en")
                    res = norm.retrieval_query
            elif target_language == "kn":
                raw_translated = self.nllb_engine.translate(clean_text, source_language, target_language)
                res = self.heritage_translator.post_process_kannada(raw_translated)
            elif target_language == "en":
                raw_translated = self.nllb_engine.translate(clean_text, source_language, target_language)
                en_fixed = re.sub(r"\bBeirut\b", "Belur", raw_translated, flags=re.IGNORECASE)
                en_fixed = re.sub(r"\bChennaikeshava\b", "Chennakeshava", en_fixed, flags=re.IGNORECASE)
                res = en_fixed
            else:
                raw_translated = self.nllb_engine.translate(clean_text, source_language, target_language)
                res = raw_translated

            if len(self._trans_cache) >= 1024:
                self._trans_cache.pop(next(iter(self._trans_cache)))
            self._trans_cache[cache_key] = res
            return res

        # 3. Argos Translate fallback
        translated = self.argos_engine.translate(text, source_language, target_language)
        if translated is not None:
            return translated

        # 4. Graceful fallback: return normalized/passthrough text
        logger.info(
            "translation_model_unavailable_fallback",
            source_language=source_language,
            target_language=target_language,
        )
        if source_language == "kn" and target_language == "en":
            norm = self.normalizer.normalize_for_retrieval(text, source_lang=source_language, target_lang=target_language)
            return norm.retrieval_query

        return text

    async def sync_translation_registry(self, session: AsyncSession) -> list[TranslationRegistry]:
        """Synchronize installed offline translation packages into the relational translation_registry table."""
        packages = self.argos_engine.get_installed_packages()

        # Fetch existing rows in translation_registry
        stmt = select(TranslationRegistry)
        result = await session.execute(stmt)
        existing_rows = { (r.source_language, r.target_language): r for r in result.scalars().all() }

        synced_records: list[TranslationRegistry] = []

        for pkg in packages:
            key = (pkg.source_language, pkg.target_language)
            if key in existing_rows:
                record = existing_rows[key]
                record.is_installed = pkg.is_installed
                record.package_name = pkg.package_name
                session.add(record)
                synced_records.append(record)
            else:
                new_record = TranslationRegistry(
                    source_language=pkg.source_language,
                    target_language=pkg.target_language,
                    package_name=pkg.package_name,
                    is_installed=pkg.is_installed,
                )
                session.add(new_record)
                synced_records.append(new_record)

        await session.flush()
        logger.info("translation_registry_synchronized", count=len(synced_records))
        return synced_records

    def get_status(self) -> dict[str, Any]:
        """Return runtime status of translation models and installed packages."""
        packages = self.argos_engine.get_installed_packages()
        return {
            "engine": "argos",
            "installed_packages_count": len(packages),
            "packages": [p.model_dump() for p in packages],
            "kn_en_available": self.argos_engine.is_language_pair_available("kn", "en"),
            "en_kn_available": self.argos_engine.is_language_pair_available("en", "kn"),
        }
