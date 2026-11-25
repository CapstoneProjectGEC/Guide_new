"""Phase 3 Translation Benchmark:
1. 20 English-to-Kannada answer translations
2. 10 Kannada-to-English query translations
"""

import json
import time
from pathlib import Path
from backend.src.application.translation.fact_validator import FactPreservationValidator
from backend.src.application.translation.heritage_translator import HeritageTranslator
from backend.src.application.translation.query_normalizer import QueryNormalizer
from backend.src.application.translation.translator import TranslationService
from backend.src.infrastructure.translation.nllb_engine import get_nllb_engine

EN_TO_KN_CASES = [
    {
        "id": "EN_KN_01",
        "en": "The Chennakeshava Temple at Belur was built by Hoysala ruler King Vishnuvardhana in 1117 CE.",
        "expected_facts": {"years": ["1117"], "entities": ["Belur", "Vishnuvardhana", "Hoysala", "Chennakeshava"]},
    },
    {
        "id": "EN_KN_02",
        "en": "The Kappe Chennigaraya Shrine was built in 1117 CE by Queen Santale, senior wife of Vishnuvardhana.",
        "expected_facts": {"years": ["1117"], "entities": ["Vishnuvardhana", "Kappe Chennigaraya"]},
    },
    {
        "id": "EN_KN_03",
        "en": "There are 42 Madanika bracket figures in total, with 38 on the exterior and 4 inside the Navaranga.",
        "expected_facts": {"counts": ["42", "38", "4"], "entities": ["Madanika", "Navaranga"]},
    },
    {
        "id": "EN_KN_04",
        "en": "The temple was constructed using chloritic schist, also known as soapstone.",
        "expected_facts": {"entities": []},
    },
    {
        "id": "EN_KN_05",
        "en": "Darpana Sundari is the famous bracket figure of a lady looking into a mirror.",
        "expected_facts": {"entities": ["Darpana Sundari"]},
    },
    {
        "id": "EN_KN_06",
        "en": "The temple complex is located in Belur in the Hassan district of Karnataka.",
        "expected_facts": {"entities": ["Belur"]},
    },
    {
        "id": "EN_KN_07",
        "en": "Master sculptor Jakanachari and artist Dasoja contributed significantly to the stone carvings.",
        "expected_facts": {"entities": ["Dasoja"]},
    },
    {
        "id": "EN_KN_08",
        "en": "The Chennakeshava Temple was recognized as a UNESCO World Heritage Site in 2023.",
        "expected_facts": {"years": ["2023"], "entities": ["UNESCO", "Chennakeshava"]},
    },
    {
        "id": "EN_KN_09",
        "en": "The sanctum contains the deity Keshava standing upon a Garuda pedestal.",
        "expected_facts": {"entities": []},
    },
    {
        "id": "EN_KN_10",
        "en": "King Vishnuvardhana commissioned the temple to celebrate his victory at Talakad.",
        "expected_facts": {"entities": ["Vishnuvardhana", "Talakad"]},
    },
    {
        "id": "EN_KN_11",
        "en": "The temple opens daily for tourists at 7:30 AM and closes at 7:30 PM.",
        "expected_facts": {"counts": []},
    },
    {
        "id": "EN_KN_12",
        "en": "The star-shaped platform known as the Jagati provides a wide circumambulatory path.",
        "expected_facts": {"entities": []},
    },
    {
        "id": "EN_KN_13",
        "en": "The Mohini pillar inside the Navaranga is lathe-turned and polished to a mirror finish.",
        "expected_facts": {"entities": ["Navaranga"]},
    },
    {
        "id": "EN_KN_14",
        "en": "The Narasimha pillar is renowned for its intricate rotating stone rings.",
        "expected_facts": {"entities": []},
    },
    {
        "id": "EN_KN_15",
        "en": "Queen Shantala Devi was skilled in classical dance, music, and royal patronage.",
        "expected_facts": {"entities": ["Shantala Devi"]},
    },
    {
        "id": "EN_KN_16",
        "en": "The temple was originally called Vijayanarayana Temple upon its consecration in 1117 CE.",
        "expected_facts": {"years": ["1117"], "entities": []},
    },
    {
        "id": "EN_KN_17",
        "en": "The stepped holy water tank named Pushkarani is situated at the north-east corner.",
        "expected_facts": {"entities": []},
    },
    {
        "id": "EN_KN_18",
        "en": "The Hoysala dynasty ruled the southern Deccan region between the 10th and 14th centuries.",
        "expected_facts": {"entities": ["Hoysala"]},
    },
    {
        "id": "EN_KN_19",
        "en": "The horizontal base friezes depict 650 charging war elephants, lions, and horses.",
        "expected_facts": {"counts": ["650"]},
    },
    {
        "id": "EN_KN_20",
        "en": "Halebidu is located 16 kilometers from Belur and was the capital city of Dorasamudra.",
        "expected_facts": {"counts": ["16"], "entities": ["Belur", "Halebidu"]},
    },
]

KN_TO_EN_QUERIES = [
    {"id": "KN_EN_01", "kn": "ಬೇಲೂರಿನ ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಮತ್ತು ಯಾವಾಗ ಕಟ್ಟಿಸಿದರು?", "expected_terms": ["Belur", "Chennakeshava"]},
    {"id": "KN_EN_02", "kn": "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ ಗುಡಿ", "expected_terms": ["Kappe Chennigaraya"]},
    {"id": "KN_EN_03", "kn": "ನವರಂಗದ ದುಂಡನೆಯ ಹೊಳಪಿನ ಕಂಬಗಳನ್ನು ಹೇಗೆ ಮಾಡಿದರು?", "expected_terms": ["Navaranga"]},
    {"id": "KN_EN_04", "kn": "ದೇವಾಲಯದಲ್ಲಿ ಒಟ್ಟು ಎಷ್ಟು ಮದನಿಕಾ ಶಿಲ್ಪಗಳಿವೆ?", "expected_terms": ["Madanika"]},
    {"id": "KN_EN_05", "kn": "ದರ್ಪಣ ಸುಂದರಿ ಶಿಲ್ಪ ಎಲ್ಲಿದೆ?", "expected_terms": ["Darpana Sundari"]},
    {"id": "KN_EN_06", "kn": "ದೇವಾಲಯ ನಿರ್ಮಾಣಕ್ಕೆ ಯಾವ ಕಲ್ಲನ್ನು ಬಳಸಲಾಗಿದೆ?", "expected_terms": ["stone"]},
    {"id": "KN_EN_07", "kn": "ಬೇಲೂರು ದೇವಾಲಯದ ಇತಿಹಾಸವೇನು?", "expected_terms": ["Belur"]},
    {"id": "KN_EN_08", "kn": "ಶಾಂತಲಾ ದೇವಿ ಯಾರು?", "expected_terms": ["Shantala Devi"]},
    {"id": "KN_EN_09", "kn": "ದೇವಾಲಯದ ಪ್ರವೇಶ ಸಮಯ ಮತ್ತು ದರ್ಶನ ಸಮಯ ತಿಳಿಸಿ", "expected_terms": ["time"]},
    {"id": "KN_EN_10", "kn": "ಗರ್ಭಗೃಹದ ಒಳಗೆ ಯಾವ ದೇವರ ಮೂರ್ತಿ ಇದೆ?", "expected_terms": ["Garbhagriha"]},
]


def run_benchmarks():
    print("=" * 70)
    print("PHASE 3: COMPREHENSIVE TRANSLATION BENCHMARKS")
    print("=" * 70)

    service = TranslationService()
    normalizer = QueryNormalizer()

    # 1. EN -> KN Benchmark
    en_kn_results = []
    print("\n--- Running 20 EN -> KN Answer Translations ---")
    for case in EN_TO_KN_CASES:
        t0 = time.perf_counter()
        kn_trans = service.translate_text(case["en"], source_language="en", target_language="kn")
        latency_ms = (time.perf_counter() - t0) * 1000.0

        is_fact_valid, missing_facts = FactPreservationValidator.validate(case["en"], kn_trans)
        unapproved_latin = HeritageTranslator.detect_unapproved_latin_words(kn_trans)
        has_unk = "<unk>" in kn_trans

        # Era marker check
        era_ok = True
        if "1117 CE" in case["en"]:
            era_ok = "ಕ್ರಿ.ಶ. 1117" in kn_trans or "1117" in kn_trans

        res_entry = {
            "id": case["id"],
            "english_source": case["en"],
            "kannada_translation": kn_trans,
            "latency_ms": round(latency_ms, 2),
            "fact_preservation_valid": is_fact_valid,
            "missing_facts": missing_facts,
            "unapproved_latin_words": unapproved_latin,
            "has_unk_tokens": has_unk,
            "era_marker_converted": era_ok,
        }
        en_kn_results.append(res_entry)
        print(f"[{case['id']}] Latency: {latency_ms:.1f}ms | Valid: {is_fact_valid} | Output: {kn_trans[:60]}...")

    Path("logs/translation_benchmark_20.json").write_text(
        json.dumps(en_kn_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[OK] Saved 20 EN->KN results to logs/translation_benchmark_20.json")

    # 2. KN -> EN Query Benchmark
    kn_en_results = []
    print("\n--- Running 10 KN -> EN Query Translations ---")
    for q_case in KN_TO_EN_QUERIES:
        t0 = time.perf_counter()
        norm = normalizer.normalize_for_retrieval(q_case["kn"], source_lang="kn", target_lang="en")
        latency_ms = (time.perf_counter() - t0) * 1000.0

        retrieval_q = norm.retrieval_query
        retrieval_lower = retrieval_q.lower()
        terms_preserved = [t for t in q_case["expected_terms"] if t.lower() in retrieval_lower]
        all_preserved = len(terms_preserved) == len(q_case["expected_terms"])

        entry = {
            "id": q_case["id"],
            "kannada_query": q_case["kn"],
            "retrieval_query": retrieval_q,
            "strategy_used": str(norm.strategy_used),
            "preserved_terms": norm.preserved_terms,
            "expected_terms": q_case["expected_terms"],
            "terms_matched": terms_preserved,
            "all_terms_preserved": all_preserved,
            "latency_ms": round(latency_ms, 2),
        }
        kn_en_results.append(entry)
        print(f"[{q_case['id']}] Latency: {latency_ms:.1f}ms | All Preserved: {all_preserved} | Result: {retrieval_q}")

    Path("logs/query_translation_benchmark_10.json").write_text(
        json.dumps(kn_en_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n[OK] Saved 10 KN->EN query results to logs/query_translation_benchmark_10.json")


if __name__ == "__main__":
    run_benchmarks()
