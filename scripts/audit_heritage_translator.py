import sys
import os

sys.path.insert(0, os.path.abspath("."))
sys.stdout.reconfigure(encoding="utf-8")
from backend.src.infrastructure.translation.nllb_engine import get_nllb_engine
from backend.src.application.translation.heritage_translator import HeritageTranslator

nllb = get_nllb_engine()
ht = HeritageTranslator()

sentences = [
    "Vishnuvardhana's court was filled with talented poets and artists.",
    "The foundation was laid before 1117 without royal opposition.",
    "The war lasted from 1117 to 1120 across southern Karnataka.",
    "Artisans gathered in Belur to work on the stone carvings.",
    "Vishnuvardhana ruled the territory with great distinction.",
    "The sculptors presented their work directly to Vishnuvardhana.",
    "Many temples were commissioned in 1117 across the kingdom.",
    "Queen Shantala praised the architectural beauty of Belur.",
]

os.makedirs("logs", exist_ok=True)
out_path = os.path.join("logs", "heritage_translator_8_sentences.txt")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("HERITAGETRANSLATOR OVERFIT AUDIT & PURE NORMALIZER VERIFICATION\n")
    f.write("===============================================================\n\n")
    for i, s in enumerate(sentences):
        raw_kn = nllb.translate(s, "en", "kn")
        post_kn = ht.post_process_kannada(raw_kn)
        block = (
            f"[{i+1}] EN: {s}\n"
            f"     RAW : {raw_kn}\n"
            f"     POST: {post_kn}\n"
            f"{'-' * 65}\n"
        )
        print(block, end="")
        f.write(block)

print(f"\nArtifact saved to: {out_path}")
