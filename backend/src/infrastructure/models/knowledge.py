"""Knowledge base, document ingestion, and vector metadata models."""

from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.src.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Uploaded PDF document and cryptographic fingerprint."""

    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), default="application/pdf", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uploaded_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeGeneration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable knowledge generation tracking."""

    __tablename__ = "knowledge_generations"

    generation_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "BUILD", "PARSE", "CHUNK", "EMBED", "INDEX", "VALIDATE", "PROMOTE", "ACTIVE", "ARCHIVED", "FAILED",
            name="generation_status_enum",
        ),
        default="BUILD",
        index=True,
        nullable=False,
    )
    chroma_collection_name: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    statuses: Mapped[list["GenerationStatus"]] = relationship("GenerationStatus", back_populates="generation", cascade="all, delete-orphan")
    chunks: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="generation", cascade="all, delete-orphan")


class GenerationStatus(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Step execution tracker for pipeline runs."""

    __tablename__ = "generation_status"

    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_generations.id", ondelete="CASCADE"), index=True, nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    generation: Mapped["KnowledgeGeneration"] = relationship("KnowledgeGeneration", back_populates="statuses")


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Parsed and segmented text chunk with provenance mapping."""

    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_generations.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    section_heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    generation: Mapped["KnowledgeGeneration"] = relationship("KnowledgeGeneration", back_populates="chunks")
    embeddings: Mapped[list["ChunkEmbedding"]] = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")


class ChunkEmbedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Embedding vector mapping and collection checksum."""

    __tablename__ = "embeddings"

    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_generations.id", ondelete="CASCADE"), index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), default="all-MiniLM-L6-v2", nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, default=384, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk", back_populates="embeddings")


class CitationReference(Base):
    """Explicit mapping linking generated message turns to source chunks."""

    __tablename__ = "citation_references"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
