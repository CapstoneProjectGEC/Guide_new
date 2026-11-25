import httpx
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

def test_query(question: str, lang: str):
    print("=" * 60)
    print(f"Testing [{lang}]: {question}")
    payload = {
        "content": question,
        "preferred_language": lang,
        "input_mode": "text"
    }

    t0 = time.perf_counter()
    tokens = []
    citations = []
    done_payload = {}

    with httpx.Client(timeout=30.0) as client:
        with client.stream("POST", "http://127.0.0.1:8000/api/v1/chat/stream", json=payload) as response:
            status = response.status_code
            first_token_time = None
            for line in response.iter_lines():
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        if "token" in data:
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            tokens.append(data["token"])
                        if "citations" in data:
                            citations = data["citations"]
                        if "is_grounded" in data:
                            done_payload = data
                    except Exception as e:
                        pass
    t1 = time.perf_counter()
    total_ms = int((t1 - t0) * 1000)
    ttft_ms = int((first_token_time - t0) * 1000) if first_token_time else None

    print(f"HTTP Status: {status}")
    print(f"Total Latency: {total_ms} ms (TTFT: {ttft_ms} ms, Reported: {done_payload.get('latency_ms')} ms)")
    print(f"Grounded: {done_payload.get('is_grounded')}")
    print(f"Citations ({len(citations)}):")
    for c in citations:
        print(f"  * Page {c.get('page_number')}: {c.get('section_heading')}")
    print(f"Answer:\n{''.join(tokens).strip()}")
    print("=" * 60)

if __name__ == "__main__":
    # Test 1: English
    test_query("Who built the Chennakeshava Temple at Belur and when?", "en")
    # Test 2: Kannada
    test_query("ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", "kn")

