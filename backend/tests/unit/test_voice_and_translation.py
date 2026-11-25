"""Unit tests verifying Piper voice discovery, config validation, Argos translation status, and offline fallback."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.src.application.translation.translator import TranslationService
from backend.src.infrastructure.audio.piper_engine import PiperEngine
from backend.src.infrastructure.translation.argos_engine import ArgosTranslationEngine


def test_piper_voice_discovery_missing_onnx(tmp_path: Path) -> None:
    """Verify is_voice_available returns False when .onnx file is absent."""
    engine = PiperEngine(models_dir=str(tmp_path))
    json_file = tmp_path / "test-voice.onnx.json"
    json_file.write_text('{"audio": {"sample_rate": 22050}}', encoding="utf-8")

    assert engine.is_voice_available("test-voice") is False


def test_piper_voice_discovery_missing_json(tmp_path: Path) -> None:
    """Verify is_voice_available returns False when .onnx.json config is absent."""
    engine = PiperEngine(models_dir=str(tmp_path))
    onnx_file = tmp_path / "test-voice.onnx"
    onnx_file.write_bytes(b"dummy onnx weights" * 100)

    assert engine.is_voice_available("test-voice") is False


def test_piper_voice_discovery_corrupt_json(tmp_path: Path) -> None:
    """Verify is_voice_available returns False when .onnx.json is corrupt/invalid JSON."""
    engine = PiperEngine(models_dir=str(tmp_path))
    onnx_file = tmp_path / "test-voice.onnx"
    onnx_file.write_bytes(b"dummy onnx weights" * 100)
    json_file = tmp_path / "test-voice.onnx.json"
    json_file.write_text("CORRUPTED NOT JSON {{{", encoding="utf-8")

    assert engine.is_voice_available("test-voice") is False


def test_piper_voice_discovery_valid_pair(tmp_path: Path) -> None:
    """Verify is_voice_available returns True when valid .onnx and .onnx.json pair exists."""
    engine = PiperEngine(models_dir=str(tmp_path))
    onnx_file = tmp_path / "valid-voice.onnx"
    onnx_file.write_bytes(b"dummy onnx weights" * 100)
    json_file = tmp_path / "valid-voice.onnx.json"
    json_file.write_text('{"audio": {"sample_rate": 22050}, "espeak": {"voice": "en"}}', encoding="utf-8")

    assert engine.is_voice_available("valid-voice") is True


def test_argos_translation_unavailable_pair_returns_none() -> None:
    """Verify that unsupported language pair (e.g. kn->en) returns None from engine to trigger offline fallback."""
    engine = ArgosTranslationEngine()
    # Kannada is not supported in Argos catalog
    assert engine.is_language_pair_available("kn", "en") is False
    res = engine.translate("ಬೇಲೂರು ದೇವಾಲಯ", "kn", "en")
    assert res is None


def test_translation_service_graceful_offline_fallback() -> None:
    """Verify TranslationService falls back to normalized retrieval text for Kannada queries without cloud APIs."""
    svc = TranslationService()
    # Input Kannada text with temple term
    kannada_input = "ಬೇಲೂರು ಚನ್ನಕೇಶವ"
    output = svc.translate_text(kannada_input, source_language="kn", target_language="en", preserve_heritage=True)

    # Offline normalization should expand or preserve the term rather than failing
    assert output is not None
    assert len(output.strip()) > 0
