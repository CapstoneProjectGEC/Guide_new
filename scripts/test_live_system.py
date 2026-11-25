"""Empirical validation script for running services."""

import sys
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=== STARTING EMPIRICAL VALIDATION SUITE ===\n")

# 1. Health Probe
print("1. Testing Backend /health ...")
r = httpx.get("http://127.0.0.1:8000/health", timeout=10.0)
assert r.status_code == 200, f"Health failed: {r.status_code}"
data = r.json()
assert data["status"] == "healthy"
assert data["components"]["database"]["status"] == "healthy"
print(f"   [PASS] Status: healthy, DB latency: {data['components']['database']['latency_ms']}ms, STT Device: {data['components']['speech_to_text']['device']}")

# 2. Frontend Server
print("2. Testing Frontend HTML delivery on http://127.0.0.1:3000 ...")
r_fe = httpx.get("http://127.0.0.1:3000/", timeout=10.0)
assert r_fe.status_code == 200
assert "html" in r_fe.text.lower()
print("   [PASS] Frontend delivered React HTML index")

# 3. Frontend to Backend Proxy
print("3. Testing Vite API Reverse Proxy on http://127.0.0.1:3000/api/v1/health ...")
r_proxy = httpx.get("http://127.0.0.1:3000/api/v1/health", timeout=10.0)
assert r_proxy.status_code == 200
print(f"   [PASS] Vite proxy forwarded /api successfully (status {r_proxy.status_code})")

# 4. Admin Auth
print("4. Testing Admin Auth (/api/v1/auth/login) ...")
r_auth = httpx.post("http://127.0.0.1:8000/api/v1/auth/login", json={"username": "admin", "password": "AdminPassword123!"}, timeout=10.0)
assert r_auth.status_code == 200, f"Login failed: {r_auth.status_code}"
auth_data = r_auth.json()
token = auth_data["access_token"]
assert token and auth_data["role"] == "SUPER_ADMIN"
print(f"   [PASS] SuperAdmin authenticated (token length: {len(token)}, role: {auth_data['role']})")

# 5. Admin Knowledge Generations
print("5. Testing Admin Knowledge Generations list ...")
r_gen = httpx.get("http://127.0.0.1:8000/api/v1/admin/knowledge/generations", headers={"Authorization": f"Bearer {token}"}, timeout=10.0)
assert r_gen.status_code == 200
gen_data = r_gen.json()
active_id = gen_data.get("active_generation_id")
print(f"   [PASS] Total generations: {gen_data['total']}, Active generation ID: {active_id}")

# 6. Tourist Grounded Chat (English)
print("6. Testing Tourist RAG Chat (English query) ...")
r_chat = httpx.post("http://127.0.0.1:8000/api/v1/chat/message", json={"content": "Who commissioned the Chennakeshava Temple at Belur?"}, timeout=30.0)
assert r_chat.status_code == 200
chat_res = r_chat.json()
assert chat_res["is_grounded"] is True
assert len(chat_res["citations"]) > 0
print(f"   [PASS] English RAG answer returned in {chat_res['latency_ms']}ms with {len(chat_res['citations'])} citation(s)")
snippet = chat_res['content'][:110].replace('\n', ' ')
print(f"          Snippet: \"{snippet}...\"")

# 7. Out-of-Domain Canonical Fallback Guard
print("7. Testing Grounding Guard Fallback (Out-of-Domain query) ...")
r_guard = httpx.post("http://127.0.0.1:8000/api/v1/chat/message", json={"content": "How do I make chocolate ice cream and pizza dough at home?"}, timeout=30.0)
assert r_guard.status_code == 200
guard_res = r_guard.json()
assert guard_res["is_grounded"] is False
assert guard_res["content"] == "Information is not available in the knowledge base."
print(f"   [PASS] Grounding guard triggered in {guard_res['latency_ms']}ms with canonical message: \"{guard_res['content']}\"")

# 8. Offline Voice Synthesis
print("8. Testing Piper TTS Audio Synthesis (/api/v1/voice/synthesize) ...")
r_tts = httpx.post("http://127.0.0.1:8000/api/v1/voice/synthesize", json={"text": "Welcome to Karnataka tourism.", "language": "en"}, timeout=20.0)
assert r_tts.status_code == 200
assert r_tts.headers.get("content-type") == "audio/wav"
assert len(r_tts.content) > 1000
print(f"   [PASS] Synthesized WAV audio received ({len(r_tts.content)} bytes, Content-Type: {r_tts.headers.get('content-type')})")

print("\n=== ALL 8 EMPIRICAL VALIDATION CHECKS PASSED PERFECTLY! ===")
