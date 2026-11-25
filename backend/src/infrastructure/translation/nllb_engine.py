"""Offline Neural Machine Translation Engine using Meta NLLB-200 distilled 600M via CTranslate2 INT8."""

import os
import threading
import time
from functools import lru_cache
from typing import Any
import ctranslate2
from transformers import AutoTokenizer
from backend.src.core.logging import get_logger

logger = get_logger("infrastructure.translation.nllb_engine")

NLLB_MODEL_DIR = "data/models/nllb-200-600M-ct2-int8"
NLLB_TOKENIZER_DIR = r"C:\Users\user\.cache\huggingface\hub\models--facebook--nllb-200-distilled-600M\snapshots\f8d333a098d19b4fd9a8b18f94170487ad3f821d"

# NLLB Language code mapping
NLLB_LANG_CODES = {
    "en": "eng_Latn",
    "kn": "kan_Knda",
    "eng_Latn": "eng_Latn",
    "kan_Knda": "kan_Knda",
}


class NllbTranslationEngine:
    """Production-grade offline translation engine backed by CTranslate2 int8 quantized NLLB-200."""

    def __init__(
        self,
        model_dir: str = NLLB_MODEL_DIR,
        tokenizer_dir: str = NLLB_TOKENIZER_DIR,
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_dir = model_dir
        self.tokenizer_dir = tokenizer_dir
        self.device = device
        self.compute_type = compute_type
        self._lock = threading.Lock()
        self._translator: ctranslate2.Translator | None = None
        self._tokenizer: Any = None
        self._is_initialized = False

        self._initialize_runtime()

    def _initialize_runtime(self) -> None:
        """Load tokenizer and quantized model weights once into resident memory."""
        with self._lock:
            if self._is_initialized:
                return

            try:
                t0 = time.perf_counter()
                logger.info("loading_nllb_engine", model_dir=self.model_dir, device=self.device)

                self._tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_dir)
                self._translator = ctranslate2.Translator(
                    self.model_dir,
                    device=self.device,
                    compute_type=self.compute_type,
                    intra_threads=4,
                )

                # Warmup execution to eliminate first-request cold start overhead
                self.warmup()

                load_ms = (time.perf_counter() - t0) * 1000
                self._is_initialized = True
                logger.info("nllb_engine_initialized", load_time_ms=f"{load_ms:.2f}")

            except Exception as exc:
                logger.error("nllb_engine_init_failed", error=str(exc))
                self._is_initialized = False

    def is_available(self) -> bool:
        """Check if engine runtime is active and operational."""
        return self._is_initialized and self._translator is not None

    def warmup(self) -> None:
        """Run a single micro-translation to warm up CTranslate2 execution kernels."""
        if self._translator and self._tokenizer:
            try:
                self._tokenizer.src_lang = "eng_Latn"
                tokens = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode("Belur temple warmup"))
                self._translator.translate_batch([tokens], target_prefix=[["kan_Knda"]])
            except Exception as exc:
                logger.warning("nllb_warmup_warning", error=str(exc))

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate text between English and Kannada using true neural translation."""
        cleaned = text.strip()
        if not cleaned:
            return ""

        src_code = NLLB_LANG_CODES.get(source_lang, source_lang)
        tgt_code = NLLB_LANG_CODES.get(target_lang, target_lang)

        if src_code == tgt_code or not self.is_available():
            return cleaned

        # Normalize unicode punctuation that triggers <unk> tokens in NLLB
        cleaned = (
            cleaned.replace("–", "-")
            .replace("—", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )

        with self._lock:
            try:
                self._tokenizer.src_lang = src_code
                input_tokens = self._tokenizer.convert_ids_to_tokens(self._tokenizer.encode(cleaned))

                results = self._translator.translate_batch(
                    [input_tokens],
                    target_prefix=[[tgt_code]],
                    max_decoding_length=256,
                    beam_size=2,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                    replace_unknowns=True,
                )

                hyp_tokens = results[0].hypotheses[0]
                # Strip the forced target language prefix token if present
                if hyp_tokens and hyp_tokens[0] == tgt_code:
                    hyp_tokens = hyp_tokens[1:]

                decoded = self._tokenizer.decode(
                    self._tokenizer.convert_tokens_to_ids(hyp_tokens),
                    skip_special_tokens=True,
                )
                import re
                decoded = re.sub(r"<(?:unk|s|/s|pad)>", "", decoded)
                decoded = re.sub(r"\s+", " ", decoded).strip()
                return decoded

            except Exception as exc:
                logger.warning("nllb_translation_exception", error=str(exc), text=cleaned[:50])
                return cleaned


@lru_cache(maxsize=1)
def get_nllb_engine() -> NllbTranslationEngine:
    """Return cached singleton instance of NllbTranslationEngine."""
    return NllbTranslationEngine()

