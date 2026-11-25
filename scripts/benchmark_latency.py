import httpx
import json
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

def run_benchmark(lang: str, question: str, n_runs: int = 5):
    print(f"\n--- Running Benchmark for [{lang}] ({n_runs} runs) ---")
    print(f"Question: {question}")
    
    total_latencies = []
    ttfts = []
    reported_latencies = []
    sample_answer = ""
    citations_sample = []

    payload = {
        "content": question,
        "preferred_language": lang,
        "input_mode": "text"
    }

    with httpx.Client(timeout=30.0) as client:
        for i in range(n_runs):
            t0 = time.perf_counter()
            first_token_time = None
            tokens = []
            citations = []
            reported_ms = None

            with client.stream("POST", "http://127.0.0.1:8000/api/v1/chat/stream", json=payload) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:].strip())
                            if "token" in data:
                                if first_token_time is None:
                                    first_token_time = time.perf_counter()
                                tokens.append(data["token"])
                            if "citations" in data:
                                citations = data["citations"]
                            if "latency_ms" in data:
                                reported_ms = data["latency_ms"]
                        except Exception:
                            pass
            t1 = time.perf_counter()
            tot_ms = int((t1 - t0) * 1000)
            ttft_ms = int((first_token_time - t0) * 1000) if first_token_time else tot_ms
            
            total_latencies.append(tot_ms)
            ttfts.append(ttft_ms)
            if reported_ms:
                reported_latencies.append(reported_ms)
            sample_answer = "".join(tokens).strip()
            citations_sample = citations
            print(f"  Run {i+1}: Total = {tot_ms} ms | TTFT = {ttft_ms} ms | Reported = {reported_ms} ms")

    def p95(data):
        sorted_d = sorted(data)
        idx = max(0, int(len(sorted_d) * 0.95) - 1)
        return sorted_d[idx]

    stats = {
        "runs": n_runs,
        "total_median": statistics.median(total_latencies),
        "total_mean": statistics.mean(total_latencies),
        "total_p95": p95(total_latencies),
        "total_min": min(total_latencies),
        "total_max": max(total_latencies),
        "ttft_median": statistics.median(ttfts),
        "ttft_mean": statistics.mean(ttfts),
        "reported_median": statistics.median(reported_latencies) if reported_latencies else None,
        "sample_answer": sample_answer,
        "citations": [f"p.{c.get('page_number')}: {c.get('section_heading')}" for c in citations_sample]
    }

    print(f"\nResults for [{lang}]:")
    print(f"  Total Latency - Median: {stats['total_median']:.1f} ms | Mean: {stats['total_mean']:.1f} ms | P95: {stats['total_p95']} ms")
    print(f"  TTFT - Median: {stats['ttft_median']:.1f} ms | Mean: {stats['ttft_mean']:.1f} ms")
    print(f"  Citations: {stats['citations']}")
    print(f"  Sample Answer: {sample_answer}")
    return stats

if __name__ == "__main__":
    en_stats = run_benchmark("en", "Who built the Chennakeshava Temple at Belur and when?", 5)
    kn_stats = run_benchmark("kn", "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", 5)
    
    with open("logs/latency_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({"en": en_stats, "kn": kn_stats}, f, indent=2, ensure_ascii=False)
    print("\nBenchmark results saved to logs/latency_benchmark_results.json")

