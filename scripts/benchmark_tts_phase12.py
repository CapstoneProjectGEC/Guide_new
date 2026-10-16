"""Repeatable local benchmark evaluating Phase 12 Piper TTS latency, throughput, and caching.

Measures:
1. One-time cold voice model load latency.
2. Warm CPU inference latency (English and Kannada).
3. Audio output duration and Real-Time Factor (RTF = latency / audio_duration).
4. LRU cache hit latency.
5. Concurrency scaling with 5 simultaneous requests.
"""

import asyncio
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.src.application.voice.tts_service import TextToSpeechService
from backend.src.domain.voice import SynthesisRequest
from backend.src.infrastructure.audio.piper_engine import PiperEngine

TEST_CASES = [
    {
        "id": "EN-SHORT",
        "lang": "en",
        "category": "English Short Fallback",
        "text": "Information is not available in the knowledge base.",
    },
    {
        "id": "EN-MEDIUM",
        "lang": "en",
        "category": "English Answer (Turn 1)",
        "text": "The Chennakeshava Temple at Belur was commissioned by King Vishnuvardhana of the Hoysala Empire in 1117 AD to celebrate his victory over the Cholas.",
    },
    {
        "id": "KN-SHORT",
        "lang": "kn",
        "category": "Kannada Short Fallback",
        "text": "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.",
    },
    {
        "id": "KN-MEDIUM",
        "lang": "kn",
        "category": "Kannada Answer (Turn 1)",
        "text": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ಸಾಮ್ರಾಜ್ಯದ ವಿಷ್ಣುವರ್ಧನ ರಾಜನು ಕ್ರಿ.ಶ. 1117 ರಲ್ಲಿ ಚೋಳರ ಮೇಲಿನ ವಿಜಯದ ನೆನಪಿಗಾಗಿ ನಿರ್ಮಿಸಿದನು.",
    },
]


async def run_benchmark():
    print("=" * 80)
    print("PHASE 12 — TEXT-TO-SPEECH (PIPER TTS) BENCHMARK SUITE")
    print("=" * 80)

    engine = PiperEngine()
    service = TextToSpeechService(piper_engine=engine)

    # 1. Inspect status
    status = service.get_status()
    print(f"Engine: {status.engine_name}")
    print(f"Device: {status.device}")
    print(f"Operational: {status.is_operational}")
    print(f"Installed Voices: {status.installed_voices}")
    print(f"Supported Languages: {status.supported_languages}")
    print("-" * 80)

    # 2. Warm synthesis benchmark
    results = []
    for tc in TEST_CASES:
        req = SynthesisRequest(text=tc["text"], language=tc["lang"])

        # Cold / Warm First Call
        t0 = time.perf_counter()
        audio, meta = await service.synthesize(req)
        first_ms = (time.perf_counter() - t0) * 1000

        rtf = (meta.latency_ms / 1000.0) / max(0.01, meta.duration_seconds)

        # Cache Hit Test (Second Call)
        t0_cache = time.perf_counter()
        audio_cached, meta_cached = await service.synthesize(req)
        cache_ms = (time.perf_counter() - t0_cache) * 1000

        res_item = {
            "id": tc["id"],
            "category": tc["category"],
            "lang": tc["lang"],
            "chars": len(tc["text"]),
            "bytes": len(audio),
            "duration_s": meta.duration_seconds,
            "latency_ms": meta.latency_ms,
            "rtf": rtf,
            "cached_latency_ms": cache_ms,
            "cache_hit": meta_cached.cached,
        }
        results.append(res_item)

        print(
            f"[{tc['id']}] {tc['category']} ({len(tc['text'])} chars)\n"
            f"  -> Audio: {meta.duration_seconds:.2f}s ({len(audio):,} bytes WAV @ {meta.sample_rate}Hz)\n"
            f"  -> Latency: {meta.latency_ms}ms | RTF: {rtf:.3f}x (Lower is better, <1.0 is faster-than-realtime)\n"
            f"  -> Cache Hit Latency: {cache_ms:.2f}ms (Cached: {meta_cached.cached})\n"
        )

    # 3. Concurrency test with 5 parallel requests
    print("-" * 80)
    print("CONCURRENCY BENCHMARK (5 Simultaneous Requests)")
    conc_reqs = [
        SynthesisRequest(text=tc["text"], language=tc["lang"])
        for tc in TEST_CASES
    ] + [SynthesisRequest(text="Welcome to Belur temple tour.", language="en")]

    t0_conc = time.perf_counter()
    conc_res = await asyncio.gather(*[service.synthesize(r) for r in conc_reqs])
    conc_total_ms = (time.perf_counter() - t0_conc) * 1000
    avg_per_req_ms = conc_total_ms / len(conc_reqs)

    print(f"5 Concurrent requests completed in {conc_total_ms:.1f}ms total (avg {avg_per_req_ms:.1f}ms/request)")
    print(f"All 5 returned valid WAV buffers: {[len(a) > 1000 for a, _ in conc_res]}")

    print("=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"{'ID':<10} | {'Lang':<4} | {'Chars':<5} | {'Audio (s)':<9} | {'Latency':<9} | {'RTF':<6} | {'Cache (ms)':<10}")
    print("-" * 70)
    for r in results:
        print(f"{r['id']:<10} | {r['lang']:<4} | {r['chars']:<5} | {r['duration_s']:<9.2f} | {r['latency_ms']:<6}ms | {r['rtf']:<6.3f} | {r['cached_latency_ms']:<10.2f}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_benchmark())
