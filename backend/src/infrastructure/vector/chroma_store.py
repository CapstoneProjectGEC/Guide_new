"""ChromaDB vector store adapter and MiniLM embedding service."""

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any
import chromadb
from sentence_transformers import SentenceTransformer
from backend.src.core.config import get_settings
from backend.src.core.logging import get_logger
from backend.src.domain.knowledge import TextChunk

logger = get_logger("infrastructure.vector.chroma_store")


class EmbeddingService:
    """Computes dense vector embeddings using all-MiniLM-L6-v2."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._query_cache: dict[str, list[float]] = {}

    @property
    def model(self) -> SentenceTransformer:
        """Lazily load SentenceTransformer model singleton."""
        if self._model is None:
            logger.info("loading_embedding_model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Compute 384-dimensional dense vectors for a batch of strings."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return [vec.tolist() for vec in embeddings]

    def embed_query(self, query: str) -> list[float]:
        """Compute embedding vector for a single query string with in-memory caching."""
        clean_q = query.strip()
        if clean_q in self._query_cache:
            return self._query_cache[clean_q]
        embedding = self.model.encode(clean_q, convert_to_numpy=True, normalize_embeddings=True).tolist()
        if len(self._query_cache) >= 1024:
            self._query_cache.pop(next(iter(self._query_cache)))
        self._query_cache[clean_q] = embedding
        return embedding

    @staticmethod
    def calculate_vector_checksum(vector: list[float]) -> str:
        """Generate SHA-256 fingerprint for a float vector."""
        vec_bytes = ",".join(f"{v:.6f}" for v in vector).encode("utf-8")
        return hashlib.sha256(vec_bytes).hexdigest()


class ChromaVectorStore:
    """Manages persistent ChromaDB collections with isolated generation namespaces."""

    def __init__(self, persist_dir: str | Path) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        logger.info("chroma_store_initialized", path=str(self.persist_dir))

    def get_or_create_collection(self, collection_name: str) -> chromadb.Collection:
        """Retrieve existing collection or allocate an isolated namespace."""
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def get_collection(self, collection_name: str) -> chromadb.Collection | None:
        """Retrieve collection by name or return None if non-existent."""
        try:
            return self.client.get_collection(name=collection_name)
        except Exception:
            return None

    def delete_collection(self, collection_name: str) -> bool:
        """Safely delete an isolated generation collection."""
        try:
            self.client.delete_collection(name=collection_name)
            logger.info("chroma_collection_deleted", collection=collection_name)
            return True
        except Exception as exc:
            logger.warning("chroma_collection_delete_failed", collection=collection_name, error=str(exc))
            return False

    def index_chunks(
        self,
        collection_name: str,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> list[dict[str, Any]]:
        """Index chunks and dense embeddings into an isolated Chroma collection."""
        if not chunks:
            return []

        collection = self.get_or_create_collection(collection_name)

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        index_records: list[dict[str, Any]] = []

        for chunk, vec in zip(chunks, embeddings, strict=True):
            vector_id = f"{chunk.document_id}_{chunk.chunk_index}"
            ids.append(vector_id)
            documents.append(chunk.content)
            metadatas.append(
                {
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "section_heading": chunk.section_heading or "",
                    "token_count": chunk.token_count,
                }
            )
            index_records.append(
                {
                    "vector_id": vector_id,
                    "embedding": vec,
                    "checksum": EmbeddingService.calculate_vector_checksum(vec),
                }
            )

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "chunks_indexed_in_chroma",
            collection=collection_name,
            count=len(chunks),
        )
        return index_records

    def query_dense(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 15,
    ) -> list[dict[str, Any]]:
        """Execute dense cosine search against collection."""
        collection = self.get_collection(collection_name)
        if not collection:
            return []

        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return output

        ids = results["ids"][0]
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        for idx, item_id in enumerate(ids):
            # Chroma returns cosine distance (1 - cosine_similarity).
            # Cosine similarity = 1 - distance.
            dist = distances[idx] if idx < len(distances) else 1.0
            similarity = 1.0 - dist
            output.append(
                {
                    "vector_id": item_id,
                    "content": docs[idx] if idx < len(docs) else "",
                    "metadata": metas[idx] if idx < len(metas) else {},
                    "distance": dist,
                    "similarity": similarity,
                }
            )

        return output

    def count(self, collection_name: str) -> int:
        """Return number of vectors in a collection."""
        col = self.get_collection(collection_name)
        return col.count() if col else 0


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return cached EmbeddingService singleton."""
    settings = get_settings()
    return EmbeddingService(model_name=settings.EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def get_vector_store() -> ChromaVectorStore:
    """Return cached ChromaVectorStore singleton."""
    settings = get_settings()
    return ChromaVectorStore(persist_dir=settings.CHROMA_PERSIST_DIRECTORY)
