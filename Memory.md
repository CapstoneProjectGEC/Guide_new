# PROJECT MEMORY & ACTIVE STATE TRACKER

**Project Title:** AI-Powered Smart Tourist Guide Platform for Karnataka  
**Document Version:** 1.0.0  
**Current Phase:** Phase 16 — End-to-End Integration Verification  
**Phase Status:** Complete  
**Active Checkpoint:** CHECKPOINT-P16  
**Last Updated:** 2026-10-13  

---

## 1. Executive Status & Progress Overview

Phase 16 (End-to-End Integration & Real-Component Verification) is complete and empirically proven. All five integration areas have been tested and verified across live FastAPI endpoints, ChromaDB RAG, Piper TTS, faster-whisper STT, Argos translation, and MySQL persistence:
1. **SSE Multibyte UTF-8 Streaming**: Incremental Kannada character decoding verified across chunk boundaries with zero corruption or replacement characters (`\ufffd`).
2. **Authentication & Token Lifecycle**: Refresh token rotation, rejection of reused refresh tokens, server-side JTI logout invalidation, single-flight refresh coordination, and strict RBAC endpoint security verified.
3. **RAG Citations & Active Generation**: Answer citations verified as a strict subset of retrieved knowledge chunks, source document traceability confirmed, and queries pinned to active generation.
4. **Instant Rollback**: Atomic rollback verified (<100ms) with immediate retrieval pointer switch without restarting FastAPI or Ollama.
5. **Offline Voice Workflows**: Microphone error states, audio MIME validation, faster-whisper STT silence bypass, Piper binary WAV synthesis headers, and air-gapped operation verified.

- **Completed Phases**: Phase 1 through Phase 16
- **Current Active Checkpoint**: `CHECKPOINT-P16`
- **Application Code Status**: 159 automated tests passing (118 backend tests: 106 unit + 12 integration; 41 frontend tests; 100% pass rate) with zero regressions across all subsystems.

---

## 2. Invariant Architectural Decisions (Locked)

1. **Pure Software Scope**: Hardware, robotics, ROS2, Jetson, Raspberry Pi, Arduino, and RPLIDAR are strictly prohibited.
2. **Database Engine**: **MySQL 8.0 ONLY** (via async driver and SQLAlchemy 2.0). PostgreSQL and SQLite are prohibited for production runtime.
3. **Tourist Access**: **Strictly Zero Authentication**. Tourists never create accounts or log in.
4. **Admin Access**: Argon2id password hashing + JWT with refresh token rotation + RBAC (`SUPER_ADMIN`, `SITE_CURATOR`, `OPERATOR`, `VIEWER`).
5. **AI & RAG Subsystems**:
   - Embeddings: `all-MiniLM-L6-v2` (384-dim).
   - Vector Store: Local persistent ChromaDB collections (`data/chroma`).
   - Retrieval: Hybrid (Dense Top-15 + BM25 Top-15) fused via Reciprocal Rank Fusion (RRF $k=60$) and re-ranked via `cross-encoder/ms-marco-MiniLM-L-6-v2` (Top-4 selected, threshold $>0.35$).
   - LLM: Local Ollama runtime (`llama3.1:8b` default).
   - STT: Local `faster-whisper`.
   - Translation: Offline Argos Translate (`en_kn` / `kn_en`).
   - TTS: Local Piper neural speech synthesizer.
6. **Grounding Policy**: Zero hallucinations. Canonical fallback messages enforced in English and Kannada:
   - English: `"Information is not available in the knowledge base."`
   - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
7. **Frontend Stack**: React 19 + TypeScript + Vite + Tailwind CSS + shadcn/ui + Framer Motion.
8. **Design System**: Heritage Modernity with Hoysala-inspired palette (Temple Gold `#D4AF37`, Deep Heritage Brown `#2C1810`, Soapstone Grey `#4A4A4A`, Ivory `#FDFBF7`).
9. **Deployment Profiles**: Single codebase supporting `dev`, `standalone` (offline local), and `cloud` (Docker Compose + Nginx) via `APP_PROFILE`.

---

## 3. Relational Schema Status (All 17 Tables Migrated in MySQL 8.0)

```text
1. admins (Active)                 9. audit_logs (Active Audit Trail)
2. documents (Active)             10. system_logs
3. document_chunks (Active)       11. deployment_history
4. knowledge_generations (Active) 12. health_metrics
5. generation_status (Active)     13. model_registry
6. embeddings (Active)            14. voice_registry
7. chat_sessions (Active)         15. translation_registry
8. chat_messages (Active)         16. system_settings
                                  17. citation_references (Active)
```

### Active Conversational Engine Performance:
- **Zero-Auth Verification**: Confirmed public endpoints `/api/v1/chat/*` function without tokens or credentials.
- **Language Auto-Detection**: Kannada Unicode script detection (`kn`), English (`en`), and mixed inputs.
- **Multi-Turn Coreference Resolution**: Warm follow-up query latency: **47.2ms** (reformulating pronouns like *"Who built it?"* to full context queries).
- **Strict Grounding Guard**: Out-of-domain queries return canonical fallback in **43.2ms** with zero hallucinations.

---

## 4. Phase 8 Deliverables & Files Created

### Source Code Files:
- `backend/src/domain/conversation.py`: Domain contracts and schemas for `Citation`, `ChatMessageResponse`, `ChatSessionResponse`, `CreateSessionRequest`, and `SendMessageRequest`.
- `backend/src/application/chat/language_detector.py`: `LanguageDetector` classifying text into `"kn"` or `"en"` with script confidence metrics and mixed-script detection.
- `backend/src/application/chat/grounding_guard.py`: `GroundingGuard` enforcing canonical fallback messages when retrieval confidence is below 0.35.
- `backend/src/application/chat/conversation_manager.py`: `ConversationManager` coordinating session creation, coreference query reformulation, hybrid retrieval, grounding verification, and relational persistence into `chat_sessions`, `chat_messages`, and `citation_references`.
- `backend/src/presentation/api/chat.py`: Public tourist REST endpoints (`POST /api/v1/chat/message`, `POST /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{id}`) with zero authentication barriers.
- `backend/src/main.py`: Mounted `chat_router` under `/api/v1`.
- `tests/unit/test_conversation_engine.py`: Automated test suite covering script detection, grounding guard fallbacks, zero-auth access, multi-turn coreference resolution, and MySQL citation persistence.

---

## 5. Verification & Test Evidence

- **Database Engine**: MySQL 8.0 on `localhost:3306` (service `MySQL80`)
- **Test Runner**: Pytest 9.1.1 on Python 3.12.10
- **Test Results**: 38 passed in 20.83s (100% pass rate)
  - `test_language_detector_kannada_english_mixed`: PASSED
  - `test_strict_grounding_guard_fallback`: PASSED
  - `test_tourist_public_endpoints_require_zero_auth`: PASSED
  - `test_multi_turn_coreference_resolution`: PASSED
  - `test_out_of_domain_query_triggers_canonical_fallback`: PASSED
  - `test_citation_references_relational_persistence`: PASSED
  - All 32 previous regression tests (Phases 2-7): PASSED
- **Empirical Multi-Turn Probe**:
  - Live 3-turn probe executed on Belur data: Turn 1 established subject, Turn 2 resolved pronoun coreference in 47.2ms with 2 citations, Turn 3 triggered canonical fallback in 43.2ms with zero citations.

---

## 6. Phase 10 Deliverables & Files Created

### Source Code & Test Files:
- `backend/src/domain/voice.py`: Domain contracts for `TranscriptionSegment`, `TranscriptionResult`, `VoiceChatResponse`, and `VoiceEngineInfo`.
- `backend/src/infrastructure/audio/whisper_engine.py`: Thread-safe CTranslate2 Faster-Whisper wrapper with auto-discovered Ollama CUDA DLLs (`cublas64_12.dll`) and seamless CPU fallback.
- `backend/src/application/voice/stt_service.py`: Audio validation (WebM, WAV, MP3, OGG, M4A), 16kHz mono normalization, RMS silence shortcut (<0.002), and timeout guard.
- `backend/src/presentation/api/voice.py`: Public tourist endpoints `/api/v1/voice/info`, `/api/v1/voice/transcribe`, `/api/v1/voice/chat`, and `/api/v1/voice/stream`.
- `backend/src/main.py`: Mounted `voice_router` under `/api/v1`.
- `tests/unit/test_voice_stt.py`: 15 comprehensive unit & integration tests covering Kannada/English/mixed speech, silence, noise, malformed uploads, boundaries, and end-to-end voice streaming.
- `tests/fixtures/audio/*`: Static local test audio fixtures for offline regression verification.

### Empirical Benchmarks & Hardware Footprint:
- **Test Results**: 60/60 passed in 25.35s (100% pass rate across all 10 modules).
- **Spoken Kannada Query (4.90s)**: 151ms STT transcription latency (criterion: <1.0s).
- **Spoken English Query (3.46s)**: 195ms STT transcription latency.
- **Spoken Mixed-Language Query (4.25s)**: 156ms STT transcription latency.
- **Pure Silence Query (3.00s)**: 37ms instant RMS bypass latency.
- **Simultaneous GPU VRAM (RTX 3050 8GB)**: Peak 4563 MB with Ollama `gemma3:4b` (4241 MB) + Whisper `base` float16 (237 MB delta), leaving 3479 MB headroom.
- **Reliable CPU Fallback**: Verified with `int8` (English: 628ms, Kannada: 862ms).

---

## 7. Phase 11 Deliverables & Files Created

### Source Code & Test Files:
- `backend/src/domain/translation.py`: Pydantic domain models for `NormalizedQuery`, `HeritageTermMapping`, `TranslationPackageInfo`, and `TranslationStrategy`.
- `backend/src/application/translation/heritage_glossary.py`: Canonical 30+ entity Belur heritage dictionary (Belur, Chennakeshava, Vishnuvardhana, Shantala Devi, Madanika, Darpana Sundari, Natya Mohini, Jakanachari, Hoysala, Garbhagriha, Navaranga, Pushkarani, Soapstone, etc.) with proper-noun masking/unmasking and intent expansion patterns.
- `backend/src/infrastructure/translation/argos_engine.py`: Thread-safe offline Argos Translate engine manager discovering local `.argosmodel` packages in `data/models/argos` with graceful failure handling.
- `backend/src/application/translation/transliteration.py`: Deterministic phonetic Kannada-to-Latin transliteration strictly distinguishing phonetic script conversion (`"deevaalaya"`) from semantic translation (`"temple"`).
- `backend/src/application/translation/query_normalizer.py`: Cross-lingual query normalizer orchestrating English passthrough, entity preservation, intent expansion, common term mapping, and transliterated out-of-domain preservation.
- `backend/src/application/translation/translator.py`: Service coordinating translation pipeline, glossaries, and MySQL `translation_registry` persistence.
- `backend/src/presentation/api/translation.py`: Public tourist and management endpoints `/api/v1/translation/status`, `/api/v1/translation/normalize`, and `/api/v1/translation/sync`.
- `backend/src/main.py`: Mounted `translation_router` under `/api/v1/translation`.
- `backend/src/application/chat/conversation_manager.py`: Integrated `QueryNormalizer` into message processing and SSE streaming, preserving verbatim Kannada queries in session history and LLM prompts while querying hybrid retrieval with normalized terms.
- `tests/unit/test_translation_hardening.py`: 13 automated unit & integration tests covering glossary masking/unmasking, transliteration distinction, English passthrough, Kannada query expansion, mixed queries, empty inputs, offline model unavailability fallback, database sync, REST endpoints, end-to-end grounded retrieval, out-of-domain fallback, and SSE event streaming.
- `scripts/benchmark_retrieval_phase11.py`: Repeatable local retrieval quality and latency benchmark suite.

### Empirical Benchmarks & Verification:
- **Test Results**: 73/73 passed in 26.74s (100% pass rate across all 11 phases, zero regressions).
- **Kannada In-Domain Grounding**: Jumped from **0%** (baseline monolingual retrieval) to **100% grounded** on indexed topics with top cross-encoder scores $>0.997$ and valid citations.
- **Out-of-Domain Precision**: **100%** rejection with immediate canonical Kannada fallback (`"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`), preventing hallucinations.
- **Query Normalization Latency**: **0.126 ms** average overhead (sub-millisecond).
- **English Passthrough**: **0.014 ms** zero-mutation overhead; English behavior completely preserved ($0.9999$ top score).
- **Total RAG Retrieval Latency**: **44 - 49 ms** for hybrid retrieval + re-ranking across both Kannada and English.

---

## 8. Phase 12 Deliverables & Files Created

### Source Code & Test Files:
- `backend/src/infrastructure/audio/piper_engine.py`: Thread-safe local Piper ONNX engine adapter managing lazy loading, session caching, and CPU speech synthesis.
- `backend/src/infrastructure/audio/tts_cache.py`: Bounded thread-safe LRU audio cache (128 entries) with in-flight deduplication locks for canonical grounding fallbacks and short phrases (<=150 chars).
- `backend/src/application/voice/tts_service.py`: Application-level TTS service orchestrating input validation (1000 char ceiling), language script auto-detection fallback (`LanguageDetector`), bounded background thread execution, and relational sync.
- `backend/src/domain/voice.py`: Domain contracts extended with `SynthesisRequest`, `SynthesisMetadata`, `TTSEngineStatus`, and `TTSVoiceInfo`.
- `backend/src/presentation/api/voice.py`: Public tourist endpoints `/api/v1/voice/synthesize`, `/api/v1/voice/tts/status`, `/api/v1/voice/tts/voices`, and `/api/v1/voice/tts/sync`.
- `backend/src/core/config.py`: Integrated TTS settings (`TTS_ENABLED`, `TTS_ENGINE`, `TTS_MODELS_DIR`, `TTS_VOICE_EN`, `TTS_VOICE_KN`, `TTS_MAX_TEXT_LENGTH`, `TTS_CACHE_MAX_ENTRIES`, `TTS_TIMEOUT_SECONDS`, `TTS_USE_CUDA`).
- `backend/src/core/errors.py`: Typed domain errors `TTSValidationError`, `TTSTooLargeError`, `TTSUnavailableError`, and `TTSTimeoutError`.
- `backend/src/main.py`: Clean engine shutdown hooks in application lifespan context manager.
- `scripts/download_tts_models.py`: Model provisioning script validating local file sizes and offline CPU synthesis.
- `scripts/benchmark_tts_phase12.py`: Repeatable local latency, throughput, and concurrency benchmark suite.
- `tests/unit/test_voice_tts.py`: 20 comprehensive unit, integration, and smoke tests covering validation, caching, concurrency, real local models, and existing contract preservation.

### Empirical Benchmarks & Hardware Footprint:
- **Test Results**: 93/93 passed in 33.51s (100% pass rate across all 12 modules, zero regressions).
- **Warm English Synthesis (148 chars, 9.64s audio)**: 184ms latency (RTF: **0.019x**, over 50x faster than real-time).
- **Warm Kannada Synthesis (124 chars, 11.45s audio)**: 217ms latency (RTF: **0.019x**, over 50x faster than real-time).
- **Short Canonical Fallback Synthesis (51 chars)**: 0.16ms via LRU cache hit.
- **5 Concurrent Requests**: 168.9ms total (average 33.8ms per request).
- **Added GPU VRAM Footprint**: **0 MB** (100% CPU execution via ONNX Runtime, preserving GPU memory for Gemma 3:4b).
- **Verified Audio Format**: 22050Hz 16-bit Mono PCM WAV.

---

## 9. Phase 13 Deliverables & Files Created

### Source Code & Test Files:
- `backend/src/presentation/router.py`: Unified API gateway router composing all 9 sub-routers under `/api/v1` with OpenAPI tags metadata.
- `backend/src/core/limiter.py`: Thread-safe monotonic sliding-window `RateLimiter` and `RateLimitMiddleware` (60 tourist / 120 admin RPM, anti-spoofing, bounded storage).
- `backend/src/core/config.py`: Gateway configuration settings (`RATE_LIMIT_*`, `TRUSTED_PROXIES`, `cors_allow_credentials` validator).
- `backend/src/core/errors.py`: `RateLimitExceededError` (HTTP 429) and exception handler injection of standard `Retry-After` and `X-RateLimit-*` headers.
- `backend/src/presentation/api/health.py`: Liveness (`/health/live`) and readiness (`/health/ready`) probes separating application uptime from local AI engine availability.
- `backend/src/presentation/api/admin_sync.py`: Secure RBAC sync management endpoints (`/api/v1/admin/sync/voice`, `/api/v1/admin/sync/translation`, `/api/v1/admin/sync/status`).
- `backend/src/main.py`: Gateway middleware assembly, secure CORS, router mount, `/health` alias, and OpenAPI schema customization with `BearerAuth`.
- `tests/unit/test_unified_gateway.py`: 13 automated unit and integration tests covering route inventory, OpenAPI schema, rate limits, headers, anti-spoofing, trusted proxies, SSE and WAV compatibility, admin sync auth, and CORS credentials.

### Empirical Benchmarks & Verification:
- **Test Results**: 106/106 passed in 38.62s (100% pass rate across all 13 modules, zero regressions).
- **Rate Limit Enforcement**: 60 RPM tourist quota and 120 RPM admin quota verified with deterministic HTTP 429 + `Retry-After` headers.
- **Anti-Spoofing Immunity**: Rejecting spoofed `X-Admin-Role` and untrusted `X-Forwarded-For` verified.
- **Streaming Pass-Through**: SSE and binary WAV audio responses stream without buffering or corruption.
- **Zero Database Changes**: Clean architectural layer composition requiring no schema migrations.

---

## 10. Phase 14 Deliverables & Files Created

### Source Code & Test Files:
- `frontend/package.json`: React 19 + TypeScript + Vite 6 + Tailwind CSS + Vitest dependency manifest.
- `frontend/tsconfig.json` & `frontend/vite.config.ts`: Strict TypeScript config with `@/*` aliases and dev proxy to `http://127.0.0.1:8000`.
- `frontend/tailwind.config.js` & `frontend/src/index.css`: Hoysala theme tokens, WCAG 2.1 AA accessible focus rings, and `prefers-reduced-motion` styles.
- `frontend/src/theme/tokens.ts`: Canonical heritage colors, Belur attractions with coordinates, suggested questions, and localized English/Kannada UI strings.
- `frontend/src/types/api.ts`: Typed TypeScript contracts matching `/api/v1` FastAPI schemas.
- `frontend/src/services/api.ts`: Typed client for chat, sessions, voice STT, TTS, and health endpoints.
- `frontend/src/services/streaming.ts`: Resilient SSE stream reader with multibyte UTF-8 Kannada character chunking resilience.
- `frontend/src/services/audio.ts`: MediaRecorder voice capture and Piper WAV playback service.
- `frontend/src/features/layout/`: `Header.tsx`, `Sidebar.tsx`, `Layout.tsx` for responsive 3-column / mobile drawer layout.
- `frontend/src/features/chat/`: `ChatContainer.tsx`, `MessageBubble.tsx`, `CitationBadge.tsx`, `SuggestedQuestions.tsx`, `MessageInput.tsx`.
- `frontend/src/features/voice/`: `AudioVisualizer.tsx` (28-bar canvas gold wave) and `VoiceWidget.tsx` (recording timer and mic trigger).
- `frontend/src/features/citations/CitationDrawer.tsx`: Slide-over citation inspector with verbatim document chunk excerpts.
- `frontend/src/features/map/TourismMap.tsx`: Interactive precinct map of Belur Jagati platform with 5 Hoysala monument pins.
- `frontend/src/tests/`: 17 automated tests (`streaming.test.ts`, `api.test.ts`, `components.test.tsx`, `setup.ts`).

### Empirical Benchmarks & Verification:
- **Frontend Build**: `npm run build` succeeds cleanly in 1.57s (Production bundle: 285 kB JS / 85 kB gzip, 27 kB CSS).
- **Frontend Automated Tests**: 17/17 passed in 1.28s (100% pass rate).
- **Backend Regression Suite**: 106/106 passed in 64.03s (100% pass rate across all 13 modules).
- **Grand Total Automated Tests**: 123/123 passed (100% pass rate).
- **Zero-Auth Verification**: Frictionless tourist chat, voice, and precinct map exploration without login.

---

## 11. Phase 15 Deliverables & Files Created

### Source Code & Test Files:
- `frontend/src/types/api.ts`: Domain models for `AdminProfile`, `DocumentItem`, `KnowledgeGenerationItem`, `ModelSyncStatusResponse`, and `RetrievalDiagnosticResponse`.
- `frontend/src/services/auth.ts`: Secure in-memory authentication singleton with zero browser storage footprint, refresh token rotation, and RBAC hierarchy (`SUPER_ADMIN` > `SITE_CURATOR` > `OPERATOR` > `VIEWER`).
- `frontend/src/services/adminApi.ts`: Typed API client handling Bearer auth, automatic 401 retry, document lifecycle, generation build/promote/rollback, model sync, and diagnostics.
- `frontend/src/features/admin/AdminLogin.tsx`: Accessible administrative login view with zero-storage disclosure and clean error handling.
- `frontend/src/features/admin/AdminDashboard.tsx`: Karnataka heritage administrative control shell with role badge, tab navigation, and logout action.
- `frontend/src/features/admin/OverviewTab.tsx`: Live system telemetry and AI model status based strictly on verified API probes with zero fabricated metrics.
- `frontend/src/features/admin/DocumentManager.tsx`: Document inventory table, 50MB PDF upload validation, binary download, and explicit delete confirmation dialog.
- `frontend/src/features/admin/GenerationManager.tsx`: Visual 6-step pipeline stepper (`PARSE` to `PROMOTE`), active generation highlight, build trigger with bounded polling, and instant rollback modal (<100ms pointer update).
- `frontend/src/features/admin/ModelSyncTab.tsx`: Offline Piper voice model and Argos translation package synchronization into MySQL registries.
- `frontend/src/features/admin/DiagnosticsTab.tsx`: Hybrid RAG diagnostic probe visualizing dense, sparse, RRF, and cross-encoder scores with latency profiling.
- `frontend/src/tests/adminAuth.test.ts`: In-memory auth tests, token rotation, RBAC role hierarchy, and zero localStorage verification.
- `frontend/src/tests/adminApi.test.ts`: Typed API tests, Bearer header injection, 401 token refresh retry, and error envelopes.
- `frontend/src/tests/adminComponents.test.tsx`: Component tests for login, overview, document manager, generation manager, model sync, diagnostics, and dashboard navigation.

### Empirical Benchmarks & Verification:
- **Frontend Production Build**: `npm run build` succeeds cleanly in 1.64s (Bundle: 364 kB JS / 99 kB gzip, 34 kB CSS).
- **Frontend Automated Tests**: 41/41 passed in 1.64s (100% pass rate).
- **Backend Regression Suite**: 106/106 passed in 40.17s (100% pass rate across all 13 modules).
- **Grand Total Automated Tests**: 147/147 passed (100% pass rate).
- **Zero Browser Storage Footprint**: Verified 0 tokens in localStorage/sessionStorage.

---

## 12. Known Technical Debt & Risks

- None in Phase 15. The admin portal is fully decoupled from the public tourist interface, runs with strict in-memory security, and requires zero external internet access.

---

## NEXT TASK

Phase 15 is complete with 147/147 tests passing and CHECKPOINT-P15 locked.
The next planned phase on the roadmap is **Phase 16 — End-to-End Integration**:
1. Validate complete Tourist Voice Flow: Browser mic ➔ Whisper STT ➔ Hybrid RAG ➔ Ollama LLM ➔ Piper TTS ➔ Audio playback.
2. Validate complete Tourist Text Flow: Text query ➔ RAG ➔ Streaming SSE ➔ Citation Drawer inspect.
3. Validate Admin Lifecycle Flow: PDF upload ➔ Pipeline run ➔ Chunk check ➔ Generation promotion ➔ Instant rollback.
4. Validate fallback behavior on non-temple queries in both Kannada and English.
5. Create automated E2E test runner executing tourist queries and admin flows against running containers.

