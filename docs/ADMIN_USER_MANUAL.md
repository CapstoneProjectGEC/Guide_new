# Heritage Administration & Knowledge Governance User Manual
**AI-Powered Smart Tourist Guide Platform for Karnataka**  
*Belur Chennakeshava Temple & Multi-Site Heritage Governance*

---

## Table of Contents
1. [Introduction & Architectural Context](#1-introduction--architectural-context)
2. [Security Invariants & Authentication Protocol](#2-security-invariants--authentication-protocol)
3. [Role-Based Access Control (RBAC) Matrix](#3-role-based-access-control-rbac-matrix)
4. [Accessing the Administrator Portal](#4-accessing-the-administrator-portal)
5. [Provisioning Administrator Accounts (CLI / Seed)](#5-provisioning-administrator-accounts-cli--seed)
6. [Tab 1: System & Knowledge Base Overview](#6-tab-1-system--knowledge-base-overview)
7. [Tab 2: Document Catalog & Ingestion Manager](#7-tab-2-document-catalog--ingestion-manager)
8. [Tab 3: Knowledge Pipeline & Generation Governance](#8-tab-3-knowledge-pipeline--generation-governance)
9. [Tab 4: Voice & Translation Model Registry](#9-tab-4-voice--translation-model-registry)
10. [Tab 5: Retrieval Diagnostics & RAG Tuning](#10-tab-5-retrieval-diagnostics--rag-tuning)
11. [Audit Logging & Security Compliance](#11-audit-logging--security-compliance)
12. [Troubleshooting & Operational FAQ](#12-troubleshooting--operational-faq)

---

## 1. Introduction & Architectural Context

The **AI-Powered Smart Tourist Guide Platform for Karnataka** is an offline-capable, commercial-grade cultural intelligence platform delivering citation-backed historical and architectural information.

While public visitors explore the monument through a zero-friction, registration-free interface, the **Heritage Administrator Portal** provides administrative staff, site curators, and IT operators with governance controls over:
- Monument PDF literature ingestion and deduplication.
- Immutable Knowledge Generation builds (parsing, chunking, MiniLM vector indexing, and BM25 sparse indexing).
- Real-time promotion and atomic zero-downtime rollback of active RAG indexes.
- Local speech synthesis (Piper TTS) and neural translation (Argos Translate) synchronization.
- Multi-stage retrieval diagnostics (Dense, Sparse, Reciprocal Rank Fusion, Cross-Encoder reranking).

---

## 2. Security Invariants & Authentication Protocol

The platform implements security guardrails designed for high-integrity public heritage platforms:

- **Zero-Storage Protocol**: Administrative JWT access and refresh tokens are maintained strictly within **volatile client memory** (React state / closure). Tokens are **never** written to `localStorage`, `sessionStorage`, or unencrypted cookies. Closing the browser tab or clicking *Logout* immediately clears all tokens.
- **Argon2id Password Hashing**: Passwords are cryptographically salted and hashed using Argon2id before storage in MySQL 8.0.
- **Short-Lived Token Rotation**: Access tokens expire in 15 minutes. The frontend transparently rotates authentication using single-use refresh tokens via `/auth/refresh`.
- **Immutable Audit Logging**: Every administrative action (logins, file uploads, deletions, generation builds, promotions, rollbacks, model synchronizations) is permanently recorded in the MySQL `audit_logs` table with user attribution, IP address, and payload parameters.

---

## 3. Role-Based Access Control (RBAC) Matrix

The system enforces four hierarchical permission tiers:

| Role | Hierarchy Level | Badge Color | Permitted Operations | Typical Persona |
| :--- | :---: | :---: | :--- | :--- |
| **`SUPER_ADMIN`** | **Level 4** | Purple | Full system authority; administrative user management; system settings configuration; full audit log inspection; all curator/operator functions. | State Tourism Director, Head IT Administrator |
| **`SITE_CURATOR`** | **Level 3** | Heritage Gold | Upload and delete PDF monument literature; trigger knowledge generation builds; promote generations to `ACTIVE`; execute generation rollbacks. | Archaeological Curator, Belur Site Historian |
| **`OPERATOR`** | **Level 2** | Blue | Trigger Piper voice model discovery; trigger Argos neural translation package synchronization; monitor operational health. | DevOps Engineer, Field Systems Operator |
| **`VIEWER`** | **Level 1** | Slate Gray | Read-only access: view system health telemetry; view document catalog; inspect knowledge generations; run retrieval diagnostics. | Research Intern, Cultural Officer, Auditor |

*Note: Roles inherit permissions from lower levels (e.g., `SITE_CURATOR` can also perform all `OPERATOR` and `VIEWER` actions).*

---

## 4. Accessing the Administrator Portal

### Step 1: Open the Portal Login Screen
1. Navigate to the main public tourist interface in your browser (`http://localhost:5173` or your production domain).
2. In the top navigation bar (Header), locate the **Shield Crest** icon (🛡️) on the far right next to the theme toggle.
3. Click the Shield Crest icon to enter **Heritage Administrator Portal** mode.

```
┌────────────────────────────────────────────────────────────────────────┐
│ 🏛️ Karnataka Heritage Guide  [ಕನ್ನಡ / English]  [🔊]  [🌙]  [🛡️ Admin]  │
└────────────────────────────────────────────────────────────────────────┘
```

### Step 2: Sign In
1. In the login modal, input your **Username or Email Address**.
2. Input your **Administrative Password**.
3. Click **Sign In to Administrative Console**.
4. Upon successful validation, the dashboard automatically loads your role profile and displays your permitted navigation tabs.

> **Note**: To return to the public tourist interface at any time without logging out, click the **"Tourist View"** button in the top left. To terminate your administrative session and flush memory tokens, click **"Logout"**.

---

## 5. Provisioning Administrator Accounts (CLI / Seed)

Initial administrator credentials must be provisioned via backend database utilities or direct CLI script execution to prevent unauthorized public account registration.

### Creating an Administrator via Python CLI

Open a terminal in the project root directory and execute the following Python helper:

```bash
python -c "
import asyncio, uuid
from backend.src.core.security import hash_password
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.auth import Admin

async def create_admin():
    session_factory = get_session_factory()
    async with session_factory() as session:
        admin = Admin(
            id=str(uuid.uuid4()),
            username='curator_belur',
            email='curator@karnatakagov.in',
            password_hash=hash_password('HeritageSecure2026!'),
            role='SITE_CURATOR',
            is_active=True
        )
        session.add(admin)
        await session.commit()
        print('Admin account curator_belur created successfully.')

asyncio.run(create_admin())
"
```

---

## 6. Tab 1: System & Knowledge Base Overview

The **Overview Tab** provides high-level observability into local AI engines, database connectivity, and active index status.

![Overview Tab](file:///d:/vikasAn/frontend/src/features/admin/OverviewTab.tsx)

### Key Telemetry Cards:
1. **Core API & Database Health**:
   - `healthy` / `degraded`: Verifies MySQL connection pool liveness and query response latency.
   - Server process uptime counter (`Hh Mm Ss`).
   - Active deployment profile indicator: `dev`, `standalone` (offline local host), or `cloud`.
2. **Active Knowledge Generation**:
   - Displays the current active generation sequence number (e.g., `Generation #1`).
   - Displays total embedded chunks indexed in the active ChromaDB collection (`belur_knowledge_gen_{N}`).
3. **Document Repository Count**:
   - Total number of validated, unique PDF files stored in the document repository.
4. **Voice & Translation Engines**:
   - Speech-to-Text (STT): `faster-whisper` (device: `cuda` or `cpu`).
   - Text-to-Speech (TTS): `Piper` (installed Kannada and English neural voice ONNX models).
   - Machine Translation: `Argos Translate` (installed bidirectional `kn <-> en` neural models).
5. **Telemetry Refresh**:
   - Click the **"Refresh Telemetry"** button in the upper right corner to query live subsystem probes.

---

## 7. Tab 2: Document Catalog & Ingestion Manager

The **Documents Tab** manages the ingestion, inspection, and cataloging of authoritative heritage literature.

![Document Manager](file:///d:/vikasAn/frontend/src/features/admin/DocumentManager.tsx)

### 7.1 Ingestion Workflow (Uploading a New PDF)
1. Ensure your account possesses the **`SITE_CURATOR`** or **`SUPER_ADMIN`** role.
2. Click the **"Upload PDF Document"** button.
3. Select an authentic PDF document from your filesystem (e.g., `Temple_info.pdf` or state archaeological monographs).
4. The system validates:
   - **File Format & Magic Bytes**: Verifies the file begins with authentic `%PDF` magic bytes.
   - **Size Limit**: Enforces a strict maximum ceiling of **50 MB**.
   - **SHA-256 Deduplication**: Calculates the cryptographic SHA-256 hash. If an identical file already exists in the catalog, the upload is rejected with a `409 Conflict` notice to prevent chunk duplication.
5. Once uploaded, the document receives a unique UUID, is stored in secure local storage, and is registered in the MySQL `documents` table.

### 7.2 Inspecting Documents
- Search documents by name using the search bar.
- Each document card displays:
  - Document Title & MIME type.
  - Page count and File Size (in MB).
  - SHA-256 Checksum (with one-click copy button).
  - Upload date and uploader reference.

### 7.3 Downloading & Deleting Documents
- **Download**: Click the download icon to retrieve the original stored PDF.
- **Delete**: Click the trash icon to open the confirmation modal.
  > **Safety Invariant**: A document cannot be deleted if its chunks are currently bound to an `ACTIVE` knowledge generation. You must first build and promote a new generation that excludes this document before deleting it.

---

## 8. Tab 3: Knowledge Pipeline & Generation Governance

The **Pipeline & Generations Tab** controls the RAG index lifecycle through an **immutable generation model**. Rather than mutating a live vector database in-place, the system constructs a brand-new, isolated generation index in parallel, allowing zero-downtime cutover and instantaneous rollback.

![Generation Manager](file:///d:/vikasAn/frontend/src/features/admin/GenerationManager.tsx)

### 8.1 The 6-Stage Knowledge Lifecycle

When a generation build is triggered, the asynchronous pipeline executes the following stages:

```
[1. BUILD] ➔ [2. PARSE] ➔ [3. CHUNK] ➔ [4. EMBED] ➔ [5. INDEX] ➔ [6. VALIDATE] ➔ [ACTIVE]
```

1. **`BUILD`**: Pipeline initializes database tracking records and allocates a monotonic sequence number (e.g., `Generation #2`).
2. **`PARSE`**: PyMuPDF extracts text, structure, tables, and page boundaries from all active PDF documents.
3. **`CHUNK`**: The semantic chunker divides text into discrete passages (typically 400 tokens with 60-token overlap), attaching metadata: source document, page number, and section heading hierarchy.
4. **`EMBED`**: Text chunks are embedded into 384-dimensional dense vectors using the local `all-MiniLM-L6-v2` transformer model.
5. **`INDEX`**: Vectors and metadata are committed to an isolated ChromaDB collection (`belur_knowledge_gen_{N}`) and the BM25 sparse keyword index is generated.
6. **`VALIDATE`**: Pre-flight verification confirms chunk counts, embedding dimensions, and retrieval responsiveness.

### 8.2 Building a New Generation
1. In the **Pipeline & Generations** tab, click **"Build New Generation"**.
2. Confirm the build in the modal dialog.
3. The generation card appears with a live progress indicator. The dashboard polls status every 3 seconds until completion.
4. Upon successful validation, the generation transitions to `ACTIVE` (or is ready for manual promotion).

### 8.3 Promoting a Generation
If manual promotion is required:
1. Locate the validated generation card in the list.
2. Click **"Promote to Active"**.
3. The platform performs an atomic database pointer swap. All incoming tourist queries immediately query the new ChromaDB collection and BM25 index with zero downtime.

### 8.4 Instantaneous Rollback
If a newly published generation exhibits unexpected retrieval discrepancies:
1. Click the **"Rollback Generation"** button in the header bar.
2. Select an earlier, verified generation from the dropdown list.
3. Click **"Execute Rollback"**.
4. The active pointer instantly reverts to the selected historical generation, restoring verified retrieval state in sub-second time.

---

## 9. Tab 4: Voice & Translation Model Registry

The **Models & Translation Tab** manages offline neural voice models and language translation packages.

![Model Sync Tab](file:///d:/vikasAn/frontend/src/features/admin/ModelSyncTab.tsx)

### 9.1 Offline Speech Synthesis (Piper TTS)
The platform uses the fast, local **Piper TTS** neural engine to speak responses in Kannada and English without internet access.
- When new Piper voice models (`.onnx` and `.onnx.json` files) are placed in the server's voice model directory:
  1. Click **"Sync Voice Registry"**.
  2. The system scans the directory, registers newly detected voices, and marks them active in the MySQL `voice_registry` table.
  3. The table displays registered Voice IDs, Language Codes (`kn_IN`, `en_US`, `en_GB`), sample rates, and engine status.

### 9.2 Offline Neural Translation (Argos Translate)
The platform uses **Argos Translate** to provide offline bidirectional translation between Kannada and English.
- When new `.argosmodel` packages are installed on the host system:
  1. Click **"Sync Translation Registry"**.
  2. The system indexes installed translation pairs (`kn -> en` and `en -> kn`) and writes records into the MySQL `translation_registry`.
  3. Status badges indicate whether Kannada-English bidirectional routing is operational.

---

## 10. Tab 5: Retrieval Diagnostics & RAG Tuning

The **Retrieval Diagnostics Tab** enables curators to simulate tourist queries, inspect the internal scoring of the hybrid RAG pipeline, and calibrate relevance cutoffs.

![Diagnostics Tab](file:///d:/vikasAn/frontend/src/features/admin/DiagnosticsTab.tsx)

### 10.1 Diagnostic Execution Steps
1. Enter a test query in the **Query Input Box** (e.g., *"Who built the Chennakeshava Temple and when?"* or *"Describe the Darpana Sundari bracket figure"*).
2. Configure retrieval pipeline hyper-parameters:
   - **Top Dense Candidates** (Default: `15`): Number of candidate chunks retrieved via ChromaDB MiniLM semantic similarity.
   - **Top Sparse Candidates** (Default: `15`): Number of candidate chunks retrieved via BM25 keyword matching.
   - **Top Fused (RRF)** (Default: `10`): Number of candidates merged via Reciprocal Rank Fusion.
   - **Top Final Candidates** (Default: `4`): Number of top chunks passed to the Cross-Encoder.
   - **Relevance Cutoff Threshold** (Default: `0.35`): Minimum Cross-Encoder reranking score required for a chunk to be injected into the LLM context.
3. Click **"Execute Diagnostic Run"**.

### 10.2 Interpreting the Results & Intermediate Scores Matrix
The diagnostic view breaks down candidates across 5 filter tabs:
- **Final**: Only candidates that exceeded the Cross-Encoder score cutoff and would be passed to the LLM.
- **Reranked**: All candidates scored by the `cross-encoder/ms-marco-MiniLM-L-6-v2` re-ranker.
- **Fused**: Candidates merged using Reciprocal Rank Fusion ($RRF = \frac{1}{60 + \text{rank}}$).
- **Dense**: ChromaDB semantic distance scores and rank.
- **Sparse**: BM25 keyword frequency scores and rank.

#### Candidate Card Breakdown:
```text
┌────────────────────────────────────────────────────────────────────────┐
│ #1 chunk_951f3385  •  Page 4  •  Section: Architecture & Sanctum       │
│ Dense: 0.8124 (Rank 1) | Sparse: 14.22 (Rank 2) | Cross-Encoder: 0.8712│
│ [PASSED CUTOFF]                                                        │
├────────────────────────────────────────────────────────────────────────┤
│ "The Chennakeshava Temple was commissioned by Hoysala King             │
│  Vishnuvardhana in 1117 CE to commemorate his military victory..."     │
└────────────────────────────────────────────────────────────────────────┘
```

> **Curator Tip**: If factual questions return generic fallback responses, check whether the relevant chunk passed the **Cutoff Threshold**. If the Cross-Encoder score is valid (e.g. `0.28`) but rejected by a strict threshold of `0.35`, adjust the threshold parameter or re-examine document chunk boundaries.

---

## 11. Audit Logging & Security Compliance

Every privileged action triggers an immutable entry in the `audit_logs` table.

### Audit Record Schema
- `id`: Unique UUID.
- `admin_id`: Foreign key referencing the authenticated admin account.
- `action`: Operational action code:
  - `ADMIN_LOGIN_SUCCESS` / `ADMIN_LOGIN_FAILED`
  - `DOC_UPLOAD` / `DOC_DELETE`
  - `GEN_BUILD` / `GEN_PROMOTE` / `GEN_ROLLBACK`
  - `VOICE_SYNC` / `TRANS_SYNC`
- `resource_type`: Affected subsystem (`document`, `knowledge_generation`, `auth`, `model_registry`).
- `resource_id`: Primary key of affected resource.
- `payload`: JSON object containing file names, hash digests, page counts, or configuration details.
- `ip_address`: Origin IP address of client request.
- `created_at`: UTC timestamp.

### Querying Audit Logs via SQL

```sql
SELECT 
    a.created_at,
    adm.username,
    adm.role,
    a.action,
    a.resource_type,
    a.payload,
    a.ip_address
FROM audit_logs a
LEFT JOIN admins adm ON a.admin_id = adm.id
ORDER BY a.created_at DESC
LIMIT 50;
```

---

## 12. Troubleshooting & Operational FAQ

### Q1: I uploaded a PDF, but the system returned "Document with identical SHA-256 hash already exists."
* **Cause**: The platform strictly enforces cryptographic deduplication. An exact duplicate of this file has already been ingested.
* **Resolution**: Check the Document Catalog in Tab 2 to verify if the file is already registered. If you intended to upload a revised edition, ensure the PDF contains modifications before uploading.

### Q2: Why are changes in newly uploaded PDFs not appearing in tourist answers?
* **Cause**: Uploading a document stores the PDF in the catalog, but does **not** alter the active search index.
* **Resolution**: Navigate to **Pipeline & Generations** (Tab 3), click **"Build New Generation"**, wait for validation, and ensure the new generation is marked **`ACTIVE`**.

### Q3: My session suddenly returned me to the login screen.
* **Cause**: The Zero-Storage protocol maintains access tokens exclusively in browser memory. Refreshing the browser page, closing the tab, or allowing the 15-minute token rotation window to expire without network activity will require re-authentication.
* **Resolution**: Re-enter your credentials. Your work in progress on the server (builds, indexes) is unaffected.

### Q4: I receive a `403 Forbidden` error when trying to upload documents.
* **Cause**: Your account has the `OPERATOR` or `VIEWER` role. Document upload and deletion requires at least the `SITE_CURATOR` permission level.
* **Resolution**: Request a role upgrade from your `SUPER_ADMIN`.

### Q5: How do I recover if a generation build gets stuck in `PARSE` or `EMBED`?
* **Cause**: Extremely large PDFs or temporary hardware exhaustion on local CPU/GPU during batch embedding.
* **Resolution**: Check backend container/process logs. The system automatically marks timed-out builds as `FAILED`. You may trigger a new build once hardware resources normalize. The existing `ACTIVE` generation continues serving tourist queries uninterrupted.

---
*Heritage Administration Manual • Karnataka AI Tourism Platform • Version 1.0.0*
