"""Offline NLLB-200 model setup and conversion utility.

Verifies local CTranslate2 INT8 model files, downloads from HuggingFace if missing,
and converts to INT8 format for offline high-performance inference.
"""

import os
import sys
import subprocess

MODEL_DIR = os.path.join("data", "models", "nllb-200-600M-ct2-int8")
REQUIRED_FILES = ["model.bin", "config.json", "shared_vocabulary.json"]
HF_MODEL_ID = "facebook/nllb-200-distilled-600M"


def verify_local_model() -> bool:
    """Check if all required CTranslate2 model files exist and have non-zero size."""
    if not os.path.isdir(MODEL_DIR):
        return False
    for fname in REQUIRED_FILES:
        fpath = os.path.join(MODEL_DIR, fname)
        if not os.path.isfile(fpath) or os.path.getsize(fpath) == 0:
            return False
    return True


def setup_model() -> None:
    """Ensure NLLB-200 CTranslate2 INT8 model is available locally."""
    print("=" * 65)
    print("NLLB-200 Offline Translation Engine Setup")
    print("=" * 65)
    print(f"Target Directory: {os.path.abspath(MODEL_DIR)}")

    if verify_local_model():
        model_bin = os.path.join(MODEL_DIR, "model.bin")
        size_mb = os.path.getsize(model_bin) / (1024 * 1024)
        print(f"[OK] CTranslate2 INT8 model already present and verified ({size_mb:.2f} MB).")
        print("[OK] All required files exist:", REQUIRED_FILES)
        return

    print(f"[INFO] Model files missing. Preparing conversion from {HF_MODEL_ID}...")
    os.makedirs(MODEL_DIR, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "ctranslate2.converters.transformers",
        "--model",
        HF_MODEL_ID,
        "--output_dir",
        MODEL_DIR,
        "--quantization",
        "int8",
        "--force",
    ]
    print(f"[EXEC] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    if verify_local_model():
        print("[SUCCESS] NLLB-200 INT8 model converted and verified.")
    else:
        print("[ERROR] Conversion finished but verification failed.")
        sys.exit(1)


if __name__ == "__main__":
    setup_model()

