/**
 * Typed API interfaces strictly matching FastAPI backend contracts from /api/v1.
 */

export interface Citation {
  chunk_id: string;
  document_id: string;
  page_number: number;
  section_heading: string | null;
  relevance_score: number;
  snippet: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  detected_language: string;
  input_mode: "text" | "voice";
  latency_ms?: number | null;
  is_grounded: boolean;
  created_at: string;
  citations: Citation[];
}

export interface ChatSession {
  id: string;
  client_fingerprint: string;
  preferred_language: string;
  created_at: string;
  last_active_at: string;
  messages: ChatMessage[];
}

export interface SendMessageRequest {
  session_id?: string | null;
  client_fingerprint?: string | null;
  content: string;
  preferred_language?: "en" | "kn" | null;
  input_mode?: "text" | "voice";
}

export interface StreamDonePayload {
  message_id: string;
  session_id: string;
  is_grounded: boolean;
  detected_language: string;
  latency_ms: number;
}

export interface TranscriptionSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface TranscriptionResult {
  text: string;
  detected_language: string;
  language_probability: number;
  duration_seconds: number;
  is_silent: boolean;
  device: string;
  compute_type: string;
  model_name: string;
  latency_ms: number;
  segments?: TranscriptionSegment[];
}

export interface VoiceChatResponse {
  transcription: TranscriptionResult;
  chat_response: ChatMessage;
}

export interface SynthesisRequest {
  text: string;
  language?: "en" | "kn" | string | null;
  voice?: string | null;
}

export interface SynthesisMetadataHeaders {
  engine?: string;
  language?: string;
  voice?: string;
  durationSeconds?: number;
  latencyMs?: number;
  cached?: boolean;
  fallbackRecommended?: boolean;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, any>;
  correlation_id?: string;
}

export interface ErrorEnvelope {
  error: ErrorDetail;
}

export interface SystemHealth {
  status: string;
  version: string;
  profile: string;
  uptime_seconds: number;
  timestamp: string;
  components: {
    api?: string;
    database?: {
      status?: string;
      connected?: boolean;
      dialect?: string;
      latency_ms?: number;
    };
    speech_to_text?: {
      status: string;
      device?: string;
      model?: string;
      error?: string;
    };
    text_to_speech?: {
      status: string;
      device?: string;
      installed_voices?: string[];
      error?: string;
    };
    [key: string]: any;
  };
}

// -------------------------------------------------------------
// Admin & RBAC Contracts
// -------------------------------------------------------------

export type AdminRoleType = "SUPER_ADMIN" | "SITE_CURATOR" | "OPERATOR" | "VIEWER";

export interface AdminProfile {
  id: string;
  username: string;
  email: string;
  role: AdminRoleType;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
  role: AdminRoleType;
  username: string;
}

// -------------------------------------------------------------
// Document Management Contracts
// -------------------------------------------------------------

export interface DocumentItem {
  id: string;
  filename: string;
  sha256_hash: string;
  file_size_bytes: number;
  mime_type: string;
  page_count: number;
  uploaded_by_id: string | null;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total: number;
}

// -------------------------------------------------------------
// Knowledge Generation Contracts
// -------------------------------------------------------------

export interface GenerationStep {
  step: string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | string;
  progress_pct: number;
  error_message?: string | null;
}

export interface KnowledgeGenerationItem {
  id: string;
  generation_number: number;
  status: "BUILD" | "PARSE" | "CHUNK" | "EMBED" | "INDEX" | "VALIDATE" | "PROMOTE" | "ACTIVE" | "ARCHIVED" | "FAILED" | string;
  chroma_collection_name: string;
  chunk_count: number;
  created_by_id?: string | null;
  created_at: string;
  promoted_at?: string | null;
  steps: GenerationStep[];
}

export interface KnowledgeGenerationListResponse {
  generations: KnowledgeGenerationItem[];
  active_generation_id: string | null;
  total: number;
}

// -------------------------------------------------------------
// Model & Translation Registry Sync Contracts
// -------------------------------------------------------------

export interface ModelSyncVoiceItem {
  voice_id: string;
  language_code: string;
  engine: string;
  is_active: boolean;
}

export interface ModelSyncTranslationItem {
  source_language: string;
  target_language: string;
  package_name: string;
  is_installed: boolean;
}

export interface VoiceSyncResponse {
  status: string;
  synced_by: string;
  synced_voices_count: number;
  voices: ModelSyncVoiceItem[];
}

export interface TranslationSyncResponse {
  status: string;
  synced_by: string;
  synced_packages_count: number;
  packages: ModelSyncTranslationItem[];
}

export interface ModelSyncStatusResponse {
  status: string;
  voice: {
    engine: string;
    installed_voices: string[];
    operational: boolean;
  };
  translation: {
    engine: string;
    installed_packages_count: number;
    kn_en_available: boolean;
    en_kn_available: boolean;
  };
}

// -------------------------------------------------------------
// Retrieval Diagnostics Contracts
// -------------------------------------------------------------

export interface RetrievalCandidate {
  chunk_id: string;
  document_id: string;
  page_number: number;
  section_heading: string | null;
  content: string;
  dense_rank?: number | null;
  dense_score?: number | null;
  sparse_rank?: number | null;
  sparse_score?: number | null;
  rrf_score: number;
  rerank_score?: number | null;
  is_selected: boolean;
}

export interface RetrievalDiagnosticRequest {
  query: string;
  top_dense?: number;
  top_sparse?: number;
  top_fused?: number;
  top_final?: number;
  score_threshold?: number;
}

export interface RetrievalDiagnosticResponse {
  query: string;
  generation_id: string;
  generation_number: number;
  dense_candidates: RetrievalCandidate[];
  sparse_candidates: RetrievalCandidate[];
  fused_candidates: RetrievalCandidate[];
  reranked_candidates: RetrievalCandidate[];
  final_chunks: RetrievalCandidate[];
  latency_breakdown_ms: Record<string, number>;
}
