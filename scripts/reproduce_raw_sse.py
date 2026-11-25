"""Send raw HTTP/SSE requests to running FastAPI server and record raw streams."""

import sys
import os
import time
import httpx

sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")

URL = "http://127.0.0.1:8000/api/v1/chat/stream"

def test_endpoint(payload: dict, output_path: str):
    print(f"\n--- Testing Endpoint: {URL} ---")
    print(f"Payload: {payload}")
    t0 = time.perf_counter()

    raw_events = []
    with httpx.Client(timeout=60.0) as client:
        with client.stream("POST", URL, json=payload, headers={"Accept": "text/event-stream"}) as response:
            t_connect = time.perf_counter()
            print(f"HTTP Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Connection Time: {(t_connect - t0)*1000:.2f} ms")

            for chunk in response.iter_raw():
                raw_events.append(chunk)

    t_end = time.perf_counter()
    total_ms = (t_end - t0) * 1000
    print(f"Total Request Duration: {total_ms:.2f} ms")

    full_raw = b"".join(raw_events).decode("utf-8", errors="replace")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_raw)
    print(f"Saved raw SSE to {output_path} ({len(full_raw)} bytes)")

    # Print summary of lines
    print("--- RAW SSE OUTPUT PREVIEW ---")
    for line in full_raw.splitlines()[:20]:
        print(line)
    if len(full_raw.splitlines()) > 20:
        print("... (truncated preview)")

if __name__ == "__main__":
    # 1. English Reference Test
    en_payload = {
        "content": "Who built the Chennakeshava Temple at Belur and when?",
        "preferred_language": "en",
        "input_mode": "text"
    }
    test_endpoint(en_payload, "logs/english_raw_sse.txt")

    # 2. Kannada Reference Test
    kn_payload = {
        "content": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?",
        "preferred_language": "kn",
        "input_mode": "text"
    }
    test_endpoint(kn_payload, "logs/kannada_raw_sse.txt")

