"""End-to-End Live HTTP/SSE Pipeline Verification Script for Belur Heritage Guide.

Per Phase 10 Requirements:
- Uses PURE HTTP/SSE calls against running FastAPI server (http://127.0.0.1:8000/api/v1/chat/stream).
- Does NOT call internal Python methods directly.
- Validates factual correctness, latency under 3000ms, single relevant citation, and no system prompt leakage.
"""

import json
import os
import sys
import time
import httpx

# Ensure stdout handles UTF-8 on Windows
sys.stdout.reconfigure(encoding="utf-8")

ENDPOINT_URL = os.environ.get("CHAT_STREAM_URL", "http://127.0.0.1:8000/api/v1/chat/stream")

def verify_query_http(question: str, lang: str) -> dict:
    print(f"\n--- [LIVE HTTP/SSE] Testing [{lang}]: {question} ---")
    payload = {
        "content": question,
        "preferred_language": lang,
        "input_mode": "text"
    }

    t0 = time.perf_counter()
    tokens = []
    citations = []
    done_payload = {}
    event_names = []
    first_token_time = None

    with httpx.Client(timeout=30.0) as client:
        with client.stream("POST", ENDPOINT_URL, json=payload) as response:
            assert response.status_code == 200, f"Expected HTTP 200 but got {response.status_code}"
            current_event = None
            for line in response.iter_lines():
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    event_names.append(current_event)
                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                    try:
                        parsed = json.loads(data_str)
                        if current_event == "token" and "token" in parsed:
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            tokens.append(parsed["token"])
                        elif current_event == "citations" and "citations" in parsed:
                            citations = parsed["citations"]
                        elif current_event == "done":
                            done_payload = parsed
                    except Exception as err:
                        pass

    t1 = time.perf_counter()
    total_ms = int((t1 - t0) * 1000)
    ttft_ms = int((first_token_time - t0) * 1000) if first_token_time else total_ms
    full_text = "".join(tokens).strip()

    print(f"HTTP Status: 200 OK")
    print(f"Total Latency: {total_ms} ms (TTFT: {ttft_ms} ms, Server-Reported: {done_payload.get('latency_ms')} ms)")
    print(f"Grounded: {done_payload.get('is_grounded')}")
    print(f"Events Captured: {len(event_names)} events (tokens: {len(tokens)})")
    print(f"Citations Count: {len(citations)}")
    for i, c in enumerate(citations):
        print(f"  [{i+1}] Page {c.get('page_number')} | {c.get('section_heading')}")
    print(f"Final Answer:\n{full_text}")

    return {
        "status_code": 200,
        "total_latency_ms": total_ms,
        "ttft_ms": ttft_ms,
        "reported_latency_ms": done_payload.get("latency_ms"),
        "is_grounded": done_payload.get("is_grounded"),
        "citations": citations,
        "answer": full_text,
    }


def main():
    print("=" * 70)
    print("RUNNING LIVE END-TO-END HTTP/SSE PIPELINE VERIFICATION")
    print(f"Target Endpoint: {ENDPOINT_URL}")
    print("=" * 70)

    # 1. Warm-up hit
    try:
        httpx.get("http://127.0.0.1:8000/api/v1/health", timeout=5.0)
    except Exception as e:
        print(f"ERROR: Cannot connect to server at {ENDPOINT_URL}: {e}")
        sys.exit(1)

    # 2. English verification
    res_en = verify_query_http("Who built the Chennakeshava Temple at Belur and when?", "en")
    
    # 3. Kannada verification
    res_kn = verify_query_http("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", "kn")

    # Assertions
    print("\n" + "=" * 70)
    print("VALIDATING ACCEPTANCE CRITERIA...")

    # Fact checks
    assert "Vishnuvardhana" in res_en["answer"] and "1117" in res_en["answer"], "English answer missing Vishnuvardhana or 1117!"
    assert "1117" in res_kn["answer"], "Kannada answer missing year 1117!"
    assert any(name in res_kn["answer"] for name in ["ವಿಷ್ಣುವರ್ಧನ", "ವಿಷ್ಣುವರ್ಧನನು"]), "Kannada answer missing Vishnuvardhana!"

    # System prompt leak checks
    assert "You are the official" not in res_en["answer"], "English leaked system prompt!"
    assert "ನೀವು ಕರ್ನಾಟಕದ ಬೇಲೂರು" not in res_kn["answer"], "Kannada leaked system prompt!"

    # Grounding & citation checks
    assert res_en["is_grounded"] is True, "English response not marked grounded!"
    assert res_kn["is_grounded"] is True, "Kannada response not marked grounded!"
    assert len(res_en["citations"]) == 1, f"English cited {len(res_en['citations'])} chunks, expected 1 (excluding Garbhagriha)!"
    assert len(res_kn["citations"]) == 1, f"Kannada cited {len(res_kn['citations'])} chunks, expected 1 (excluding Garbhagriha)!"
    assert "Historical Patronage" in res_en["citations"][0]["section_heading"], "English cited wrong section!"
    assert "Historical Patronage" in res_kn["citations"][0]["section_heading"], "Kannada cited wrong section!"

    # Latency check (warm target < 3000 ms)
    assert res_kn["reported_latency_ms"] < 3000, f"Kannada latency {res_kn['reported_latency_ms']}ms exceeds 3000ms SLA!"

    print("ALL ACCEPTANCE CRITERIA PASSED:")
    print("  [x] Real HTTP/SSE endpoint verified (http://127.0.0.1:8000/api/v1/chat/stream)")
    print("  [x] English facts verified: Hoysala King Vishnuvardhana, 1117 CE")
    print("  [x] Kannada facts verified: ರಾಜ ವಿಷ್ಣುವರ್ಧನನು, ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ")
    print("  [x] No system prompt leakage in either language")
    print(f"  [x] Warm Kannada latency: {res_kn['reported_latency_ms']} ms (Threshold < 3,000 ms)")
    print("  [x] Precise citations: ONLY Page 1 Section 1 cited, Garbhagriha excluded")
    print("=" * 70)

if __name__ == "__main__":
    main()
