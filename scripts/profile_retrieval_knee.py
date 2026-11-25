"""Profile Cross-Encoder re-ranking candidate counts (N in [5, 8, 10, 15])
Evaluates:
- Latency (rerank_ms and total retrieval_ms)
- Top-1 Recall compared to N=15 baseline
Saves to logs/retrieval_knee_profile.json
"""

import asyncio
import json
import time
from pathlib import Path
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.infrastructure.database.session import get_session_factory

TEST_QUERIES = [
    "Who built the Chennakeshava Temple at Belur and when?",
    "Kappe Chennigaraya Shrine",
    "How many Madanika bracket figures are there in total?",
    "What stone was used to construct the temple?",
    "Where is the Darpana Sundari sculpture located?",
    "What are the temple opening hours and visiting times?",
    "What is the architectural style of Belur temple?",
    "Why did King Vishnuvardhana build the temple at Belur?",
]


async def profile_knee():
    print("=" * 70)
    print("PHASE 5: RETRIEVAL KNEE PROFILING (N in [5, 8, 10, 15])")
    print("=" * 70)

    session_factory = get_session_factory()
    results = {}

    async with session_factory() as session:
        retriever = HybridRAGRetriever(session=session)

        # Warm up retriever
        await retriever.diagnose(query="warmup query", top_fused=10)

        for n in [15, 10, 8, 5]:
            timings = []
            top1_chunks = []

            for q in TEST_QUERIES:
                t0 = time.perf_counter()
                diag = await retriever.diagnose(query=q, top_fused=n, top_final=4)
                elap = (time.perf_counter() - t0) * 1000.0
                timings.append(elap)
                top1 = diag.final_chunks[0].chunk_id if diag.final_chunks else None
                top1_chunks.append(top1)

            mean_ms = sum(timings) / len(timings)
            results[n] = {
                "top_fused_candidates": n,
                "mean_retrieval_ms": round(mean_ms, 2),
                "latencies_ms": [round(t, 2) for t in timings],
                "top1_chunk_ids": top1_chunks,
            }
            print(f"N = {n:2d} | Mean Retrieval: {mean_ms:.2f} ms")

    # Measure top-1 agreement against N=15 baseline
    baseline_top1 = results[15]["top1_chunk_ids"]
    for n in [10, 8, 5]:
        matches = sum(1 for a, b in zip(baseline_top1, results[n]["top1_chunk_ids"]) if a == b)
        recall = (matches / len(baseline_top1)) * 100.0
        results[n]["top1_recall_vs_baseline"] = round(recall, 1)
        print(f"N = {n:2d} | Top-1 Agreement with N=15: {recall:.1f}%")
    results[15]["top1_recall_vs_baseline"] = 100.0

    out_path = Path("logs/retrieval_knee_profile.json")
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n[OK] Saved knee profile to {out_path}")


if __name__ == "__main__":
    asyncio.run(profile_knee())

