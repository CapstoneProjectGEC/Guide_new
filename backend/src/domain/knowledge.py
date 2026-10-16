"""Domain models, validation rules, and schemas for knowledge base pipeline."""

from enum import Enum
from pydantic import BaseModel, Field


class GenerationStatusEnum(str, Enum):
    """Lifecycle states for immutable knowledge generations."""

    BUILD = "BUILD"
    PARSE = "PARSE"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    INDEX = "INDEX"
    VALIDATE = "VALIDATE"
    PROMOTE = "PROMOTE"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class PipelineStep(str, Enum):
    """Step execution names for the knowledge generation pipeline."""

    PARSE = "PARSE"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    INDEX = "INDEX"
    VALIDATE = "VALIDATE"
    PROMOTE = "PROMOTE"


class StepExecutionStatus(str, Enum):
    """Execution status of an individual pipeline step."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractedSection(BaseModel):
    """Structured text block extracted from a document page."""

    page_number: int = Field(ge=1, description="1-indexed source document page")
    section_heading: str | None = Field(default=None, description="Heading title or section label")
    content: str = Field(description="Normalized text content")


class TextChunk(BaseModel):
    """Segmented semantic text chunk with provenance metadata."""

    document_id: str = Field(description="Parent document UUID")
    chunk_index: int = Field(ge=0, description="Sequential chunk index within document")
    page_number: int = Field(ge=1, description="Page number of origin")
    section_heading: str | None = Field(default=None, description="Section heading context")
    content: str = Field(description="Chunk body text")
    token_count: int = Field(ge=0, description="Estimated token count")


class GenerationStepResponse(BaseModel):
    """Status details for a pipeline execution step."""

    step: str
    status: str
    progress_pct: float
    error_message: str | None = None


class KnowledgeGenerationResponse(BaseModel):
    """Representation contract for a knowledge generation."""

    id: str
    generation_number: int
    status: str
    chroma_collection_name: str
    chunk_count: int
    created_by_id: str | None = None
    created_at: str
    promoted_at: str | None = None
    steps: list[GenerationStepResponse] = Field(default_factory=list)


class KnowledgeGenerationListResponse(BaseModel):
    """Paginated or complete list of knowledge generations."""

    generations: list[KnowledgeGenerationResponse]
    active_generation_id: str | None = None
    total: int


class BuildGenerationRequest(BaseModel):
    """Optional payload to trigger a knowledge generation build."""

    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of specific document UUIDs to index. Defaults to all ingested documents.",
    )


class RollbackRequest(BaseModel):
    """Target specification for rolling back the active knowledge generation."""

    target_generation_id: str | None = Field(
        default=None,
        description="Target generation UUID to reactivate.",
    )
    target_generation_number: int | None = Field(
        default=None,
        description="Target generation number to reactivate.",
    )
