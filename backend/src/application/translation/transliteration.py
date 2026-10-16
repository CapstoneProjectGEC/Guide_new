"""Deterministic phonetic Kannada-to-Latin transliteration utility.

Distinguishes phonetic script mapping (transliteration) from semantic translation.
Transliteration converts Kannada Unicode characters into Latin phonetics (e.g. 'ದೇವಾಲಯ' -> 'devalaya'),
whereas translation converts semantic meaning (e.g. 'ದೇವಾಲಯ' -> 'temple').
"""

VOWELS = {
    "\u0c85": "a",
    "\u0c86": "aa",
    "\u0c87": "i",
    "\u0c88": "ee",
    "\u0c89": "u",
    "\u0c8a": "oo",
    "\u0c8b": "ru",
    "\u0c8e": "e",
    "\u0c8f": "ee",
    "\u0c90": "ai",
    "\u0c92": "o",
    "\u0c93": "oo",
    "\u0c94": "au",
}

VOWEL_SIGNS = {
    "\u0cbe": "aa",
    "\u0cbf": "i",
    "\u0cc0": "ee",
    "\u0cc1": "u",
    "\u0cc2": "oo",
    "\u0cc3": "ru",
    "\u0cc4": "roo",
    "\u0cc6": "e",
    "\u0cc7": "ee",
    "\u0cc8": "ai",
    "\u0cca": "o",
    "\u0ccb": "oo",
    "\u0ccc": "au",
}

CONSONANTS = {
    "\u0c95": "k",
    "\u0c96": "kh",
    "\u0c97": "g",
    "\u0c98": "gh",
    "\u0c99": "ng",
    "\u0c9a": "ch",
    "\u0c9b": "chh",
    "\u0c9c": "j",
    "\u0c9d": "jh",
    "\u0c9e": "ny",
    "\u0c9f": "t",
    "\u0ca0": "th",
    "\u0ca1": "d",
    "\u0ca2": "dh",
    "\u0ca3": "n",
    "\u0ca4": "t",
    "\u0ca5": "th",
    "\u0ca6": "d",
    "\u0ca7": "dh",
    "\u0ca8": "n",
    "\u0caa": "p",
    "\u0cab": "ph",
    "\u0cac": "b",
    "\u0cad": "bh",
    "\u0cae": "m",
    "\u0caf": "y",
    "\u0cb0": "r",
    "\u0cb1": "r",
    "\u0cb2": "l",
    "\u0cb3": "l",
    "\u0cb5": "v",
    "\u0cb6": "sh",
    "\u0cb7": "sh",
    "\u0cb8": "s",
    "\u0cb9": "h",
}

VIRAMA = "\u0ccd"
ANUSVARA = "\u0c82"
VISARGA = "\u0c83"


def transliterate_kannada_to_latin(text: str) -> str:
    """Phonetically transliterate Kannada Unicode text into Latin characters."""
    if not text:
        return ""

    out: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        char = text[i]

        if char in VOWELS:
            out.append(VOWELS[char])
            i += 1
        elif char in CONSONANTS:
            base = CONSONANTS[char]
            # Check following character
            if i + 1 < n:
                nxt = text[i + 1]
                if nxt == VIRAMA:
                    out.append(base)
                    i += 2
                    continue
                elif nxt in VOWEL_SIGNS:
                    out.append(base + VOWEL_SIGNS[nxt])
                    i += 2
                    continue
            # Default inherent vowel 'a'
            out.append(base + "a")
            i += 1
        elif char == ANUSVARA:
            out.append("m")
            i += 1
        elif char == VISARGA:
            out.append("h")
            i += 1
        else:
            out.append(char)
            i += 1

    return "".join(out)
