"""Unit tests verifying FactPreservationValidator negative detection, warnings, and retry behavior."""

import logging
import pytest
from backend.src.application.translation.fact_validator import FactPreservationValidator


def test_fact_validator_detects_missing_year_1117(capsys: pytest.CaptureFixture) -> None:
    """Verify FactPreservationValidator flags missing year 1117 as invalid and logs a warning."""
    english = "The Chennakeshava Temple at Belur was built by Hoysala ruler King Vishnuvardhana in 1117 CE."
    # Flawed response where the year 1117 is dropped (reproducing the exact bug from the user screenshot)
    kannada_flawed = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ದೊರೆ ವಿಷ್ಣುವರ್ಧನನು ನಿರ್ಮಿಸಿದನು."

    is_valid, missing = FactPreservationValidator.validate(english, kannada_flawed)

    assert is_valid is False
    assert "Year 1117" in missing
    # Verify warning was logged via structlog
    captured = capsys.readouterr().out + capsys.readouterr().err
    assert "fact_preservation_validation_failed" in captured
    assert "Year 1117" in captured


def test_fact_validator_passes_when_year_1117_present() -> None:
    """Verify FactPreservationValidator passes when year 1117 is properly preserved."""
    english = "The Chennakeshava Temple at Belur was built by Hoysala ruler King Vishnuvardhana in 1117 CE."
    kannada_valid = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ದೊರೆ ವಿಷ್ಣುವರ್ಧನನು 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು."

    is_valid, missing = FactPreservationValidator.validate(english, kannada_valid)
    assert is_valid is True
    assert len(missing) == 0


def test_fact_validator_passes_with_kannada_numerals() -> None:
    """Verify FactPreservationValidator recognizes native Kannada numerals ೧೧೧೭."""
    english = "The Chennakeshava Temple at Belur was built by Hoysala ruler King Vishnuvardhana in 1117 CE."
    kannada_numerals = "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ದೊರೆ ವಿಷ್ಣುವರ್ಧನನು ೧೧೧೭ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು."

    is_valid, missing = FactPreservationValidator.validate(english, kannada_numerals)
    assert is_valid is True
    assert len(missing) == 0


def test_fact_validator_retry_pipeline_simulation() -> None:
    """Simulate the generation retry loop when first translation drops facts."""
    english = "The Chennakeshava Temple was built in 1117 CE by King Vishnuvardhana."
    mock_translations = [
        "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ವಿಷ್ಣುವರ್ಧನನು ನಿರ್ಮಿಸಿದನು.",  # Attempt 1: dropped 1117
        "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ವಿಷ್ಣುವರ್ಧನನು 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು.",  # Attempt 2: retry success
    ]

    selected_translation = None
    retries = 0

    for cand in mock_translations:
        is_valid, missing = FactPreservationValidator.validate(english, cand)
        if is_valid:
            selected_translation = cand
            break
        retries += 1

    assert retries == 1
    assert selected_translation == mock_translations[1]
    assert "1117" in selected_translation
