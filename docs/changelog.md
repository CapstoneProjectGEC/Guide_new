# CHANGELOG

All notable changes to the **AI-Powered Smart Tourist Guide Platform for Karnataka** will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.16.0] - 2026-10-13 (CHECKPOINT-P16)

### Added
- **Incremental UTF-8 SSE Decoding Verification (`backend/tests/integration/test_sse_utf8.py`, `tests/integration/test_sse_utf8.py`)**:
  - Validated incremental UTF-8 character reconstruction across byte chunk boundaries with arbitrary chunk sizes (`[1, 2, 5, 3, 7]` bytes) for Kannada text (`ಹೊಯ್ಸಳರ ವಾಸ್ತುಶಿಲ್ಪ ಅದ್ಭುತವಾಗಿದೆ.`), verifying zero replacement characters (`\ufffd`).
  - Tested SSE event reconstruction for multi-event split buffers across chunk borders.
- **Comprehensive End-to-End Integration Test Suite (`tests/integration/test_e2e_workflow.py`)**:
  - `test_e2e_sse_stream_kannada_utf8_token_chunks`: Live FastAPI `/api/v1/chat/stream` SSE stream validation for Kannada queries.
  - `test_e2e_auth_token_rotation_and_old_token_reuse_rejected`: Validated that after refresh token rotation, reusing the old refresh token is immediately rejected with HTTP 401.
  - `test_e2e_auth_logout_server_side_invalidation`: Validated server-side JTI revocation upon `POST /api/v1/auth/logout`, invalidating both access and refresh tokens.
  - `test_e2e_rbac_endpoint_authorization_enforced`: Validated strict RBAC HTTP 401/403 status codes across roles (`VIEWER`, `SITE_CURATOR`, `SUPER_ADMIN`).
  - `test_e2e_citations_reference_real_retrieved_chunks`: Verified that generated answer citations are a strict subset of retrieved knowledge chunks, and each cited chunk has valid document metadata.
  - `test_e2e_grounding_unsupported_questions_trigger_canonical_fallback`: Verified that queries completely outside Belur Chennakeshava domain return canonical fallback with zero hallucination.
  - `test_e2e_generation_rollback_immediate_retrieval_switch`: Verified atomic rollback switching active generation pointer and immediate retrieval binding without restarting FastAPI or Ollama.
  - `test_e2e_voice_audio_mime_validation_and_stt`: Verified MIME type validation, rejection of non-audio files, silence handling, and latency metrics in faster-whisper STT.
  - `test_e2e_voice_tts_piper_synthesis_headers_and_wav_format`: Verified local Piper TTS binary WAV format (RIFF, WAVEfmt headers), `X-TTS-Engine: piper`, and latency/duration telemetry headers.

### Security
- **Server-Side Token Revocation Registry (`backend/src/core/security.py`)**:
  - Added in-memory token revocation store tracking revoked token JTIs (`revoke_token`, `is_token_revoked`, `clear_revoked_tokens`).
  - Integrated revocation checks into `decode_token()` to prevent token reuse even before natural expiration.
  - Updated `POST /api/v1/auth/refresh` to revoke rotated refresh token JTIs.
  - Updated `POST /api/v1/auth/logout` to revoke both access token and refresh token JTIs server-side.

## [0.15.0] - 2026-10-13 (CHECKPOINT-P15)

### Added
- **Secure In-Memory Admin Authentication & Session Management (`frontend/src/services/auth.ts`)**:
  - Implemented strictly in-memory JWT authentication lifecycle (`authService`) with zero tokens written to `localStorage`, `sessionStorage`, or client cookies.
  - Full RBAC role hierarchy matching backend FastAPI policies: `SUPER_ADMIN` (4) > `SITE_CURATOR` (3) > `OPERATOR` (2) > `VIEWER` (1).
  - Rotating refresh token lifecycle handling silent re-authentication on token expiration.
  - Reactive subscription listener notifying UI components on authentication transitions.
  - Explicit logout invoking `/api/v1/auth/logout` with Bearer auth and complete memory cleanup.
- **Typed Administrative API Gateway Client (`frontend/src/services/adminApi.ts`)**:
  - Type-safe integration covering `/api/v1/auth/*`, `/api/v1/admin/documents/*`, `/api/v1/admin/knowledge/generations/*`, `/api/v1/admin/sync/*`, `/api/v1/admin/diagnostics/*`, and `/api/v1/health`.
  - Automatic `Authorization: Bearer <token>` attachment with seamless 401 retry and refresh rotation.
  - Unified `ErrorEnvelope` handling throwing typed `AdminApiError` with detailed codes and correlation IDs.
- **Heritage Administrative Portal Shell & Login (`frontend/src/features/admin/AdminLogin.tsx` & `AdminDashboard.tsx`)**:
  - `AdminLogin`: Accessible WCAG-compliant login form with field validation, zero-storage protocol disclosure banner, and seamless return to tourist mode.
  - `AdminDashboard`: Responsive administrative shell reusing Karnataka Heritage design tokens (Temple Gold `#D4AF37`, Heritage Brown `#2C1810`, Midnight Basalt `#120E0C`), display of authenticated admin username and role badge, role-aware tab navigation, and logout action.
- **Heritage Document Management (`frontend/src/features/admin/DocumentManager.tsx`)**:
  - Paginated document archive table displaying filename, page count, file size (formatted KB/MB), truncated SHA-256 digest with copy-to-clipboard, and ingestion date.
  - Client-side validation enforcing authentic `.pdf` extensions and maximum 50MB file size ceiling.
  - Binary PDF streaming download trigger via object URL.
  - Protected document deletion requiring explicit confirmation dialog and `SITE_CURATOR` privilege.
- **Knowledge Pipeline & Generation Management (`frontend/src/features/admin/GenerationManager.tsx`)**:
  - Reverse chronological generations list with radiant gold active generation highlight.
  - Expandable 6-step pipeline execution stepper (`PARSE`, `CHUNK`, `EMBED`, `INDEX`, `VALIDATE`, `PROMOTE`) displaying progress percentage and step errors.
  - Trigger Generation Build button (`SITE_CURATOR+`) with bounded polling (every 3s, max 30 iterations) and unmount cleanup.
  - Promotion to active state for non-active generations.
  - Instant Rollback modal dialog with target generation selector and atomic pointer update (<100ms).
- **Model Registry Synchronization (`frontend/src/features/admin/ModelSyncTab.tsx`)**:
  - Inspection and synchronization cards for offline Piper TTS voices (`voice_registry`) and Argos neural translation packages (`translation_registry`).
  - Strict air-gapped offline operation: reconciles local disk models into MySQL without external internet requests.
  - Restricted to `OPERATOR+` roles with feedback banners showing reconciled counts and admin identity.
- **Hybrid RAG Retrieval Diagnostics (`frontend/src/features/admin/DiagnosticsTab.tsx`)**:
  - Administrative test probe tool evaluating user search queries with configurable hyperparameters (`top_dense`, `top_sparse`, `top_fused`, `top_final`, `score_threshold`).
  - Stage-by-stage candidate inspector displaying ChromaDB dense cosine scores, BM25 sparse lexical scores, RRF fusion ranks, and Cross-Encoder confidence cutoff flags.
  - Granular latency profiling cards reporting milliseconds across dense, sparse, fusion, reranking, and total search.
- **Real-Time Telemetry & Subsystem Health (`frontend/src/features/admin/OverviewTab.tsx`)**:
  - Live system status cards based strictly on verified `/api/v1/health` and `/api/v1/admin/sync/status` endpoints (Gateway API, Relational DB, Active Generation, Document count).
  - Subsystem readiness matrix reporting faster-whisper STT, Piper TTS, and Argos translation states with zero fabricated graphs.
- **Comprehensive Automated Test Suite (`frontend/src/tests/adminAuth.test.ts`, `adminApi.test.ts`, `adminComponents.test.tsx`)**:
  - 24 new automated frontend tests (41 frontend tests total) covering in-memory auth, zero localStorage footprint, role hierarchy, 401 refresh retry, document upload/download/delete, pipeline build/rollback, model sync, diagnostics, and tab navigation.
  - 100% test pass rate across 106 backend tests and 41 frontend tests (147 total repo automated tests).

## [0.14.0] - 2026-10-13 (CHECKPOINT-P14)

### Added
- **Production React 19 Frontend Application (`frontend/`)**:
  - Scaffolded modern React 19 + TypeScript + Vite 6 + Tailwind CSS architecture with strict type checking.
  - Implemented the complete Karnataka Heritage design system from `Design.md` with Hoysala theme tokens (Temple Gold `#D4AF37`, Heritage Brown `#2C1810`, Soapstone Grey `#4A4A4A`, Ivory `#FDFBF7`, Midnight Basalt `#120E0C`, Sandstone, and Marble).
  - Integrated full light and dark mode toggles with WCAG 2.1 AA accessible contrast ratios and visible keyboard focus rings.
  - Supported `prefers-reduced-motion` to disable animations for motion-sensitive users.
- **Multilingual Tourist Conversational Interface (`frontend/src/features/chat/`)**:
  - Real-time SSE streaming reader with multibyte UTF-8 decoding resilience, preserving Kannada script across arbitrary network chunk boundaries.
  - Automatic fallback, graceful error banner handling, and clean `AbortController` cancellation.
  - Full Unicode Kannada text input, rendering, and language switching toggle (`ಕನ್ನಡ` / `English`).
  - Welcoming landing view explaining verified grounding rules, with curated heritage inquiry cards (History, Architecture, Sculptures, Queen Shantala Devi).
  - Interactive citation pill badges (`[Source: 1: p.4]`) linked to verified document chunks.
- **Offline Voice Interaction & Canvas Frequency Visualizer (`frontend/src/features/voice/`)**:
  - Browser microphone capture via HTML5 `MediaRecorder` API with echo cancellation, noise suppression, and MIME format negotiation.
  - Real-time 28-bar canvas frequency wave visualizer styled in radiant gold (`#D4AF37` / `#E5C058`).
  - Integrated faster-whisper STT transcription (`/api/v1/voice/transcribe`) with silence handling and automatic conversational dispatch.
  - Integrated Piper offline TTS synthesis (`/api/v1/voice/synthesize`) with binary `audio/wav` blob decoding and audio playback controls.
- **Side Panels & Spatial Exploration (`frontend/src/features/`)**:
  - `CitationDrawer`: Slide-over panel displaying document filename, page number, relevance match score (%), and verbatim knowledge chunk excerpt.
  - `TourismMap`: Interactive architectural precinct map of the Belur Chennakeshava Jagati platform featuring 5 key Hoysala monuments with geo-coordinates and quick inquiry triggers.
  - `Sidebar`: Session management, offline assurance guarantee, and temple attraction catalog.
- **Typed API Gateway Client (`frontend/src/services/api.ts`)**:
  - Typed integration covering `/api/v1` chat, sessions, voice STT, TTS, translation, and health endpoints with structured `ErrorEnvelope` parsing.
- **Automated Frontend Test Suite (`frontend/src/tests/`)**:
  - 17 unit and component tests with Vitest and React Testing Library covering SSE chunk boundaries, Kannada multibyte encoding, error handling, abort cancellation, API contracts, and accessibility interactions.
  - Zero build warnings; production bundle size: 285 kB JS (85 kB gzip), 27 kB CSS.

## [0.13.0] - 2026-10-13 (CHECKPOINT-P13)

### Added
- **Unified `/api/v1` Gateway Router Composition (`backend/src/presentation/router.py`)**:
  - Consolidated all tourist and admin endpoints under a canonical `/api/v1` prefix via FastAPI APIRouter composition.
  - Organized route topology into clean functional domains: Health Probes, Tourist Chat, Tourist Voice STT/TTS, Translation & Cross-Lingual RAG, Admin Authentication, Admin Documents, Admin Knowledge Pipeline, Admin Diagnostics, and Admin Management Synchronization.
  - Defined comprehensive `GATEWAY_TAGS_METADATA` establishing clear tag groups, descriptions, and BearerAuth security schemes across `/docs`, `/redoc`, and `/openapi.json`.
- **In-Memory Sliding-Window Rate Limiting (`backend/src/core/limiter.py` & `backend/src/core/middleware.py`)**:
  - Implemented thread-safe `RateLimiter` utilizing monotonic clock (`time.monotonic()`) preventing NTP drift vulnerabilities.
  - Configured default quotas: **60 requests/min** for anonymous tourists, **120 requests/min** for authenticated admins (`RATE_LIMIT_TOURIST_RPM` and `RATE_LIMIT_ADMIN_RPM`).
  - Implemented anti-spoofing security: client-supplied role headers (`X-Role`, `X-Admin`, `X-User-Type`) are strictly ignored. Admin status is granted exclusively through verified JWT Bearer tokens via `decode_token()`.
  - Implemented trusted proxy verification: `X-Forwarded-For` is only parsed when the direct peer socket is in `TRUSTED_PROXIES` (e.g. `127.0.0.1`, `::1`, `localhost`). Untrusted client IPs are directly bound to peer socket host.
  - Returns structured HTTP 429 response via `ErrorEnvelope` with `code: "RATE_LIMIT_EXCEEDED"`, `Retry-After`, and `X-RateLimit-*` headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).
  - Added periodic pruning of stale timestamps and hard ceiling eviction (`RATE_LIMIT_MAX_TRACKED_CLIENTS=10000`) to guarantee bounded memory.
  - Documented per-process local enforcement semantics: limits apply per server worker process and reset on application restart; no external Redis or cloud dependencies needed.
- **Health & Readiness Probes (`backend/src/presentation/api/health.py`)**:
  - Refined `/api/v1/health` and added dedicated `/api/v1/health/live` (shallow liveness check for orchestrator uptime) and `/api/v1/health/ready` (deep readiness check inspecting MySQL database, ChromaDB vector store, and optional local AI engines STT/TTS/Translation).
  - Preserved root `/health` container orchestrator alias for Docker/Kubernetes backward compatibility.
  - Health and OpenAPI documentation endpoints explicitly exempt from rate limiting.
- **Admin Management Synchronization Router (`backend/src/presentation/api/admin_sync.py`)**:
  - Added secure RBAC-protected administrative synchronization endpoints:
    - `POST /api/v1/admin/sync/voice`: Discovers local Piper TTS models and synchronizes `voice_registry`.
    - `POST /api/v1/admin/sync/translation`: Discovers local Argos Translate packages and synchronizes `translation_registry`.
    - `GET /api/v1/admin/sync/status`: Reports combined voice and translation model disk discovery status.
  - Protected by `get_current_active_admin` with `AdminRole.OPERATOR` (write sync) and `AdminRole.VIEWER` (read status).
- **CORS Hardening & Configuration (`backend/src/core/config.py` & `backend/src/main.py`)**:
  - Added `cors_allow_credentials` property that strictly disallows permissive wildcard origins (`*`) when credentials are enabled (`allow_credentials=True`), preventing CORS credential leakage.
  - Bound CORS middleware to configured explicit origins.
- **Automated Gateway Test Suite (`tests/unit/test_unified_gateway.py`)**:
  - Authored 13 automated unit and integration tests verifying route inventory under `/api/v1`, OpenAPI schema and security schemes, tourist 60 RPM rate limit enforcement, admin 120 RPM quota, anti-spoofing header rejection, trusted proxy handling, health probe exemption, monotonic window expiration, SSE stream pass-through, audio WAV streaming headers, admin sync authentication (401), and CORS credentials policy.
  - Total repository test suite expanded from 93 to 106 tests (100% pass rate in 38.62s, zero regressions).

## [0.12.0] - 2026-10-13 (CHECKPOINT-P12)

### Added
- **Local Offline Speech Synthesis Engine (`backend/src/infrastructure/audio/piper_engine.py`)**:
  - Implemented thread-safe `PiperEngine` adapter integrating `piper-tts` (v1.8.0) and ONNX Runtime (v1.31.0) on CPU.
  - Zero added GPU VRAM footprint, leaving all 8GB VRAM headroom available for Ollama (`gemma3:4b` resident).
  - Provisioned and verified real offline voices:
    - English (`en_US-lessac-medium.onnx`, 63.2 MB, 22050 Hz, LibriTTS / Public Domain).
    - Kannada (`kn_IN-syspin_male-medium.onnx`, 63.5 MB, 22050 Hz, IISc Bangalore SYSPIN dataset, Apache-2.0 / open license).
  - Implemented model session reuse with per-voice mutex locking for safe concurrency across thread pools.
  - Graceful degradation: reports clean errors or client fallback hints if models are absent or service disabled.
- **In-Memory LRU Audio Cache (`backend/src/infrastructure/audio/tts_cache.py`)**:
  - Built bounded thread-safe LRU cache (128 entries default) for frequent short phrases (canonical grounding fallbacks, greetings, silence warnings <= 150 chars).
  - Normalizes text (Unicode NFKC, whitespace strip, lowercase for English) for deterministic keying.
  - In-flight request deduplication preventing duplicate concurrent CPU synthesis of identical queries.
  - Delivers **0.10ms - 0.16ms** instantaneous sub-millisecond cache hit responses.
- **Application Speech Synthesis Service (`backend/src/application/voice/tts_service.py`)**:
  - Coordinates input validation (rejects blank strings, enforces 1000-character ceiling).
  - Implemented automatic script-level language fallback (`LanguageDetector`) when explicit language hints are absent.
  - Offloads blocking ONNX CPU inference to bounded thread pool (`asyncio.to_thread`) with 15-second timeout guard.
  - Never modifies or generates temple facts; synthesizes verbatim answers already validated by GroundingGuard.
  - Structured operational telemetry recording latency, duration, audio bytes, and cache hit/miss without logging sensitive full user text.
- **Public Voice REST Endpoints (`backend/src/presentation/api/voice.py`)**:
  - `POST /api/v1/voice/synthesize`: Zero-auth public endpoint returning standard playable `audio/wav` with `Content-Disposition: inline`, `X-TTS-Engine`, `X-TTS-Language`, `X-TTS-Voice`, `X-TTS-Latency-Ms`, `X-TTS-Cached`, and `X-TTS-Fallback-Recommended` headers.
  - `GET /api/v1/voice/tts/status`: Operational probe reporting active voices, sample rate, and LRU cache statistics.
  - `GET /api/v1/voice/tts/voices`: Discovered voice catalog with model paths and disk availability.
  - `POST /api/v1/voice/tts/sync`: Relational database synchronization into MySQL `voice_registry` table.
- **Configuration & Typed Errors (`backend/src/core/config.py` & `backend/src/core/errors.py`)**:
  - Added `TTS_ENABLED`, `TTS_ENGINE`, `TTS_MODELS_DIR`, `TTS_VOICE_EN`, `TTS_VOICE_KN`, `TTS_MAX_TEXT_LENGTH`, `TTS_CACHE_MAX_ENTRIES`, `TTS_TIMEOUT_SECONDS`, `TTS_USE_CUDA`.
  - Added typed exceptions: `TTSValidationError` (HTTP 400), `TTSTooLargeError` (HTTP 413), `TTSUnavailableError` (HTTP 503), `TTSTimeoutError` (HTTP 504).
- **Provisioning & Benchmark Tooling (`scripts/download_tts_models.py` & `scripts/benchmark_tts_phase12.py`)**:
  - Repeatable provisioning script with SHA/size verification and offline CPU test synthesis.
  - Repeatable local benchmark suite evaluating warm latency, audio duration, RTF, cache hits, and 5-request concurrency.
- **Automated Test Suite (`tests/unit/test_voice_tts.py`)**:
  - Added 20 comprehensive unit, integration, and smoke tests (mocked engine, validation, timeout, concurrency, cache eviction, real local models, and existing STT/chat regression verification).
  - Test suite expanded from 73 to 93 tests (100% pass rate in 33.51s, zero regressions).

---

## [0.11.0] - 2026-10-12 (CHECKPOINT-P11)

### Added
- **Cross-Lingual Query Normalization (`backend/src/application/translation/query_normalizer.py`)**:
  - Engineered high-precision query normalizer converting non-English tourist queries (Kannada, mixed-language) into optimized English retrieval queries for dense `all-MiniLM-L6-v2` and sparse `BM25` search.
  - Implemented zero-overhead passthrough for pure English queries (0.014ms latency, zero mutation).
  - Preserved original verbatim Kannada queries for tourist conversational turn tracking, session history, and LLM Kannada prompt generation while executing retrieval with normalized terms.
- **Belur Temple Heritage Glossary & Intent Expander (`backend/src/application/translation/heritage_glossary.py`)**:
  - Authored canonical dictionary of 30+ Belur heritage entities (Belur, Chennakeshava, Vishnuvardhana, Shantala Devi, Madanika, Darpana Sundari, Natya Mohini, Jakanachari, Hoysala, Garbhagriha, Navaranga, Pushkarani, Soapstone, etc.) with synonyms.
  - Built proper-noun masking and unmasking mechanism protecting cultural terms from neural translation corruption.
  - Added query intent expansion mapping Kannada interrogatives ("ಯಾರು ಕಟ್ಟಿಸಿದರು", "ವಾಸ್ತುಶಿಲ್ಪ", "ಎಲ್ಲಿದೆ", "ಪ್ರವೇಶ ಶುಲ್ಕ") to semantic retrieval anchors without introducing answer bias.
- **Offline Argos Translation Engine (`backend/src/infrastructure/translation/argos_engine.py`)**:
  - Implemented thread-safe local Argos Translate runtime manager with package directory discovery (`data/models/argos`).
  - Added graceful fallback returning `None` if specific language pairs are not installed, allowing seamless fallback to deterministic domain translation.
- **Phonetic Transliteration Module (`backend/src/application/translation/transliteration.py`)**:
  - Implemented deterministic Kannada-to-Latin transliterator strictly distinguishing phonetic script conversion (`"deevaalaya"`) from semantic translation (`"temple"`).
  - Used for preserving unknown out-of-domain terms (e.g. `"maisooru"`) so the hybrid retriever and cross-encoder can reject them cleanly without false positives.
- **Translation REST & Synchronization Endpoints (`backend/src/presentation/api/translation.py`)**:
  - Exposed `GET /api/v1/translation/status` reporting active translation engine, installed packages, and glossary statistics.
  - Exposed `POST /api/v1/translation/normalize` providing query diagnostic normalization.
  - Exposed `POST /api/v1/translation/sync` syncing installed model packages to MySQL `translation_registry`.
- **RAG & Conversation Integration (`backend/src/application/chat/conversation_manager.py`)**:
  - Wired `QueryNormalizer` into both synchronous `/api/v1/chat/message` and streaming `/api/v1/chat/stream`.
  - Guaranteed `GroundingGuard` confidence threshold (>0.35) remains strictly enforced, preventing hallucinations on unsupported or out-of-domain queries.
- **Repeatable Local Benchmark Suite (`scripts/benchmark_retrieval_phase11.py`)**:
  - Created automated benchmark evaluating English, Kannada, mixed, and out-of-domain retrieval quality, top chunk scores, grounding guard verdicts, and latency.
- **Automated Test Suite (`tests/unit/test_translation_hardening.py`)**:
  - Added 13 tests covering glossary masking/unmasking, transliteration distinction, English passthrough, Kannada query expansion, mixed queries, empty inputs, offline model unavailability fallback, database sync, REST endpoints, end-to-end grounded retrieval, out-of-domain fallback, and SSE event streaming.
  - Test suite expanded from 60 to 73 tests (100% pass rate in 26.74s).

---

## [0.10.0] - 2026-10-12 (CHECKPOINT-P10)

### Added
- **Local Speech-To-Text Engine (`backend/src/infrastructure/audio/whisper_engine.py`)**:
  - Implemented thread-safe `WhisperEngine` integrating `faster-whisper` (v1.2.1) and `ctranslate2` (v4.8.2) with the `base` model (74M parameters, 145 MB).
  - Built Windows CUDA 12 runtime DLL auto-discovery (`cublas64_12.dll` via local Ollama directory) enabling native GPU execution on NVIDIA GeForce RTX 3050 with `float16` precision.
  - Implemented automatic, verified hardware fallback to CPU with `int8` quantization and configurable thread concurrency (`WHISPER_CPU_THREADS=4`).
- **Audio Validation & Signal Normalization (`backend/src/application/voice/stt_service.py`)**:
  - Engineered audio payload validator supporting WebM, WAV, MP3, OGG, and M4A with 25 MB payload ceiling, magic byte checking, and duration guardrails (0.3s - 60.0s).
  - In-memory decoding and resampling to 16kHz mono float32 PCM using `av` (PyAV v13.1.0) and `soundfile` with zero disk overhead.
  - Implemented RMS energy silence shortcut (<0.002 RMS) detecting silent audio in ~37ms, preventing model hallucination.
  - Integrated Silero VAD filtering to handle ambient background noise without crash.
- **Voice REST & SSE Streaming Endpoints (`backend/src/presentation/api/voice.py`)**:
  - Exposed `GET /api/v1/voice/info` returning hardware, device, compute type, and audio format capabilities.
  - Exposed `POST /api/v1/voice/transcribe` returning speech transcript, detected language, confidence, timestamps, and latency.
  - Exposed `POST /api/v1/voice/chat` connecting voice queries directly to the grounded conversational RAG engine with `input_mode="voice"`.
  - Exposed `POST /api/v1/voice/stream` streaming `transcript`, `citations`, `token`, and `done` events over SSE.
- **Typed Audio Domain Errors (`backend/src/core/errors.py`)**:
  - Added `AudioValidationError` (HTTP 400), `AudioTooLargeError` (HTTP 413), and `AudioTimeoutError` (HTTP 504).
- **Automated Test Suite & Audio Fixtures (`tests/unit/test_voice_stt.py` & `tests/fixtures/audio/*`)**:
  - Created 15 unit and integration tests covering English, Kannada, mixed audio, silence shortcut, noise filtering, boundary conditions, malformed uploads, and end-to-end voice streaming.
  - Test suite expanded from 45 to 60 tests (100% pass rate in 25.35s).

---

## [0.9.0] - 2026-10-09 (CHECKPOINT-P9)

### Added
- **Local Ollama LLM Async Integration (`backend/src/infrastructure/llm/ollama_client.py`)**:
  - Engineered asynchronous client for local Ollama daemon (`http://127.0.0.1:11434`) using bounded connection pooling (`httpx.AsyncClient`).
  - Added cancellation handling with `asyncio.CancelledError`, NDJSON stream decoding, keep_alive parameter conversion, and generation timeout guards.
  - Lifecycle integration hooks into FastAPI `lifespan` for clean HTTP client teardown on process exit.
- **Budget-Enforced Prompt Builder (`backend/src/application/chat/prompt_builder.py`)**:
  - Structured prompt compiler enforcing 1500-token ceiling to minimize prefill latency.
  - Strict system prompt enforcement for English and Kannada (`ಕನ್ನಡ`) with verbatim fallback instructions.
  - Formatted chunk context with document metadata provenance (`Page X | Section Y`) and condensed turn history.
- **Server-Sent Events (SSE) Streaming Endpoint (`backend/src/presentation/api/chat.py` & `conversation_manager.py`)**:
  - Mounted `POST /api/v1/chat/stream` delivering `citations`, `token`, and `done` events over SSE.
  - Implemented zero-token ungrounded bypass: queries failing grounding guard immediately short-circuit to canonical fallback without invoking LLM, saving GPU cycles and responding in ~105ms.
  - Emits UTF-8 native Kannada script tokens without Unicode escaping (`ensure_ascii=False`).
  - Added upstream outage fallback: if Ollama is unreachable, gracefully streams verified ground truth knowledge base excerpts.
- **Frontend Streaming Client (`frontend/src/services/streaming.ts`)**:
  - Implemented React SSE stream reader with multibyte UTF-8 incremental decoder (`TextDecoder("utf-8", { stream: true })`) preventing character corruption across arbitrary TCP chunk boundaries.
  - Supports streaming callbacks (`onToken`, `onCitations`, `onDone`, `onError`), abort signals, and buffer splitting.
- **Empirical RAG Benchmark Suite (`scripts/benchmark_rag.py`)**:
  - Created reproducible benchmark runner testing 7 representative queries (English, Kannada, follow-up, architecture, unsupported, adversarial).
  - Evaluates cold-start vs warm TTFT, tokens/sec throughput, grounding accuracy, and concurrency (1 and 2 simultaneous requests).
- **Automated Regression Test Suite (`tests/unit/test_ollama_streaming.py`)**:
  - Added 7 tests covering Ollama configuration, prompt construction, SSE token streaming, ungrounded fallback short-circuiting, native Kannada Unicode decoding, and upstream error recovery (45/45 tests passing across entire repository).

---

## [0.8.0] - 2026-10-09 (CHECKPOINT-P8)

### Added
- **Language Auto-Detection Subsystem (`backend/src/application/chat/language_detector.py`)**:
  - Implemented deterministic script-level detector distinguishing Kannada (`\u0C80-\u0CFF`), Latin English, and mixed multilingual inputs with confidence metrics.
- **Strict Grounding Guard & Deterministic Fallbacks (`backend/src/application/chat/grounding_guard.py`)**:
  - Enforced strict zero-hallucination verification against retrieved evidence and confidence cutoff ($<0.35$).
  - Implemented canonical deterministic fallbacks:
    - English: `"Information is not available in the knowledge base."`
    - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
- **Multi-Turn Conversation Engine & Coreference Resolver (`backend/src/application/chat/conversation_manager.py`)**:
  - Built `ConversationManager` tracking frictionless tourist sessions in MySQL `chat_sessions` and turns in `chat_messages`.
  - Implemented context query reformulation resolving pronouns and follow-up queries ("Who built it?", "Why?") using previous turns.
  - Linked assistant message turns directly to source chunks and confidence scores in MySQL `citation_references`.
- **Public Tourist Chat REST API (`backend/src/presentation/api/chat.py`)**:
  - `POST /api/v1/chat/message`: Public message endpoint with zero authentication barriers or tourist logins.
  - `POST /api/v1/chat/sessions`: Public session initialization endpoint.
  - `GET /api/v1/chat/sessions/{id}`: Public turn history and citation retrieval.
- **Automated Verification**:
  - Added `tests/unit/test_conversation_engine.py` verifying language detection, grounding fallbacks, zero-auth tourist access, coreference context retention, and citation persistence (38/38 tests passing across codebase).

---

## [0.7.0] - 2026-10-09 (CHECKPOINT-P7)

### Added
- **In-Memory BM25 Lexical Retriever (`backend/src/application/rag/bm25.py`)**:
  - Implemented BM25Okapi inverted indexing engine supporting Latin and Unicode Kannada script tokens.
  - Generates lexical sparse candidates (Top-15) based on exact keyword frequencies and smoothed IDF.
- **Cross-Encoder Re-Ranking Engine (`backend/src/application/rag/reranker.py`)**:
  - Built `CrossEncoderReranker` utilizing local `cross-encoder/ms-marco-MiniLM-L-6-v2`.
  - Calibrated raw logits to normalized $[0, 1]$ confidence probabilities via sigmoid activation.
  - Implemented noise filtering (boilerplate, bibliography, table of contents) and strict confidence thresholding ($>0.35$).
- **Hybrid Fusion Retriever (`backend/src/application/rag/retriever.py`)**:
  - Orchestrated 4-stage retrieval: Chroma dense search ($Top\text{-}15$) + BM25 sparse search ($Top\text{-}15$) $\longrightarrow$ Reciprocal Rank Fusion ($k=60$) $\longrightarrow$ Cross-Encoder re-ranking ($Top\text{-}10 \longrightarrow Top\text{-}4$).
  - Built caching layer for in-memory BM25 index keyed by active generation ID.
  - Measures comprehensive latency breakdown across dense, sparse, fusion, and re-ranking stages.
- **Administrative Diagnostic Endpoints (`backend/src/presentation/api/diagnostics.py`)**:
  - `POST /api/v1/admin/diagnostics/retrieval` & `GET /api/v1/admin/diagnostics/retrieval`: Returns full candidate rankings, intermediate scores, and latency profile (`VIEWER+`).
- **Automated Verification**:
  - Added `tests/unit/test_rag_retrieval.py` verifying BM25 recall, Cross-Encoder scoring, RRF fusion, live knowledge base retrieval, and diagnostics API (32/32 tests passing across codebase).

---

## [0.6.0] - 2026-10-09 (CHECKPOINT-P6)

### Added
- **PDF Extraction & Unicode NFKC Normalizer (`backend/src/application/pipeline/extractor.py`)**:
  - Implemented `PDFExtractor` using PyMuPDF (`fitz` / `pymupdf`).
  - Enforced Unicode NFKC normalization, whitespace cleanup, and structural section heading detection.
- **Structural Semantic Chunker (`backend/src/application/pipeline/chunker.py`)**:
  - Implemented `SemanticChunker` enforcing 300-500 token window with 50-token overlap.
  - Preserved document heading hierarchy, paragraph boundaries, and source page provenance.
- **Vector Storage & MiniLM Embeddings (`backend/src/infrastructure/vector/chroma_store.py`)**:
  - Built `ChromaVectorStore` with persistent ChromaDB storage under `data/chroma`.
  - Built `EmbeddingService` generating 384-dimensional dense vectors using `all-MiniLM-L6-v2`.
  - Implemented SHA-256 vector checksumming and dense cosine similarity retrieval.
- **Immutable Knowledge Generation State Machine (`backend/src/application/pipeline/generation_manager.py`)**:
  - Implemented state machine: `BUILD` ➔ `PARSE` ➔ `CHUNK` ➔ `EMBED` ➔ `INDEX` ➔ `VALIDATE` ➔ `PROMOTE` ➔ `ACTIVE`.
  - Step progression tracked in `generation_status` table with percentage completion and error tracking.
  - Relational records synchronized in MySQL `document_chunks` and `embeddings`.
  - Built instant (<100ms) zero-rebuild rollback mechanism to revert active pointer to previous generations.
- **Administrative Knowledge Base Endpoints (`backend/src/presentation/api/admin_knowledge.py`)**:
  - `POST /api/v1/admin/knowledge/generations/build`: Triggers pipeline build with audit logging (`GEN_BUILD`).
  - `GET /api/v1/admin/knowledge/generations`: Lists generations in reverse chronological order.
  - `GET /api/v1/admin/knowledge/generations/active`: Returns current ACTIVE generation.
  - `GET /api/v1/admin/knowledge/generations/{id}`: Detailed generation status and step inspection.
  - `POST /api/v1/admin/knowledge/generations/{id}/promote`: Promotes generation to ACTIVE status.
  - `POST /api/v1/admin/knowledge/generations/rollback`: Fast active pointer rollback.
- **Automated Verification**:
  - Added `tests/unit/test_knowledge_pipeline.py` verifying extraction, chunking, ChromaDB dense search, full lifecycle progression, rollback, and RBAC security (27/27 tests passing across the codebase).

---

## [0.5.0] - 2026-10-06 (CHECKPOINT-P5)

### Added
- **PDF Ingestion & Validation Engine (`backend/src/domain/document.py`)**:
  - Implemented binary validation verifying $<50$MB file limit, `.pdf` extension, and `%PDF-` magic-byte inspection.
  - Defined `DocumentResponse` and `DocumentListResponse` data contracts.
- **Filesystem Storage Management (`backend/src/infrastructure/storage/local_storage.py`)**:
  - Built `LocalStorageService` managing secure filesystem operations under `data/documents/` with UUID filenames.
  - Implemented automatic SHA-256 calculation for document deduplication.
  - Integrated PyMuPDF for reliable document page counting.
- **Administrative Document Endpoints (`backend/src/presentation/api/admin_documents.py`)**:
  - `POST /api/v1/admin/documents`: Multipart upload with cryptographic deduplication, storage, and MySQL metadata creation.
  - `GET /api/v1/admin/documents`: Paginated list of all ingested documents.
  - `GET /api/v1/admin/documents/{id}`: Detailed metadata retrieval.
  - `GET /api/v1/admin/documents/{id}/download`: Raw PDF streaming for administrative download.
  - `DELETE /api/v1/admin/documents/{id}`: Deletes file from storage and database record with audit logging.
- **Initial Knowledge Base Dataset**:
  - Created and ingested curated production baseline `Temple_info.pdf` covering historical patronage, Hoysala architecture, and Madanika sculptures of Belur Chennakeshava Temple.
- **Automated Verification**:
  - Added `tests/unit/test_document_management.py` verifying upload, conflict rejection, magic bytes check, download, and deletion lifecycle (21/21 tests passing).

---

## [0.4.0] - 2026-10-06 (CHECKPOINT-P4)

### Added
- **Cryptographic Security Engine (`backend/src/core/security.py`)**:
  - Implemented Argon2id password hashing complying with OWASP guidelines ($m=65536, t=3, p=4$).
  - Implemented JWT token generation with unique `jti` claims and expiration verification (15m access token, 7d refresh token).
- **Role-Based Access Control (`backend/src/domain/auth.py`, `backend/src/presentation/dependencies/auth.py`)**:
  - Defined `AdminRole` hierarchy (`SUPER_ADMIN` > `SITE_CURATOR` > `OPERATOR` > `VIEWER`).
  - Created dependency `get_current_admin` extracting Bearer tokens and validating database status.
  - Created dependency factory `require_role(minimum_role)` strictly enforcing privilege levels.
- **Administrative Endpoints (`backend/src/presentation/api/auth.py`)**:
  - `POST /api/v1/auth/login`: Validates credentials, issues JWT token pair, and writes audit logs.
  - `POST /api/v1/auth/refresh`: Rotates active refresh tokens.
  - `POST /api/v1/auth/logout`: Revokes session context with audit recording.
  - `GET /api/v1/auth/me`: Delivers authenticated admin profile.
  - `GET /api/v1/auth/curator-zone`: Role-guarded endpoint for testing RBAC hierarchy.
- **Database Auditing**:
  - Recorded authentication attempts (`ADMIN_LOGIN_SUCCESS`, `ADMIN_LOGIN_FAILED`, `TOKEN_ROTATED`) into MySQL `audit_logs`.
- **Automated Verification**:
  - Added `tests/unit/test_admin_auth.py` verifying hashing, token rotation, RBAC enforcement, and public tourist access (16/16 tests passing).

---

## [0.3.0] - 2026-10-06 (CHECKPOINT-P3)

### Added
- **MySQL 8.0 Persistence Engine (`backend/src/infrastructure/database/`)**:
  - `session.py`: Asynchronous engine pool utilizing `asyncmy` with automatic pre-ping, connection recycling, and session dependency `get_db_session()`.
  - `base.py`: Declarative ORM `Base`, `TimestampMixin` with UTC timestamps, and `UUIDPrimaryKeyMixin`.
- **Complete 17-Table Relational Schema (`backend/src/infrastructure/models/`)**:
  - `auth.py`: `Admin` model for administrative authentication.
  - `knowledge.py`: `Document`, `KnowledgeGeneration`, `GenerationStatus`, `DocumentChunk`, `ChunkEmbedding`, `CitationReference` models.
  - `chat.py`: `ChatSession`, `ChatMessage` models for multi-turn conversations.
  - `system.py`: `AuditLog`, `SystemLog`, `DeploymentHistory`, `HealthMetric`, `ModelRegistry`, `VoiceRegistry`, `TranslationRegistry`, `SystemSetting` models.
- **Alembic Database Migrations (`backend/alembic/`)**:
  - Setup async migration runner connecting directly to `Base.metadata`.
  - Generated and executed migration `81eec6c21793_001_initial_schema.py` creating all 17 tables, indexes, and foreign keys in MySQL 8.0.
- **Health Check Integration**:
  - Enhanced `GET /api/v1/health` with a live asynchronous database probe measuring query latency.
- **Verification Tests**:
  - Added `tests/unit/test_persistence_foundation.py` verifying connection ping, CRUD transaction lifecycle, health reporting, and model validity (9/9 tests passing).

---

## [0.2.0] - 2026-10-06 (CHECKPOINT-P2)

### Added
- **Backend Core Infrastructure (`backend/src/core/`)**:
  - `config.py`: Integrated `pydantic-settings` to manage application environment configurations across profiles (`APP_PROFILE=dev|standalone|cloud`).
  - `logging.py`: Configured `structlog` for structured JSON output in non-dev environments and console formatting in development.
  - `middleware.py`: Built ASGI `CorrelationIdMiddleware` injecting `X-Correlation-ID` and measuring `X-Process-Time-Ms`.
  - `errors.py`: Implemented typed domain exception hierarchy (`AppException`, `NotFoundError`, `ValidationError`, etc.) with standardized JSON response envelopes.
- **FastAPI Presentation Gateway (`backend/src/`)**:
  - `main.py`: Configured application factory, CORS origins, middleware stack, and lifespan hooks.
  - `presentation/api/health.py`: Exposed `GET /api/v1/health` reporting server health, version, deployment profile, and uptime.
- **Automated Verification**:
  - Configured test harness with `pytest` and `httpx`.
  - Added unit test suite `tests/unit/test_backend_foundation.py` (5/5 tests passing).

---

## [0.1.0] - 2026-10-06 (CHECKPOINT-P1)

### Added
- **Product Requirements Document (`PRD.md`)**:
  - Defined product vision, problem statement, user personas, and tourist/admin user journeys.
  - Specified functional requirements (multilingual RAG, speech in/out, immutable generations, interactive maps).
  - Defined non-functional performance budgets, security requirements, and accessibility (WCAG 2.1 AA) targets.
  - Locked invariant constraints (pure software, no robotics, zero tourist authentication).
- **System Architecture Document (`Architecture.md`)**:
  - Detailed Pragmatic Clean Architecture layers (Domain, Application, Infrastructure, Presentation).
  - Designed the complete 17-table MySQL 8.0 schema with relations, constraints, and indexes.
  - Architected hybrid RAG pipeline (MiniLM dense + BM25 sparse + Reciprocal Rank Fusion + Cross-Encoder re-ranker).
  - Architected local voice pipeline (`faster-whisper` STT, Argos Translate, and Piper TTS).
  - Specified Unified Client Gateway under `/api/v1/...` with REST + SSE contracts.
  - Outlined deployment profiles (`dev`, `standalone`, `cloud`) and container topology.
- **Engineering Rules (`Rules.md`)**:
  - Established lean pragmatic coding rules, dead-code removal protocols, and dependency justification rules.
  - Defined strict invariant negative directives (no robotics, MySQL 8.0 locked, no tourist auth, zero mock generation in prod).
  - Enforced security, testing, API, and Alembic database migration standards.
- **Master Roadmap (`Phases.md`)**:
  - Outlined detailed specifications, task breakdowns, file impacts, verification criteria, and checkpoints for all 23 phases (`CHECKPOINT-P1` to `CHECKPOINT-P23`).
- **UI/UX Design System (`Design.md`)**:
  - Formulated the Karnataka Heritage Modernity design language inspired by Hoysala stone architecture.
  - Defined color tokens: Temple Gold (`#D4AF37`), Deep Heritage Brown (`#2C1810`), Soapstone Grey (`#4A4A4A`), and Ivory (`#FDFBF7`).
  - Specified typography (Inter, Outfit, Noto Sans Kannada), spacing grid, elevation, and component specs.
- **Project Memory & State (`Memory.md`)**:
  - Established project state tracker, recording Phase 1 completion, active checkpoint `CHECKPOINT-P1`, and exact next task.
- **Supporting Documentation**:
  - Created `docs/CHECKPOINTS.md`, `docs/changelog.md`, and `docs/milestones.md`.
