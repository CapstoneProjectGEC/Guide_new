# PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Project Title:** AI-Powered Smart Tourist Guide Platform for Karnataka  
**Document Version:** 1.0.0  
**Status:** Approved Baseline (Phase 1 Locked)  
**Author:** Unified Principal Engineering Team  

---

## 1. Executive Summary & Vision

The **AI-Powered Smart Tourist Guide Platform for Karnataka** is a commercial-grade, multilingual, offline-capable AI tourism platform. It delivers verified, citation-backed cultural, historical, architectural, and logistical intelligence to tourists exploring Karnataka’s heritage sites.

Initial validation focuses on the Hoysala architectural marvel of **Belur (Chennakeshava Temple)** via curated knowledge base ingestion (`Temple_info.pdf`), while the architecture is intentionally generalized to support multi-site Karnataka tourism (Hampi, Pattadakal, Badami, Halebidu, Mysore, etc.) and future regional languages without core redesign.

---

## 2. Problem Statement

1. **Information Fragmentation & Hallucination**: Tourists either rely on unverified online searches or generic LLM chatbots that hallucinate historical facts and temple architectural chronologies.
2. **Language Barriers**: International and regional tourists struggle to access authentic, verified folklore, temple architecture details, and local history in Kannada or regional languages.
3. **Connectivity Challenges**: Heritage monuments and rural archaeological sites often have degraded cellular reception; cloud-only AI assistants fail completely in these environments.
4. **Friction in Public Software**: Conventional tourism applications mandate registration, SMS OTPs, and profile creation, causing heavy user drop-off.

---

## 3. Product Principles & Invariant Guardrails

- **Zero-Friction Tourist Experience**: Tourists NEVER create accounts, NEVER log in, and NEVER supply personal data.
- **Strict Factual Grounding**: The conversational agent only answers based on verified ingested documents. It NEVER invents historical facts. If evidence is missing, it provides a deterministic, standard fallback response.
- **Offline & Local First**: Once models and packages are downloaded, the platform can operate completely self-contained on local hardware (Windows 10/11, Linux) or containerized VPS/cloud without recurring commercial API dependencies.
- **Pure Software Architecture**: The platform is 100% pure software (Web + Server + AI). Robotics, hardware sensors, Arduino, ROS2, and embedded microcontrollers are strictly out of scope.
- **Single Universal Codebase**: The identical codebase runs in local development (`dev`), standalone offline deployment (`standalone`), and cloud production (`cloud`) controlled entirely via environment variables.

---

## 4. User Personas & Core Journeys

### 4.1 Tourist (Unauthenticated)
- **Primary Persona**: Cultural tourist, student, backpacker, or researcher visiting Karnataka heritage sites.
- **Interaction Modes**:
  - Voice-driven conversational interaction (browser microphone, natural speech-to-speech feedback).
  - Text chat with instant streaming responses.
  - Interactive destination and nearby attraction exploration on OpenStreetMap.
  - Inspecting citation sources down to the exact document page and chunk.
- **Default Language**: Kannada (ಕನ್ನಡ) with auto-detection for English and mixed queries.

#### Tourist Journey
```text
[Landing Page] ➔ [Language Auto-Detect / Select] ➔ [Ask via Voice or Text]
       │
       ▼
[Instant Streaming Answer with Source Citations]
       │
       ├─► [Click Citation ➔ Side Panel Displays Source Page Excerpt]
       ├─► [Click Map ➔ Nearby Monuments & Heritage Route Displayed]
       └─► [Follow-Up Query with Maintained Conversational Context]
```

### 4.2 Administrator (Authenticated)
- **Primary Persona**: State tourism official, archaeological curator, or system administrator.
- **Interaction Modes**:
  - Secure login via Argon2id + JWT with refresh token rotation.
  - PDF document upload, validation, and SHA-256 deduplication.
  - Knowledge Base pipeline management (immutable generations: `BUILD` to `ACTIVE`).
  - Chunk & embedding inspection and retrieval diagnostic tests.
  - AI model selection (Ollama models: llama3.1:8b, mistral:7b, qwen2.5, gemma2).
  - Real-time system health, telemetry, and audit logs.

#### Admin Journey
```text
[Secure Login] ➔ [Admin Dashboard] ➔ [Upload New Monument PDF]
       │
       ▼
[Trigger Pipeline] ➔ [Parse ➔ Chunk ➔ MiniLM Embed ➔ ChromaDB Local Index]
       │
       ▼
[Inspect Chunks / Run Retrieval Diagnostics] ➔ [Promote Generation to ACTIVE]
       │
       ▼
[System Health Telemetry / Audit Logs Review]
```

---

## 5. Functional Requirements

### 5.1 Multilingual Conversational Engine
- **FR-01 (Language Detection)**: Automatically detect whether user query is in Kannada, English, or mixed-script.
- **FR-02 (Default Kannada)**: If query script is ambiguous or initiated via default greeting, respond in Kannada.
- **FR-03 (Conversational Memory)**: Maintain multi-turn conversational session context, supporting coreference resolution (e.g., "Who built it?" followed by "Why?").
- **FR-04 (Streaming Delivery)**: Stream AI answers to the frontend client via Server-Sent Events (SSE).

### 5.2 Retrieval-Augmented Generation (RAG)
- **FR-05 (Hybrid Retrieval)**: Execute dual retrieval:
  - Dense semantic retrieval via ChromaDB + `all-MiniLM-L6-v2` (384 dimensions).
  - Sparse lexical retrieval via BM25.
- **FR-06 (Fusion & Re-ranking)**: Fuse results using Reciprocal Rank Fusion (RRF) and re-rank top candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- **FR-07 (Context Filtering)**: Down-rank or exclude tables of contents, bibliographies, and repetitive boilerplates.
- **FR-08 (Citation Preservation)**: Maintain exact mapping to source document filename, page number, and chunk index for every factual statement.

### 5.3 Strict Grounding Policy
- **FR-09 (Grounding Validation)**: Answers must be strictly grounded in the ingested knowledge base.
- **FR-10 (Standard Fallback)**: When evidence is insufficient, the system must return:
  - English: `"Information is not available in the knowledge base."`
  - Kannada: `"ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ."`
  - LLM general parametric knowledge must never be used to fabricate answers.

### 5.4 Speech-to-Text & Text-to-Speech
- **FR-11 (Browser Audio Input)**: Capture microphone input directly using Web Audio API / `MediaRecorder` (WebM, WAV, MP3, OGG, M4A).
- **FR-12 (Local STT)**: Transcribe speech locally using `faster-whisper`, returning transcript, detected language, and confidence score.
- **FR-13 (Local TTS)**: Synthesize audio responses locally using Piper (with Kannada and English voice models) and stream audio back to the browser.
- **FR-14 (TTS Fallback)**: Support browser-native Web Speech Synthesis API as a fallback if the local TTS engine is under high load or disabled.

### 5.5 Document & Knowledge Base Management
- **FR-15 (PDF Ingestion)**: Support administrative upload of heritage PDF documents with file size limits (max 50MB), MIME check, magic-byte inspection, and SHA-256 deduplication.
- **FR-16 (Immutable Knowledge Generations)**: Every ingestion cycle creates an isolated, versioned generation (`BUILD` ➔ `PARSE` ➔ `CHUNK` ➔ `EMBED` ➔ `INDEX` ➔ `VALIDATE` ➔ `PROMOTE` ➔ `ACTIVE`).
- **FR-17 (Instant Rollback)**: Admins can instantly activate a previous verified generation without re-indexing.

### 5.6 Interactive Maps & Exploration
- **FR-18 (Geospatial Discovery)**: Interactive map powered by Leaflet and OpenStreetMap displaying Karnataka tourist destinations, heritage monuments, architectural points of interest, and nearby attractions.
- **FR-19 (Contextual Suggestions)**: Dynamically generate recommended follow-up questions and related monuments based on the active destination.

### 5.7 Administration & Observability
- **FR-20 (Role-Based Access Control)**: Admin roles: `SUPER_ADMIN`, `SITE_CURATOR`, `OPERATOR`, `VIEWER`.
- **FR-21 (Retrieval Diagnostics)**: Admin tool to run test queries, view hit scores, inspect dense vs. sparse rankings, and observe re-ranker weights.
- **FR-22 (System Health Probes)**: Monitor CPU, memory, disk, MySQL status, ChromaDB availability, Ollama responsiveness, Whisper, and Piper latency every 5 seconds.
- **FR-23 (Audit Logging)**: Comprehensive logging of all admin actions, document uploads, generation promotions, and configuration changes.

---

## 6. Non-Functional Requirements

### 6.1 Performance & Latency
- **NFR-01 (API Latency)**: Health checks and metadata APIs < 50ms.
- **NFR-02 (RAG Retrieval Latency)**: Dense + Sparse + Re-ranking pipeline < 250ms.
- **NFR-03 (Time-to-First-Token)**: Streaming LLM response initiates within 800ms on GPU, < 2.5s on modern multi-core CPU.
- **NFR-04 (STT Latency)**: Transcribe a 5-second audio clip in < 1.0s.
- **NFR-05 (TTS Latency)**: Synthesize audio response within 600ms of text completion.

### 6.2 Reliability & Offline Capability
- **NFR-06 (Offline Functionality)**: Standalone mode must function with zero internet connection once installed.
- **NFR-07 (Graceful Degradation)**: Failure of STT or TTS must leave text chat operational. Failure of ChromaDB or Ollama must return structured errors without crashing the FastAPI gateway.

### 6.3 Security & Compliance
- **NFR-08 (Zero Tourist PII)**: No tourist IP addresses, geolocation coordinates, or personal conversations are tied to identifiable user accounts.
- **NFR-09 (Password Hashing)**: Admin credentials hashed using Argon2id with recommended OWASP memory and iteration parameters.
- **NFR-10 (Token Security)**: Short-lived JWT access tokens (15 minutes) with rotating refresh tokens stored in secure, `HttpOnly`, `SameSite=Strict` cookies.
- **NFR-11 (OWASP Top 10 Mitigation)**: Strict input validation via Pydantic v2, parameterized queries via SQLAlchemy 2.x, strict CORS origin policies, rate limiting, and security headers (CSP, HSTS, X-Content-Type-Options).

### 6.4 Usability & Accessibility
- **NFR-12 (Accessibility Standard)**: WCAG 2.1 AA compliance across tourist and admin portals. Full keyboard navigability, high contrast text, and ARIA labels.
- **NFR-13 (Responsiveness)**: Fluid layout optimized for mobile smartphones (360px+), tablets, and high-resolution desktop displays.

---

## 7. Out of Scope

- Robotics, mobile robot chassis, LIDAR, ROS2, motors, and microcontrollers.
- Commercial payment gateway processing and ticket reservations (reserved for future phases).
- User accounts or authentication for general tourists.
- Cloud-only proprietary LLM APIs (OpenAI GPT-4, Anthropic Claude) in core offline mode.
- Non-Karnataka tourism databases during initial launch.

---

## 8. Acceptance Criteria

1. A tourist can visit the web application, immediately ask a question in Kannada or English via voice or text without logging in, and receive a streaming, citation-backed response within specified latency limits.
2. Clicking any citation opens a drawer displaying the exact extracted source text and page number from `Temple_info.pdf`.
3. If asked an out-of-scope query (e.g. "What is the capital of France?"), the assistant strictly replies with the mandated fallback message.
4. An admin can log in, upload a new monument PDF, watch the pipeline process chunks and embeddings into ChromaDB and MySQL, test retrieval, and promote the generation to active.
5. The entire application runs locally in Docker or standalone with zero active internet access.
