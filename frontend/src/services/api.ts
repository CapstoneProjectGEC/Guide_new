/**
 * Typed API Client for the Unified FastAPI Gateway (/api/v1).
 * Handles structured ErrorEnvelope parsing, network errors, and binary audio blobs.
 */

import {
  ChatMessage,
  ChatSession,
  SendMessageRequest,
  TranscriptionResult,
  VoiceChatResponse,
  SynthesisRequest,
  SynthesisMetadataHeaders,
  SystemHealth,
  ErrorEnvelope,
} from "@/types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

class ApiError extends Error {
  code: string;
  details?: Record<string, any>;
  status: number;

  constructor(status: number, message: string, code: string = "API_ERROR", details?: Record<string, any>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errCode = `HTTP_${res.status}`;
    let errMsg = `Request failed with status ${res.status}`;
    let details: Record<string, any> | undefined;

    try {
      const data = (await res.json()) as ErrorEnvelope;
      if (data && data.error) {
        errCode = data.error.code || errCode;
        errMsg = data.error.message || errMsg;
        details = data.error.details;
      }
    } catch {
      // Body not JSON
    }

    throw new ApiError(res.status, errMsg, errCode, details);
  }

  return (await res.json()) as T;
}

export const apiClient = {
  getApiBase(): string {
    return API_BASE;
  },

  /**
   * Health status probe.
   */
  async getHealth(): Promise<SystemHealth> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<SystemHealth>(res);
  },

  /**
   * Create a new anonymous tourist session.
   */
  async createSession(fingerprint?: string, language: "kn" | "en" = "kn"): Promise<ChatSession> {
    const res = await fetch(`${API_BASE}/chat/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        client_fingerprint: fingerprint || null,
        preferred_language: language,
      }),
    });
    return handleResponse<ChatSession>(res);
  },

  /**
   * Fetch conversation history for a given session.
   */
  async getSession(sessionId: string): Promise<ChatSession> {
    const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`);
    return handleResponse<ChatSession>(res);
  },

  /**
   * Standard single-turn message endpoint (non-streaming fallback).
   */
  async sendMessage(req: SendMessageRequest): Promise<ChatMessage> {
    const res = await fetch(`${API_BASE}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    return handleResponse<ChatMessage>(res);
  },

  /**
   * Transcribe user audio bytes via faster-whisper STT.
   */
  async transcribeAudio(audioBlob: Blob, language?: "en" | "kn"): Promise<TranscriptionResult> {
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "tourist_query.wav");
    if (language) {
      formData.append("language", language);
    }

    const res = await fetch(`${API_BASE}/voice/transcribe`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<TranscriptionResult>(res);
  },

  /**
   * Full end-to-end voice query with grounded RAG answer.
   */
  async voiceChat(audioBlob: Blob, sessionId?: string, language?: "en" | "kn"): Promise<VoiceChatResponse> {
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "tourist_query.wav");
    if (sessionId) {
      formData.append("session_id", sessionId);
    }
    if (language) {
      formData.append("preferred_language", language);
    }

    const res = await fetch(`${API_BASE}/voice/chat`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<VoiceChatResponse>(res);
  },

  /**
   * Synthesize speech via offline Piper TTS, returning object URL and synthesis telemetry.
   */
  async synthesizeSpeech(req: SynthesisRequest): Promise<{ audioUrl: string; metadata: SynthesisMetadataHeaders }> {
    const res = await fetch(`${API_BASE}/voice/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      let errCode = `HTTP_${res.status}`;
      let errMsg = `Speech synthesis failed with status ${res.status}`;
      try {
        const data = (await res.json()) as ErrorEnvelope;
        if (data?.error) {
          errCode = data.error.code;
          errMsg = data.error.message;
        }
      } catch {
        // Not JSON
      }
      throw new ApiError(res.status, errMsg, errCode);
    }

    const metadata: SynthesisMetadataHeaders = {
      engine: res.headers.get("X-TTS-Engine") || undefined,
      language: res.headers.get("X-TTS-Language") || undefined,
      voice: res.headers.get("X-TTS-Voice") || undefined,
      durationSeconds: Number(res.headers.get("X-TTS-Duration-Seconds")) || undefined,
      latencyMs: Number(res.headers.get("X-TTS-Latency-Ms")) || undefined,
      cached: res.headers.get("X-TTS-Cached") === "true",
      fallbackRecommended: res.headers.get("X-TTS-Fallback-Recommended") === "true",
    };

    const blob = await res.blob();
    const audioUrl = URL.createObjectURL(blob);
    return { audioUrl, metadata };
  },
};
