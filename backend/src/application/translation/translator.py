"""Application service managing translation operations, glossary filters, and database registry synchronization."""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.application.translation.heritage_glossary import HeritageGlossary
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.core.logging import get_logger
from backend.src.infrastructure.models.system import TranslationRegistry
from backend.src.infrastructure.translation.argos_engine import ArgosTranslationEngine, get_argos_engine

logger = get_logger("application.translation.translator")


class TranslationService:
    """Coordinates offline translation, proper-noun glossary preservation, and registry persistence."""

    def __init__(
        self,
        argos_engine: ArgosTranslationEngine | None = None,
        glossary: HeritageGlossary | None = None,
        normalizer: QueryNormalizer | None = None,
    ) -> None:
        self.argos_engine = argos_engine or get_argos_engine()
        self.glossary = glossary or HeritageGlossary()
        self.normalizer = normalizer or QueryNormalizer(argos_engine=self.argos_engine, glossary=self.glossary)

    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preserve_heritage: bool = True,
    ) -> str:
        """Translate text between languages with optional heritage entity preservation."""
        if not text.strip() or source_language == target_language:
            return text

        # 1. If heritage preservation is requested, mask domain proper nouns
        masks: dict[str, str] = {}
        processed_input = text
        if preserve_heritage:
            processed_input, masks = self.glossary.mask_heritage_terms(text)

        # 2. Attempt neural translation
        translated = self.argos_engine.translate(processed_input, source_language, target_language)

        if translated is not None:
            # Unmask preserved proper nouns
            if preserve_heritage and masks:
                translated = self.glossary.unmask_heritage_terms(translated, masks)
            return translated

        # 3. Graceful fallback: if neural model is unavailable, return normalized/passthrough text
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
