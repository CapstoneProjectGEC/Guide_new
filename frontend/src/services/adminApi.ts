/**
 * Typed Administrative API Client.
 *
 * Implements:
 * - Bearer authorization attachment.
 * - Automatic 401 retry with in-memory refresh token rotation.
 * - ErrorEnvelope unmarshaling and type-safe ApiError propagation.
 * - Document upload, download, deletion, knowledge generation build/promote/rollback,
 *   model registry sync, and retrieval diagnostic probes.
 */

import { authService } from "./auth";
import {
  AdminProfile,
  DocumentItem,
  DocumentListResponse,
  KnowledgeGenerationItem,
  KnowledgeGenerationListResponse,
  ModelSyncStatusResponse,
  VoiceSyncResponse,
  TranslationSyncResponse,
  RetrievalDiagnosticRequest,
  RetrievalDiagnosticResponse,
  SystemHealth,
  ErrorEnvelope,
} from "@/types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class AdminApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, any>;

  constructor(status: number, message: string, code: string = "ADMIN_API_ERROR", details?: Record<string, any>) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function requestWithAuth<T>(
  endpoint: string,
  options: RequestInit = {},
  isRetry: boolean = false
): Promise<T> {
  const token = authService.getAccessToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized with token refresh rotation
  if (response.status === 401 && !isRetry) {
    const refreshed = await authService.refresh();
    if (refreshed) {
      return requestWithAuth<T>(endpoint, options, true);
    } else {
      throw new AdminApiError(401, "Session expired or invalid. Please re-authenticate.", "SESSION_EXPIRED");
    }
  }

  if (!response.ok) {
    let code = `HTTP_${response.status}`;
    let message = `Request failed with status ${response.status}`;
    let details: Record<string, any> | undefined;

    try {
      const errEnvelope = (await response.json()) as ErrorEnvelope;
      if (errEnvelope?.error) {
        code = errEnvelope.error.code || code;
        message = errEnvelope.error.message || message;
        details = errEnvelope.error.details;
      }
    } catch {
      // Body was not JSON
    }

    throw new AdminApiError(response.status, message, code, details);
  }

  // Handle empty or 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export const adminApiClient = {
  /**
   * Current authenticated administrator profile.
   */
  async getProfile(): Promise<AdminProfile> {
    return requestWithAuth<AdminProfile>("/auth/me");
  },

  /**
   * Health and diagnostic probe.
   */
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) {
      throw new AdminApiError(res.status, "Health probe failed", "HEALTH_UNAVAILABLE");
    }
    return res.json();
  },

  /**
   * Container readiness probe.
   */
  async getReadiness(): Promise<{ status: string; database: string; uptime_seconds: number }> {
    const res = await fetch(`${API_BASE}/health/ready`);
    return res.json();
  },

  // -------------------------------------------------------------
  // Document Management (SITE_CURATOR+ for write/delete, VIEWER+ for read)
  // -------------------------------------------------------------

  async listDocuments(limit: number = 50, offset: number = 0): Promise<DocumentListResponse> {
    return requestWithAuth<DocumentListResponse>(`/admin/documents?limit=${limit}&offset=${offset}`);
  },

  async getDocument(documentId: string): Promise<DocumentItem> {
    return requestWithAuth<DocumentItem>(`/admin/documents/${documentId}`);
  },

  async uploadDocument(file: File): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", file, file.name);

    return requestWithAuth<DocumentItem>("/admin/documents", {
      method: "POST",
      body: formData,
    });
  },

  async downloadDocument(documentId: string): Promise<Blob> {
    const token = authService.getAccessToken();
    const headers = new Headers();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    const res = await fetch(`${API_BASE}/admin/documents/${documentId}/download`, {
      headers,
    });

    if (!res.ok) {
      throw new AdminApiError(res.status, "Failed to download document", "DOWNLOAD_FAILED");
    }

    return res.blob();
  },

  async deleteDocument(documentId: string): Promise<{ message: string }> {
    return requestWithAuth<{ message: string }>(`/admin/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  // -------------------------------------------------------------
  // Knowledge Generation Lifecycle (SITE_CURATOR+ for build/promote/rollback)
  // -------------------------------------------------------------

  async listGenerations(): Promise<KnowledgeGenerationListResponse> {
    return requestWithAuth<KnowledgeGenerationListResponse>("/admin/knowledge/generations");
  },

  async getActiveGeneration(): Promise<KnowledgeGenerationItem> {
    return requestWithAuth<KnowledgeGenerationItem>("/admin/knowledge/generations/active");
  },

  async getGeneration(generationId: string): Promise<KnowledgeGenerationItem> {
    return requestWithAuth<KnowledgeGenerationItem>(`/admin/knowledge/generations/${generationId}`);
  },

  async buildGeneration(documentIds?: string[]): Promise<KnowledgeGenerationItem> {
    return requestWithAuth<KnowledgeGenerationItem>("/admin/knowledge/generations/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds || null }),
    });
  },

  async promoteGeneration(generationId: string): Promise<KnowledgeGenerationItem> {
    return requestWithAuth<KnowledgeGenerationItem>(`/admin/knowledge/generations/${generationId}/promote`, {
      method: "POST",
    });
  },

  async rollbackGeneration(targetId?: string, targetNumber?: number): Promise<KnowledgeGenerationItem> {
    return requestWithAuth<KnowledgeGenerationItem>("/admin/knowledge/generations/rollback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target_generation_id: targetId || null,
        target_generation_number: targetNumber || null,
      }),
    });
  },

  // -------------------------------------------------------------
  // Model Registry Synchronization (OPERATOR+ for write, VIEWER+ for read)
  // -------------------------------------------------------------

  async getSyncStatus(): Promise<ModelSyncStatusResponse> {
    return requestWithAuth<ModelSyncStatusResponse>("/admin/sync/status");
  },

  async syncVoices(): Promise<VoiceSyncResponse> {
    return requestWithAuth<VoiceSyncResponse>("/admin/sync/voice", {
      method: "POST",
    });
  },

  async syncTranslation(): Promise<TranslationSyncResponse> {
    return requestWithAuth<TranslationSyncResponse>("/admin/sync/translation", {
      method: "POST",
    });
  },

  // -------------------------------------------------------------
  // Retrieval Pipeline Diagnostics (VIEWER+)
  // -------------------------------------------------------------

  async runRetrievalDiagnostics(req: RetrievalDiagnosticRequest): Promise<RetrievalDiagnosticResponse> {
    return requestWithAuth<RetrievalDiagnosticResponse>("/admin/diagnostics/retrieval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  },
};
