/**
 * Resilient Server-Sent Events (SSE) stream parser and client for tourist chat.
 * Correctly decodes multibyte UTF-8 Kannada characters across arbitrary network chunk boundaries.
 */

export interface Citation {
  chunk_id: string;
  document_id: string;
  page_number: number;
  section_heading: string | null;
  relevance_score: number;
  snippet: string;
}

import { ImageCard } from "@/types/api";

export interface StreamDonePayload {
  message_id: string;
  session_id: string;
  is_grounded: boolean;
  has_timing_uncertainty?: boolean;
  detected_language: string;
  latency_ms: number;
}

export interface SendMessagePayload {
  session_id?: string | null;
  client_fingerprint?: string | null;
  content: string;
  preferred_language?: string | null;
  input_mode?: "text" | "voice";
}

export interface StreamCallbacks {
  onToken?: (token: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onImages?: (images: ImageCard[]) => void;
  onTimingNotice?: (notice: boolean) => void;
  onDone?: (payload: StreamDonePayload) => void;
  onError?: (error: Error) => void;
}

/**
 * Consumes the /api/v1/chat/stream SSE endpoint with streaming UTF-8 decoding.
 */
export async function streamTouristMessage(
  endpointUrl: string,
  payload: SendMessagePayload,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;

  try {
    const response = await fetch(endpointUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      const errText = await response.text();
      const error = new Error(`Streaming failed with status ${response.status}: ${errText}`);
      callbacks.onError?.(error);
      throw error;
    }

    reader = response.body?.getReader();
    if (!reader) {
      const error = new Error("Response body is not readable.");
      callbacks.onError?.(error);
      throw error;
    }

    // Preserve multibyte UTF-8 state across chunk boundaries (crucial for Kannada script)
    const decoder = new TextDecoder("utf-8", { fatal: false });
    let buffer = "";
    let currentEvent = "message";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete double-newline separated SSE messages
      let boundaryIndex: number;
      while ((boundaryIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawMessage = buffer.slice(0, boundaryIndex);
        buffer = buffer.slice(boundaryIndex + 2);

        const lines = rawMessage.split(/\r?\n/);
        let dataStr = "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const dataLine = line.slice(5).trim();
            dataStr = dataStr ? `${dataStr}\n${dataLine}` : dataLine;
          }
        }

        if (dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            if (currentEvent === "token" && parsed.token !== undefined) {
              callbacks.onToken?.(parsed.token);
            } else if (currentEvent === "citations" && parsed.citations) {
              callbacks.onCitations?.(parsed.citations);
            } else if (currentEvent === "images" && parsed.images) {
              callbacks.onImages?.(parsed.images);
            } else if (currentEvent === "timing_notice") {
              callbacks.onTimingNotice?.(Boolean(parsed.notice));
            } else if (currentEvent === "done") {
              callbacks.onDone?.(parsed);
            } else if (currentEvent === "error") {
              callbacks.onError?.(new Error(parsed.error || "Unknown stream error"));
            }
          } catch {
            // Raw text fallback if data was not JSON
            if (currentEvent === "token") {
              callbacks.onToken?.(dataStr);
            }
          }
        }

        currentEvent = "message"; // Reset for next SSE frame
      }
    }

    // Flush any remaining decoder buffer
    decoder.decode();
  } catch (err: any) {
    if (signal?.aborted || err?.name === "AbortError") {
      // Clean abort, do not trigger error callback or rethrow
      return;
    }
    callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    throw err;
  } finally {
    if (reader) {
      try {
        reader.releaseLock();
      } catch {
        // Ignored
      }
    }
  }
}
