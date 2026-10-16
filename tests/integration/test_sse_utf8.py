"""Integration tests verifying SSE streaming and multibyte UTF-8 decoding resilience for Kannada script."""

import codecs


def test_kannada_utf8_split_across_single_byte_chunks():
    """Verify incremental decoding when UTF-8 bytes are sliced at arbitrary single-byte boundaries."""
    original = "ಹೊಯ್ಸಳರ ವಾಸ್ತುಶಿಲ್ಪ ಅದ್ಭುತವಾಗಿದೆ."
    encoded = original.encode("utf-8")
    decoder = codecs.getincrementaldecoder("utf-8")()
    pieces = [encoded[i:i + 1] for i in range(len(encoded))]
    decoded = "".join(decoder.decode(piece, final=False) for piece in pieces)
    decoded += decoder.decode(b"", final=True)

    assert decoded == original
    assert "\ufffd" not in decoded


def test_kannada_sse_events_split_across_chunks():
    """Verify incremental decoding of multiple SSE frames across varied chunk boundaries."""
    original = (
        'data: {"token":"ಹೊಯ್ಸಳ"}\n\n'
        'data: {"token":"ವಾಸ್ತುಶಿಲ್ಪ"}\n\n'
    )
    encoded = original.encode("utf-8")
    decoder = codecs.getincrementaldecoder("utf-8")()
    decoded_parts = []
    # Vary chunk boundaries instead of assuming that
    # network chunks align with characters or events.
    chunk_sizes = [1, 2, 5, 3, 7]
    position = 0
    index = 0
    while position < len(encoded):
        size = chunk_sizes[index % len(chunk_sizes)]
        piece = encoded[position:position + size]
        decoded_parts.append(
            decoder.decode(piece, final=False)
        )
        position += size
        index += 1

    decoded_parts.append(decoder.decode(b"", final=True))
    decoded = "".join(decoded_parts)

    assert decoded == original
    assert "\ufffd" not in decoded
    assert decoded.count("\n\n") == 2


def test_sse_framing_reconstruction_across_split_delimiters():
    """Verify SSE line framing parser correctly reconstructs split JSON and double-newline event delimiters."""
    events_raw = (
        'event: token\r\n'
        'data: {"token":"ಬೇಲೂರು"}\r\n\r\n'
        'event: token\r\n'
        'data: {"token":" "}\r\n\r\n'
        'event: token\r\n'
        'data: {"token":"ಚೆನ್ನಕೇಶವ"}\r\n\r\n'
    )
    encoded = events_raw.encode("utf-8")
    decoder = codecs.getincrementaldecoder("utf-8")()

    # Split with awkward chunk size = 4 bytes
    buffer = ""
    parsed_tokens = []
    chunk_size = 4

    for pos in range(0, len(encoded), chunk_size):
        chunk = encoded[pos:pos + chunk_size]
        buffer += decoder.decode(chunk, final=False)

        while "\r\n\r\n" in buffer or "\n\n" in buffer:
            sep = "\r\n\r\n" if "\r\n\r\n" in buffer else "\n\n"
            msg, buffer = buffer.split(sep, 1)
            for line in msg.splitlines():
                if line.startswith("data:"):
                    import json
                    payload = json.loads(line[5:].strip())
                    parsed_tokens.append(payload["token"])

    buffer += decoder.decode(b"", final=True)
    reconstructed = "".join(parsed_tokens)
    assert reconstructed == "ಬೇಲೂರು ಚೆನ್ನಕೇಶವ"
    assert "\ufffd" not in reconstructed
