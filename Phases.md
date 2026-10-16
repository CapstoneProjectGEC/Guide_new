# MASTER 23-PHASE ROADMAP & EXECUTION GATES

**Project Title:** AI-Powered Smart Tourist Guide Platform for Karnataka  
**Document Version:** 1.0.0  
**Status:** Approved Baseline (Phase 1 Locked)  
**Author:** Unified Principal Engineering Team  

---

## 1. Roadmap Architecture & Execution Protocol

The 23 phases are strictly sequential. No phase may commence until the preceding phase satisfies all acceptance gates and records its checkpoint.

```text
[Phase 1: Specs & Architecture] ──► [Phase 2: Backend Core] ──► [Phase 3: MySQL DB]
       │
       ▼
[Phase 4: Admin Auth & RBAC] ──► [Phase 5: PDF Ingestion] ──► [Phase 6: KB Pipeline]
       │
       ▼
[Phase 7: RAG Retrieval] ──► [Phase 8: Conversation Engine] ──► [Phase 9: Ollama LLM]
       │
       ▼
[Phase 10: Whisper STT] ──► [Phase 11: Argos Translation] ──► [Phase 12: Piper TTS]
       │
       ▼
[Phase 13: Unified Gateway] ──► [Phase 14: Tourist Web UI] ──► [Phase 15: Admin Dashboard]
       │
       ▼
[Phase 16: E2E Integration] ──► [Phase 17: Docker & Cloud] ──► [Phase 18: Performance]
       │
       ▼
[Phase 19: Telemetry & Mon] ──► [Phase 20: Security Hardening] ──► [Phase 21: Test Suite]
       │
       ▼
[Phase 22: Complete Docs] ──► [Phase 23: Production Readiness (GO / NO-GO)]
```

---

## 2. Detailed Phase Specifications (Phases 1 - 23)

---

### PHASE 1 — Requirements & Architecture
- **Objective**: Establish the authoritative architectural, technical, and design blueprint.
- **Scope**: Documentation and specifications only. No application code.
- **Tasks**:
  1. Author `PRD.md` capturing all functional, non-functional, tourist, and admin requirements.
  2. Author `Architecture.md` defining Clean Architecture, MySQL 17-table schema, and AI/RAG pipelines.
  3. Author `Rules.md` governing lean coding, invariant locks, and development protocol.
  4. Author `Phases.md` specifying all 23 phases with gates and deliverables.
  5. Author `Design.md` detailing the Karnataka heritage design system and UI specs.
  6. Author `Memory.md` for active session tracking.
  7. Create `docs/CHECKPOINTS.md`, `docs/changelog.md`, and `docs/milestones.md`.
- **Expected Files**: `PRD.md`, `Architecture.md`, `Rules.md`, `Phases.md`, `Design.md`, `Memory.md`, `docs/CHECKPOINTS.md`, `docs/changelog.md`, `docs/milestones.md`.
- **Database / API / UI Impact**: None (Design phase).
- **Tests Required**: Internal consistency review across all specification documents.
- **Completion Criteria**: Complete alignment between PRD, Architecture, Rules, Design, and Phases.
- **Exclusions**: Application implementation, migrations, model downloads.
- **Checkpoint**: `CHECKPOINT-P1`

---

### PHASE 2 — Backend Foundation
- **Objective**: Build the minimal, robust, extensible FastAPI application foundation.
- **Scope**: App scaffolding, configuration management, structured logging, typed errors, correlation IDs, and health probes.
- **Tasks**:
  1. Initialize Python 3.12 project structure under `backend/`.
  2. Implement settings validation via `pydantic-settings` (`APP_PROFILE=dev|standalone|cloud`).
  3. Configure structured JSON logging via `structlog`.
  4. Implement correlation ID middleware attaching UUIDs to every request context.
  5. Build global exception handler translating domain errors into standardized JSON envelopes.
  6. Create `/api/v1/health` endpoint returning server status and uptime.
- **Expected Files**: `backend/src/core/config.py`, `backend/src/core/logging.py`, `backend/src/core/errors.py`, `backend/src/core/middleware.py`, `backend/src/main.py`.
- **Database / API Impact**: No database tables yet. Exposes `/api/v1/health`.
- **Tests Required**: Unit tests for settings loading, correlation ID propagation, and health check response.
- **Completion Criteria**: Health probe responds HTTP 200 with JSON payload; correlation headers verified.
- **Checkpoint**: `CHECKPOINT-P2`

---

### PHASE 3 — MySQL Persistence Foundation
- **Objective**: Establish production-ready MySQL persistence with async SQLAlchemy 2.0 and Alembic.
- **Scope**: Async engine, session pooling, Alembic configuration, base declarative models, and database health probes.
- **Tasks**:
  1. Configure async MySQL connection pool using SQLAlchemy 2.0 and `asyncmy`.
  2. Setup Alembic migration environment supporting async operations.
  3. Define base model classes with UTC `created_at` and `updated_at` mixins.
  4. Write initial migrations generating initial core metadata tables.
  5. Add database ping probe to `/api/v1/health`.
- **Expected Files**: `backend/src/infrastructure/database/session.py`, `backend/src/infrastructure/database/base.py`, `backend/alembic.ini`, `backend/alembic/env.py`.
- **Database Impact**: Core database connectivity established; Alembic version table created.
- **Tests Required**: Connection pool acquisition, async transaction commit/rollback, Alembic migration up/down.
- **Completion Criteria**: Database health check passes; migration runs cleanly.
- **Checkpoint**: `CHECKPOINT-P3`

---

### PHASE 4 — Admin Authentication & RBAC
- **Objective**: Implement secure administrative authentication and Role-Based Access Control.
- **Scope**: Password hashing with Argon2id, JWT token issuance with rotation, and FastAPI role security dependencies.
- **Tasks**:
  1. Create `admins` table model and Alembic migration.
  2. Implement Argon2id password hashing and verification utility.
  3. Implement JWT access (15 min) and refresh (7 day) token creation and verification.
  4. Create `/api/v1/auth/login`, `/api/v1/auth/refresh`, and `/api/v1/auth/logout` endpoints.
  5. Build FastAPI dependency `require_role(role)` enforcing RBAC: `SUPER_ADMIN`, `SITE_CURATOR`, `OPERATOR`, `VIEWER`.
  6. Add audit event logging for login attempts.
- **Expected Files**: `backend/src/core/security.py`, `backend/src/domain/admin.py`, `backend/src/infrastructure/models/admin.py`, `backend/src/presentation/api/auth.py`.
- **Database Impact**: `admins` and `audit_logs` tables populated and migrated.
- **Tests Required**: Password hash strength, valid/invalid login, token refresh rotation, role permission guards.
- **Completion Criteria**: Tourists have zero auth barriers; admins receive JWTs and role-guarded endpoints function.
- **Checkpoint**: `CHECKPOINT-P4`

---

### PHASE 5 — PDF Document Management
- **Objective**: Secure administrative upload, validation, and storage of heritage PDF documents.
- **Scope**: Ingestion endpoints, MIME/magic byte inspection, SHA-256 deduplication, filesystem storage abstraction.
- **Tasks**:
  1. Create `documents` table model and migration.
  2. Build upload validator checking file size ($<50$MB), MIME type (`application/pdf`), and magic bytes (`%PDF-`).
  3. Implement SHA-256 calculation for deduplication (reject or reference existing hashes).
  4. Store physical files under secure UUID paths in `data/documents/`.
  5. Implement administrative CRUD endpoints: `/api/v1/admin/documents` (upload, list, inspect, delete).
  6. Log document upload actions in `audit_logs`.
- **Expected Files**: `backend/src/domain/document.py`, `backend/src/infrastructure/storage/local_storage.py`, `backend/src/presentation/api/admin_documents.py`.
- **Database Impact**: `documents` table migrated and active.
- **Tests Required**: Valid PDF upload, invalid magic byte rejection, oversized file rejection, SHA-256 deduplication test.
- **Completion Criteria**: Ingestion of `Temple_info.pdf` succeeds; hash and metadata recorded in MySQL.
- **Checkpoint**: `CHECKPOINT-P5`

---

### PHASE 6 — Knowledge Base Pipeline
- **Objective**: Construct the PDF parsing, structural chunking, embedding, and immutable knowledge generation engine.
- **Scope**: PyMuPDF extraction, semantic chunking, ChromaDB integration, and generation state machine.
- **Tasks**:
  1. Create `knowledge_generations`, `document_chunks`, `generation_status`, and `embeddings` models.
  2. Implement PDF text extraction and Unicode NFKC normalization using PyMuPDF (`fitz`).
  3. Implement structural semantic chunker (300-500 tokens, 50-token overlap, preserving headings and page numbers).
  4. Generate dense vectors using local `all-MiniLM-L6-v2` embeddings.
  5. Store vectors in isolated ChromaDB collection named `kbase_gen_{N}`.
  6. Store chunk text and metadata in MySQL `document_chunks`.
  7. Implement state machine: `BUILD` ➔ `PARSE` ➔ `CHUNK` ➔ `EMBED` ➔ `INDEX` ➔ `VALIDATE` ➔ `PROMOTE` ➔ `ACTIVE`.
  8. Implement zero-rebuild rollback endpoint to revert active pointer to previous generation.
- **Expected Files**: `backend/src/application/pipeline/extractor.py`, `backend/src/application/pipeline/chunker.py`, `backend/src/infrastructure/vector/chroma_store.py`, `backend/src/application/pipeline/generation_manager.py`.
- **Database Impact**: `knowledge_generations`, `document_chunks`, `embeddings` tables populated.
- **Tests Required**: PDF text extraction fidelity, chunk boundary verification, ChromaDB vector insertion, generation promotion and rollback.
- **Completion Criteria**: `Temple_info.pdf` processed into active generation with vector and relational records synchronized.
- **Checkpoint**: `CHECKPOINT-P6`

---

### PHASE 7 — RAG Retrieval Optimization
- **Objective**: Implement hybrid dense + sparse retrieval with Reciprocal Rank Fusion and Cross-Encoder re-ranking.
- **Scope**: BM25 indexer, ChromaDB dense query, RRF rank fusion, cross-encoder scoring, and noise filtering.
- **Tasks**:
  1. Build an in-memory BM25 index over the active generation's chunks.
  2. Implement dense retrieval against ChromaDB using query embeddings (Top-15).
  3. Implement sparse retrieval against BM25 (Top-15).
  4. Implement Reciprocal Rank Fusion (RRF with $k=60$) merging candidate sets.
  5. Integrate `cross-encoder/ms-marco-MiniLM-L-6-v2` to re-score top-10 fused candidates.
  6. Filter out boilerplates, bibliographies, and chunks scoring below threshold ($<0.35$).
  7. Expose diagnostic endpoint `/api/v1/admin/diagnostics/retrieval` displaying intermediate scores.
- **Expected Files**: `backend/src/application/rag/retriever.py`, `backend/src/application/rag/bm25.py`, `backend/src/application/rag/reranker.py`, `backend/src/presentation/api/diagnostics.py`.
- **Database Impact**: Read queries on `document_chunks`.
- **Tests Required**: Dense query precision, BM25 exact match recall, RRF merge ranking, re-ranker scoring speed.
- **Completion Criteria**: Retrieval pipeline executes in $<250$ms and returns relevant Belur Temple chunks for benchmark queries.
- **Checkpoint**: `CHECKPOINT-P7`

---

### PHASE 8 — Multilingual Conversation Engine
- **Objective**: Build session management, language auto-detection, and contextual multi-turn conversation handling.
- **Scope**: Chat sessions, Kannada/English detection, coreference resolution, and strict grounding verification.
- **Tasks**:
  1. Migrate and model `chat_sessions` and `chat_messages` tables.
  2. Implement language detector recognizing Kannada script, English, and mixed inputs.
  3. Build session context builder assembling conversation turns for coreference awareness.
  4. Implement strict Grounding Guard evaluating retrieval evidence before LLM synthesis.
  5. Enforce deterministic fallback string when evidence is missing:
     - English: `"Information is not available in the knowledge base."`
     - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
  6. Map citations down to chunk ID, document, and page number.
- **Expected Files**: `backend/src/domain/conversation.py`, `backend/src/application/chat/language_detector.py`, `backend/src/application/chat/conversation_manager.py`, `backend/src/application/chat/grounding_guard.py`.
- **Database Impact**: `chat_sessions` and `chat_messages` tables active.
- **Tests Required**: Kannada script detection, multi-turn context retention, grounding fallback trigger on out-of-domain queries.
- **Completion Criteria**: Multi-turn questions ("Who built it?", "Why?") resolve context accurately; fallbacks trigger reliably.
- **Checkpoint**: `CHECKPOINT-P8`

---

### PHASE 9 — Ollama LLM Integration
- **Objective**: Connect local Ollama server, build context-budgeted prompts, and stream grounded answers via SSE.
- **Scope**: Ollama client adapter, prompt templating, token window budgeting, SSE streaming endpoint.
- **Tasks**:
  1. Implement async Ollama client adapter supporting `llama3.1:8b` (default), `mistral:7b`, `qwen2.5`, `gemma2`.
  2. Implement prompt builder enforcing system grounding constraints and context budgeting (1500-token ceiling).
  3. Create streaming generation worker delivering token chunks.
  4. Implement SSE endpoint `/api/v1/chat/message` streaming tokens and citation metadata to the client.
  5. Log LLM latency, token counts, and completion status.
- **Expected Files**: `backend/src/infrastructure/llm/ollama_client.py`, `backend/src/application/chat/prompt_builder.py`, `backend/src/presentation/api/chat.py`.
- **Database Impact**: Message records updated with latency metrics.
- **Tests Required**: Ollama connection probe, context length budgeting, SSE stream integrity, prompt injection resistance.
- **Completion Criteria**: Streaming text answer in Kannada and English verified via curl SSE test with citations attached.
- **Checkpoint**: `CHECKPOINT-P9`

---

### PHASE 10 — Speech-To-Text (STT) [COMPLETED]
- **Objective**: Implement local, offline multilingual speech transcription using faster-whisper.
- **Scope**: Audio validation, container normalization, CTranslate2 Whisper engine, speech transcription API, and voice RAG streaming.
- **Status**: **COMPLETED & VERIFIED (Checkpoint: `CHECKPOINT-P10`)**
- **Tasks Completed**:
  1. Integrated `faster-whisper` (v1.2.1) and `ctranslate2` (v4.8.2) with `base` model (74M parameters, 145 MB). Auto-discovered Ollama CUDA 12 runtime DLLs (`cublas64_12.dll`) enabling native GPU execution on NVIDIA GeForce RTX 3050 with graceful CPU fallback (`int8`).
  2. Implemented strict audio payload validator supporting WebM, WAV, MP3, OGG, and M4A with 25 MB payload ceiling, magic byte checking, and duration guardrails (0.3s - 60.0s).
  3. Decoded incoming audio in-memory to 16kHz mono float32 PCM using `av` (PyAV v13.1.0) and `soundfile` without disk temporary files.
  4. Implemented RMS energy silence shortcut (<0.002 RMS) resolving silent audio in ~37ms and built-in Silero VAD filtering noisy inputs.
  5. Implemented CTranslate2 `WhisperEngine` supporting Kannada (`kn`) and English (`en`), returning transcript, language confidence, timestamps, and latency.
  6. Connected voice inputs to conversational RAG engine via `POST /api/v1/voice/chat` and `POST /api/v1/voice/stream` (SSE), preserving strict Grounding Guard, zero-auth access, and attribution citations.
  7. Exposed `GET /api/v1/voice/info`, `POST /api/v1/voice/transcribe`, `POST /api/v1/voice/chat`, and `POST /api/v1/voice/stream`.
- **Expected Files**:
  - `backend/src/domain/voice.py`
  - `backend/src/infrastructure/audio/whisper_engine.py`
  - `backend/src/application/voice/stt_service.py`
  - `backend/src/presentation/api/voice.py`
  - `tests/unit/test_voice_stt.py`
  - `tests/fixtures/audio/*`
- **Database Impact**: None.
- **Empirical Measurements & Completion Evidence**:
  - Spoken Kannada audio query (4.90s): **151ms** STT transcription latency (**PASS**, exceeds $<1.0$s criterion by $>6.5\times$).
  - Spoken English audio query (3.46s): **195ms** STT transcription latency.
  - Spoken Mixed-language audio query (4.25s): **156ms** STT transcription latency.
  - Pure silence audio query (3.00s): **37ms** instant RMS bypass latency.
  - Noisy audio query (3.00s): **68ms** VAD filtering latency.
  - Peak Simultaneous GPU VRAM (RTX 3050 8GB): **4563 MB** with Ollama `gemma3:4b` (4241 MB) + Whisper `base` (float16) resident, leaving **3479 MB** headroom.
  - Reliable CPU Fallback: Verified with `int8` quantization (English: 628ms, Kannada: 862ms).
  - Test Suite: 60/60 tests passing in 25.35s (100% pass rate, 0 regressions).
- **Setup & Offline Verification**:
  1. Dependencies: `pip install faster-whisper av<14 soundfile`.
  2. Local Models: Whisper `base` weights cached locally in `~/.cache/huggingface/hub/models--Systran--faster-whisper-base`.
  3. Completely Offline: No external HTTP calls, telemetry, or remote APIs invoked during transcription or audio processing.
- **Known Limitations**:
  1. Multilingual Kannada recognition in Whisper `base` outputs phonetic Latin or Kannada script; for higher Kannada script purity without romanization, domain fine-tuning or acoustic adaptation can be layered in future phases.
  2. Windows CUDA execution requires `cublas64_12.dll`, which `whisper_engine.py` auto-discovers from the local Ollama directory.
- **Manual Test Steps**:
  1. Health/Info Probe:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/voice/info
     ```
  2. Transcribe Audio Query:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/voice/transcribe \
          -F "audio_file=@tests/fixtures/audio/english_query.wav" \
          -F "language=en"
     ```
  3. Voice Chat with Grounded RAG:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/voice/chat \
          -F "audio_file=@tests/fixtures/audio/english_query.wav" \
          -F "preferred_language=en"
     ```
  4. Stream Voice Chat over SSE:
     ```bash
     curl -N -X POST http://127.0.0.1:8000/api/v1/voice/stream \
          -F "audio_file=@tests/fixtures/audio/english_query.wav"
     ```
- **Checkpoint**: `CHECKPOINT-P10` (Locked & Verified)

---

### PHASE 11 — Translation Hardening & Cross-Lingual RAG
- **Status**: **COMPLETED** (Checkpoint Locked & Verified)
- **Objective**: Implement lowest-latency, fully offline cross-lingual query normalization and translation hardening enabling Kannada tourist queries to accurately retrieve English knowledge base chunks without corrupting heritage terminology, hallucinations, or breaking existing contracts.
- **Scope**: Hybrid offline architecture: `ArgosTranslationEngine` discovering local `.argosmodel` packages, 30+ entity Belur heritage glossary with proper-noun masking/unmasking, question intent expansion, phonetic transliteration distinction, MySQL `translation_registry` synchronization, zero-overhead English passthrough, and seamless integration into `ConversationManager` and SSE streams.
- **Delivered Files**:
  - `backend/src/domain/translation.py`: Pydantic domain models (`NormalizedQuery`, `HeritageTermMapping`, `TranslationPackageInfo`, `TranslationStrategy`).
  - `backend/src/application/translation/heritage_glossary.py`: Canonical dictionary of 30+ Belur heritage entities (Belur, Chennakeshava, Vishnuvardhana, Shantala Devi, Madanika, Darpana Sundari, Jakanachari, Hoysala, Garbhagriha, Navaranga, Pushkarani) with entity masking/unmasking and intent expansion patterns.
  - `backend/src/infrastructure/translation/argos_engine.py`: Thread-safe offline Argos Translate runtime manager with package directory discovery (`data/models/argos`) and graceful failure fallback.
  - `backend/src/application/translation/transliteration.py`: Deterministic phonetic Kannada-to-Latin transliteration strictly distinguished from semantic translation.
  - `backend/src/application/translation/query_normalizer.py`: Cross-lingual query normalizer orchestrating English passthrough, entity preservation, intent expansion, common term mapping, and transliterated out-of-domain preservation.
  - `backend/src/application/translation/translator.py`: Service coordinating translation pipeline, glossaries, and MySQL `translation_registry` persistence.
  - `backend/src/presentation/api/translation.py`: REST routes (`GET /api/v1/translation/status`, `POST /api/v1/translation/normalize`, `POST /api/v1/translation/sync`).
  - `tests/unit/test_translation_hardening.py`: 13 automated unit & integration tests covering Kannada, English, mixed queries, empty inputs, offline fallbacks, grounding enforcement, and SSE compatibility.
  - `scripts/benchmark_retrieval_phase11.py`: Repeatable local retrieval quality and latency benchmark suite.
- **Database Impact**: `translation_registry` populated and synchronized with local installed translation models.
- **Empirical Measurements & Completion Evidence**:
  - **Kannada In-Domain Grounding**: Jumped from **0%** (0/3 on baseline monolingual retrieval) to **100% grounded** on indexed topics with top cross-encoder scores $>0.997$ and valid citations.
  - **Out-of-Domain Precision**: **100%** rejection (2/2) with immediate canonical Kannada fallback (`"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`), preventing hallucinations.
  - **Query Normalization Latency**: **0.126 ms** average overhead (**sub-millisecond**, $<1\%$ of retrieval time).
  - **English Passthrough**: **0.014 ms** zero-mutation overhead; English behavior and scores completely preserved ($0.9999$ top score).
  - **Total RAG Retrieval Latency**: **44 - 49 ms** for hybrid retrieval + re-ranking across both Kannada and English.
  - **Automated Test Suite**: **73/73 tests passing** in 26.74s (100% pass rate across all 11 phases, zero regressions).
- **Setup & Offline Verification**:
  1. Dependencies: `argostranslate>=1.9.0` installed in backend virtual environment.
  2. Offline Operation: Zero external network requests during runtime; operates entirely from local disk and RAM.
  3. Graceful Model Degradation: In the absence of heavy neural `.argosmodel` packages, falls back automatically to high-precision domain glossary + intent expansion + phonetic preservation.
- **Known Limitations**:
  1. Official Argos package repository currently has 100 packages but lacks an official `kn_en` / `en_kn` pre-packaged model. The hybrid deterministic glossary and intent expansion guarantees robust offline retrieval for all Belur temple entities and tourist inquiries without needing internet access.
- **Manual Test Steps**:
  1. Translation Status Probe:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/translation/status
     ```
  2. Normalize Query Probe:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/translation/normalize \
          -H "Content-Type: application/json" \
          -d "{\"query\": \"ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?\"}"
     ```
  3. Grounded Kannada Chat Turn:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/chat/message \
          -H "Content-Type: application/json" \
          -d "{\"content\": \"ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?\", \"preferred_language\": \"kn\"}"
     ```
  4. Out-of-Domain Kannada Rejection:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/chat/message \
          -H "Content-Type: application/json" \
          -d "{\"content\": \"ಮೈಸೂರು ಅರಮನೆಯ ಇತಿಹಾಸವೇನು?\", \"preferred_language\": \"kn\"}"
     ```
- **Checkpoint**: `CHECKPOINT-P11` (Locked & Verified)

---

### PHASE 12 — Text-To-Speech (TTS) [COMPLETED]
- **Status**: **COMPLETED & VERIFIED (Checkpoint: `CHECKPOINT-P12`)**
- **Objective**: Implement offline speech synthesis using Piper for Kannada and English with sub-600ms latency, zero GPU VRAM bloat, bounded LRU caching, and strict grounding safety.
- **Scope**: Piper local engine adapter (`piper_engine.py`), voice registry sync with MySQL `voice_registry`, bounded in-memory LRU audio cache (`tts_cache.py`), application TTS service (`tts_service.py`), public REST endpoints (`/api/v1/voice/synthesize`, `/api/v1/voice/tts/status`, `/api/v1/voice/tts/voices`, `/api/v1/voice/tts/sync`), and client Web Speech API fallback metadata.
- **Tasks Completed**:
  1. Integrated `piper-tts` (v1.8.0) and ONNX Runtime (v1.31.0) on CPU, maintaining zero additional VRAM footprint to leave full GPU headroom for Ollama `gemma3:4b`.
  2. Verified and provisioned genuine offline voice models:
     - English: `en_US-lessac-medium.onnx` (63.2 MB, 22050 Hz, LibriTTS / Public Domain).
     - Kannada: `kn_IN-syspin_male-medium.onnx` (63.5 MB, 22050 Hz, IISc Bangalore SYSPIN dataset, Apache 2.0 / open license).
  3. Built bounded in-memory LRU audio cache (`TTSAudioCache`) with 128 entries for canonical grounding fallbacks and short phrases (<=150 chars), delivering instant **0.10ms - 0.16ms** cache hits.
  4. Implemented in-flight request deduplication lock preventing duplicate concurrent CPU synthesis of identical queries.
  5. Implemented `TextToSpeechService` with script auto-detection fallback (`LanguageDetector`), length validation (1000 char limit), and 15-second timeout guard.
  6. Preserved strict GroundingGuard invariant: TTS only speaks answers already verified by GroundingGuard and never synthesizes or alters temple facts.
  7. Exposed public endpoints: `POST /api/v1/voice/synthesize`, `GET /api/v1/voice/tts/status`, `GET /api/v1/voice/tts/voices`, and `POST /api/v1/voice/tts/sync`.
  8. Created repeatable provisioning script `scripts/download_tts_models.py` and benchmark runner `scripts/benchmark_tts_phase12.py`.
- **Expected Files**:
  - `backend/src/infrastructure/audio/piper_engine.py`
  - `backend/src/infrastructure/audio/tts_cache.py`
  - `backend/src/application/voice/tts_service.py`
  - `backend/src/domain/voice.py`
  - `backend/src/presentation/api/voice.py`
  - `tests/unit/test_voice_tts.py`
  - `scripts/download_tts_models.py`
  - `scripts/benchmark_tts_phase12.py`
- **Database Impact**: `voice_registry` updated and synchronized with local installed voice models.
- **Empirical Measurements & Completion Evidence**:
  - Warm English Synthesis (148 chars, 9.64s audio): **184ms** latency (**RTF: 0.019x**, over $50\times$ faster than real-time; criterion: $<600$ms).
  - Warm Kannada Synthesis (124 chars, 11.45s audio): **217ms** latency (**RTF: 0.019x**, over $50\times$ faster than real-time; criterion: $<600$ms).
  - Short Canonical Fallback Synthesis (51 chars): **0.16ms** via LRU cache hit.
  - Concurrency Scaling (5 simultaneous requests): **168.9ms total** (average 33.8ms per request).
  - Added GPU VRAM Footprint: **0 MB** (100% CPU execution with ONNX Runtime, preserving GPU memory for Gemma).
  - Audio Format: Verified standard **22050Hz 16-bit Mono PCM WAV** playable natively in all browsers.
  - Automated Test Suite: **93/93 tests passing** in 33.51s (100% pass rate across all 12 modules, zero regressions).
- **Setup & Offline Verification**:
  1. Dependencies: `pip install piper-tts`.
  2. Model Provisioning: `python scripts/download_tts_models.py` provisions models once during setup to `data/models/piper/`.
  3. Runtime: 100% offline; zero network calls during synthesis. Models are never downloaded automatically during app startup.
- **Manual Test Steps**:
  1. TTS Status & Capability Probe:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/voice/tts/status
     ```
  2. List Registered Voices:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/voice/tts/voices
     ```
  3. Synthesize English Audio:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/voice/synthesize \
          -H "Content-Type: application/json" \
          -d '{"text": "Welcome to the Chennakeshava Temple at Belur.", "language": "en"}' \
          --output speech_en.wav
     ```
  4. Synthesize Kannada Audio:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/voice/synthesize \
          -H "Content-Type: application/json" \
          -d '{"text": "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯಕ್ಕೆ ಸುಸ್ವಾಗತ.", "language": "kn"}' \
          --output speech_kn.wav
     ```
  5. Sync Voice Registry to MySQL:
     ```bash
     curl -X POST http://127.0.0.1:8000/api/v1/voice/tts/sync
     ```
- **Checkpoint**: `CHECKPOINT-P12` (Locked & Verified)

---

### PHASE 13 — Unified FastAPI Client Gateway [COMPLETED]
- **Status**: **COMPLETED & VERIFIED (Checkpoint: `CHECKPOINT-P13`)**
- **Objective**: Consolidate and harden all tourist and admin endpoints into a unified `/api/v1` gateway with in-memory sliding-window rate limiting, anti-spoofing, health/readiness probes, and secure CORS.
- **Scope**: Canonical route organization under `/api/v1`, zero-auth tourist access preservation, JWT-derived admin rate-limit quotas, anti-spoofing header rejection, trusted proxy handling, structured HTTP 429 error envelopes with `Retry-After` headers, OpenAPI documentation with `BearerAuth` security schemes, and streaming/binary audio compatibility.
- **Tasks Completed**:
  1. Composed all functional routers under `api_v1_router` in `backend/src/presentation/router.py`:
     - System Health (`/api/v1/health`, `/api/v1/health/live`, `/api/v1/health/ready` + root `/health` alias)
     - Tourist Chat (`/api/v1/chat/message`, `/api/v1/chat/stream`, `/api/v1/chat/sessions`, `/api/v1/chat/sessions/{session_id}`)
     - Tourist Voice (`/api/v1/voice/info`, `/api/v1/voice/transcribe`, `/api/v1/voice/chat`, `/api/v1/voice/stream`, `/api/v1/voice/synthesize`, `/api/v1/voice/tts/status`, `/api/v1/voice/tts/voices`, `/api/v1/voice/tts/sync`)
     - Translation & Cross-Lingual RAG (`/api/v1/translation/status`, `/api/v1/translation/normalize`, `/api/v1/translation/sync`)
     - Admin Authentication (`/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`, `/api/v1/auth/me`, `/api/v1/auth/curator-zone`)
     - Admin Documents (`/api/v1/admin/documents`, `/api/v1/admin/documents/{document_id}`, `/api/v1/admin/documents/{document_id}/download`)
     - Admin Knowledge Base (`/api/v1/admin/knowledge/generations`, `/api/v1/admin/knowledge/generations/build`, `/api/v1/admin/knowledge/generations/rollback`, `/api/v1/admin/knowledge/generations/active`, `/api/v1/admin/knowledge/generations/{generation_id}`, `/api/v1/admin/knowledge/generations/{generation_id}/promote`)
     - Admin Diagnostics (`/api/v1/admin/diagnostics/retrieval`)
     - Admin Synchronization (`/api/v1/admin/sync/voice`, `/api/v1/admin/sync/translation`, `/api/v1/admin/sync/status`)
  2. Implemented thread-safe `RateLimiter` and `RateLimitMiddleware` in `backend/src/core/limiter.py`:
     - Default quotas: **60 req/min** for anonymous tourists, **120 req/min** for authenticated admins (`RATE_LIMIT_TOURIST_RPM` and `RATE_LIMIT_ADMIN_RPM`).
     - Uses monotonic clock (`time.monotonic()`) preventing NTP adjustments from distorting rate limits.
     - Anti-spoofing: Ignores client-supplied role headers (`X-Role`, `X-Admin`, `X-User-Type`). Derives admin quota exclusively from verified JWT access tokens.
     - Trusted proxy verification: Ignores `X-Forwarded-For` from untrusted peers. Only respects forwarding headers when peer socket IP is in `TRUSTED_PROXIES`.
     - Standard HTTP 429 response via `ErrorEnvelope` with `code: "RATE_LIMIT_EXCEEDED"`, `Retry-After`, and `X-RateLimit-*` headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).
     - Bounded memory with sliding-window prune cycle and hard client key ceiling (`RATE_LIMIT_MAX_TRACKED_CLIENTS=10000`).
     - Health probes (`/health`, `/api/v1/health*`) and OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) explicitly exempt from rate limiting.
  3. Preserved streaming integrity: SSE (`/api/v1/chat/stream`, `/api/v1/voice/stream`) and binary WAV audio responses pass cleanly without middleware buffering or corruption.
  4. Secured CORS: `cors_allow_credentials` property prevents wildcard origins (`*`) when credentials are enabled.
  5. Enriched OpenAPI schema with tag metadata and `BearerAuth` security schemes.
  6. Added 13 automated unit and integration tests in `tests/unit/test_unified_gateway.py`.
- **Expected Files**:
  - `backend/src/core/config.py`
  - `backend/src/core/errors.py`
  - `backend/src/core/limiter.py`
  - `backend/src/presentation/api/health.py`
  - `backend/src/presentation/api/admin_sync.py`
  - `backend/src/presentation/router.py`
  - `backend/src/main.py`
  - `tests/unit/test_unified_gateway.py`
- **Database / API Impact**: All API routers composed into `/api/v1`; zero database schema mutations required.
- **Empirical Measurements & Completion Evidence**:
  - **Automated Test Suite**: **106/106 tests passing** in 38.62s (100% pass rate across all 13 modules, zero regressions).
  - **Rate Limiting Accuracy**: Anonymous tourist quota strictly throttled at configured limit with HTTP 429 and `Retry-After` header. Authenticated admins reliably granted 120 RPM quota.
  - **Anti-Spoofing Immunity**: Spoofed `X-Admin-Role` or `X-Forwarded-For` headers from untrusted clients strictly rejected/ignored.
  - **Streaming Pass-Through**: SSE stream retains `text/event-stream`, `X-Accel-Buffering: no`, and rate-limit headers on the initial request.
- **Manual Test Probes**:
  1. Gateway Liveness Probe:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/health/live
     ```
  2. Gateway Deep Readiness Probe:
     ```bash
     curl -s http://127.0.0.1:8000/api/v1/health/ready
     ```
  3. OpenAPI Security & Tag Inspection:
     ```bash
     curl -s http://127.0.0.1:8000/openapi.json | jq .components.securitySchemes
     ```
  4. Tourist Rate Limit Probe:
     ```bash
     curl -i http://127.0.0.1:8000/api/v1/voice/tts/status
     ```
- **Checkpoint**: `CHECKPOINT-P13` (Locked & Verified)

---

### PHASE 14 — Premium Tourist Web Experience [COMPLETED]
- **Status**: **COMPLETED & VERIFIED (Checkpoint: `CHECKPOINT-P14`)**
- **Objective**: Build the production React 19 frontend implementing the Karnataka Heritage design system with conversational SSE streaming, offline voice STT/TTS widgets, citation inspection drawers, and interactive temple precinct map.
- **Scope**: Production React 19 + TypeScript + Vite 6 + Tailwind CSS application, Hoysala theme tokens, light and dark themes with WCAG 2.1 AA contrast compliance, resilient multibyte UTF-8 Kannada SSE stream parser, HTML5 MediaRecorder audio recording, 28-bar canvas gold wave frequency visualizer, Piper offline TTS playback, citation inspection slide-out drawer, interactive Belur Jagati precinct map, and zero-auth tourist access.
- **Tasks Completed**:
  1. Scaffolded React 19 + TypeScript + Vite + Tailwind CSS project under `frontend/` with strict type checking.
  2. Implemented Karnataka Heritage design system tokens (`frontend/src/theme/tokens.ts`, `frontend/tailwind.config.js`, `frontend/src/index.css`):
     - Hoysala palette: Temple Gold (`#D4AF37`), Heritage Brown (`#2C1810`), Soapstone Grey (`#4A4A4A`), Ivory (`#FDFBF7`), Midnight Basalt (`#120E0C`), Sandstone, and Marble.
     - Accessible focus rings, custom scrollbars, and `prefers-reduced-motion` compliance.
  3. Built responsive 3-column / mobile drawer layout shell (`frontend/src/features/layout/`):
     - `Header.tsx`: Language toggle (`ಕನ್ನಡ` / `English`), audio auto-speak toggle, light/dark mode switch, offline badge.
     - `Sidebar.tsx`: Session reset, grounding assurance guarantee, Belur attraction catalog.
     - `Layout.tsx`: Responsive viewport managing slide-over navigation and inspection drawers.
  4. Built conversational streaming interface (`frontend/src/features/chat/`):
     - `ChatContainer.tsx`: Message stream with auto-scroll and welcoming hero guide view.
     - `SuggestedQuestions.tsx`: Curated inquiries across History, Architecture, and Sculptures.
     - `MessageBubble.tsx`: Formatted assistant and user bubbles with verified grounding badges and citation pills.
     - `MessageInput.tsx`: Auto-expanding textarea supporting Unicode Kannada input with voice trigger.
  5. Built voice interaction & audio visualizer (`frontend/src/features/voice/`):
     - `AudioVisualizer.tsx`: 28-bar canvas frequency wave visualizer styled in radiant gold.
     - `VoiceWidget.tsx`: MediaRecorder capture with pulsing recording states and elapsed timer.
     - `audioService.ts`: Recording format negotiation, echo cancellation, and Piper WAV playback.
  6. Built inspection & spatial side panels (`frontend/src/features/citations/` & `frontend/src/features/map/`):
     - `CitationDrawer.tsx`: Slide-over drawer displaying document filename, page number, relevance match score (%), and verbatim knowledge chunk excerpt.
     - `TourismMap.tsx`: Stylized interactive precinct map of the Belur Jagati platform with 5 major Hoysala monument pins and quick-inquiry triggers.
  7. Built resilient SSE parser (`frontend/src/services/streaming.ts`):
     - Decodes multibyte UTF-8 Kannada characters across arbitrary network chunk boundaries.
     - Handles `token`, `citations`, `done`, `error` events and clean `AbortSignal` cancellation.
  8. Authored 17 automated tests with Vitest and React Testing Library (`frontend/src/tests/`):
     - Verified SSE parser with chunk boundary splits, Kannada multibyte decoding, error handling, and aborts.
     - Verified API client contracts against `/api/v1` chat, sessions, voice, tts, and error envelopes.
     - Verified component rendering, language switching, message flow, and accessibility.
- **Delivered Files**:
  - `frontend/package.json`
  - `frontend/tsconfig.json`
  - `frontend/vite.config.ts`
  - `frontend/tailwind.config.js`
  - `frontend/postcss.config.js`
  - `frontend/index.html`
  - `frontend/src/index.css`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/theme/tokens.ts`
  - `frontend/src/types/api.ts`
  - `frontend/src/services/api.ts`
  - `frontend/src/services/streaming.ts`
  - `frontend/src/services/audio.ts`
  - `frontend/src/features/layout/Header.tsx`
  - `frontend/src/features/layout/Sidebar.tsx`
  - `frontend/src/features/layout/Layout.tsx`
  - `frontend/src/features/chat/ChatContainer.tsx`
  - `frontend/src/features/chat/MessageBubble.tsx`
  - `frontend/src/features/chat/CitationBadge.tsx`
  - `frontend/src/features/chat/SuggestedQuestions.tsx`
  - `frontend/src/features/chat/MessageInput.tsx`
  - `frontend/src/features/voice/AudioVisualizer.tsx`
  - `frontend/src/features/voice/VoiceWidget.tsx`
  - `frontend/src/features/citations/CitationDrawer.tsx`
  - `frontend/src/features/map/TourismMap.tsx`
  - `frontend/src/tests/setup.ts`
  - `frontend/src/tests/streaming.test.ts`
  - `frontend/src/tests/api.test.ts`
  - `frontend/src/tests/components.test.tsx`
- **Database / API Impact**: Consumes existing `/api/v1` gateway endpoints; zero backend schema changes required.
- **Empirical Measurements & Completion Evidence**:
  - **Frontend Build**: `npm run build` succeeds cleanly in 1.57s (Production bundle: 285 kB JS / 85 kB gzip, 27 kB CSS).
  - **Frontend Automated Tests**: **17/17 tests passing** in 1.28s (100% pass rate).
  - **Backend Automated Regression Suite**: **106/106 tests passing** in 64.03s (100% pass rate across all 13 modules, zero regressions).
  - **Total Repo Automated Tests**: **123/123 tests passing** (100% pass rate).
  - **Multilingual Support**: Verified Kannada script rendering, input handling, and language toggle.
  - **Frictionless Tourist Access**: Strictly zero authentication required for public tourist exploration.
- **Verification Commands**:
  1. Typecheck: `npx tsc --noEmit` (exit code 0)
  2. Frontend Tests: `npm run test` (17 passed)
  3. Production Build: `npm run build` (exit code 0)
  4. Backend Regression: `pytest -v` (106 passed)
- **Checkpoint**: `CHECKPOINT-P14` (Locked & Verified)

---

### PHASE 15 — Premium Admin Dashboard [COMPLETED]
- **Status**: **COMPLETED & VERIFIED (Checkpoint: `CHECKPOINT-P15`)**
- **Objective**: Build the administrative control center for knowledge management, diagnostics, and telemetry.
- **Scope**: In-memory admin authentication, role-based navigation (SUPER_ADMIN, SITE_CURATOR, OPERATOR, VIEWER), PDF document ingestion & lifecycle, knowledge generation pipeline & instant rollback (<100ms), offline voice & translation model registry sync, hybrid RAG retrieval diagnostic probe, and real-time system telemetry.
- **Tasks Completed**:
  1. Implemented secure In-Memory Admin Authentication (`frontend/src/services/auth.ts`):
     - Zero tokens in localStorage or sessionStorage.
     - Token rotation lifecycle via `/api/v1/auth/refresh`.
     - Explicit logout with `/api/v1/auth/logout` audit logging and memory wipe.
     - RBAC hierarchy: `SUPER_ADMIN` (4) > `SITE_CURATOR` (3) > `OPERATOR` (2) > `VIEWER` (1).
  2. Built Typed Admin API Client (`frontend/src/services/adminApi.ts`):
     - Bearer authorization attachment, automatic 401 retry with token refresh rotation, ErrorEnvelope unmarshaling.
  3. Built Document Management interface (`frontend/src/features/admin/DocumentManager.tsx`):
     - Document inventory table with pagination, search filter, SHA-256 hash copy button, download trigger, and explicit delete confirmation dialog (`SITE_CURATOR+`).
     - Client-side validation enforcing authentic `.pdf` extensions and 50MB file size ceiling.
  4. Built Knowledge Generation Manager (`frontend/src/features/admin/GenerationManager.tsx`):
     - Timeline stepper showing execution steps (`PARSE`, `CHUNK`, `EMBED`, `INDEX`, `VALIDATE`, `PROMOTE`) with progress percentages and errors.
     - Trigger Build button with bounded status polling (every 3s, max 30 iterations) and unmount cleanup.
     - Active generation radiant gold badge and promotion action.
     - Instant Rollback modal dialog with target generation selector (<100ms pointer update).
  5. Built Model & Translation Registry Sync (`frontend/src/features/admin/ModelSyncTab.tsx`):
     - Air-gapped offline synchronization of discovered Piper TTS voices and Argos translation packages into MySQL registries (`OPERATOR+`).
  6. Built Hybrid RAG Retrieval Diagnostics (`frontend/src/features/admin/DiagnosticsTab.tsx`):
     - Interactive probe tool evaluating test queries with configurable hyperparameters (`top_dense`, `top_sparse`, `top_fused`, `top_final`, `score_threshold`).
     - Candidate view across Chroma dense cosine scores, BM25 sparse scores, RRF fusion ranks, and Cross-Encoder re-rank confidence scores with latency profiling.
  7. Built Real-Time System Telemetry (`frontend/src/features/admin/OverviewTab.tsx`):
     - Live status cards based strictly on verified `/api/v1/health` and `/api/v1/admin/sync/status` endpoints with honest metric reporting.
  8. Created comprehensive automated tests (`frontend/src/tests/`):
     - Auth lifecycle, zero browser storage, role hierarchy, 401 retry, documents, generations, models, diagnostics, and dashboard navigation.
- **Delivered Files**:
  - `frontend/src/types/api.ts` (extended with admin contracts)
  - `frontend/src/services/auth.ts`
  - `frontend/src/services/adminApi.ts`
  - `frontend/src/features/admin/AdminLogin.tsx`
  - `frontend/src/features/admin/AdminDashboard.tsx`
  - `frontend/src/features/admin/OverviewTab.tsx`
  - `frontend/src/features/admin/DocumentManager.tsx`
  - `frontend/src/features/admin/GenerationManager.tsx`
  - `frontend/src/features/admin/ModelSyncTab.tsx`
  - `frontend/src/features/admin/DiagnosticsTab.tsx`
  - `frontend/src/tests/adminAuth.test.ts`
  - `frontend/src/tests/adminApi.test.ts`
  - `frontend/src/tests/adminComponents.test.tsx`
- **Database / API Impact**: Consumes existing `/api/v1/admin/*`, `/api/v1/auth/*`, and `/api/v1/health` endpoints; zero backend schema changes required.
- **Empirical Measurements & Completion Evidence**:
  - **Frontend Build**: `npm run build` succeeds cleanly in 1.64s (Production bundle: 364 kB JS / 99 kB gzip, 34 kB CSS).
  - **Frontend Automated Tests**: **41/41 tests passing** in 1.64s (100% pass rate).
  - **Backend Automated Regression Suite**: **106/106 tests passing** in 40.17s (100% pass rate across all 13 modules, zero regressions).
  - **Total Repo Automated Tests**: **147/147 tests passing** (100% pass rate).
  - **Zero Browser Storage Footprint**: Verified 0 tokens in localStorage/sessionStorage.
- **Verification Commands**:
  1. Typecheck: `npx tsc --noEmit` (exit code 0)
  2. Frontend Tests: `npm run test` (41 passed)
  3. Production Build: `npm run build` (exit code 0)
  4. Backend Regression: `pytest -q` (106 passed)
- **Checkpoint**: `CHECKPOINT-P15` (Locked & Verified)

---

### PHASE 16 — End-to-End Integration
- **Objective**: Wire all frontend and backend subsystems together and validate full live user workflows.
- **Scope**: Full-loop validation across voice input, transcription, hybrid RAG, LLM synthesis, TTS, and citation rendering.
- **Tasks**:
  1. Validate complete Tourist Voice Flow: Browser mic ➔ Whisper STT ➔ Hybrid RAG ➔ Ollama LLM ➔ Piper TTS ➔ Audio playback.
  2. Validate complete Tourist Text Flow: Text query ➔ RAG ➔ Streaming SSE ➔ Citation Drawer inspect.
  3. Validate Admin Lifecycle Flow: PDF upload ➔ Pipeline run ➔ Chunk check ➔ Generation promotion ➔ Instant rollback.
  4. Validate fallback behavior on non-temple queries in both Kannada and English.
- **Expected Files**: `tests/integration/test_e2e_workflow.py`.
- **Database / API Impact**: Live verification across all tables and routes.
- **Tests Required**: Automated E2E test runner executing tourist queries and admin flows against running containers.
- **Completion Criteria**: 100% of core tourist and admin user journeys pass without manual intervention.
- **Checkpoint**: `CHECKPOINT-P16`

---

### PHASE 17 — Docker & Cloud Deployment
- **Objective**: Create reproducible containerized environments for local standalone and cloud deployments.
- **Scope**: Dockerfiles, Docker Compose, Nginx reverse proxy, environment profiles, persistent volume mounts.
- **Tasks**:
  1. Author multi-stage `Dockerfile.backend` (Python 3.12, CTranslate2, Piper dependencies).
  2. Author multi-stage `Dockerfile.frontend` (Node build to Nginx static serve).
  3. Build `docker-compose.yml` orchestrating: `backend`, `frontend`, `mysql`, `chromadb`, `ollama`.
  4. Configure Nginx reverse proxy with gzip compression, SSE buffering disablement, and security headers.
  5. Verify single-command local offline startup (`docker compose up`).
- **Expected Files**: `deployment/docker/Dockerfile.backend`, `deployment/docker/Dockerfile.frontend`, `deployment/docker/docker-compose.yml`, `deployment/nginx/nginx.conf`.
- **Database Impact**: Persistent volume mounts for MySQL data and ChromaDB vectors.
- **Tests Required**: Container build smoke tests, volume persistence verification across container restart.
- **Completion Criteria**: System boots cleanly via Docker Compose with zero external internet access.
- **Checkpoint**: `CHECKPOINT-P17`

---

### PHASE 18 — Performance & Scalability
- **Objective**: Profile and optimize verified bottlenecks across database queries, RAG retrieval, and LLM streaming.
- **Scope**: Empirical latency profiling, index tuning, connection pooling optimization, caching.
- **Tasks**:
  1. Profile API latency with Locust / Pytest-benchmark.
  2. Add compound database indexes on `document_chunks (generation_id, page_number)` and `chat_messages (session_id, created_at)`.
  3. Optimize BM25 in-memory indexing to build in $<100$ms upon generation promotion.
  4. Tune Ollama context parameters (`num_ctx=2048`, `num_predict=512`) for minimum time-to-first-token.
  5. Validate concurrency: handle 20 concurrent tourist chat streams without timeout.
- **Expected Files**: `tests/benchmarks/benchmark_latency.py`, `backend/src/infrastructure/database/migrations/indexes.py`.
- **Database Impact**: Compound indexes applied to hot MySQL tables.
- **Tests Required**: Latency benchmarks before and after optimization.
- **Completion Criteria**: RAG pipeline latency $<250$ms; Time-to-first-token $<800$ms on GPU / $<2.5$s on CPU.
- **Checkpoint**: `CHECKPOINT-P18`

---

### PHASE 19 — Monitoring & Analytics
- **Objective**: Implement telemetry, system resource tracking, and operational analytics.
- **Scope**: Health background worker, resource snapshotting into `health_metrics`, usage analytics.
- **Tasks**:
  1. Implement background async worker collecting CPU, RAM, disk, and MySQL query rates every 5 seconds.
  2. Store hourly rollups in `health_metrics` with 30-day retention cleanup.
  3. Implement conversation analytics tracking query volume, language breakdown (Kannada vs. English), and average latency.
  4. Expose `/api/v1/admin/analytics/overview` for Admin Dashboard charts.
- **Expected Files**: `backend/src/infrastructure/monitoring/telemetry_collector.py`, `backend/src/presentation/api/admin_analytics.py`.
- **Database Impact**: `health_metrics` populated periodically.
- **Tests Required**: Metric collection accuracy, background worker resource overhead ($<1\%$ CPU).
- **Completion Criteria**: Admin Dashboard displays live, updating telemetry charts and query metrics.
- **Checkpoint**: `CHECKPOINT-P19`

---

### PHASE 20 — Security Hardening
- **Objective**: Audit and enforce enterprise-grade security posture across the entire application stack.
- **Scope**: OWASP Top 10 mitigation, CORS restrictions, rate limiting, dependency vulnerability scans.
- **Tasks**:
  1. Run `pip-audit` / `safety` on backend dependencies and `npm audit` on frontend packages.
  2. Perform penetration testing against SQL injection, path traversal, and XSS.
  3. Enforce strict Content Security Policy (CSP), HSTS, and X-Content-Type-Options via Nginx/FastAPI.
  4. Audit logging compliance: verify zero PII, passwords, or JWT secrets in application logs.
  5. Enforce role-based token invalidation and refresh token blacklisting.
- **Expected Files**: `deployment/nginx/security_headers.conf`, `backend/src/core/security_audit.py`.
- **Database Impact**: None.
- **Tests Required**: Automated security test suite, bandit static analysis, CORS origin rejection tests.
- **Completion Criteria**: Zero high or critical vulnerabilities detected; security scan report clean.
- **Checkpoint**: `CHECKPOINT-P20`

---

### PHASE 21 — Testing & Verification
- **Objective**: Execute comprehensive multi-tier automated test suite verifying functional and non-functional requirements.
- **Scope**: Unit, integration, E2E, multilingual translation, voice, and accessibility test suites.
- **Tasks**:
  1. Run complete unit test suite achieving $>85\%$ coverage across domain and application layers.
  2. Run RAG evaluation test set measuring precision@3 and recall@3 against known Belur Temple facts.
  3. Run multilingual linguistic evaluation verifying correct Kannada phrasing and fallback behavior.
  4. Execute axe-core accessibility audit ensuring WCAG 2.1 AA compliance on all screens.
  5. Run 50-user load test verifying system stability under concurrent requests.
- **Expected Files**: `tests/unit/*`, `tests/integration/*`, `tests/evaluations/rag_eval.py`, `tests/accessibility/wcag_audit.py`.
- **Database Impact**: Test database populated and cleaned.
- **Tests Required**: Full test runner execution (`pytest`, `npm test`, `playwright`).
- **Completion Criteria**: 100% of test suites pass; zero regressions reported.
- **Checkpoint**: `CHECKPOINT-P21`

---

### PHASE 22 — Documentation
- **Objective**: Compile exhaustive, production-grade documentation for developers, administrators, and operators.
- **Scope**: Developer onboarding, local setup guide, cloud deployment runbook, API reference, admin manual.
- **Tasks**:
  1. Create `docs/DEVELOPER_SETUP.md` with step-by-step local workstation installation instructions.
  2. Create `docs/CLOUD_DEPLOYMENT.md` detailing Docker Compose, VPS provisioning, and TLS certificates.
  3. Create `docs/ADMIN_GUIDE.md` outlining PDF ingestion, generation promotion, and rollback procedures.
  4. Generate OpenAPI specification export in `docs/api/openapi.json`.
  5. Create `docs/TROUBLESHOOTING.md` covering common failure states (Ollama offline, MySQL connection pool exhausted).
- **Expected Files**: `docs/DEVELOPER_SETUP.md`, `docs/CLOUD_DEPLOYMENT.md`, `docs/ADMIN_GUIDE.md`, `docs/TROUBLESHOOTING.md`, `docs/api/openapi.json`.
- **Database / API Impact**: None.
- **Tests Required**: Technical writer verification of commands against clean workstation environment.
- **Completion Criteria**: An external engineer can install and run the platform using documentation alone.
- **Checkpoint**: `CHECKPOINT-P22`

---

### PHASE 23 — Production Readiness Review (GO / NO-GO)
- **Objective**: Conduct final multi-disciplinary review to decide GO or NO-GO for production launch.
- **Scope**: Architectural, security, performance, accessibility, operational, and disaster recovery audits.
- **Tasks**:
  1. Principal Architect review: verify Clean Architecture integrity and zero unwanted abstractions.
  2. Security review: verify zero leaked secrets, valid TLS, Argon2id parameters, and RBAC lockdown.
  3. Operational review: verify backup and restore scripts for MySQL and ChromaDB vectors.
  4. Disaster recovery drill: simulate Ollama failure and verify graceful degraded responses.
  5. Final human acceptance testing of Belur Temple conversational Q&A in Kannada and English.
  6. Sign off formal GO / NO-GO decision document.
- **Expected Files**: `docs/PRODUCTION_READINESS_REVIEW.md`.
- **Database / API Impact**: None.
- **Tests Required**: Disaster recovery test, backup restore test.
- **Completion Criteria**: Unanimous sign-off across all Principal roles; formal GO decision recorded.
- **Checkpoint**: `CHECKPOINT-P23`
