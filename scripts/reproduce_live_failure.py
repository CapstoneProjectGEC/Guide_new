"""Reproduce and diagnose live failures for Kappe Chennigaraya query in Kannada and English."""

import os
import sys
import json
import time
import httpx

sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")

from backend.src.infrastructure.database.session import get_session_factory
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.infrastructure.translation.nllb_engine import get_nllb_engine

STREAM_URL = "http://127.0.0.1:8000/api/v1/chat/stream"


def parse_sse_stream(raw_text: str) -> dict:
    tokens = []
    citations = []
    done_payload = {}
    for block in raw_text.strip().split("\n\n"):
        lines = block.strip().split("\n")
        ev_name, d_str = None, None
        for line in lines:
            if line.startswith("event: "):
                ev_name = line[7:].strip()
            elif line.startswith("data: "):
                d_str = line[6:].strip()
        if ev_name == "token" and d_str:
            try:
                tokens.append(json.loads(d_str).get("token", ""))
            except Exception:
                pass
        elif ev_name == "citations" and d_str:
            try:
                citations = json.loads(d_str).get("citations", [])
            except Exception:
                pass
        elif ev_name == "done" and d_str:
            try:
                done_payload = json.loads(d_str)
            except Exception:
                pass
    return {"text": "".join(tokens).strip(), "citations": citations, "done": done_payload}


async def diagnose():
    print("=" * 70)
    print("PHASE 1: LIVE FAILURE REPRODUCTION & DETAILED DIAGNOSIS")
    print("=" * 70)

    client = httpx.Client(timeout=60.0)
    session_factory = get_session_factory()
    nllb = get_nllb_engine()

    queries = [
        {"lang": "kn", "query": "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ಗುಡಿ"},
        {"lang": "en", "query": "Kappe Chennigaraya Shrine"},
    ]

    results = {}

    for item in queries:
        q_text = item["query"]
        lang = item["lang"]
        print(f"\n--- Testing Query: '{q_text}' [{lang}] ---")

        # 1. Measure HTTP live endpoint
        t0 = time.perf_counter()
        resp = client.post(
            STREAM_URL,
            json={"content": q_text, "preferred_language": lang, "input_mode": "text"},
        )
        total_http_ms = (time.perf_counter() - t0) * 1000.0
        parsed = parse_sse_stream(resp.text)

        # 2. Inspect query translation
        en_retrieval_query = q_text
        norm_result = None
        if lang == "kn":
            normalizer = QueryNormalizer(nllb_engine=nllb)
            norm_result = normalizer.normalize_for_retrieval(q_text, source_lang="kn")
            en_retrieval_query = norm_result.retrieval_query
            print(f"  Normalized retrieval query: {norm_result.retrieval_query}")
            print(f"  NLLB translated EN query : {en_retrieval_query}")

        # 3. Retrieve chunks directly for full inspection
        async with session_factory() as session:
            retriever = HybridRAGRetriever(session=session)
            ret_query = en_retrieval_query if lang == "kn" else q_text
            chunks = await retriever.retrieve(query=ret_query)

        chunk_details = []
        for c in chunks:
            chunk_details.append({
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "page_number": c.page_number,
                "section_heading": c.section_heading,
                "rerank_score": c.rerank_score,
                "content_preview": c.content[:250],
                "full_content": c.content,
            })

        print(f"  Live HTTP Latency: {total_http_ms:.1f} ms")
        print(f"  Reported Done Latency: {parsed['done'].get('latency_ms')} ms")
        print(f"  Citations Returned ({len(parsed['citations'])}):")
        for c in parsed["citations"]:
            print(f"    Page {c.get('page_number')} - {c.get('section_heading')}")
        print(f"  Answer Output:\n    {parsed['text']}")

        results[lang] = {
            "input_query": q_text,
            "detected_language": lang,
            "english_retrieval_query": en_retrieval_query,
            "http_latency_ms": round(total_http_ms, 1),
            "server_latency_ms": parsed["done"].get("latency_ms"),
            "citations": parsed["citations"],
            "answer_text": parsed["text"],
            "top_chunks": chunk_details,
            "raw_sse": resp.text,
        }

    out_file = os.path.join("logs", "live_failure_diagnosis.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Diagnosis saved to {out_file}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(diagnose())
