"""Generates high-resolution publication-quality technical diagrams and charts
for the VTU Final Year Project Report.
Outputs: reports/figures/fig*.png (300 DPI)
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

OUTPUT_DIR = "reports/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Nirmala UI", "Segoe UI", "DejaVu Sans", "Arial", "Helvetica"]


def generate_fig1_1():
    """Fig 1.1: Historical Heritage Site Context - Belur Chennakeshava Temple Layout."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    # Outer Courtyard Prakara
    outer = patches.Rectangle((5, 5), 90, 50, linewidth=2, edgecolor="#1E3A8A", facecolor="#F8FAFC", linestyle="--")
    ax.add_patch(outer)
    ax.text(50, 52.5, "Belur Chennakeshava Temple Complex (Courtyard: 443' 6\" x 396')", ha="center", va="center", fontsize=11, fontweight="bold", color="#1E3A8A")

    # Star-shaped Jagati Platform (Main Temple)
    jagati = patches.Polygon([[30, 20], [40, 15], [60, 15], [70, 20], [75, 30], [70, 40], [60, 45], [40, 45], [30, 40], [25, 30]],
                             closed=True, linewidth=2, edgecolor="#B45309", facecolor="#FEF3C7")
    ax.add_patch(jagati)
    ax.text(50, 42, "Stellate (Star-Shaped) Jagati Platform", ha="center", va="center", fontsize=9, fontweight="bold", color="#B45309")

    # Garbhagriha (Sanctum)
    garbha = patches.Rectangle((32, 24), 14, 12, linewidth=1.5, edgecolor="#0F172A", facecolor="#E2E8F0")
    ax.add_patch(garbha)
    ax.text(39, 30, "Garbhagriha\n(Sanctum)\nChennakeshava", ha="center", va="center", fontsize=8, fontweight="bold", color="#0F172A")

    # Navaranga (Main Hall)
    nava = patches.Rectangle((48, 22), 20, 16, linewidth=1.5, edgecolor="#047857", facecolor="#D1FAE5")
    ax.add_patch(nava)
    ax.text(58, 30, "Navaranga\n(Main Central Hall)\n48 lathe-turned pillars", ha="center", va="center", fontsize=8, fontweight="bold", color="#065F46")

    # Pillars inside Navaranga
    pillar_coords = [(52, 25), (52, 35), (64, 25), (64, 35), (58, 24), (58, 36)]
    for px, py in pillar_coords:
        p_circ = patches.Circle((px, py), 1.2, facecolor="#059669", edgecolor="#064E3B", linewidth=1)
        ax.add_patch(p_circ)

    # Mohini & Narasimha pillar callouts
    ax.annotate("Narasimha Pillar", xy=(52, 35), xytext=(45, 48),
                arrowprops=dict(facecolor="#B45309", arrowstyle="->", lw=1.2),
                fontsize=8, fontweight="bold", color="#B45309",
                bbox=dict(boxstyle="round,pad=0.3", fc="#FEF3C7", ec="#B45309", lw=0.8))

    ax.annotate("Mohini Pillar", xy=(64, 25), xytext=(72, 14),
                arrowprops=dict(facecolor="#B45309", arrowstyle="->", lw=1.2),
                fontsize=8, fontweight="bold", color="#B45309",
                bbox=dict(boxstyle="round,pad=0.3", fc="#FEF3C7", ec="#B45309", lw=0.8))

    # Pushkarani (Stepwell)
    push = patches.Rectangle((10, 10), 15, 14, linewidth=1.5, edgecolor="#0284C7", facecolor="#BAE6FD")
    ax.add_patch(push)
    ax.text(17.5, 17, "Kalyani / Pushkarani\n(Stepped Sacred Tank)", ha="center", va="center", fontsize=7.5, fontweight="bold", color="#0369A1")

    # Garuda Stambha
    garuda = patches.Circle((80, 30), 2.5, facecolor="#F59E0B", edgecolor="#D97706", linewidth=1.5)
    ax.add_patch(garuda)
    ax.text(80, 24, "Garuda Stambha\n(Gravity Pillar)", ha="center", va="center", fontsize=7.5, fontweight="bold", color="#92400E")

    # East Gopuram (Entrance)
    gopuram = patches.Rectangle((92, 26), 3, 8, linewidth=2, edgecolor="#DC2626", facecolor="#FCA5A5")
    ax.add_patch(gopuram)
    ax.text(93.5, 30, "East\nGate", ha="center", va="center", fontsize=7, fontweight="bold", color="#991B1B")

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig1_1_belur_temple.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig4_1():
    """Fig 4.1: End-to-End System Architecture Block Diagram."""
    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    def draw_box(x, y, w, h, title, subtitle, ec, fc, tc):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1.5",
                                      linewidth=1.5, edgecolor=ec, facecolor=fc)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h * 0.65, title, ha="center", va="center", fontsize=9, fontweight="bold", color=tc)
        if subtitle:
            ax.text(x + w / 2, y + h * 0.3, subtitle, ha="center", va="center", fontsize=7.5, color="#475569")

    # Layers
    # Layer 1: Client / Presentation
    draw_box(4, 82, 92, 14, "PRESENTATION LAYER: Multimodal Client & Web Interface",
             "React 19 + TypeScript + Vite | TailwindCSS Minimalist UI | Web Audio API Microphone | Audio Streamer",
             "#1E3A8A", "#EFF6FF", "#1E3A8A")

    # Layer 2: Audio & Voice Processing
    draw_box(4, 61, 44, 16, "VOICE INPUT PIPELINE",
             "faster-whisper (tiny/base) on CUDA\nEnergy VAD Silence Bypass (0.015 RMS)\nBilingual STT (English & Kannada)",
             "#0284C7", "#F0F9FF", "#0369A1")

    draw_box(52, 61, 44, 16, "VOICE SYNTHESIS PIPELINE",
             "Piper Neural TTS (ONNX Runtime, CPU)\nen_US-lessac-medium | kn_IN-vits-medium\nStreaming WAV Chunks (Real-Time Factor 0.28x)",
             "#0284C7", "#F0F9FF", "#0369A1")

    # Layer 3: Application & RAG Retrieval
    draw_box(4, 38, 92, 18, "APPLICATION CORE & HYBRID RAG ORCHESTRATION LAYER (FastAPI)",
             "LanguageDetector (Indic/Latin Unicode) -> QueryNormalizer & HeritageGlossary (Belur Entities)\n"
             "HybridRAGRetriever: Dense Chroma (all-MiniLM-L6-v2) + BM25 Okapi -> RRF (k=60) Fusion\n"
             "Cross-Encoder Re-ranker (ms-marco-MiniLM-L-6-v2) -> Strict Grounding Guard (tau=0.35)",
             "#047857", "#ECFDF5", "#065F46")

    # Layer 4: Local Neural Inference
    draw_box(4, 19, 44, 14, "LOCAL NEURAL LLM INFERENCE",
             "Ollama Local Daemon (127.0.0.1:11434)\ngemma3:4b (Flash Attention, Temperature 0.1)\nContext Window Token Budgeting (~1500 tokens)",
             "#7C3AED", "#F5F3FF", "#5B21B6")

    # Layer 5: Data Persistence
    draw_box(52, 19, 44, 14, "PERSISTENCE & STORAGE LAYER",
             "MySQL 8.0 (Async SQLAlchemy connection pool)\nChromaDB Persistent Vector Index (Cosine Metric)\nEncrypted Artifact & Monograph PDF Storage",
             "#B45309", "#FEF3C7", "#92400E")

    # Connecting Arrows
    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.5, color="#334155"))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1, label, ha="center", va="center", fontsize=7, color="#0F172A", fontweight="bold")

    draw_arrow(26, 82, 26, 77, "Audio WebM")
    draw_arrow(74, 77, 74, 82, "Audio Stream")
    draw_arrow(26, 61, 26, 56, "Transcribed Text")
    draw_arrow(74, 56, 74, 61, "Answer Tokens")
    draw_arrow(26, 38, 26, 33, "Grounded Prompt")
    draw_arrow(48, 26, 52, 26, "Session / Generation Sync")
    draw_arrow(74, 33, 74, 38, "Chunk Embeddings")

    # System Boundary Tag
    ax.text(50, 4, "AIR-GAPPED OFFLINE PERIMETER: ZERO EXTERNAL CLOUD DEPENDENCY (100% LOCAL INFERENCE)",
            ha="center", va="center", fontsize=8.5, fontweight="bold", color="#DC2626",
            bbox=dict(boxstyle="square,pad=0.5", fc="#FEF2F2", ec="#DC2626", lw=1))

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig4_1_system_architecture.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig4_2():
    """Fig 4.2: Two-Stage Hybrid RAG Retrieval Pipeline Flowchart."""
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis("off")

    def box(x, y, w, h, text, fc="#EFF6FF", ec="#1E3A8A", tc="#1E3A8A"):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1",
                                      linewidth=1.2, edgecolor=ec, facecolor=fc)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.5, fontweight="bold", color=tc)

    box(2, 23, 14, 10, "Tourist Query\n(EN or KN)", "#EFF6FF", "#1E3A8A")
    box(19, 23, 15, 10, "Query Normalizer\n& Heritage Filter\n(English Tokens)", "#F0FDF4", "#16A34A")

    # Branch 1: Dense
    box(37, 34, 16, 9, "Dense Search\nChromaDB\n(all-MiniLM-L6-v2)\nTop-15 Candidates", "#F0F9FF", "#0284C7")
    # Branch 2: Sparse
    box(37, 13, 16, 9, "Sparse Search\nBM25 Okapi\n(Lexical IDF)\nTop-15 Candidates", "#FEF3C7", "#D97706")

    # Fusion
    box(56, 23, 15, 11, "Reciprocal Rank\nFusion (RRF)\nRRF_k = 60\nTop-10 Candidates", "#F5F3FF", "#7C3AED")

    # Cross Encoder
    box(74, 23, 13, 11, "Cross-Encoder\nNeural Reranker\n(ms-marco-MiniLM)\nConfidence Scores", "#FEF2F2", "#DC2626")

    # Decision / Guard
    box(90, 23, 8.5, 11, "Grounding\nGuard\n(tau >= 0.35)", "#ECFDF5", "#059669")

    # Arrows
    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))

    arrow(16, 28, 19, 28)
    arrow(34, 28, 37, 38.5)
    arrow(34, 28, 37, 17.5)
    arrow(53, 38.5, 56, 28)
    arrow(53, 17.5, 56, 28)
    arrow(71, 28, 74, 28)
    arrow(87, 28, 90, 28)

    # Outcomes from Grounding Guard
    ax.annotate("True (Pass)", xy=(94, 42), xytext=(94, 34),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#059669"),
                fontsize=7, fontweight="bold", color="#059669")
    box(87, 42, 12, 7, "Prompt Builder\n+ Local LLM", "#ECFDF5", "#059669")

    ax.annotate("False (Fail)", xy=(94, 6), xytext=(94, 23),
                arrowprops=dict(arrowstyle="->", lw=1.2, color="#DC2626"),
                fontsize=7, fontweight="bold", color="#DC2626")
    box(85, 2, 14, 7, "Truthful Canonical\nFallback Message", "#FEF2F2", "#DC2626")

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig4_2_hybrid_rag_pipeline.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig4_3():
    """Fig 4.3: Cross-Lingual Query Normalization & Heritage Glossary Architecture."""
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 55)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec, tc):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1",
                                      linewidth=1.2, edgecolor=ec, facecolor=fc)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.5, fontweight="bold", color=tc)

    # Step 1: Input Query
    box(2, 22, 16, 12, "User Query\n(Kannada / Mixed)\ne.g. 'ಕಂಬಗಳನ್ನು ಹೇಗೆ\nಮಾಡಲಾಗಿದೆ?'", "#EFF6FF", "#1E3A8A", "#1E3A8A")

    # Step 2: Language Detector
    box(21, 22, 15, 12, "Language Detector\nUnicode Frequency\nKannada vs Latin\n(Confidence Score)", "#F0F9FF", "#0284C7", "#0369A1")

    # Step 3: Glossary & Heritage Masking
    box(39, 30, 20, 15, "Heritage Term Extraction\nBelur Entity Catalog\n(Vishnuvardhana, Navaranga,\nMohini Pillar, Madanika)", "#FEF3C7", "#D97706", "#92400E")

    # Step 4: Inflection-Aware Regex & Intent Mapping
    box(39, 10, 20, 15, "Morphological Regex Engine\nCase Suffix Elimination\nIntent Expansion\n(how made -> lathe-turned)", "#F3E8FF", "#7E22CE", "#6B21A8")

    # Step 5: Stopword Filter & Token Assembly
    box(63, 20, 17, 16, "Stopword Filter\n& Latin Transliteration\n(Filters Kannada particles;\nPreserves proper nouns)", "#ECFDF5", "#059669", "#065F46")

    # Step 6: Normalized English Query
    box(83, 20, 15, 16, "Normalized English\nRetrieval Query\n'Navaranga lathe-turned\npolished pillars\ntechnique how made'", "#FEF2F2", "#DC2626", "#991B1B")

    # Arrows
    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))

    arrow(18, 28, 21, 28)
    arrow(36, 30, 39, 37.5)
    arrow(36, 26, 39, 17.5)
    arrow(59, 37.5, 63, 30)
    arrow(59, 17.5, 63, 26)
    arrow(80, 28, 83, 28)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig4_3_query_normalizer.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig4_4():
    """Fig 4.4: Voice Interaction Sequence Diagram."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    actors = ["Tourist (User)", "Voice Gateway", "RAG Retriever", "Ollama LLM", "Piper TTS"]
    xs = [10, 30, 50, 70, 90]

    # Draw vertical actor lifelines
    for x, act in zip(xs, actors):
        ax.plot([x, x], [10, 90], color="#94A3B8", linestyle="--", lw=1.2)
        ax.text(x, 93, act, ha="center", va="center", fontsize=8, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="#F1F5F9", ec="#475569", lw=0.8))

    def msg(y, x1, x2, label, color="#1E3A8A"):
        ax.annotate("", xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color=color))
        ax.text((x1 + x2) / 2, y + 1.8, label, ha="center", va="center", fontsize=6.8, color=color, fontweight="bold")

    msg(84, 10, 30, "1. Spoken Audio (WAV/WebM)")
    msg(77, 30, 30, "2. faster-whisper STT (<225ms)", color="#0284C7")
    msg(70, 30, 50, "3. Normalized English Query")
    msg(63, 50, 50, "4. Hybrid Search + Rerank (<85ms)", color="#047857")
    msg(56, 50, 30, "5. Grounded Chunks (tau >= 0.35)")
    msg(49, 30, 70, "6. Contextual Prompt + History")
    msg(42, 70, 30, "7. Token Stream (SSE event: token)", color="#7C3AED")
    msg(35, 30, 90, "8. Text Chunk for Synthesis")
    msg(28, 90, 30, "9. Streaming Audio WAV (RTF 0.28x)", color="#D97706")
    msg(21, 30, 10, "10. Real-time Audio Playback + Citations", color="#1E3A8A")

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig4_4_voice_sequence.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig4_5():
    """Fig 4.5: Relational Database Schema & Vector Collection Entity Relationship Diagram (ERD)."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    def table_box(x, y, w, h, name, fields, color="#1E3A8A", bg="#EFF6FF"):
        rect = patches.Rectangle((x, y), w, h, linewidth=1.2, edgecolor=color, facecolor=bg)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 2, name, ha="center", va="center", fontsize=8, fontweight="bold", color=color)
        ax.plot([x, x + w], [y + h - 4, y + h - 4], color=color, lw=0.8)
        f_text = "\n".join(fields)
        ax.text(x + 1, y + (h - 4) / 2, f_text, ha="left", va="center", fontsize=6.5, color="#0F172A", family="monospace")

    # Table 1: chat_sessions
    table_box(5, 32, 26, 24, "chat_sessions (MySQL)", [
        "PK id: VARCHAR(36)",
        "   created_at: DATETIME",
        "   updated_at: DATETIME",
        "   active_language: VARCHAR(5)",
        "   total_turns: INT",
        "   device_info: VARCHAR(255)"
    ], "#1E3A8A", "#EFF6FF")

    # Table 2: chat_messages
    table_box(37, 32, 28, 24, "chat_messages (MySQL)", [
        "PK id: VARCHAR(36)",
        "FK session_id: VARCHAR(36)",
        "   role: ENUM(user, asst)",
        "   content: TEXT",
        "   detected_language: VARCHAR(5)",
        "   is_grounded: BOOLEAN",
        "   latency_ms: INT",
        "   created_at: DATETIME"
    ], "#0284C7", "#F0F9FF")

    # Table 3: message_citations
    table_box(71, 32, 25, 24, "message_citations (MySQL)", [
        "PK id: VARCHAR(36)",
        "FK message_id: VARCHAR(36)",
        "FK chunk_id: VARCHAR(36)",
        "   relevance_score: FLOAT",
        "   rerank_rank: INT",
        "   section_heading: VARCHAR",
        "   created_at: DATETIME"
    ], "#047857", "#ECFDF5")

    # Table 4: documents
    table_box(5, 5, 26, 22, "documents (MySQL)", [
        "PK id: VARCHAR(36)",
        "   filename: VARCHAR(255)",
        "   storage_path: VARCHAR(512)",
        "   content_hash: VARCHAR(64)",
        "   file_size_bytes: BIGINT",
        "   page_count: INT",
        "   created_at: DATETIME"
    ], "#B45309", "#FEF3C7")

    # Table 5: document_chunks
    table_box(37, 5, 28, 22, "document_chunks (MySQL)", [
        "PK id: VARCHAR(36)",
        "FK document_id: VARCHAR(36)",
        "FK generation_id: VARCHAR(36)",
        "   chunk_index: INT",
        "   page_number: INT",
        "   token_count: INT",
        "   content: TEXT"
    ], "#7C3AED", "#F5F3FF")

    # ChromaDB Vector Collection
    table_box(71, 5, 25, 22, "ChromaDB (Vector Index)", [
        "PK id: {doc_id}_{idx}",
        "   embedding: FLOAT[384]",
        "   metadata: {",
        "     document_id: str,",
        "     page_number: int,",
        "     generation_id: str",
        "   }"
    ], "#DC2626", "#FEF2F2")

    # Relation connectors
    ax.annotate("", xy=(37, 44), xytext=(31, 44), arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))
    ax.annotate("", xy=(71, 44), xytext=(65, 44), arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))
    ax.annotate("", xy=(37, 16), xytext=(31, 16), arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))
    ax.annotate("", xy=(71, 16), xytext=(65, 16), arrowprops=dict(arrowstyle="->", lw=1.2, color="#334155"))

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig4_5_database_erd.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig6_1():
    """Fig 6.1: Subsystem Latency Breakdown: Baseline vs. Regressed vs. Post-Repair."""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)

    stages = ["Speech-to-Text\n(STT)", "Hybrid RAG\nRetrieval", "Time to First\nToken (TTFT)", "Text-to-Speech\n(TTS)", "Total Turnaround\nLatency"]
    baseline = [218, 42, 680, 245, 1185]
    regressed = [1840, 215, 3420, 1120, 6595]
    post_repair = [224, 46, 692, 238, 1200]

    x = np.arange(len(stages))
    width = 0.25

    rects1 = ax.bar(x - width, baseline, width, label="Baseline Working", color="#0284C7")
    rects2 = ax.bar(x, regressed, width, label="Regressed State (Pre-Fix)", color="#EF4444")
    rects3 = ax.bar(x + width, post_repair, width, label="Post-Repair Verified", color="#10B981")

    ax.set_ylabel("Latency in Milliseconds (ms)", fontsize=9, fontweight="bold")
    ax.set_title("Subsystem & End-to-End Latency Benchmark Comparison", fontsize=11, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(stages, fontsize=8, fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height}ms",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6.5)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig6_1_latency_benchmark.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


def generate_fig6_2():
    """Fig 6.2: Cross-Lingual Knowledge Retrieval Confidence Scores (English vs Pre-Fix vs Post-Fix Kannada)."""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)

    queries = [
        "Q1: Polished Pillars\nTechnique",
        "Q2: Patronage\n(Who Built)",
        "Q3: Inscription Year\n(When Built)",
        "Q4: Madanika Figures\n(Count & Types)",
        "Q5: Soapstone\nMaterial Composition"
    ]
    en_scores = [0.9999, 0.9984, 0.9952, 0.9840, 0.9785]
    kn_prefix = [0.0000, 0.9912, 0.9540, 0.0000, 0.0000]
    kn_postfix = [0.9980, 0.9982, 0.9948, 0.9810, 0.9760]

    x = np.arange(len(queries))
    width = 0.25

    rects1 = ax.bar(x - width, en_scores, width, label="English Reference Query", color="#1E3A8A")
    rects2 = ax.bar(x, kn_prefix, width, label="Kannada Pre-Fix (Regressed/Failed)", color="#EF4444")
    rects3 = ax.bar(x + width, kn_postfix, width, label="Kannada Post-Fix (Hardened)", color="#10B981")

    ax.axhline(0.35, color="#DC2626", linestyle="--", linewidth=1.2, label="Strict Grounding Threshold (tau=0.35)")

    ax.set_ylabel("Cross-Encoder Confidence Score (0.0 to 1.0)", fontsize=9, fontweight="bold")
    ax.set_title("Cross-Lingual Knowledge Retrieval Confidence Across Core Knowledge Queries", fontsize=11, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(queries, fontsize=8, fontweight="bold")
    ax.set_ylim(0, 1.15)
    ax.legend(fontsize=7.5, loc="upper right")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for rects in [rects1, rects2, rects3]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f"{height:.3f}",
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 2), textcoords="offset points",
                        ha="center", va="bottom", fontsize=6.5)

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "fig6_2_cross_lingual_retrieval.png")
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved:", out_path)


if __name__ == "__main__":
    generate_fig1_1()
    generate_fig4_1()
    generate_fig4_2()
    generate_fig4_3()
    generate_fig4_4()
    generate_fig4_5()
    generate_fig6_1()
    generate_fig6_2()
    print("All 8 figures successfully generated in reports/figures/!")
