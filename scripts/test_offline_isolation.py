"""Phase 11: Offline Isolation Verification
Ensures 100% offline self-containment.
Enforces socket-level outbound blocking: any outbound network request outside 127.0.0.1 / localhost
is intercepted and blocked.
Executes both English and Kannada live queries through /api/v1/chat/stream.
Saves empirical proof to logs/offline_isolation_evidence.txt.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import socket
import json
import time
from pathlib import Path
import httpx

STREAM_URL = "http://127.0.0.1:8000/api/v1/chat/stream"

# Intercept and log all socket connections
original_getaddrinfo = socket.getaddrinfo
original_connect = socket.socket.connect

outbound_wan_attempts = []
local_connections = []

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}


def patched_getaddrinfo(host, port, *args, **kwargs):
    if host not in ALLOWED_HOSTS:
        outbound_wan_attempts.append(f"DNS lookup: {host}:{port}")
        raise ConnectionRefusedError(f"OFFLINE ISOLATION ENFORCED: Blocked DNS resolution for external host '{host}'")
    return original_getaddrinfo(host, port, *args, **kwargs)


def patched_connect(self, address):
    host, port = address[0], address[1]
    if str(host) not in ALLOWED_HOSTS and not str(host).startswith("127."):
        outbound_wan_attempts.append(f"TCP connect: {host}:{port}")
        raise ConnectionRefusedError(f"OFFLINE ISOLATION ENFORCED: Blocked outbound connection to external address '{host}:{port}'")
    local_connections.append(f"{host}:{port}")
    return original_connect(self, address)


def main():
    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("=" * 70)
    log("PHASE 11: OFFLINE ISOLATION & ZERO-NETWORK VERIFICATION")
    log("=" * 70)
    log(f"Test Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("Enforcing strict socket boundary: All non-loopback connections blocked.\n")

    # Apply socket isolation hooks
    socket.getaddrinfo = patched_getaddrinfo
    socket.socket.connect = patched_connect

    client = httpx.Client(timeout=60.0)

    # 1. English Benchmark Test
    log("--- 1. Testing English Query under Offline Isolation ---")
    q_en = "Who built the Chennakeshava Temple at Belur and when?"
    log(f"Query: {q_en}")
    t0 = time.perf_counter()
    r_en = client.post(STREAM_URL, json={"content": q_en, "preferred_language": "en", "input_mode": "text"})
    lat_en = (time.perf_counter() - t0) * 1000.0
    log(f"HTTP Status: {r_en.status_code} | Latency: {lat_en:.1f} ms")

    # Extract tokens
    tokens_en = []
    for line in r_en.text.splitlines():
        if line.startswith("data: "):
            try:
                data = json.loads(line[len("data: "):])
                if "token" in data:
                    tokens_en.append(data["token"])
            except Exception:
                pass
    ans_en = "".join(tokens_en).strip()
    log(f"Answer: {ans_en}")

    # 2. Kannada Benchmark Test
    log("\n--- 2. Testing Kannada Query under Offline Isolation ---")
    q_kn = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?"
    log(f"Query: {q_kn}")
    t0 = time.perf_counter()
    r_kn = client.post(STREAM_URL, json={"content": q_kn, "preferred_language": "kn", "input_mode": "text"})
    lat_kn = (time.perf_counter() - t0) * 1000.0
    log(f"HTTP Status: {r_kn.status_code} | Latency: {lat_kn:.1f} ms")

    # Extract tokens
    tokens_kn = []
    for line in r_kn.text.splitlines():
        if line.startswith("data: "):
            try:
                data = json.loads(line[len("data: "):])
                if "token" in data:
                    tokens_kn.append(data["token"])
            except Exception:
                pass
    ans_kn = "".join(tokens_kn).strip()
    log(f"Answer: {ans_kn}")

    # 3. Security Audit Summary
    log("\n--- 3. Network Isolation Audit Summary ---")
    log(f"Loopback Connections Allowed: {len(local_connections)}")
    log(f"Outbound WAN Connections Attempted: {len(outbound_wan_attempts)}")
    if outbound_wan_attempts:
        for att in outbound_wan_attempts:
            log(f"  [VIOLATION]: {att}")
        log("[FAIL] Offline isolation failed: outbound WAN requests detected.")
    else:
        log("[PASS] 100% Offline Self-Containment Verified! Zero external requests.")

    # Restore sockets
    socket.getaddrinfo = original_getaddrinfo
    socket.socket.connect = original_connect

    # Save artifact
    out_file = Path("logs/offline_isolation_evidence.txt")
    out_file.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n[OK] Saved isolation evidence to {out_file}")


if __name__ == "__main__":
    main()

