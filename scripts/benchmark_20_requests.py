"""Phase 7: Live 20-Request HTTP Benchmark
20 requests per language (English and Kannada) over the real /chat/stream HTTP endpoint.
- 5 distinct supported questions per language
- 4 repetitions per question (20 per language, 40 total)
- Nearest-rank P95 and median calculation
- Saves logs/latency_20_requests.json
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import json
import math
import time
from pathlib import Path
import httpx

STREAM_URL = "http://127.0.0.1:8000/api/v1/chat/stream"

SUPPORTED_QUERIES = [
    {
        "id": "Q1_Patron",
        "en": "Who built the Chennakeshava Temple at Belur and when?",
        "kn": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?",
    },
    {
        "id": "Q2_Material",
        "en": "What stone was used to construct the temple?",
        "kn": "ದೇವಾಲಯವನ್ನು ಯಾವ ಕಲ್ಲಿನಿಂದ ನಿರ್ಮಿಸಲಾಗಿದೆ?",
    },
    {
        "id": "Q3_Madanikas",
        "en": "How many Madanika bracket figures are there in total?",
        "kn": "ದೇವಾಲಯದಲ್ಲಿ ಒಟ್ಟು ಎಷ್ಟು ಮದನಿಕಾ ಶಿಲ್ಪಗಳಿವೆ?",
    },
    {
        "id": "Q4_Darpana",
        "en": "Where is the Darpana Sundari sculpture located?",
        "kn": "ದರ್ಪಣ ಸುಂದರಿ ಮದನಿಕಾ ಶಿಲ್ಪ ಎಲ್ಲಿದೆ?",
    },
    {
        "id": "Q5_Shrine",
        "en": "Kappe Chennigaraya Shrine",
        "kn": "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ಗುಡಿ",
    },
]


def nearest_rank_p95(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    rank = math.ceil(0.95 * len(sorted_v))
    idx = max(0, min(rank - 1, len(sorted_v) - 1))
    return sorted_v[idx]


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    mid = n // 2
    if n % 2 == 1:
        return sorted_v[mid]
    return (sorted_v[mid - 1] + sorted_v[mid]) / 2.0


def run_benchmark():
    print("=" * 70)
    print("PHASE 7: 20-REQUEST PER-LANGUAGE LIVE HTTP BENCHMARK (40 TOTAL)")
    print("=" * 70)

    client = httpx.Client(timeout=60.0)

    raw_samples = {"en": [], "kn": []}

    # Interleave requests: 4 repetitions across 5 questions
    for rep in range(1, 5):
        print(f"\n--- Repetition {rep} of 4 ---")
        for q_item in SUPPORTED_QUERIES:
            # 1. English
            q_en = q_item["en"]
            t0 = time.perf_counter()
            r_en = client.post(
                STREAM_URL,
                json={"content": q_en, "preferred_language": "en", "input_mode": "text"},
            )
            lat_en = (time.perf_counter() - t0) * 1000.0
            raw_samples["en"].append({
                "query_id": q_item["id"],
                "query": q_en,
                "repetition": rep,
                "latency_ms": round(lat_en, 2),
                "status_code": r_en.status_code,
            })
            print(f"[EN rep {rep}] {lat_en:6.1f} ms | {q_item['id']}")

            # 2. Kannada
            q_kn = q_item["kn"]
            t0 = time.perf_counter()
            r_kn = client.post(
                STREAM_URL,
                json={"content": q_kn, "preferred_language": "kn", "input_mode": "text"},
            )
            lat_kn = (time.perf_counter() - t0) * 1000.0
            raw_samples["kn"].append({
                "query_id": q_item["id"],
                "query": q_kn,
                "repetition": rep,
                "latency_ms": round(lat_kn, 2),
                "status_code": r_kn.status_code,
            })
            print(f"[KN rep {rep}] {lat_kn:6.1f} ms | {q_item['id']}")

    # Compute Statistics
    en_latencies = [s["latency_ms"] for s in raw_samples["en"]]
    kn_latencies = [s["latency_ms"] for s in raw_samples["kn"]]

    stats = {
        "method": "nearest-rank (rank = ceil(p/100 * n))",
        "sample_size_per_language": 20,
        "total_requests": 40,
        "english": {
            "sample_count": len(en_latencies),
            "median_latency_ms": round(median(en_latencies), 2),
            "p95_latency_ms": round(nearest_rank_p95(en_latencies), 2),
            "min_latency_ms": round(min(en_latencies), 2),
            "max_latency_ms": round(max(en_latencies), 2),
            "raw_samples": raw_samples["en"],
        },
        "kannada": {
            "sample_count": len(kn_latencies),
            "median_latency_ms": round(median(kn_latencies), 2),
            "p95_latency_ms": round(nearest_rank_p95(kn_latencies), 2),
            "min_latency_ms": round(min(kn_latencies), 2),
            "max_latency_ms": round(max(kn_latencies), 2),
            "raw_samples": raw_samples["kn"],
        },
    }

    print("\n" + "=" * 70)
    print("FINAL BENCHMARK SUMMARY (Nearest-Rank Method):")
    print(f"English (n=20): Median = {stats['english']['median_latency_ms']} ms | P95 = {stats['english']['p95_latency_ms']} ms")
    print(f"Kannada (n=20): Median = {stats['kannada']['median_latency_ms']} ms | P95 = {stats['kannada']['p95_latency_ms']} ms")
    print("=" * 70)

    out_file = Path("logs/latency_20_requests.json")
    out_file.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\n[OK] Saved results to {out_file}")


if __name__ == "__main__":
    run_benchmark()

