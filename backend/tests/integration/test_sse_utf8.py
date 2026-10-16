"""Integration tests verifying SSE streaming and multibyte UTF-8 decoding resilience for Kannada script."""

from tests.integration.test_sse_utf8 import (
    test_kannada_utf8_split_across_single_byte_chunks,
    test_kannada_sse_events_split_across_chunks,
    test_sse_framing_reconstruction_across_split_delimiters,
)

__all__ = [
    "test_kannada_utf8_split_across_single_byte_chunks",
    "test_kannada_sse_events_split_across_chunks",
    "test_sse_framing_reconstruction_across_split_delimiters",
]
