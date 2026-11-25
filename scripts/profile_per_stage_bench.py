"""Phase 6: Stage Timing Instrumentation & Profiling
Executes real HTTP requests across languages, captures cold-start first request,
computes per-stage nearest-rank median and P95, and saves logs/per_stage_timings.json.
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

TEST_PAIRS = [
    ("Who built the Chennakeshava Temple at Belur and when?", "en"),
    ("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", "kn"),
    ("What stone was used to construct the temple?", "en"),
    ("ದೇವಾಲಯವನ್ನು ಯಾವ ಕಲ್ಲಿನಿಂದ ನಿರ್ಮಿಸಲಾಗಿದೆ?", "kn"),
    ("How many Madanika bracket figures are there in total?", "en"),
    ("ದೇವಾಲಯದಲ್ಲಿ ಒಟ್ಟು ಎಷ್ಟು ಮದನಿಕಾ ಶಿಲ್ಪಗಳಿವೆ?", "kn"),
    ("Where is the Darpana Sundari sculpture located?", "en"),
    ("ದರ್ಪಣ ಸುಂದರಿ ಮದನಿಕಾ ಶಿಲ್ಪ ಎಲ್ಲಿದೆ?", "kn"),
    ("Kappe Chennigaraya Shrine", "en"),
    ("ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ಗುಡಿ", "kn"),
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


def run_stage_profiling():
    print("=" * 70)
    print("PHASE 6: PER-STAGE TIMING INSTRUMENTATION & BENCHMARK")
    print("=" * 70)

    # Clear timings log
    timings_log = Path("logs/request_timings.jsonl")
    timings_log.write_text("", encoding="utf-8")

    client = httpx.Client(timeout=60.0)

    # 1. Capture Cold-Start Request (First Request)
    print("\n--- Measuring Cold-Start First Request ---")
    t0 = time.perf_counter()
    r_cold = client.post(
        STREAM_URL,
        json={"content": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", "preferred_language": "kn", "input_mode": "text"},
    )
    cold_http_ms = (time.perf_counter() - t0) * 1000.0
    print(f"Cold-Start Kannada Request HTTP Latency: {cold_http_ms:.1f} ms")

    # 2. Run warm paired requests (3 runs per query)
    print("\n--- Running Warm Paired Profile Requests ---")
    for loop in range(2):
        for q_text, lang in TEST_PAIRS:
            t_req = time.perf_counter()
            resp = client.post(
                STREAM_URL,
                json={"content": q_text, "preferred_language": lang, "input_mode": "text"},
            )
            dur_ms = (time.perf_counter() - t_req) * 1000.0
            print(f"[{lang.upper()}] {dur_ms:6.1f} ms | Q: {q_text[:40]}")

    # 3. Read back structured logs from logs/request_timings.jsonl
    lines = [json.loads(l) for l in timings_log.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\nCaptured {len(lines)} structured request timing records.")

    # 4. Partition by language
    stages_by_lang = {"en": {}, "kn": {}}
    for entry in lines:
        lang = entry["language"]
        for stage, val in entry["stage_timings"].items():
            stages_by_lang[lang].setdefault(stage, []).append(val)

    summary = {
        "method": "nearest-rank (rank = ceil(p/100 * n))",
        "cold_start_kannada_first_request_ms": round(cold_http_ms, 2),
        "total_requests_profiled": len(lines),
        "languages": {},
    }

    for lang in ["en", "kn"]:
        summary["languages"][lang] = {}
        print(f"\n--- Stage Timings Summary [{lang.upper()}] ---")
        for stage, vals in sorted(stages_by_lang[lang].items()):
            med_val = round(median(vals), 2)
            p95_val = round(nearest_rank_p95(vals), 2)
            summary["languages"][lang][stage] = {
                "count": len(vals),
                "median_ms": med_val,
                "p95_ms": p95_val,
                "min_ms": round(min(vals), 2),
                "max_ms": round(max(vals), 2),
            }
            print(f"  {stage:24s} | Median: {med_val:6.1f} ms | P95: {p95_val:6.1f} ms (n={len(vals)})")

    out_file = Path("logs/per_stage_timings.json")
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n[OK] Saved per-stage summary to {out_file}")


if __name__ == "__main__":
    run_stage_profiling()
