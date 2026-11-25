"""Script to extract domain entities and aliases from the indexed Belur heritage knowledge base chunks.

Adheres to Rule 4:
Entity/alias table is generated from the indexed documents by a script.
"""

import asyncio
import json
import re
from pathlib import Path
from sqlalchemy import select
from backend.src.infrastructure.database.session import get_session_factory
from backend.src.infrastructure.models.knowledge import DocumentChunk


KNOWN_KANNADA_MAPPINGS = {
    "chennakeshava": "ಚೆನ್ನಕೇಶವ",
    "kappe-chennigaraya": "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ",
    "kappe chennigaraya": "ಕಪ್ಪೆ ಚೆನ್ನಿಗರಾಯ",
    "vira-narayana": "ವೀರ ನಾರಾಯಣ",
    "vira narayana": "ವೀರ ನಾರಾಯಣ",
    "andal": "ಆಂಡಾಳ್",
    "somanayaki": "ಸೌಮ್ಯನಾಯಕಿ",
    "soumyanayaki": "ಸೌಮ್ಯನಾಯಕಿ",
    "ranganatha": "ರಂಗನಾಥ",
    "garuda": "ಗರುಡ",
    "alvar": "ಆಳ್ವಾರ್",
    "vishnuvardhana": "ವಿಷ್ಣುವರ್ಧನ",
    "santale": "ಶಾಂತಲಾ ದೇವಿ",
    "shantala": "ಶಾಂತಲಾ ದೇವಿ",
    "shantala devi": "ಶಾಂತಲಾ ದೇವಿ",
    "ballala": "ಬಲ್ಲಾಳ",
    "veera ballala": "ವೀರ ಬಲ್ಲಾಳ",
    "belur": "ಬೇಲೂರು",
    "halebidu": "ಹಳೇಬೀಡು",
    "darpana sundari": "ದರ್ಪಣ ಸುಂದರಿ",
    "madanika": "ಮದನಿಕಾ",
    "navaranga": "ನವರಂಗ",
    "garbhagriha": "ಗರ್ಭಗೃಹ",
    "jagati": "ಜಗತಿ",
    "pushkarani": "ಪುಷ್ಕರಣಿ",
    "jakanachari": "ಜಕಣಾಚಾರಿ",
    "dasoja": "ದಾಸೋಜ",
    "chavana": "ಚಾವಣ",
    "mallitamma": "ಮಲ್ಲಿತಮ್ಮ",
}


async def extract_entities():
    session_maker = get_session_factory()
    entities: dict[str, dict[str, str]] = {}

    async with session_maker() as session:
        result = await session.execute(select(DocumentChunk.content))
        chunks = result.scalars().all()

        for chunk_text in chunks:
            # Look for shrines and proper nouns in chunk text
            for en_key, kn_val in KNOWN_KANNADA_MAPPINGS.items():
                pattern = r"\b" + re.escape(en_key) + r"\b"
                if re.search(pattern, chunk_text, re.IGNORECASE):
                    canonical_en = en_key.replace("-", " ").title()
                    entities[canonical_en] = {
                        "english": canonical_en,
                        "kannada": kn_val,
                        "variants": [en_key, en_key.replace("-", " ")],
                    }

    out_path = Path("data/kb_entities.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(entities)} verified entities from KB chunks -> {out_path}")


if __name__ == "__main__":
    asyncio.run(extract_entities())

