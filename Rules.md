# ENGINEERING RULES & DEVELOPMENT PROTOCOL

**Project Title:** AI-Powered Smart Tourist Guide Platform for Karnataka  
**Document Version:** 1.0.0  
**Status:** Approved Baseline (Phase 1 Locked)  
**Author:** Unified Principal Engineering Team  

---

## 1. Core Operating Mandate

All development sessions must strictly comply with this document. You are an engineering team governed by discipline, empirical evidence, and lean craftsmanship. 

**Core Principle:**
> Build the smallest, cleanest, maintainable, testable, production-quality implementation that completely satisfies the approved requirements. Do not over-engineer.

---

## 2. Invariant Locks & Negative Rules (NEVER DO THIS)

1. **NEVER Introduce Hardware or Robotics**:
   - Zero physical robotics code.
   - Absolutely no Arduino, Raspberry Pi, NVIDIA Jetson, ROS2, RPLIDAR, motor controllers, servo libraries, or chassis drivers.
   - The platform is **100% pure software**.

2. **NEVER Change the Database Engine**:
   - **MySQL 8.0 ONLY** (via async driver).
   - Never switch to PostgreSQL, SQLite, MongoDB, or arbitrary NoSQL stores for persistence.

3. **NEVER Authenticate General Tourists**:
   - Tourists must never see a login form, registration page, password prompt, or OTP requirement.
   - Interaction is completely frictionless.
   - Only administrators authenticate.

4. **NEVER Over-Engineer Abstractions**:
   - Do NOT introduce interface + implementation + factory + wrapper + manager cascades for simple operations.
   - Introduce abstract ports only where true physical decoupling is necessary (e.g., LLM provider, vector database, STT, TTS, file storage).

5. **NEVER Use Mocks or Fakes in Production**:
   - Production code paths must invoke genuine services (Ollama, ChromaDB, MySQL, Whisper, Piper).
   - If a service is down, report structured failure/degradation—never simulate fake AI generation in production code.

6. **NEVER Bypass Database Migrations**:
   - Never run raw SQL `CREATE TABLE` or `ALTER TABLE` statements in production code.
   - All schema modifications must occur via versioned, reversible Alembic migrations.

7. **NEVER Hardcode Secrets**:
   - Zero passwords, JWT signing keys, or tokens in git repositories or code.
   - Load everything via environment variables validated by `pydantic-settings`.

8. **NEVER Silently Redesign the Architecture**:
   - If a technical bottleneck requires architectural changes, you must stop, document the rationale, and wait for human approval.

---

## 3. Approved Technology Matrix

| Layer | Approved Technology | Locked Version | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python | 3.12+ | Modern AsyncIO performance, typing enhancements |
| **API Framework** | FastAPI | 0.115+ | High-performance async ASGI gateway, OpenAPI docs |
| **Data Validation** | Pydantic | 2.x | High-speed Rust-based schema validation |
| **Relational ORM** | SQLAlchemy | 2.0+ (Async) | Industry standard async ORM & query builder |
| **DB Migrations** | Alembic | 1.13+ | Deterministic database schema versioning |
| **Relational DB** | MySQL | 8.0 | Mandatory transactional data store |
| **Vector DB** | ChromaDB | Latest stable | Local persistent embedded vector search |
| **Embedding Model** | all-MiniLM-L6-v2 | 384 dimensions | Fast, high-density CPU-friendly embeddings |
| **LLM Runtime** | Ollama | Latest local | Local execution for llama3.1:8b & mistral:7b |
| **Speech-to-Text** | faster-whisper | Latest | High-speed CTranslate2 Whisper implementation |
| **Translation** | Argos Translate | Latest | Offline neural translation (English ↔ Kannada) |
| **Text-to-Speech** | Piper | Latest | Fast, natural-sounding local neural TTS |
| **Frontend Framework**| React | 19.x | Modern UI rendering, server component readiness |
| **Frontend Language** | TypeScript | 5.x (Strict) | Type safety, maintainability |
| **Build Tool** | Vite | 6.x | Fast build and HMR toolchain |
| **CSS Framework** | Tailwind CSS | Latest stable | Utility-first styling with design system tokens |
| **Component Library** | shadcn/ui | Radix-based | Accessible, customizable UI primitives |
| **Motion & Animation**| Framer Motion | Latest | Subtle micro-interactions and transitions |
| **Server State** | TanStack Query | v5 | Caching, deduplication, and background polling |
| **Client State** | Zustand | v5 | Minimal, lightweight client state management |
| **Mapping Engine** | Leaflet + OpenStreetMap| Latest | Pure open-source, local-friendly map rendering |

---

## 4. Lean Pragmatic Coding Directives

### 4.1 Simplicity First
- Do not write 50 lines of complex metaprogramming when 10 lines of standard library or native framework code suffice.
- Prefer standard library functions before reaching for external third-party dependencies.

### 4.2 Priority Order for Capabilities
1. Python / JavaScript Language Standard Library.
2. Existing project module or utility.
3. Framework-native feature (FastAPI / React).
4. Browser-native API (`MediaRecorder`, Web Audio API, Web Speech API).
5. Existing installed dependency.
6. **New external package** (requires explicit written justification).

### 4.3 Dependency Justification Protocol
Before adding any new dependency to `pyproject.toml` or `package.json`, record:
```text
Dependency: <package-name>
Problem Solved: <specific-need>
Why Standard/Existing Tools Are Insufficient: <explanation>
Why This Dependency Is Best Suited: <explanation>
```

### 4.4 Dead Code Elimination
Before marking any checkpoint complete:
- Remove unused imports.
- Delete obsolete draft functions or commented-out blocks.
- Purge scratch test scripts from production directories.

---

## 5. Security & Data Protection Standards

1. **Authentication & Session Safety**:
   - Passwords hashed with `Argon2id` (using standard OWASP parameters: $m=65536, t=3, p=4$).
   - JWT Access tokens expire in **15 minutes**. Refresh tokens expire in **7 days** with automatic token rotation.
   - Enforce RBAC roles: `SUPER_ADMIN`, `SITE_CURATOR`, `OPERATOR`, `VIEWER`.

2. **File Ingestion Safety**:
   - Limit uploaded PDFs to 50MB.
   - Validate MIME type header (`application/pdf`) and verify PDF magic bytes (`%PDF-`).
   - Hash file contents via SHA-256 for exact deduplication before storing on disk with secure UUID names.
   - Prevent path traversal attacks via strict filename sanitization.

3. **CORS & Headers**:
   - Explicit CORS whitelists in FastAPI middleware.
   - Enforce security headers: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 6. API & Communication Standards

- **Namespace**: All APIs must live under `/api/v1/...`.
- **Payloads**: All request and response bodies must be validated with Pydantic v2 schemas.
- **Errors**: Return standardized JSON error envelopes:
  ```json
  {
    "error": {
      "code": "ENTITY_NOT_FOUND",
      "message": "The requested document was not found.",
      "details": {},
      "correlation_id": "c1f7a0b3-..."
    }
  }
  ```
- **Real-Time Streaming**: Use Server-Sent Events (SSE) for token streaming. Avoid WebSockets unless bi-directional full-duplex communication is genuinely required.

---

## 7. Testing & Empirical Validation Rules

1. **Evidence-Based Completion**: Never claim a task or phase is finished without running verification commands and providing captured output.
2. **Test Suites**:
   - **Unit Tests**: Test domain calculations, chunking algorithms, prompt builders, and validation routines in total isolation.
   - **Integration Tests**: Verify database transactions, Alembic migrations, and FastAPI route responses against test containers or test schemas.
   - **Retrieval Benchmarks**: Measure recall, precision, and latency for RAG queries against known ground-truth datasets.
3. **Regression Safety**: Every phase completion requires running existing regression tests to verify zero breakage.

---

## 8. Git & Checkpoint Governance

- Checkpoints must follow the naming standard: `CHECKPOINT-P1` through `CHECKPOINT-P23`.
- Never create a checkpoint until all unit tests pass, documentation is synchronized, and dead code is purged.
- Update `Memory.md` at the conclusion of every phase with the exact next action.
