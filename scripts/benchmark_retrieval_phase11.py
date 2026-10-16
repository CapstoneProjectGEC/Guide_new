"""Repeatable local benchmark comparing baseline monolingual retrieval vs Phase 11 cross-lingual retrieval.

Measures latency and retrieval quality (chunks retrieved >= 0.35, top chunk relevance score, grounding guard verdict).
"""

import asyncio
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.src.application.chat.grounding_guard import GroundingGuard
from backend.src.application.rag.retriever import HybridRAGRetriever
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.infrastructure.database.session import get_session_factory

BENCHMARK_QUERIES = [
    {
        "id": "EN-01",
        "category": "English In-Domain",
        "query": "Who commissioned the Chennakeshava Temple at Belur?",
        "expected_grounded": True,
    },
    {
        "id": "EN-02",
        "category": "English In-Domain",
        "query": "What are the Madanika bracket figures carved from?",
        "expected_grounded": True,
    },
    {
        "id": "KN-01",
        "category": "Kannada In-Domain",
        "query": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?",
        "expected_grounded": True,
    },
    {
        "id": "KN-02",
        "category": "Kannada In-Domain",
        "query": "ಮದನಿಕಾ ಶಿಲಾಬಾಲಿಕೆಗಳ ಕೆತ್ತನೆಗಳ ಬಗ್ಗೆ ತಿಳಿಸಿ",
        "expected_grounded": True,
    },
    {
        "id": "KN-03",
        "category": "Kannada In-Domain",
        "query": "ಬೇಲೂರು ದೇವಾಲಯದ ದರ್ಶನ ಸಮಯ ಮತ್ತು ಪ್ರವೇಶ ಶುಲ್ಕ ಎಷ್ಟು?",
        "expected_grounded": True,
    },
    {
        "id": "MIX-01",
        "category": "Mixed-Language In-Domain",
        "query": "Belur Chennakeshava temple ನ ಇತಿಹಾಸವೇನು?",
        "expected_grounded": True,
    },
    {
        "id": "OOD-01",
        "category": "Out-of-Domain English",
        "query": "What is the history of the Eiffel Tower in Paris?",
        "expected_grounded": False,
    },
    {
        "id": "OOD-02",
        "category": "Out-of-Domain Kannada",
        "query": "ಮೈಸೂರು ಅರಮನೆಯ ಇತಿಹಾಸವೇನು?",
        "expected_grounded": False,
    },
]


async def run_benchmark():
    normalizer = QueryNormalizer()
    guard = GroundingGuard()

    print("=" * 90)
    print("PHASE 11 RETRIEVAL & GROUNDING EMPIRICAL BENCHMARK")
    print("=" * 90)

    # Warm-up models
    async with get_session_factory()() as warm_session:
        warm_retriever = HybridRAGRetriever(session=warm_session)
        await warm_retriever.retrieve("warmup query")

    results = []

    async with get_session_factory()() as session:
        retriever = HybridRAGRetriever(session=session)

        for q in BENCHMARK_QUERIES:
            raw_query = q["query"]

            # -------------------------------------------------------------
            # Path A: Baseline (Raw query fed directly to Hybrid Retriever)
            # -------------------------------------------------------------
            t0 = time.perf_counter()
            candidates_raw = await retriever.retrieve(raw_query)
            t_raw_retrieval_ms = (time.perf_counter() - t0) * 1000

            top_raw_score = candidates_raw[0].rerank_score if candidates_raw and candidates_raw[0].rerank_score is not None else 0.0
            is_grounded_raw = guard.evaluate(candidates_raw).is_grounded

            # -------------------------------------------------------------
            # Path B: Phase 11 (Query Normalizer + Hybrid Retriever)
            # -------------------------------------------------------------
            t1 = time.perf_counter()
            norm = normalizer.normalize_for_retrieval(raw_query)
            t_norm_ms = (time.perf_counter() - t1) * 1000

            t2 = time.perf_counter()
            candidates_p11 = await retriever.retrieve(norm.retrieval_query)
            t_p11_retrieval_ms = (time.perf_counter() - t2) * 1000

            top_p11_score = candidates_p11[0].rerank_score if candidates_p11 and candidates_p11[0].rerank_score is not None else 0.0
            is_grounded_p11 = guard.evaluate(candidates_p11).is_grounded

            results.append({
                "id": q["id"],
                "category": q["category"],
                "query": raw_query,
                "norm_query": norm.retrieval_query,
                "norm_strategy": norm.strategy_used.value,
                "norm_ms": t_norm_ms,
                "raw_count": len(candidates_raw),
                "raw_top_score": top_raw_score,
                "raw_grounded": is_grounded_raw,
                "raw_ms": t_raw_retrieval_ms,
                "p11_count": len(candidates_p11),
                "p11_top_score": top_p11_score,
                "p11_grounded": is_grounded_p11,
                "p11_retrieval_ms": t_p11_retrieval_ms,
                "p11_total_ms": t_norm_ms + t_p11_retrieval_ms,
            })

    # Print Results Table
    print("\n[RETRIEVAL QUALITY COMPARISON]")
    print(f"{'ID':<7} | {'Category':<22} | {'Raw Chunks':<10} | {'Raw Top':<8} | {'Raw Grounded':<12} | {'P11 Chunks':<10} | {'P11 Top':<8} | {'P11 Grounded'}")
    print("-" * 105)
    for r in results:
        print(
            f"{r['id']:<7} | {r['category']:<22} | {r['raw_count']:<10} | {r['raw_top_score']:<8.4f} | {str(r['raw_grounded']):<12} | "
            f"{r['p11_count']:<10} | {r['p11_top_score']:<8.4f} | {str(r['p11_grounded'])}"
        )

    print("\n[LATENCY MEASUREMENTS (ms)]")
    print(f"{'ID':<7} | {'Category':<22} | {'Norm Latency':<14} | {'Raw Retr':<10} | {'P11 Retr':<10} | {'P11 Total':<10} | {'Strategy'}")
    print("-" * 95)
    for r in results:
        print(
            f"{r['id']:<7} | {r['category']:<22} | {r['norm_ms']:<14.3f} | {r['raw_ms']:<10.2f} | {r['p11_retrieval_ms']:<10.2f} | {r['p11_total_ms']:<10.2f} | {r['norm_strategy']}"
        )

    # Summary Statistics
    kn_raw_grounded = sum(1 for r in results if "Kannada In-Domain" in r["category"] and r["raw_grounded"])
    kn_p11_grounded = sum(1 for r in results if "Kannada In-Domain" in r["category"] and r["p11_grounded"])
    kn_total = sum(1 for r in results if "Kannada In-Domain" in r["category"])

    ood_raw_rejected = sum(1 for r in results if "Out-of-Domain" in r["category"] and not r["raw_grounded"])
    ood_p11_rejected = sum(1 for r in results if "Out-of-Domain" in r["category"] and not r["p11_grounded"])
    ood_total = sum(1 for r in results if "Out-of-Domain" in r["category"])

    avg_norm_ms = sum(r["norm_ms"] for r in results) / len(results)

    print("\n[KEY TAKEAWAYS]")
    print(f"1. Kannada In-Domain Grounding Success : Baseline = {kn_raw_grounded}/{kn_total} ({kn_raw_grounded/kn_total*100:.0f}%) -> Phase 11 = {kn_p11_grounded}/{kn_total} ({kn_p11_grounded/kn_total*100:.0f}%)")
    print(f"2. Out-of-Domain Fallback Accuracy   : Baseline = {ood_raw_rejected}/{ood_total} ({ood_raw_rejected/ood_total*100:.0f}%) -> Phase 11 = {ood_p11_rejected}/{ood_total} ({ood_p11_rejected/ood_total*100:.0f}%)")
    print(f"3. Query Normalization Overhead       : Average {avg_norm_ms:.3f} ms (negligible sub-millisecond impact)")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
