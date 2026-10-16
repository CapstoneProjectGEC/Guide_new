import { describe, it, expect, vi, beforeEach } from "vitest";
import { adminApiClient } from "../services/adminApi";
import { authService } from "../services/auth";

describe("Typed Admin API Client (/api/v1/admin)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    authService.clear();
  });

  it("attaches Authorization: Bearer header when token exists", async () => {
    // Authenticate
    vi.spyOn(authService, "getAccessToken").mockReturnValue("test-admin-jwt");

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "admin-1",
          username: "curator",
          email: "curator@belur.gov.in",
          role: "SITE_CURATOR",
          is_active: true,
          created_at: "2026-10-13T10:00:00Z",
        }),
        { status: 200 }
      )
    );

    const profile = await adminApiClient.getProfile();

    expect(profile.username).toBe("curator");
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/auth/me"),
      expect.objectContaining({
        headers: expect.any(Headers),
      })
    );
  });

  it("automatically refreshes token and retries on 401 response", async () => {
    vi.spyOn(authService, "getAccessToken")
      .mockReturnValueOnce("expired-token")
      .mockReturnValueOnce("new-fresh-token");

    const refreshSpy = vi.spyOn(authService, "refresh").mockResolvedValueOnce({
      access_token: "new-fresh-token",
      refresh_token: "new-refresh-token",
      token_type: "bearer",
      expires_in_seconds: 900,
      role: "SITE_CURATOR",
      username: "curator",
    });

    const fetchSpy = vi
      .spyOn(global, "fetch")
      // First attempt fails with 401
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { message: "Token expired" } }), { status: 401 }))
      // Second attempt succeeds with 200
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            documents: [],
            total: 0,
          }),
          { status: 200 }
        )
      );

    const result = await adminApiClient.listDocuments();

    expect(refreshSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(result.total).toBe(0);
  });

  it("throws SESSION_EXPIRED when 401 occurs and refresh fails", async () => {
    vi.spyOn(authService, "getAccessToken").mockReturnValue("expired-token");
    vi.spyOn(authService, "refresh").mockResolvedValueOnce(null);

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { message: "Token expired" } }), { status: 401 })
    );

    await expect(adminApiClient.listDocuments()).rejects.toThrow(
      "Session expired or invalid. Please re-authenticate."
    );
  });

  it("handles document upload with FormData", async () => {
    vi.spyOn(authService, "getAccessToken").mockReturnValue("valid-token");

    const mockDoc = {
      id: "doc-123",
      filename: "Hoysala_Architecture.pdf",
      sha256_hash: "a".repeat(64),
      file_size_bytes: 1048576,
      mime_type: "application/pdf",
      page_count: 12,
      uploaded_by_id: "admin-1",
      created_at: "2026-10-13T12:00:00Z",
    };

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockDoc), { status: 201 })
    );

    const mockFile = new File(["%PDF-1.4 test"], "Hoysala_Architecture.pdf", { type: "application/pdf" });
    const result = await adminApiClient.uploadDocument(mockFile);

    expect(result.id).toBe("doc-123");
    expect(result.filename).toBe("Hoysala_Architecture.pdf");
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/admin/documents"),
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      })
    );
  });

  it("handles document deletion", async () => {
    vi.spyOn(authService, "getAccessToken").mockReturnValue("valid-token");

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "Document deleted" }), { status: 200 })
    );

    const res = await adminApiClient.deleteDocument("doc-123");
    expect(res.message).toBe("Document deleted");
  });

  it("triggers knowledge build and parses response", async () => {
    vi.spyOn(authService, "getAccessToken").mockReturnValue("valid-token");

    const mockGen = {
      id: "gen-2",
      generation_number: 2,
      status: "ACTIVE",
      chroma_collection_name: "belur_gen_002",
      chunk_count: 54,
      created_at: "2026-10-13T12:30:00Z",
      steps: [],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockGen), { status: 201 })
    );

    const res = await adminApiClient.buildGeneration();
    expect(res.generation_number).toBe(2);
    expect(res.chroma_collection_name).toBe("belur_gen_002");
  });

  it("handles instant generation rollback request", async () => {
    vi.spyOn(authService, "getAccessToken").mockReturnValue("valid-token");

    const mockGen = {
      id: "gen-1",
      generation_number: 1,
      status: "ACTIVE",
      chroma_collection_name: "belur_gen_001",
      chunk_count: 42,
      created_at: "2026-10-13T10:00:00Z",
      steps: [],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockGen), { status: 200 })
    );

    const res = await adminApiClient.rollbackGeneration("gen-1");
    expect(res.generation_number).toBe(1);
    expect(res.status).toBe("ACTIVE");
  });

  it("runs retrieval diagnostics probe and returns intermediate candidate ranks", async () => {
    vi.spyOn(authService, "getAccessToken").mockReturnValue("valid-token");

    const mockDiag = {
      query: "Darpana Sundari",
      generation_id: "gen-1",
      generation_number: 1,
      dense_candidates: [
        {
          chunk_id: "c-1",
          document_id: "doc-1",
          page_number: 5,
          section_heading: "Sculptures",
          content: "Darpana Sundari bracket figure holding mirror",
          dense_rank: 1,
          dense_score: 0.89,
          rrf_score: 0.03,
          is_selected: true,
        },
      ],
      sparse_candidates: [],
      fused_candidates: [],
      reranked_candidates: [],
      final_chunks: [],
      latency_breakdown_ms: {
        dense_ms: 12.4,
        sparse_ms: 8.2,
        fusion_ms: 1.1,
        rerank_ms: 45.6,
        total_ms: 67.3,
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockDiag), { status: 200 })
    );

    const res = await adminApiClient.runRetrievalDiagnostics({ query: "Darpana Sundari" });
    expect(res.query).toBe("Darpana Sundari");
    expect(res.dense_candidates).toHaveLength(1);
    expect(res.latency_breakdown_ms.dense_ms).toBe(12.4);
  });
});
