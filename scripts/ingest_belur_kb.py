"""Idempotent ingestion script for Belur Chennakeshava Temple Knowledge Base.

Validates, chunks, embeds, and indexes kb_chunks.jsonl into ChromaDB and BM25 index.
Ensures upserts by section_id, creates QA retrieval aids, and strictly validates catalogue integrity.
"""

import argparse
import json
import logging
from pathlib import Path
import re
import sys

# Ensure repository root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.src.application.rag.bm25 import BM25Index
from backend.src.core.config import get_settings
from backend.src.infrastructure.vector.chroma_store import ChromaVectorStore, EmbeddingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_belur_kb")

REQUIRED_FIELDS = [
    "document_id",
    "section_id",
    "title",
    "topic",
    "source_url",
    "source_page_title",
    "source_heading",
    "content_type",
    "image_ids",
    "language",
    "extraction_date",
    "text",
]


def validate_kb_records(records: list[dict], image_catalogue_path: Path) -> dict:
    """Validate 53 records (22 sections, 21 images, 10 conflicts) and check all image_ids."""
    if not image_catalogue_path.exists():
        raise FileNotFoundError(f"Image catalogue not found at {image_catalogue_path}")

    with open(image_catalogue_path, "r", encoding="utf-8") as f:
        catalogue = json.load(f)

    valid_image_ids = {img["image_id"] for img in catalogue}
    logger.info(f"Loaded {len(valid_image_ids)} valid image IDs from catalogue.")

    sections = []
    images = []
    conflicts = []

    for idx, r in enumerate(records):
        sid = r.get("section_id", "")
        # 1. Check required fields
        for field in REQUIRED_FIELDS:
            if field not in r:
                raise ValueError(f"Record {idx} ({sid}) missing required field '{field}'")

        # 2. Check image_ids
        for iid in r.get("image_ids", []):
            if iid not in valid_image_ids:
                raise ValueError(f"Record {sid} references unknown image_id '{iid}' not in image catalogue")

        # 3. Categorize by record kind
        topic = r.get("topic", "")
        if topic == "image" or "-IMG-" in sid:
            images.append(r)
        elif topic == "conflicts" or "-C" in sid:
            conflicts.append(r)
        else:
            sections.append(r)

    logger.info(
        f"Validation passed: Total={len(records)} | Sections={len(sections)} | "
        f"Images={len(images)} | Conflicts={len(conflicts)}"
    )

    if len(records) != 53 or len(sections) != 22 or len(images) != 21 or len(conflicts) != 10:
        raise ValueError(
            f"Record count mismatch! Expected 53 total (22 sections, 21 images, 10 conflicts), "
            f"got: {len(records)} total ({len(sections)} sections, {len(images)} images, {len(conflicts)} conflicts)"
        )

    return {
        "sections": sections,
        "images": images,
        "conflicts": conflicts,
        "valid_image_ids": valid_image_ids,
    }


def split_text_paragraphs(text: str, max_words: int = 300) -> list[str]:
    """Split text along paragraph boundaries if it exceeds word ceiling."""
    words = text.split()
    if len(words) <= max_words:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_para = []
    current_word_count = 0

    for para in paragraphs:
        p_clean = para.strip()
        if not p_clean:
            continue
        p_words = len(p_clean.split())
        if current_word_count + p_words > max_words and current_para:
            chunks.append("\n\n".join(current_para))
            current_para = [p_clean]
            current_word_count = p_words
        else:
            current_para.append(p_clean)
            current_word_count += p_words

    if current_para:
        chunks.append("\n\n".join(current_para))

    return chunks if chunks else [text]


def prepare_chunks(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build primary document chunks and QA retrieval aid chunks."""
    all_chunks = []
    raw_sections_map = {}

    for r in records:
        sid = r["section_id"]
        raw_sections_map[sid] = r
        title = r.get("title", "").strip()
        text = r.get("text", "").strip()
        has_ai_note = bool("[AI note]" in text)

        # 1. Record-level chunks (split if exceeding token limit)
        sub_texts = split_text_paragraphs(text, max_words=320)
        is_multi_part = len(sub_texts) > 1

        for p_idx, sub_text in enumerate(sub_texts, start=1):
            chunk_id = f"{sid}:p{p_idx}" if is_multi_part else sid
            full_content = f"{title}\n\n{sub_text}".strip()
            chunk_has_ai_note = bool("[AI note]" in sub_text)
            is_pure_ai_note = sub_text.strip().startswith("[AI note]")

            chunk_meta = {
                "chunk_id": chunk_id,
                "document_id": r.get("document_id", "BELUR-KB-001"),
                "section_id": sid,
                "parent_section_id": sid,
                "title": title,
                "topic": r.get("topic", ""),
                "source_url": r.get("source_url", ""),
                "source_page_title": r.get("source_page_title", ""),
                "source_heading": r.get("source_heading", ""),
                "content_type": r.get("content_type", "text"),
                "image_ids": ",".join(r.get("image_ids", [])),
                "language": r.get("language", "en"),
                "extraction_date": r.get("extraction_date", "2026-10-16"),
                "has_ai_note": chunk_has_ai_note,
                "is_ai_note": is_pure_ai_note,
                "is_qa": False,
                "part": p_idx,
                "content": full_content,
            }
            all_chunks.append(chunk_meta)

        # 2. QA Pairs chunks (retrieval aids pointing back to parent section)
        qa_pairs = r.get("qa_pairs", [])
        for q_idx, qa in enumerate(qa_pairs, start=1):
            q_text = qa.get("question", "").strip()
            a_text = qa.get("answer", "").strip()
            qa_content = f"Q: {q_text}\nA: {a_text}"
            qa_chunk_id = f"{sid}:qa:{q_idx}"

            qa_meta = {
                "chunk_id": qa_chunk_id,
                "document_id": r.get("document_id", "BELUR-KB-001"),
                "section_id": sid,
                "parent_section_id": sid,
                "title": f"Q&A: {q_text}",
                "topic": r.get("topic", ""),
                "source_url": r.get("source_url", ""),
                "source_page_title": r.get("source_page_title", ""),
                "source_heading": r.get("source_heading", ""),
                "content_type": "qa_pair",
                "image_ids": ",".join(r.get("image_ids", [])),
                "language": r.get("language", "en"),
                "extraction_date": r.get("extraction_date", "2026-10-16"),
                "has_ai_note": False,
                "is_ai_note": False,
                "is_qa": True,
                "part": 1,
                "content": qa_content,
            }
            all_chunks.append(qa_meta)

    return all_chunks, list(raw_sections_map.values())


def ingest_belur_kb(
    kb_jsonl_path: str = "data/kb/belur/kb_chunks.jsonl",
    catalogue_path: str = "data/kb/belur/image_catalogue.json",
    collection_name: str | None = None,
    output_bm25_path: str = "data/kb/belur/belur_bm25_index.json",
    output_registry_path: str = "data/kb/belur/belur_chunks_registry.json",
) -> dict:
    """Execute complete ingestion pipeline with validation, embeddings, and BM25 caching."""
    settings = get_settings()
    target_collection = collection_name or settings.BELUR_CHROMA_COLLECTION

    jsonl_file = Path(kb_jsonl_path)
    if not jsonl_file.exists():
        raise FileNotFoundError(f"Knowledge base file not found at: {kb_jsonl_path}")

    logger.info(f"Reading KB records from {jsonl_file}")
    with open(jsonl_file, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    # 1. Validate on load (fail loudly if requirements are violated)
    val_result = validate_kb_records(records, Path(catalogue_path))

    # 2. Build chunks
    all_chunks, raw_sections = prepare_chunks(records)
    logger.info(f"Prepared {len(all_chunks)} total chunks (primary records + QA aids)")

    # 3. Dense Embedding Generation
    embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL_NAME)
    chunk_texts = [c["content"] for c in all_chunks]
    logger.info(f"Generating dense embeddings using {settings.EMBEDDING_MODEL_NAME} for {len(chunk_texts)} chunks...")
    embeddings = embedding_service.embed_texts(chunk_texts)

    # 4. Upsert into ChromaDB collection (Idempotent: upserts by chunk_id)
    chroma_store = ChromaVectorStore(persist_dir=settings.CHROMA_PERSIST_DIRECTORY)
    collection = chroma_store.get_or_create_collection(target_collection)

    ids = [c["chunk_id"] for c in all_chunks]
    metadatas = []
    for c in all_chunks:
        meta = {k: v for k, v in c.items() if k not in ("content",)}
        metadatas.append(meta)

    logger.info(f"Upserting {len(ids)} chunks into Chroma collection '{target_collection}'...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunk_texts,
        metadatas=metadatas,
    )

    # Verify collection count
    collection_count = collection.count()
    logger.info(f"Chroma collection '{target_collection}' now contains {collection_count} vectors.")

    # 5. Build and serialize BM25 index for sparse keyword search
    bm25_records = [
        {
            "chunk_id": c["chunk_id"],
            "section_id": c["section_id"],
            "parent_section_id": c["parent_section_id"],
            "title": c["title"],
            "topic": c["topic"],
            "content_type": c["content_type"],
            "content": c["content"],
        }
        for c in all_chunks
    ]
    bm25_index = BM25Index(k1=1.5, b=0.75).fit(bm25_records)

    bm25_out = Path(output_bm25_path)
    bm25_out.parent.mkdir(parents=True, exist_ok=True)
    with open(bm25_out, "w", encoding="utf-8") as f:
        json.dump(bm25_records, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved BM25 corpus ({len(bm25_records)} items) to {bm25_out}")

    # 6. Save raw sections registry and chunk lookup table
    registry = {
        "document_id": "BELUR-KB-001",
        "version": settings.BELUR_KB_VERSION,
        "extraction_date": settings.BELUR_KB_EXTRACTION_DATE,
        "chunk_count": len(all_chunks),
        "collection_name": target_collection,
        "sections": {s["section_id"]: s for s in raw_sections},
        "chunks": {c["chunk_id"]: c for c in all_chunks},
    }
    reg_out = Path(output_registry_path)
    reg_out.parent.mkdir(parents=True, exist_ok=True)
    with open(reg_out, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved chunks registry to {reg_out}")

    logger.info("Ingestion completed successfully!")
    return {
        "total_records": len(records),
        "total_chunks": len(all_chunks),
        "chroma_count": collection_count,
        "collection_name": target_collection,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Belur Knowledge Base")
    parser.add_argument("--kb-path", default="data/kb/belur/kb_chunks.jsonl")
    parser.add_argument("--catalogue-path", default="data/kb/belur/image_catalogue.json")
    parser.add_argument("--collection", default=None)
    args = parser.parse_args()

    ingest_belur_kb(
        kb_jsonl_path=args.kb_path,
        catalogue_path=args.catalogue_path,
        collection_name=args.collection,
    )
