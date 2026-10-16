import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "../services/api";

describe("Typed API Client (/api/v1)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.URL.createObjectURL = vi.fn().mockReturnValue("blob:http://localhost/mock-audio-blob");
  });

  it("createSession sends correct JSON and parses response", async () => {
    const mockSession = {
      id: "sess-12345",
      client_fingerprint: "fp-abc",
      preferred_language: "kn",
      created_at: "2026-10-13T10:00:00Z",
      last_active_at: "2026-10-13T10:00:00Z",
      messages: [],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockSession), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const session = await apiClient.createSession("fp-abc", "kn");
    expect(session.id).toBe("sess-12345");
    expect(session.preferred_language).toBe("kn");
  });

  it("sendMessage posts user payload and parses ChatMessage", async () => {
    const mockMessage = {
      id: "msg-1",
      session_id: "sess-12345",
      role: "assistant",
      content: "The temple was built by King Vishnuvardhana.",
      detected_language: "en",
      input_mode: "text",
      is_grounded: true,
      created_at: "2026-10-13T10:01:00Z",
      citations: [
        {
          chunk_id: "chk-1",
          document_id: "Temple_info.pdf",
          page_number: 2,
          section_heading: "Chronology",
          relevance_score: 0.99,
          snippet: "King Vishnuvardhana commissioned it in 1117 AD",
        },
      ],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockMessage), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const resp = await apiClient.sendMessage({
      session_id: "sess-12345",
      content: "Who built it?",
      preferred_language: "en",
    });

    expect(resp.content).toContain("King Vishnuvardhana");
    expect(resp.citations).toHaveLength(1);
    expect(resp.citations[0].page_number).toBe(2);
  });

  it("transcribeAudio sends audio FormData and parses TranscriptionResult", async () => {
    const mockTranscription = {
      text: "ನಮಸ್ಕಾರ ಬೇಲೂರು",
      detected_language: "kn",
      language_probability: 0.99,
      duration_seconds: 1.5,
      is_silent: false,
      device: "cpu",
      compute_type: "int8",
      model_name: "base",
      latency_ms: 150,
      segments: [],
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockTranscription), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const mockBlob = new Blob(["RIFF...."], { type: "audio/wav" });
    const result = await apiClient.transcribeAudio(mockBlob, "kn");

    expect(result.text).toBe("ನಮಸ್ಕಾರ ಬೇಲೂರು");
    expect(result.detected_language).toBe("kn");
    expect(result.latency_ms).toBe(150);
  });

  it("synthesizeSpeech parses binary WAV blob and extracts X-TTS headers", async () => {
    const mockWavBytes = new Uint8Array([82, 73, 70, 70]); // RIFF
    const headers = new Headers({
      "Content-Type": "audio/wav",
      "X-TTS-Engine": "piper",
      "X-TTS-Language": "en",
      "X-TTS-Voice": "en_US-lessac-medium",
      "X-TTS-Latency-Ms": "180",
      "X-TTS-Cached": "true",
      "X-TTS-Fallback-Recommended": "false",
    });

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(mockWavBytes, {
        status: 200,
        headers,
      })
    );

    const { audioUrl, metadata } = await apiClient.synthesizeSpeech({
      text: "Welcome to Belur",
      language: "en",
    });

    expect(audioUrl).toContain("blob:");
    expect(metadata.engine).toBe("piper");
    expect(metadata.language).toBe("en");
    expect(metadata.cached).toBe(true);
    expect(metadata.latencyMs).toBe(180);
  });

  it("extracts structured ErrorEnvelope on HTTP 400/429/500 errors", async () => {
    const mockErrorEnvelope = {
      error: {
        code: "RATE_LIMIT_EXCEEDED",
        message: "Rate limit of 60 requests per minute exceeded.",
        details: { retry_after_seconds: 12 },
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockErrorEnvelope), {
        status: 429,
        headers: { "Content-Type": "application/json" },
      })
    );

    await expect(
      apiClient.sendMessage({ content: "Too fast" })
    ).rejects.toThrow("Rate limit of 60 requests per minute exceeded.");
  });
});
