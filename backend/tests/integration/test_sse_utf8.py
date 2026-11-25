"""Integration tests verifying SSE streaming and multibyte UTF-8 decoding resilience for Kannada script."""

import codecs
import json
import pytest


def test_kannada_utf8_split_across_single_byte_chunks() -> None:
    """Verify that multi-byte Kannada UTF-8 sequences split byte-by-byte are reconstructed without replacement chars."""
    kannada_text = "ಬೇಲೂರು ಚನ್ನಕೇಶವ ದೇವಾಲಯ ಹೊಯ್ಸಳ ವಾಸ್ತುಶಿಲ್ಪ"
    raw_bytes = kannada_text.encode("utf-8")

    decoder = codecs.getincrementaldecoder("utf-8")()
    reconstructed = []

    for b in raw_bytes:
        chunk = decoder.decode(bytes([b]), final=False)
        if chunk:
            reconstructed.append(chunk)

    final_chunk = decoder.decode(b"", final=True)
    if final_chunk:
        reconstructed.append(final_chunk)

    result = "".join(reconstructed)
    assert result == kannada_text
    assert "\ufffd" not in result


def test_kannada_sse_events_split_across_chunks() -> None:
    """Verify parsing SSE stream when Kannada token events are segmented across arbitrary buffer boundaries."""
    tokens = ["ಬೇಲೂರು ", "ಚನ್ನಕೇಶವ ", "ದೇವಾಲಯವು ", "ಕರ್ನಾಟಕದಲ್ಲಿದೆ."]
    events = [f"event: token\ndata: {json.dumps({'token': t}, ensure_ascii=False)}\n\n" for t in tokens]
    full_stream = "".join(events)
    stream_bytes = full_stream.encode("utf-8")

    # Split stream into awkward small chunks (e.g. 5 bytes each)
    chunk_size = 5
    byte_chunks = [stream_bytes[i:i + chunk_size] for i in range(0, len(stream_bytes), chunk_size)]

    # Stream parser simulator
    decoder = codecs.getincrementaldecoder("utf-8")()
    buffer = ""
    parsed_tokens = []

    for chunk in byte_chunks:
        buffer += decoder.decode(chunk, final=False)
        while "\n\n" in buffer:
            event_raw, buffer = buffer.split("\n\n", 1)
            for line in event_raw.splitlines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if "token" in payload:
                        parsed_tokens.append(payload["token"])

    buffer += decoder.decode(b"", final=True)
    assert "".join(parsed_tokens) == "".join(tokens)


def test_sse_framing_reconstruction_across_split_delimiters() -> None:
    """Verify delimiters split across frame boundaries (e.g. '\\n' in one chunk and '\\n' in the next)."""
    event = 'event: done\ndata: {"is_grounded": true, "language": "kn"}\n\n'
    raw_bytes = event.encode("utf-8")

    # Split exactly between the two newline characters
    cut_point = len(raw_bytes) - 1  # Between \n and \n
    chunk1 = raw_bytes[:cut_point]
    chunk2 = raw_bytes[cut_point:]

    decoder = codecs.getincrementaldecoder("utf-8")()
    text = decoder.decode(chunk1, final=False)
    assert "\n\n" not in text

    text += decoder.decode(chunk2, final=True)
    assert "\n\n" in text

    frame, _ = text.split("\n\n", 1)
    data_line = [l for l in frame.splitlines() if l.startswith("data: ")][0]
    payload = json.loads(data_line[6:])
    assert payload["is_grounded"] is True
    assert payload["language"] == "kn"
