# SYSTEM ARCHITECTURE DOCUMENT

**Project Title:** AI-Powered Smart Tourist Guide Platform for Karnataka  
**Document Version:** 1.0.0  
**Status:** Approved Baseline (Phase 1 Locked)  
**Author:** Unified Principal Engineering Team  

---

## 1. Architectural Principles & Patterns

The platform implements **Pragmatic Clean Architecture**, enforcing clear boundaries across four conceptual layers without superfluous interfaces or abstraction bloat:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                              │
│   FastAPI Endpoints (REST + SSE)  │  Pydantic Schemas  │  React 19 SPA │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                        Application Layer                               │
│   Use Cases & Orchestrators (Chat, RAG, Voice, Ingestion, Monitoring)   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                           Domain Layer                                 │
│   Entities, Enums, Value Objects, Domain Exceptions, Pure Logic        │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                       Infrastructure Layer                             │
│   MySQL 8.0 (Async SQLAlchemy) │ ChromaDB │ Ollama │ Whisper │ Piper   │
│   Argos Translate │ File Storage │ Auth Providers │ System Metrics     │
└────────────────────────────────────────────────────────────────────────┘
```

### Layer Rules:
1. **Domain**: Zero external framework dependencies. Houses pure entities, custom exceptions, and core invariants.
2. **Application**: Orchestrates domain entities and infrastructure ports to execute user use cases.
3. **Infrastructure**: Implements adapter boundaries (Ollama client, ChromaDB client, faster-whisper worker, MySQL repositories, Argon2id hasher).
4. **Presentation**: Translates HTTP requests/events to application inputs, and serializes responses (FastAPI routes, dependency injection, React frontend).

---

## 2. High-Level System Component Diagram

```text
                          ┌─────────────────────────────┐
                          │   Tourist / Admin Browser   │
                          │   (React 19 + TypeScript)   │
                          └──────────────┬──────────────┘
                                         │ HTTPS / SSE
                                         ▼
                          ┌─────────────────────────────┐
                          │     Reverse Proxy / Nginx   │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │          FastAPI Client Gateway       │
                     │         (Python 3.12 / AsyncIO)       │
                     └───┬───────────┬───────────┬─────────┬─┘
                         │           │           │         │
          ┌──────────────┘           │           │         └──────────────┐
          ▼                          ▼           ▼                        ▼
┌──────────────────┐    ┌─────────────────┐ ┌───────────────┐   ┌─────────────────┐
│ MySQL 8.0 Engine │    │ ChromaDB Local  │ │ Ollama Server │   │ Voice & Trans   │
│ (Metadata, Auth, │    │ (Vector Store   │ │ (llama3.1:8b, │   │ (faster-whisper,│
│ Sessions, Logs)  │    │  all-MiniLM)    │ │  mistral:7b)  │   │  Argos, Piper)  │
└──────────────────┘    └─────────────────┘ └───────────────┘   └─────────────────┘
```

---

## 3. Database Architecture (MySQL 8.0)

All relational and transactional state resides strictly in **MySQL 8.0**.  
- **Driver**: Async MySQL (`asyncmy` / `aiomysql`) via SQLAlchemy 2.0.
- **Character Set**: `utf8mb4` with `utf8mb4_unicode_ci` (full multilingual Kannada support).
- **Time Zone**: Universal UTC for all internal timestamps.
- **Migration Engine**: Alembic.

### 3.1 Complete 17-Table Relational Schema

```text
1.  admins                 - Authenticated administrative accounts
2.  documents              - Ingested PDF documents and metadata
3.  document_chunks         - Extracted text chunks with page & heading mapping
4.  knowledge_generations   - Immutable generation versions (BUILD to ACTIVE)
5.  generation_status      - Real-time pipeline step execution tracker
6.  embeddings             - Chunk embedding references and metadata checksums
7.  chat_sessions          - Tourist and admin conversation sessions
8.  chat_messages          - Individual turns (query, answer, latency, language)
9.  audit_logs             - Immutable administrative action logs
10. system_logs            - Structured application event logs
11. deployment_history     - Record of schema migrations and deployments
12. health_metrics         - Periodic system resource snapshots
13. model_registry         - Registered LLM model configurations
14. voice_registry         - Configured STT/TTS voice models and profiles
15. translation_registry   - Installed offline Argos translation language pairs
16. system_settings        - Global application configuration key-values
17. citation_references    - Explicit many-to-many link between messages & chunks
```

### 3.2 Detailed Table Definitions

#### `admins`
- `id` (CHAR(36), PK): UUID.
- `username` (VARCHAR(64), UNIQUE, INDEX): Admin handle.
- `email` (VARCHAR(191), UNIQUE, INDEX): Email address.
- `password_hash` (VARCHAR(255)): Argon2id encoded hash.
- `role` (ENUM('SUPER_ADMIN', 'SITE_CURATOR', 'OPERATOR', 'VIEWER'), INDEX): RBAC role.
- `is_active` (BOOLEAN, DEFAULT TRUE): Account status.
- `created_at` (DATETIME(6), UTC): Creation timestamp.
- `updated_at` (DATETIME(6), UTC): Modification timestamp.

#### `documents`
- `id` (CHAR(36), PK): UUID.
- `filename` (VARCHAR(255)): Original filename.
- `storage_path` (VARCHAR(512)): Secure UUID-based filesystem path.
- `sha256_hash` (CHAR(64), UNIQUE, INDEX): Content deduplication hash.
- `file_size_bytes` (BIGINT): File size.
- `mime_type` (VARCHAR(64)): Verified MIME type.
- `page_count` (INT): Total pages.
- `uploaded_by_id` (CHAR(36), FK -> admins.id): Admin uploader.
- `created_at` (DATETIME(6), UTC).

#### `knowledge_generations`
- `id` (CHAR(36), PK): UUID.
- `generation_number` (INT, UNIQUE, INDEX): Monotonic integer sequence.
- `status` (ENUM('BUILD', 'PARSE', 'CHUNK', 'EMBED', 'INDEX', 'VALIDATE', 'PROMOTE', 'ACTIVE', 'ARCHIVED', 'FAILED'), INDEX).
- `chroma_collection_name` (VARCHAR(128)): Isolated Chroma collection identifier.
- `chunk_count` (INT, DEFAULT 0): Total chunks in generation.
- `created_by_id` (CHAR(36), FK -> admins.id).
- `created_at` (DATETIME(6), UTC).
- `promoted_at` (DATETIME(6), NULL, UTC).

#### `document_chunks`
- `id` (CHAR(36), PK): UUID.
- `document_id` (CHAR(36), FK -> documents.id, INDEX).
- `generation_id` (CHAR(36), FK -> knowledge_generations.id, INDEX).
- `chunk_index` (INT): Sequential chunk index within document.
- `page_number` (INT, INDEX): Source document page.
- `section_heading` (VARCHAR(255), NULL): Parsed heading hierarchy.
- `content` (TEXT): Cleaned chunk text.
- `token_count` (INT): Token count.
- `created_at` (DATETIME(6), UTC).

#### `chat_sessions`
- `id` (CHAR(36), PK): UUID.
- `client_fingerprint` (CHAR(64), INDEX): Non-PII session grouping identifier.
- `preferred_language` (VARCHAR(10), DEFAULT 'kn'): Active language code.
- `created_at` (DATETIME(6), UTC).
- `last_active_at` (DATETIME(6), UTC, INDEX).

#### `chat_messages`
- `id` (CHAR(36), PK): UUID.
- `session_id` (CHAR(36), FK -> chat_sessions.id, INDEX).
- `role` (ENUM('user', 'assistant', 'system')).
- `content` (TEXT): Query or response body.
- `detected_language` (VARCHAR(10)): Language detected for turn.
- `input_mode` (ENUM('text', 'voice')).
- `latency_ms` (INT, NULL): Total response processing latency.
- `is_grounded` (BOOLEAN, DEFAULT TRUE): Grounding guard indicator.
- `created_at` (DATETIME(6), UTC).

#### `citation_references`
- `id` (BIGINT, AUTO_INCREMENT, PK).
- `message_id` (CHAR(36), FK -> chat_messages.id, INDEX).
- `chunk_id` (CHAR(36), FK -> document_chunks.id, INDEX).
- `relevance_score` (FLOAT): RRF/Cross-Encoder score.

#### `audit_logs`
- `id` (BIGINT, AUTO_INCREMENT, PK).
- `admin_id` (CHAR(36), FK -> admins.id, NULL, INDEX).
- `action` (VARCHAR(64), INDEX): e.g., 'DOC_UPLOAD', 'GEN_PROMOTE'.
- `resource_type` (VARCHAR(64)): e.g., 'document', 'generation'.
- `resource_id` (VARCHAR(64), NULL).
- `payload` (JSON, NULL): Contextual details.
- `ip_address` (VARCHAR(45), NULL).
- `created_at` (DATETIME(6), UTC, INDEX).

---

## 4. AI & RAG Pipeline Architecture

```text
                  [User Input: Voice or Text]
                             │
                             ▼
                  [Language Auto-Detection]
                   (Kannada / English / Mixed)
                             │
                             ▼
                 [Query Formulation & Routing]
             (Coreference Resolution via Context)
                             │
           ┌─────────────────┴─────────────────┐
           ▼                                   ▼
[Dense Retrieval: ChromaDB]          [Sparse Retrieval: BM25]
(all-MiniLM-L6-v2, 384-dim)          (Lexical exact & stem match)
           │                                   │
           └─────────────────┬─────────────────┘
                             ▼
              [Reciprocal Rank Fusion (RRF)]
                             │
                             ▼
          [Cross-Encoder Re-Ranking Model]
       (cross-encoder/ms-marco-MiniLM-L-6-v2)
                             │
                             ▼
        [Context Filtering & Token Budget Selection]
      (Strip boilerplate; enforce 1500-token window)
                             │
                             ▼
                [Grounding Validation Guard]
          (Is context sufficient to answer query?)
            ├── NO ──► Return Canonical Fallback Message
            │          ("Information is not available...")
            ▼ YES
       [Ollama LLM (llama3.1:8b) Streaming Generation]
                             │
                             ▼
           [Citations Embedded & SSE Streamed to Client]
                             │
           (If Voice Mode requested: Piper TTS Synthesizer)
```

### 4.1 Hybrid Retrieval & Fusion
1. **Dense Search**: Query embedding via `all-MiniLM-L6-v2` queries the active ChromaDB generation collection (Cosine Similarity, Top-K = 15).
2. **Sparse Search**: Query tokenized and scored against in-memory BM25 index built over the active generation's chunks (Top-K = 15).
3. **Reciprocal Rank Fusion (RRF)**:
   $$RRF(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{k + r_m(d)} \quad (k = 60)$$
4. **Re-Ranking**: Top 10 fused candidates are scored through `cross-encoder/ms-marco-MiniLM-L-6-v2`. Top 4 chunks exceeding confidence threshold ($>0.35$) are passed into context.

### 4.2 Knowledge Base Ingestion & Immutable Generation Lifecycle
- Documents are never indexed directly into production collections.
- Each run builds a new generation:
  1. `BUILD`: Allocate `generation_number` and isolated collection `kbase_gen_{N}`.
  2. `PARSE`: PyMuPDF reads text, tables, and page metadata; runs NFKC Unicode normalization.
  3. `CHUNK`: Semantic chunking (300-500 tokens with 50-token overlap, respecting paragraph/section boundaries).
  4. `EMBED`: Compute embeddings via local `sentence-transformers/all-MiniLM-L6-v2`.
  5. `INDEX`: Ingest vectors into ChromaDB collection `kbase_gen_{N}` and MySQL `document_chunks`.
  6. `VALIDATE`: Run automated regression questions against new collection.
  7. `PROMOTE`: Update `generation_status` to `ACTIVE`; point runtime pointer to `kbase_gen_{N}`.
  8. `ROLLBACK`: Re-pointing the pointer to `kbase_gen_{N-1}` completes in $<100$ms without data deletion.

---

## 5. Voice & Multilingual Pipeline

### 5.1 Speech-to-Text (STT)
- **Input Capture**: Browser `MediaRecorder` buffers audio into Opus/WebM or PCM WAV.
- **Backend Worker**: Transcribed via `faster-whisper` (`base` or `small` model running locally).
- **Language Detection**: Whisper outputs detected language and confidence. Kannada speech is tagged with code `kn`.

### 5.2 Offline Translation Subsystem
- **Engine**: Argos Translate offline package (`en_kn` and `kn_en`).
- **Domain Dictionary**: Preserves proper nouns, temple names, dynasties, and architectural terms (e.g., Hoysala, Vishnuvardhana, Chennakeshava, Garbhagriha, Madanika, Dwarpala).

### 5.3 Text-to-Speech (TTS)
- **Engine**: Piper TTS running locally.
- **Voices**: Kannada voice model (`kn_IN`) and English voice model (`en_US`/`en_GB`).
- **Delivery**: Streams audio chunks (`audio/wav`) to the browser; synchronized visualizer on the frontend.
- **Client Fallback**: If server Piper process is unavailable, fallback to browser Web Speech Synthesis API.

---

## 6. Unified Client Gateway (API Architecture)

All endpoints reside under the `/api/v1` namespace.

### 6.1 Endpoint Specification

| Method | Endpoint | Access | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Public | System and component health probes |
| `POST`| `/api/v1/chat/message` | Public (Tourist) | Send text query, receive streaming SSE answer |
| `POST`| `/api/v1/voice/transcribe` | Public (Tourist) | Upload audio clip, receive STT transcript |
| `POST`| `/api/v1/voice/synthesize` | Public (Tourist) | Stream synthesized Piper TTS audio |
| `GET` | `/api/v1/destinations` | Public (Tourist) | List tourism spots, coordinates, and metadata |
| `GET` | `/api/v1/destinations/{id}/nearby` | Public (Tourist) | Nearby attractions and heritage routes |
| `POST`| `/api/v1/auth/login` | Public | Admin login (returns JWT tokens) |
| `POST`| `/api/v1/auth/refresh` | Public | Rotate JWT access and refresh tokens |
| `POST`| `/api/v1/auth/logout` | Authenticated | Revoke refresh token |
| `POST`| `/api/v1/admin/documents` | Admin (Curator+) | Upload monument PDF |
| `GET` | `/api/v1/admin/documents` | Admin (Viewer+) | List ingested documents and statuses |
| `POST`| `/api/v1/admin/generations/build` | Admin (Curator+) | Trigger ingestion pipeline |
| `POST`| `/api/v1/admin/generations/{id}/promote` | Admin (SuperAdmin) | Promote generation to ACTIVE |
| `POST`| `/api/v1/admin/generations/{id}/rollback` | Admin (SuperAdmin) | Rollback to prior generation |
| `GET` | `/api/v1/admin/diagnostics/retrieval` | Admin (Viewer+) | Run retrieval test with diagnostic scores |
| `GET` | `/api/v1/admin/telemetry` | Admin (Operator+) | Live CPU, memory, DB, Ollama metrics |

### 6.2 SSE Streaming Contract
For `/api/v1/chat/message`:
```text
event: token
data: {"text": "King "}

event: token
data: {"text": "Vishnuvardhana..."}

event: citations
data: [{"chunk_id": "...", "doc": "Temple_info.pdf", "page": 4, "excerpt": "..."}]

event: done
data: {"latency_ms": 740, "grounded": true}
```

---

## 7. Frontend Architecture (React 19 SPA)

- **Framework**: React 19 + TypeScript + Vite.
- **Styling**: Tailwind CSS + custom heritage theme tokens (`#D4AF37`, `#2C1810`, `#4A4A4A`, `#FDFBF7`).
- **UI Components**: shadcn/ui primitives.
- **Animations**: Framer Motion (subtle, non-distracting micro-interactions).
- **State Management**:
  - `Zustand`: Chat session state, audio visualizer state, active destination panel.
  - `TanStack Query`: Server state caching, background polling for admin health metrics.
- **Map Visualizations**: Leaflet + OpenStreetMap (custom Hoysala-themed map pins).

---

## 8. Repository & Directory Structure

```text
d:/vikasAn/
├── PRD.md
├── Architecture.md
├── Rules.md
├── Phases.md
├── Design.md
├── Memory.md
│
├── docs/
│   ├── CHECKPOINTS.md
│   ├── changelog.md
│   ├── milestones.md
│   └── design/
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   └── src/
│       ├── core/           # Config, logging, security, errors
│       ├── domain/         # Pure entities, domain exceptions
│       ├── application/    # Orchestrators (RAG, Chat, Voice, Pipeline)
│       ├── infrastructure/ # MySQL, ChromaDB, Ollama, Whisper, Piper
│       └── presentation/   # FastAPI routes, schemas, dependencies
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── assets/
│       ├── components/     # UI primitives & composite widgets
│       ├── features/       # Chat, Voice, Explorer, Admin
│       ├── hooks/
│       ├── services/       # API clients & SSE listeners
│       └── store/          # Zustand stores
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── benchmarks/
│
├── deployment/
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── docker-compose.yml
│   └── nginx/
│       └── nginx.conf
│
└── scripts/
    ├── setup_local.sh
    └── download_models.py
```

---

## 9. Security & Deployment Profiles

### 9.1 Deployment Modes (`APP_PROFILE`)
1. **`dev`**: Local development; hot reloading; SQLite/mock tests allowed in test harness only; local MySQL on `localhost:3306`.
2. **`standalone`**: Production offline mode on single Windows/Linux workstation; local Ollama, local ChromaDB, local MySQL service, preloaded Piper/Whisper weights.
3. **`cloud`**: Multi-container Docker Compose setup behind Nginx reverse proxy with TLS termination.
