"""Unit tests for Phase 1-9 engineering fixes:
1. <unk> token rejection in FactPreservationValidator
2. PDF header stripping in prompt_builder
3. Sentence boundary trimming in conversation_manager
4. Era marker conversion in HeritageTranslator
5. Citation concept word-boundary isolation
"""

import pytest
import re
from backend.src.application.translation.fact_validator import FactPreservationValidator
from backend.src.application.chat.prompt_builder import PromptBuilder, clean_chunk_content
from backend.src.application.translation.heritage_translator import HeritageTranslator
from backend.src.application.chat.conversation_manager import ConversationManager
from backend.src.domain.rag import RetrievalCandidate


def test_fact_preservation_validator_unk_rejection():
    """FactPreservationValidator must reject translations containing <unk> tokens."""
    english_text = "The temple was built by King Vishnuvardhana in 1117 CE."
    kannada_with_unk = "ದೇವಾಲಯವನ್ನು <unk> ವಿಷ್ಣುವರ್ಧನನು 1117ರಲ್ಲಿ ನಿರ್ಮಿಸಿದನು."

    is_valid, missing = FactPreservationValidator.validate(english_text, kannada_with_unk)
    assert not is_valid
    assert any("UnkToken" in m for m in missing)


def test_fact_preservation_validator_missing_year():
    """FactPreservationValidator must detect missing years."""
    english_text = "The temple was built by King Vishnuvardhana in 1117 CE."
    kannada_without_year = "ದೇವಾಲಯವನ್ನು ಹೊಯ್ಸಳ ರಾಜ ವಿಷ್ಣುವರ್ಧನನು ನಿರ್ಮಿಸಿದನು."

    is_valid, missing = FactPreservationValidator.validate(english_text, kannada_without_year)
    assert not is_valid
    assert "Year 1117" in missing


def test_pdf_header_stripping():
    """PromptBuilder must strip PDF header and page artifacts."""
    raw_chunk = (
        "Belur Chennakeshava Temple – Heritage Knowledge Base\nPage 18\n3.13 Subsidiary shrines in the courtyard\n"
        "Shrine Position Key facts given in the source\n"
        "Kappe-Chennigaraya Temple (the Queen’s Shrine)\n"
        "Just south of the main temple Built in 1117 CE by Queen Santale."
    )
    cleaned = clean_chunk_content(raw_chunk)
    assert "Heritage Knowledge Base" not in cleaned
    assert "Built in 1117 CE by Queen Santale" in cleaned


def test_sentence_boundary_trimming():
    """Regex must trim incomplete trailing sentences before translation."""
    incomplete_text = "King Vishnuvardhana built the temple in 1117 CE. It features intricately carved stone pillars that were"
    pattern = r"^(.*[.!?])(?:\s+[^.!?]*)$"
    match = re.search(pattern, incomplete_text, re.DOTALL)
    assert match is not None
    trimmed = match.group(1).strip()
    assert trimmed == "King Vishnuvardhana built the temple in 1117 CE."


def test_era_marker_conversion():
    """HeritageTranslator must convert era markers and English year formats to canonical Kannada."""
    translator = HeritageTranslator()
    
    # 1. '1117 CE ಯಲ್ಲಿ' -> 'ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ'
    raw_kn = "ದೇವಾಲಯವನ್ನು 1117 CE ಯಲ್ಲಿ ನಿರ್ಮಿಸಲಾಯಿತು."
    normalized = translator.post_process_kannada(raw_kn)
    assert "ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ" in normalized
    assert "CE" not in normalized

    # 2. '1117 AD ಯಲ್ಲಿ' -> 'ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ'
    raw_ad = "ದೇವಾಲಯವನ್ನು 1117 AD ಯಲ್ಲಿ ನಿರ್ಮಿಸಲಾಯಿತು."
    normalized_ad = translator.post_process_kannada(raw_ad)
    assert "ಕ್ರಿ.ಶ. 1117ರಲ್ಲಿ" in normalized_ad
    assert "AD" not in normalized_ad


def test_citation_word_boundary_isolation():
    """_select_relevant_citations must isolate single-topic queries from irrelevant chunks (Problem 5)."""
    mock_candidates = [
        RetrievalCandidate(
            chunk_id="chunk_patron",
            document_id="doc1",
            content="The Chennakeshava Temple was commissioned by King Vishnuvardhana in 1117 CE.",
            page_number=1,
            section_heading="Section 1: Historical Patronage and Inception",
            relevance_score=0.99
        ),
        RetrievalCandidate(
            chunk_id="chunk_garbhagriha",
            document_id="doc1",
            content="The Garbhagriha houses a 6-foot-tall black stone idol of Lord Chennakeshava.",
            page_number=2,
            section_heading="Section 5: Garbhagriha and Main Sanctum",
            relevance_score=0.95
        ),
    ]

    # Single-topic query: "Who built the temple and when?"
    single_res = ConversationManager._select_relevant_citations(
        mock_candidates, "Who built the Chennakeshava temple and when? King Vishnuvardhana 1117"
    )
    assert len(single_res) == 1
    assert single_res[0].chunk_id == "chunk_patron"

    # Multi-part query: "Who built the temple and what deity is in the sanctum?"
    multi_res = ConversationManager._select_relevant_citations(
        mock_candidates, "Who built the temple and what deity idol is inside the Garbhagriha sanctum? King Vishnuvardhana 1117"
    )
    assert len(multi_res) == 2
    assert {c.chunk_id for c in multi_res} == {"chunk_patron", "chunk_garbhagriha"}
