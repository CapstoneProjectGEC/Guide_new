import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AdminLogin } from "../features/admin/AdminLogin";
import { OverviewTab } from "../features/admin/OverviewTab";
import { DocumentManager } from "../features/admin/DocumentManager";
import { GenerationManager } from "../features/admin/GenerationManager";
import { ModelSyncTab } from "../features/admin/ModelSyncTab";
import { DiagnosticsTab } from "../features/admin/DiagnosticsTab";
import { AdminDashboard } from "../features/admin/AdminDashboard";
import { authService } from "../services/auth";
import { adminApiClient } from "../services/adminApi";

describe("Admin Dashboard UI Components", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    authService.clear();
  });

  describe("AdminLogin", () => {
    it("renders form and executes login on submit", async () => {
      const onSuccess = vi.fn();
      const onCancel = vi.fn();
      const loginSpy = vi.spyOn(authService, "login").mockResolvedValueOnce({
        access_token: "tok",
        refresh_token: "ref",
        token_type: "bearer",
        expires_in_seconds: 900,
        role: "SITE_CURATOR",
        username: "curator",
      });

      render(<AdminLogin onSuccess={onSuccess} onCancel={onCancel} />);

      expect(screen.getByText("Heritage Administrator Portal")).toBeInTheDocument();
      expect(screen.getByText(/Zero-Storage Protocol/i)).toBeInTheDocument();

      const userInput = screen.getByLabelText(/Username or Email/i);
      const passInput = screen.getByLabelText(/Password/i);
      const submitBtn = screen.getByRole("button", { name: /Access Dashboard/i });

      fireEvent.change(userInput, { target: { value: "curator" } });
      fireEvent.change(passInput, { target: { value: "secret123" } });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(loginSpy).toHaveBeenCalledWith("curator", "secret123");
        expect(onSuccess).toHaveBeenCalled();
      });
    });

    it("displays error banner on authentication rejection", async () => {
      vi.spyOn(authService, "login").mockRejectedValueOnce(
        new Error("Invalid administrative credentials.")
      );

      render(<AdminLogin onSuccess={vi.fn()} onCancel={vi.fn()} />);

      const userInput = screen.getByLabelText(/Username or Email/i);
      const passInput = screen.getByLabelText(/Password/i);
      const submitBtn = screen.getByRole("button", { name: /Access Dashboard/i });

      fireEvent.change(userInput, { target: { value: "bad_user" } });
      fireEvent.change(passInput, { target: { value: "bad_pass" } });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(screen.getByRole("alert")).toHaveTextContent("Invalid administrative credentials.");
      });
    });

    it("triggers onCancel when clicking Back to Tourist Guide", () => {
      const onCancel = vi.fn();
      render(<AdminLogin onSuccess={vi.fn()} onCancel={onCancel} />);

      const backBtn = screen.getByRole("button", { name: /Back to Tourist Guide/i });
      fireEvent.click(backBtn);
      expect(onCancel).toHaveBeenCalled();
    });
  });

  describe("OverviewTab", () => {
    it("renders real health metrics and active generation cards", async () => {
      vi.spyOn(adminApiClient, "getHealth").mockResolvedValueOnce({
        status: "healthy",
        version: "0.15.0",
        profile: "dev",
        uptime_seconds: 7200,
        timestamp: "2026-10-13T12:00:00Z",
        components: {
          database: { status: "healthy", dialect: "sqlite", latency_ms: 1 },
          speech_to_text: { status: "ready", device: "cpu", model: "base" },
          text_to_speech: { status: "ready", device: "cpu", installed_voices: ["kn_IN-female"] },
        },
      });

      vi.spyOn(adminApiClient, "getActiveGeneration").mockResolvedValueOnce({
        id: "gen-1",
        generation_number: 1,
        status: "ACTIVE",
        chroma_collection_name: "belur_gen_001",
        chunk_count: 85,
        created_at: "2026-10-13T10:00:00Z",
        steps: [],
      });

      vi.spyOn(adminApiClient, "listDocuments").mockResolvedValueOnce({
        documents: [],
        total: 5,
      });

      vi.spyOn(adminApiClient, "getSyncStatus").mockResolvedValueOnce({
        status: "operational",
        voice: { engine: "piper", installed_voices: ["kn_IN-female"], operational: true },
        translation: { engine: "argos", installed_packages_count: 2, kn_en_available: true, en_kn_available: true },
      });

      render(<OverviewTab />);

      await waitFor(() => {
        expect(screen.getByText("HEALTHY")).toBeInTheDocument();
        expect(screen.getByText("CONNECTED")).toBeInTheDocument();
        expect(screen.getByText("Gen #1")).toBeInTheDocument();
        expect(screen.getByText("5")).toBeInTheDocument();
      });
    });
  });

  describe("DocumentManager", () => {
    it("renders document list and allows searching", async () => {
      vi.spyOn(authService, "hasRole").mockReturnValue(true);

      const mockDocs = [
        {
          id: "doc-1",
          filename: "Belur_Temple_Architecture.pdf",
          sha256_hash: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
          file_size_bytes: 2048000,
          mime_type: "application/pdf",
          page_count: 14,
          uploaded_by_id: "admin-1",
          created_at: "2026-10-13T10:00:00Z",
        },
        {
          id: "doc-2",
          filename: "Hoysala_Dynasty_Chronology.pdf",
          sha256_hash: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
          file_size_bytes: 512000,
          mime_type: "application/pdf",
          page_count: 8,
          uploaded_by_id: "admin-1",
          created_at: "2026-10-13T11:00:00Z",
        },
      ];

      vi.spyOn(adminApiClient, "listDocuments").mockResolvedValueOnce({
        documents: mockDocs,
        total: 2,
      });

      render(<DocumentManager />);

      await waitFor(() => {
        expect(screen.getByText("Belur_Temple_Architecture.pdf")).toBeInTheDocument();
        expect(screen.getByText("Hoysala_Dynasty_Chronology.pdf")).toBeInTheDocument();
      });

      // Filter
      const searchInput = screen.getByPlaceholderText(/Search documents by filename/i);
      fireEvent.change(searchInput, { target: { value: "Hoysala" } });

      expect(screen.queryByText("Belur_Temple_Architecture.pdf")).not.toBeInTheDocument();
      expect(screen.getByText("Hoysala_Dynasty_Chronology.pdf")).toBeInTheDocument();
    });

    it("opens delete confirmation modal when delete clicked", async () => {
      vi.spyOn(authService, "hasRole").mockReturnValue(true);

      const mockDoc = {
        id: "doc-1",
        filename: "Belur_Guide.pdf",
        sha256_hash: "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        file_size_bytes: 1024000,
        mime_type: "application/pdf",
        page_count: 10,
        uploaded_by_id: "admin-1",
        created_at: "2026-10-13T10:00:00Z",
      };

      vi.spyOn(adminApiClient, "listDocuments").mockResolvedValueOnce({
        documents: [mockDoc],
        total: 1,
      });

      render(<DocumentManager />);

      await waitFor(() => {
        expect(screen.getByText("Belur_Guide.pdf")).toBeInTheDocument();
      });

      const deleteBtn = screen.getByLabelText("Delete Belur_Guide.pdf");
      fireEvent.click(deleteBtn);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Confirm Document Deletion")).toBeInTheDocument();

      // Cancel deletion
      const cancelBtn = screen.getByRole("button", { name: "Cancel" });
      fireEvent.click(cancelBtn);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  describe("GenerationManager", () => {
    it("renders generations list and triggers build", async () => {
      vi.spyOn(authService, "hasRole").mockReturnValue(true);

      const mockGen = {
        id: "gen-1",
        generation_number: 1,
        status: "ACTIVE",
        chroma_collection_name: "belur_gen_001",
        chunk_count: 50,
        created_at: "2026-10-13T10:00:00Z",
        steps: [
          { step: "PARSE", status: "COMPLETED", progress_pct: 100 },
          { step: "CHUNK", status: "COMPLETED", progress_pct: 100 },
        ],
      };

      vi.spyOn(adminApiClient, "listGenerations").mockResolvedValue({
        generations: [mockGen],
        active_generation_id: "gen-1",
        total: 1,
      });

      const buildSpy = vi.spyOn(adminApiClient, "buildGeneration").mockResolvedValueOnce({
        id: "gen-2",
        generation_number: 2,
        status: "BUILD",
        chroma_collection_name: "belur_gen_002",
        chunk_count: 0,
        created_at: "2026-10-13T12:00:00Z",
        steps: [],
      });

      render(<GenerationManager />);

      await waitFor(() => {
        expect(screen.getByText("Generation #1")).toBeInTheDocument();
        expect(screen.getByText("50 semantic chunks")).toBeInTheDocument();
      });

      const buildBtn = screen.getByRole("button", { name: /Trigger Build/i });
      fireEvent.click(buildBtn);

      await waitFor(() => {
        expect(buildSpy).toHaveBeenCalled();
      });
    });
  });

  describe("ModelSyncTab", () => {
    it("renders subsystem cards and triggers sync when operator", async () => {
      vi.spyOn(authService, "hasRole").mockReturnValue(true);

      vi.spyOn(adminApiClient, "getSyncStatus").mockResolvedValue({
        status: "operational",
        voice: {
          engine: "piper",
          installed_voices: ["kn_IN-female-medium"],
          operational: true,
        },
        translation: {
          engine: "argostranslate",
          installed_packages_count: 2,
          kn_en_available: true,
          en_kn_available: true,
        },
      });

      const syncVoiceSpy = vi.spyOn(adminApiClient, "syncVoices").mockResolvedValueOnce({
        status: "success",
        synced_by: "operator",
        synced_voices_count: 1,
        voices: [
          { voice_id: "kn_IN", language_code: "kn", engine: "piper", is_active: true },
        ],
      });

      render(<ModelSyncTab />);

      await waitFor(() => {
        expect(screen.getByText("Piper Text-to-Speech")).toBeInTheDocument();
        expect(screen.getByText("Argos Neural Translation")).toBeInTheDocument();
      });

      const syncBtn = screen.getByRole("button", { name: /Sync Voices/i });
      fireEvent.click(syncBtn);

      await waitFor(() => {
        expect(syncVoiceSpy).toHaveBeenCalled();
      });
    });
  });

  describe("DiagnosticsTab", () => {
    it("renders query form and diagnostic probe results", async () => {
      const mockResult = {
        query: "Who built the temple?",
        generation_id: "gen-1",
        generation_number: 1,
        dense_candidates: [],
        sparse_candidates: [],
        fused_candidates: [],
        reranked_candidates: [],
        final_chunks: [
          {
            chunk_id: "chk-1",
            document_id: "doc-1",
            page_number: 3,
            section_heading: "Origins",
            content: "Commissioned by King Vishnuvardhana in 1117 AD.",
            dense_rank: 1,
            dense_score: 0.92,
            sparse_rank: 1,
            sparse_score: 14.5,
            rrf_score: 0.033,
            rerank_score: 0.88,
            is_selected: true,
          },
        ],
        latency_breakdown_ms: {
          dense_ms: 10.2,
          sparse_ms: 5.1,
          fusion_ms: 0.8,
          rerank_ms: 25.4,
          total_ms: 41.5,
        },
      };

      const diagSpy = vi.spyOn(adminApiClient, "runRetrievalDiagnostics").mockResolvedValueOnce(mockResult);

      render(<DiagnosticsTab />);

      expect(screen.getByText("Hybrid RAG Retrieval Diagnostics")).toBeInTheDocument();

      const runBtn = screen.getByRole("button", { name: /Execute Diagnostic Probe/i });
      fireEvent.click(runBtn);

      await waitFor(() => {
        expect(diagSpy).toHaveBeenCalled();
        expect(screen.getByText(/Commissioned by King Vishnuvardhana/i)).toBeInTheDocument();
        expect(screen.getByText("PASSED CUTOFF")).toBeInTheDocument();
      });
    });
  });

  describe("AdminDashboard Shell", () => {
    it("switches tabs smoothly and invokes logout", async () => {
      vi.spyOn(authService, "getRole").mockReturnValue("SITE_CURATOR");
      vi.spyOn(authService, "getUsername").mockReturnValue("curator_shantala");

      vi.spyOn(adminApiClient, "getHealth").mockResolvedValue({
        status: "healthy",
        version: "0.15.0",
        profile: "dev",
        uptime_seconds: 1000,
        timestamp: "2026-10-13T10:00:00Z",
        components: {},
      });
      vi.spyOn(adminApiClient, "getActiveGeneration").mockResolvedValue({
        id: "gen-1",
        generation_number: 1,
        status: "ACTIVE",
        chroma_collection_name: "c1",
        chunk_count: 10,
        created_at: "2026-10-13T10:00:00Z",
        steps: [],
      });
      vi.spyOn(adminApiClient, "listDocuments").mockResolvedValue({ documents: [], total: 0 });
      vi.spyOn(adminApiClient, "getSyncStatus").mockResolvedValue({
        status: "operational",
        voice: { engine: "piper", installed_voices: [], operational: true },
        translation: { engine: "argos", installed_packages_count: 0, kn_en_available: false, en_kn_available: false },
      });

      const onExit = vi.fn();
      render(<AdminDashboard onExit={onExit} />);

      expect(screen.getByText("curator_shantala")).toBeInTheDocument();
      expect(screen.getByText("SITE_CURATOR")).toBeInTheDocument();

      // Switch to Documents tab
      const docsTab = screen.getByRole("tab", { name: /Documents/i });
      fireEvent.click(docsTab);

      expect(screen.getByText("Heritage Document Archive")).toBeInTheDocument();

      // Switch to Diagnostics tab
      const diagTab = screen.getByRole("tab", { name: /Retrieval Diagnostics/i });
      fireEvent.click(diagTab);

      expect(screen.getByText("Hybrid RAG Retrieval Diagnostics")).toBeInTheDocument();

      // Click Tourist View
      const exitBtn = screen.getByRole("button", { name: /Tourist View/i });
      fireEvent.click(exitBtn);

      expect(onExit).toHaveBeenCalled();
    });
  });
});
