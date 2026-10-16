"""Domain models and contracts for translation hardening and cross-lingual query normalization."""

from enum import Enum
from pydantic import BaseModel, Field


class TranslationStrategy(str, Enum):
    """Strategy utilized for cross-lingual query normalization."""

    PASSTHROUGH = "passthrough"
    ARGOS_NEURAL = "argos_neural"
    DOMAIN_GLOSSARY_EXPANSION = "domain_glossary_expansion"
    HYBRID_FALLBACK = "hybrid_fallback"


class HeritageTermMapping(BaseModel):
    """Bidirectional domain term mapping for Belur Chennakeshava heritage entities."""

    kannada_term: str = Field(description="Canonical Kannada script representation")
    english_term: str = Field(description="Canonical Latin/English representation")
    category: str = Field(description="Entity category (e.g. temple, king, sculpture, architecture)")
    synonyms: list[str] = Field(default_factory=list, description="Alternative spellings or aliases")


class NormalizedQuery(BaseModel):
    """Result of cross-lingual query normalization for knowledge retrieval."""

    original_query: str = Field(description="Verbatim tourist query in original language")
    retrieval_query: str = Field(description="Normalized query formatted for dense/sparse knowledge retrieval")
    detected_language: str = Field(description="Source language code ('kn', 'en', etc.)")
    preserved_terms: list[str] = Field(default_factory=list, description="Heritage proper nouns identified and preserved")
    translation_applied: bool = Field(default=False, description="Whether translation or expansion was applied")
    strategy_used: TranslationStrategy = Field(description="Strategy used for query resolution")
    transliterated_query: str | None = Field(default=None, description="Pure phonetic transliteration if computed")


class TranslationPackageInfo(BaseModel):
    """Metadata regarding installed or available offline translation packages."""

    source_language: str = Field(description="Source ISO language code")
    target_language: str = Field(description="Target ISO language code")
    package_name: str = Field(description="Package identifier (e.g. translate-kn_en)")
    is_installed: bool = Field(default=False, description="Whether model weights are resident on disk")
    engine: str = Field(default="argos", description="Underlying translation runtime")
