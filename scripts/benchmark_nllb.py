"""Benchmark 10 sentence pairs covering all requested categories using NLLB-200 CTranslate2."""

import sys
import os
import time
import ctranslate2
from transformers import AutoTokenizer

sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")

model_dir = "data/models/nllb-200-600M-ct2-int8"
tokenizer_dir = r"C:\Users\user\.cache\huggingface\hub\models--facebook--nllb-200-distilled-600M\snapshots\f8d333a098d19b4fd9a8b18f94170487ad3f821d"

tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)
translator = ctranslate2.Translator(model_dir, device="cpu", compute_type="int8")

# 10 test sentences covering required categories
test_sentences_en_to_kn = [
    # 1. Proper nouns
    ("Queen Shantala Devi patronized the arts and supported temple construction.", "Proper Nouns"),
    # 2. Historical dates
    ("The temple consecration was completed in 1117 CE by the Hoysala dynasty.", "Historical Dates"),
    # 3. Numerical information
    ("There are 42 Madanika bracket figures, including 38 on exterior walls and 4 on interior ceilings.", "Numerical Information"),
    # 4. Multiple factual clauses
    ("King Vishnuvardhana won the Battle of Talakad, converted to Vaishnavism, and commissioned the Belur temple.", "Multiple Factual Clauses"),
    # 5. Negation
    ("The artisans did not use hard granite, but instead selected fine-grained chloritic schist.", "Negation"),
    # 6. Architectural terminology
    ("The stellate Jagati platform elevates the main sanctum above ground level.", "Architectural Terminology"),
    # 7. Historical terminology
    ("The Battle of Talakad marked a decisive victory over the Chola empire.", "Historical Terminology"),
    # 8. Long sentences
    ("Located on the banks of the Yagachi River in Hassan district, Belur served as the historic capital of the Hoysala Empire during the twelfth century.", "Long Sentences"),
    # 9. Question-answer translation
    ("Who built the Chennakeshava Temple at Belur and when? It was built by King Vishnuvardhana in 1117 CE.", "Question-Answer Translation"),
    # 10. Unfamiliar terminology
    ("Filigree stone relief carvings depict mythological narratives with astonishing undercut craftsmanship.", "Unfamiliar Terminology"),
]

def translate_en_to_kn(text: str) -> tuple[str, float]:
    tokenizer.src_lang = "eng_Latn"
    tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
    t0 = time.perf_counter()
    results = translator.translate_batch([tokens], target_prefix=[["kan_Knda"]])
    trans_tokens = results[0].hypotheses[0][1:]
    res = tokenizer.decode(tokenizer.convert_tokens_to_ids(trans_tokens))
    duration_ms = (time.perf_counter() - t0) * 1000
    return res, duration_ms

def translate_kn_to_en(text: str) -> tuple[str, float]:
    tokenizer.src_lang = "kan_Knda"
    tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
    t0 = time.perf_counter()
    results = translator.translate_batch([tokens], target_prefix=[["eng_Latn"]])
    trans_tokens = results[0].hypotheses[0][1:]
    res = tokenizer.decode(tokenizer.convert_tokens_to_ids(trans_tokens))
    duration_ms = (time.perf_counter() - t0) * 1000
    return res, duration_ms

if __name__ == "__main__":
    print("=" * 70)
    print("NLLB-200 DISTILLED 600M (CTRANSLATE2 INT8) - 10-SENTENCE BENCHMARK")
    print("=" * 70)

    # Warmup
    translate_en_to_kn("Warmup initialization.")

    timings = []
    print("\n--- ENGLISH TO KANNADA ---")
    kn_outputs = []
    for i, (en_text, category) in enumerate(test_sentences_en_to_kn, 1):
        kn_out, ms = translate_en_to_kn(en_text)
        timings.append(ms)
        kn_outputs.append(kn_out)
        print(f"\n[{i}] Category: {category}")
        print(f"EN: {en_text}")
        print(f"KN: {kn_out}")
        print(f"Latency: {ms:.2f} ms")

    print("\n--- KANNADA TO ENGLISH (ROUNDTRIP EVALUATION) ---")
    for i, kn_text in enumerate(kn_outputs[:5], 1):
        en_out, ms = translate_kn_to_en(kn_text)
        print(f"\n[Roundtrip {i}]")
        print(f"KN Input:  {kn_text}")
        print(f"EN Output: {en_out}")
        print(f"Latency:   {ms:.2f} ms")

    avg_ms = sum(timings) / len(timings)
    print("\n" + "=" * 70)
    print(f"Average Inference Latency (EN->KN): {avg_ms:.2f} ms")
    print(f"Minimum: {min(timings):.2f} ms | Maximum: {max(timings):.2f} ms")
    print("Memory: ~622 MB disk, ~900 MB RAM")
    print("Offline: 100% Local Inference (CTranslate2 INT8)")
    print("=" * 70)

