"""Argos Translate runtime adapter with package registry management and graceful fallback."""

import os
from pathlib import Path
import threading
from typing import Any
from backend.src.core.config import get_settings
from backend.src.core.logging import get_logger
from backend.src.domain.translation import TranslationPackageInfo

logger = get_logger("infrastructure.translation.argos_engine")


class ArgosTranslationEngine:
    """Offline neural machine translation engine wrapping Argos Translate with package discovery."""

    def __init__(self, models_dir: str | Path | None = None) -> None:
        self.settings = get_settings()
        self.models_dir = Path(models_dir or "data/models/argos")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._installed_pairs: set[tuple[str, str]] = set()
        self._is_initialized = False

        self._initialize_runtime()

    def _initialize_runtime(self) -> None:
        """Discover installed Argos models from default directories and custom models directory."""
        with self._lock:
            if self._is_initialized:
                return

            try:
                import argostranslate.package
                import argostranslate.translate

                # 1. Scan custom models_dir for any local .argosmodel files
                for model_file in self.models_dir.glob("*.argosmodel"):
                    try:
                        logger.info("installing_local_argos_package", path=str(model_file))
                        argostranslate.package.install_from_path(str(model_file))
                    except Exception as exc:
                        logger.warning("argos_local_package_install_failed", path=str(model_file), error=str(exc))

                # 2. Inspect currently installed language translation pairs
                installed_langs = argostranslate.translate.get_installed_languages()
                for source in installed_langs:
                    for target in installed_langs:
                        translation = source.get_translation(target)
                        if translation is not None:
                            self._installed_pairs.add((source.code, target.code))

                logger.info("argos_runtime_initialized", installed_pairs=list(self._installed_pairs))
                self._is_initialized = True

            except ImportError:
                logger.warning("argostranslate_library_not_imported")
                self._is_initialized = False
            except Exception as exc:
                logger.warning("argos_runtime_initialization_error", error=str(exc))
                self._is_initialized = False

    def is_language_pair_available(self, from_code: str, to_code: str) -> bool:
        """Check whether a specific language translation pair is installed and operational."""
        return (from_code, to_code) in self._installed_pairs

    def translate(self, text: str, from_code: str, to_code: str) -> str | None:
        """Translate text using Argos Translate if available; returns None on unavailability for graceful fallback."""
        if not text.strip():
            return text

        if not self.is_language_pair_available(from_code, to_code):
            logger.debug(
                "argos_language_pair_unavailable",
                from_code=from_code,
                to_code=to_code,
            )
            return None

        try:
            import argostranslate.translate
            translated = argostranslate.translate.translate(text, from_code, to_code)
            return str(translated)
        except Exception as exc:
            logger.warning("argos_translation_failed", error=str(exc), from_code=from_code, to_code=to_code)
            return None

    def get_installed_packages(self) -> list[TranslationPackageInfo]:
        """Return metadata list of all active offline translation packages."""
        packages: list[TranslationPackageInfo] = []
        for src, tgt in sorted(self._installed_pairs):
            packages.append(
                TranslationPackageInfo(
                    source_language=src,
                    target_language=tgt,
                    package_name=f"translate-{src}_{tgt}",
                    is_installed=True,
                    engine="argos",
                )
            )
        return packages


_argos_singleton: ArgosTranslationEngine | None = None
_argos_singleton_lock = threading.Lock()


def get_argos_engine() -> ArgosTranslationEngine:
    """Return cached ArgosTranslationEngine singleton."""
    global _argos_singleton
    if _argos_singleton is None:
        with _argos_singleton_lock:
            if _argos_singleton is None:
                _argos_singleton = ArgosTranslationEngine()
    return _argos_singleton
