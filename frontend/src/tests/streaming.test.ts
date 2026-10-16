import { describe, it, expect, vi } from "vitest";
import { streamTouristMessage } from "../services/streaming";

describe("Resilient SSE Streaming Parser", () => {
  it("processes token stream and calls onToken callback", async () => {
    const ssePayload = "event: token\ndata: {\"token\": \"Welcome\"}\n\nevent: token\ndata: {\"token\": \" to Belur\"}\n\n";
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(ssePayload));
        controller.close();
      },
    });

    const mockResponse = new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });

    vi.spyOn(global, "fetch").mockResolvedValueOnce(mockResponse);

    const tokens: string[] = [];
    await streamTouristMessage(
      "http://test/api/v1/chat/stream",
      { content: "Hello" },
      {
        onToken: (t) => tokens.push(t),
      }
    );

    expect(tokens).toEqual(["Welcome", " to Belur"]);
  });

  it("handles multibyte UTF-8 Kannada characters split across chunk boundaries", async () => {
    // "ಬೇಲೂರು" (Belur in Kannada) is multibyte UTF-8
    const kannadaText = "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ";
    const sseText = `event: token\ndata: {"token": "${kannadaText}"}\n\n`;
    const fullBytes = new TextEncoder().encode(sseText);

    // Deliberately slice right in the middle of a multibyte UTF-8 sequence
    const splitIndex = 25; // Splits within Kannada bytes
    const chunk1 = fullBytes.slice(0, splitIndex);
    const chunk2 = fullBytes.slice(splitIndex);

    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(chunk1);
        controller.enqueue(chunk2);
        controller.close();
      },
    });

    const mockResponse = new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });

    vi.spyOn(global, "fetch").mockResolvedValueOnce(mockResponse);

    let received = "";
    await streamTouristMessage(
      "http://test/api/v1/chat/stream",
      { content: "ಬೇಲೂರು" },
      {
        onToken: (t) => {
          received += t;
        },
      }
    );

    expect(received).toBe(kannadaText);
  });

  it("parses citations and done events correctly", async () => {
    const ssePayload =
      'event: token\ndata: {"token": "Fact"}\n\n' +
      'event: citations\ndata: {"citations": [{"chunk_id": "c1", "document_id": "Temple_info.pdf", "page_number": 3, "section_heading": "History", "relevance_score": 0.98, "snippet": "Built in 1117 AD"}]}\n\n' +
      'event: done\ndata: {"message_id": "m1", "session_id": "s1", "is_grounded": true, "detected_language": "en", "latency_ms": 140}\n\n';

    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(ssePayload));
        controller.close();
      },
    });

    vi.spyOn(global, "fetch").mockResolvedValueOnce(new Response(stream, { status: 200 }));

    let citationsReceived: any[] = [];
    let donePayload: any = null;

    await streamTouristMessage(
      "http://test/api/v1/chat/stream",
      { content: "When was it built?" },
      {
        onCitations: (c) => {
          citationsReceived = c;
        },
        onDone: (d) => {
          donePayload = d;
        },
      }
    );

    expect(citationsReceived).toHaveLength(1);
    expect(citationsReceived[0].page_number).toBe(3);
    expect(donePayload).not.toBeNull();
    expect(donePayload.is_grounded).toBe(true);
    expect(donePayload.latency_ms).toBe(140);
  });

  it("handles server error events in SSE stream", async () => {
    const ssePayload = 'event: error\ndata: {"error": "Knowledge base temporarily busy"}\n\n';
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(ssePayload));
        controller.close();
      },
    });

    vi.spyOn(global, "fetch").mockResolvedValueOnce(new Response(stream, { status: 200 }));

    let caughtError: any = null;
    await streamTouristMessage(
      "http://test/api/v1/chat/stream",
      { content: "test" },
      {
        onError: (err) => {
          caughtError = err;
        },
      }
    );

    expect(caughtError).not.toBeNull();
    expect(caughtError?.message).toContain("Knowledge base temporarily busy");
  });

  it("throws error and calls onError on HTTP 500 status", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response("Internal Server Error", { status: 500, statusText: "Internal Server Error" })
    );

    let callbackError: any = null;
    await expect(
      streamTouristMessage(
        "http://test/api/v1/chat/stream",
        { content: "test" },
        {
          onError: (err) => {
            callbackError = err;
          },
        }
      )
    ).rejects.toThrow();

    expect(callbackError).not.toBeNull();
    expect(callbackError?.message).toContain("500");
  });

  it("respects AbortController cancellation cleanly without throwing to onError", async () => {
    const controller = new AbortController();
    controller.abort();

    vi.spyOn(global, "fetch").mockRejectedValueOnce(new DOMException("Aborted", "AbortError"));

    const onError = vi.fn();
    await streamTouristMessage(
      "http://test/api/v1/chat/stream",
      { content: "test" },
      { onError },
      controller.signal
    );

    expect(onError).not.toHaveBeenCalled();
  });
});
