"""Reproducible RAG and LLM benchmark suite for Smart Tourist Guide."""

import argparse
import asyncio
import json
import statistics
import sys
import time
from typing import Any

# Ensure repository root is on PYTHONPATH and UTF-8 stream output
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from httpx import ASGITransport, AsyncClient
from backend.src.core.config import get_settings
from backend.src.main import app

BENCHMARK_DATASET = [
    {
        "id": "en_specific",
        "category": "English Fact Retrieval",
        "query": "Who commissioned the Chennakeshava Temple at Belur and in what year?",
        "expected_grounded": True,
        "language": "en",
        "keywords": ["Vishnuvardhana", "1117"],
    },
    {
        "id": "kn_specific",
        "category": "Kannada Fact Retrieval",
        "query": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವ ವರ್ಷದಲ್ಲಿ ನಿರ್ಮಿಸಿದರು?",
        "expected_grounded": True,
        "language": "kn",
        "keywords": ["ವಿಷ್ಣುವರ್ಧನ", "1117"],
    },
    {
        "id": "en_followup",
        "category": "English Sculpture Details",
        "query": "Who carved the Madanika bracket figures and how many are there?",
        "expected_grounded": True,
        "language": "en",
        "keywords": ["42", "Madanika"],
    },
    {
        "id": "en_architecture",
        "category": "English Material & Platform",
        "query": "What stone material was used to build the temple and what is the platform shape?",
        "expected_grounded": True,
        "language": "en",
        "keywords": ["soapstone", "chloritic schist", "jagati"],
    },
    {
        "id": "en_unsupported",
        "category": "English Out-of-Domain Guard",
        "query": "How do I make chocolate ice cream and pizza dough at home?",
        "expected_grounded": False,
        "language": "en",
        "keywords": ["Information is not available"],
    },
    {
        "id": "kn_unsupported",
        "category": "Kannada Out-of-Domain Guard",
        "query": "ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಮತ್ತು ಅಲ್ಲಿನ ಅಧ್ಯಕ್ಷರು ಯಾರು?",
        "expected_grounded": False,
        "language": "kn",
        "keywords": ["ಲಭ್ಯವಿಲ್ಲ"],
    },
    {
        "id": "en_adversarial",
        "category": "Adversarial Misleading Query",
        "query": "Did the British Empire build Belur Temple in 1947 CE?",
        "expected_grounded": True,
        "language": "en",
        "keywords": ["Vishnuvardhana", "1117", "Hoysala"],
    },
]


class BenchmarkRunner:
    """Executes latency, TTFT, and grounding accuracy benchmarks."""

    def __init__(self, concurrency: int = 1) -> None:
        self.concurrency = concurrency
        self.settings = get_settings()

    async def run_single_request(
        self, client: AsyncClient, item: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single SSE streaming request and record micro-metrics."""
        t_start = time.perf_counter()
        t_first_token: float | None = None
        tokens_received = 0
        full_content = []
        is_grounded = None
        citations_count = 0
        server_latency_ms = None

        payload = {
            "content": item["query"],
            "preferred_language": item["language"],
        }

        try:
            async with client.stream(
                "POST",
                "/api/v1/chat/stream",
                json=payload,
                timeout=30.0,
            ) as response:
                buffer = ""
                async for chunk_bytes in response.aiter_bytes():
                    buffer += chunk_bytes.decode("utf-8", errors="replace")
                    while "\n\n" in buffer:
                        event_text, buffer = buffer.split("\n\n", 1)
                        lines = event_text.splitlines()
                        event_type = ""
                        data_str = ""

                        for line in lines:
                            if line.startswith("event:"):
                                event_type = line.replace("event:", "").strip()
                            elif line.startswith("data:"):
                                data_str = line.replace("data:", "").strip()

                        if not data_str:
                            continue

                        try:
                            parsed = json.loads(data_str)
                        except Exception:
                            continue

                        if event_type == "token":
                            if t_first_token is None:
                                t_first_token = time.perf_counter()
                            token = parsed.get("token", "")
                            full_content.append(token)
                            tokens_received += 1

                        elif event_type == "citations":
                            citations_count = len(parsed.get("citations", []))

                        elif event_type == "done":
                            is_grounded = parsed.get("is_grounded")
                            server_latency_ms = parsed.get("latency_ms")

            t_end = time.perf_counter()
            total_duration_ms = (t_end - t_start) * 1000.0
            ttft_ms = (
                ((t_first_token - t_start) * 1000.0) if t_first_token else total_duration_ms
            )

            # Check grounding correctness
            answer_text = "".join(full_content)
            grounding_correct = is_grounded == item["expected_grounded"]
            keyword_match = any(kw.lower() in answer_text.lower() for kw in item["keywords"])

            return {
                "id": item["id"],
                "category": item["category"],
                "success": True,
                "ttft_ms": round(ttft_ms, 2),
                "total_ms": round(total_duration_ms, 2),
                "server_latency_ms": server_latency_ms,
                "tokens": tokens_received,
                "tokens_per_sec": (
                    round(tokens_received / ((t_end - (t_first_token or t_start)) or 0.001), 1)
                ),
                "citations_count": citations_count,
                "is_grounded": is_grounded,
                "grounding_correct": grounding_correct,
                "keyword_match": keyword_match,
                "answer_preview": answer_text[:80].replace("\n", " ").encode("ascii", "replace").decode("ascii"),
            }

        except Exception as exc:
            t_end = time.perf_counter()
            return {
                "id": item["id"],
                "category": item["category"],
                "success": False,
                "error": str(exc),
                "total_ms": round((t_end - t_start) * 1000.0, 2),
            }

    async def run_suite(self) -> dict[str, Any]:
        """Execute cold run followed by warm benchmark dataset."""
        print("=" * 75)
        print("  SMART TOURIST GUIDE: RAG RETRIEVAL & STREAMING BENCHMARK SUITE")
        print("=" * 75)
        print(f"Model Candidate:       {self.settings.OLLAMA_MODEL}")
        print(f"Ollama Base URL:       {self.settings.OLLAMA_BASE_URL}")
        print(f"Context Tokens:        {self.settings.OLLAMA_NUM_CTX}")
        print(f"Max Predict Tokens:    {self.settings.OLLAMA_NUM_PREDICT}")
        print(f"Temperature / Top_P:   {self.settings.OLLAMA_TEMPERATURE} / {self.settings.OLLAMA_TOP_P}")
        print(f"Keep-Alive:            {self.settings.OLLAMA_KEEP_ALIVE}")
        print(f"Concurrency Level:     {self.concurrency}")
        print("-" * 75)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Measure separate Cold Start Run
            print("\n[Stage 1] Measuring Cold-Start Latency (Model + Embeddings first load)...")
            cold_item = BENCHMARK_DATASET[0]
            cold_result = await self.run_single_request(client, cold_item)
            print(
                f"  Cold Run: TTFT={cold_result.get('ttft_ms')}ms | Total={cold_result.get('total_ms')}ms | Grounded={cold_result.get('is_grounded')}"
            )

            # 2. Warm Runs
            print(f"\n[Stage 2] Executing Warm Benchmark (Sample Count: {len(BENCHMARK_DATASET)} queries)...")
            warm_results = []

            if self.concurrency == 1:
                for item in BENCHMARK_DATASET:
                    res = await self.run_single_request(client, item)
                    warm_results.append(res)
                    print(
                        f"  [{res['id']:<15}] TTFT: {res.get('ttft_ms', 0):>6.1f}ms | Total: {res.get('total_ms', 0):>6.1f}ms | Tokens: {res.get('tokens', 0):>3} | Grounded: {str(res.get('is_grounded')):<5} | Correct: {res.get('grounding_correct')} | Error: {res.get('error')}"
                    )
            else:
                # Concurrent batches of size `self.concurrency`
                for i in range(0, len(BENCHMARK_DATASET), self.concurrency):
                    batch = BENCHMARK_DATASET[i : i + self.concurrency]
                    batch_tasks = [self.run_single_request(client, itm) for itm in batch]
                    batch_res = await asyncio.gather(*batch_tasks)
                    for res in batch_res:
                        warm_results.append(res)
                        print(
                            f"  [CONCURRENT {res['id']:<10}] TTFT: {res.get('ttft_ms', 0):>6.1f}ms | Total: {res.get('total_ms', 0):>6.1f}ms | Correct: {res.get('grounding_correct')}"
                        )

            # Aggregate statistics
            successful = [r for r in warm_results if r.get("success")]
            ttft_list = [r["ttft_ms"] for r in successful if r.get("ttft_ms")]
            total_list = [r["total_ms"] for r in successful]
            tokens_per_sec_list = [r["tokens_per_sec"] for r in successful if r.get("tokens_per_sec")]

            stats_summary = {
                "sample_count": len(warm_results),
                "success_count": len(successful),
                "error_rate_pct": round(
                    ((len(warm_results) - len(successful)) / len(warm_results)) * 100, 1
                ),
                "cold_ttft_ms": cold_result.get("ttft_ms"),
                "cold_total_ms": cold_result.get("total_ms"),
                "warm_ttft_median_ms": round(statistics.median(ttft_list), 1) if ttft_list else 0,
                "warm_ttft_p95_ms": (
                    round(statistics.quantiles(ttft_list, n=20)[18], 1)
                    if len(ttft_list) >= 2
                    else (ttft_list[0] if ttft_list else 0)
                ),
                "warm_total_median_ms": (
                    round(statistics.median(total_list), 1) if total_list else 0
                ),
                "warm_total_p95_ms": (
                    round(statistics.quantiles(total_list, n=20)[18], 1)
                    if len(total_list) >= 2
                    else (total_list[0] if total_list else 0)
                ),
                "grounding_accuracy_pct": round(
                    (sum(1 for r in successful if r.get("grounding_correct")) / len(successful))
                    * 100,
                    1,
                ),
            }

            print("\n" + "=" * 75)
            print("  BENCHMARK SUMMARY RESULTS")
            print("=" * 75)
            print(f"Total Queries Tested:      {stats_summary['sample_count']}")
            print(f"Error Rate:                {stats_summary['error_rate_pct']}%")
            print(f"Grounding Accuracy:        {stats_summary['grounding_accuracy_pct']}%")
            print(f"Cold Start TTFT:           {stats_summary['cold_ttft_ms']} ms")
            print(f"Cold Start Total:          {stats_summary['cold_total_ms']} ms")
            print(f"Warm TTFT (Median):        {stats_summary['warm_ttft_median_ms']} ms")
            print(f"Warm TTFT (p95):           {stats_summary['warm_ttft_p95_ms']} ms")
            print(f"Warm Total Latency (p50):  {stats_summary['warm_total_median_ms']} ms")
            print(f"Warm Total Latency (p95):  {stats_summary['warm_total_p95_ms']} ms")
            print("=" * 75)

            return stats_summary


def main():
    parser = argparse.ArgumentParser(description="Smart Tourist Guide RAG Benchmark Runner")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent request level (1 or 2)")
    args = parser.parse_args()

    runner = BenchmarkRunner(concurrency=args.concurrency)
    asyncio.run(runner.run_suite())


if __name__ == "__main__":
    main()
