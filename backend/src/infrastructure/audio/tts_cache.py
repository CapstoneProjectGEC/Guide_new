"""Bounded in-memory LRU cache for frequently repeated short TTS synthesis responses."""

import asyncio
from collections import OrderedDict
import unicodedata
from typing import Any
from backend.src.core.logging import get_logger

logger = get_logger("infrastructure.audio.tts_cache")


class TTSAudioCache:
    """Thread-safe, bounded LRU cache for short offline speech synthesis outputs."""

    def __init__(self, max_entries: int = 128, max_text_length: int = 150) -> None:
        self.max_entries = max(1, max_entries)
        self.max_text_length = max(1, max_text_length)
        self._cache: OrderedDict[str, tuple[bytes, float, int]] = OrderedDict()
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0
        self._lock = asyncio.Lock()
        self._inflight_locks: dict[str, asyncio.Lock] = {}
        self._inflight_meta_lock = asyncio.Lock()

    @staticmethod
    def normalize_text(text: str, language: str) -> str:
        """Normalize input string to canonical representation for deterministic caching."""
        normalized = unicodedata.normalize("NFKC", text.strip())
        normalized = " ".join(normalized.split())
        if language in ("en", "en_US"):
            normalized = normalized.lower()
        return normalized

    def build_key(self, text: str, language: str, voice: str, speed: float = 1.0) -> str:
        """Generate canonical cache key."""
        norm_text = self.normalize_text(text, language)
        return f"{language}:{voice}:{round(speed, 2)}:{norm_text}"

    def is_cacheable(self, text: str) -> bool:
        """Check whether input text is eligible for caching based on length ceiling."""
        clean = text.strip()
        return bool(clean) and len(clean) <= self.max_text_length

    async def get(self, text: str, language: str, voice: str, speed: float = 1.0) -> tuple[bytes, float, int] | None:
        """Retrieve cached audio buffer if present."""
        if not self.is_cacheable(text):
            return None

        key = self.build_key(text, language, voice, speed)
        async with self._lock:
            if key in self._cache:
                self._hits += 1
                self._cache.move_to_end(key)
                logger.debug("tts_cache_hit", key=key[:40], hits=self._hits)
                return self._cache[key]

            self._misses += 1
            return None

    async def put(self, text: str, language: str, voice: str, speed: float, audio_data: tuple[bytes, float, int]) -> None:
        """Store audio buffer into LRU cache with eviction if capacity exceeded."""
        if not self.is_cacheable(text):
            return

        key = self.build_key(text, language, voice, speed)
        async with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = audio_data
                return

            if len(self._cache) >= self.max_entries:
                oldest_key, _ = self._cache.popitem(last=False)
                self._evictions += 1
                logger.debug("tts_cache_eviction", evicted_key=oldest_key[:40], total_evictions=self._evictions)

            self._cache[key] = audio_data

    async def get_or_create_lock(self, text: str, language: str, voice: str, speed: float) -> asyncio.Lock:
        """Acquire in-flight deduplication lock to prevent duplicate concurrent synthesis."""
        key = self.build_key(text, language, voice, speed)
        async with self._inflight_meta_lock:
            if key not in self._inflight_locks:
                self._inflight_locks[key] = asyncio.Lock()
            return self._inflight_locks[key]

    async def cleanup_lock(self, text: str, language: str, voice: str, speed: float) -> None:
        """Clean up in-flight deduplication lock after synthesis finishes."""
        key = self.build_key(text, language, voice, speed)
        async with self._inflight_meta_lock:
            self._inflight_locks.pop(key, None)

    async def clear(self) -> None:
        """Clear all entries and reset hit/miss counters."""
        async with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache health and utilization statistics."""
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
        }
