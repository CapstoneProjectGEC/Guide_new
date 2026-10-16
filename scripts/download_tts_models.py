"""Provisioning script to download and verify offline Piper TTS models for English and Kannada.

Usage:
    python scripts/download_tts_models.py [--force]

Models:
    1. English (en_US):
       Model: en_US-lessac-medium.onnx (~63.2 MB) + en_US-lessac-medium.onnx.json (4.8 KB)
       Source: Rhasspy / piper-voices (Hugging Face)
       License: Public Domain / Open MIT
       Sample Rate: 22,050 Hz

    2. Kannada (kn_IN):
       Model: kn_IN-syspin_male-medium.onnx (~63.5 MB) + kn_IN-syspin_male-medium.onnx.json (5.2 KB)
       Source: micahchoo/piper-kn (Hugging Face)
       Dataset: IISc Bangalore SYSPIN (System for Speech in Indic languages)
       License: Apache 2.0 / Open Research
       Sample Rate: 22,050 Hz

Note:
    Run this script ONCE during environment setup with internet access.
    At runtime, the application operates 100% offline using locally cached model files.
    The application NEVER downloads models automatically during startup.
"""

import argparse
import hashlib
import io
from pathlib import Path
import sys
import time
import urllib.request
import wave

MODELS = [
    {
        "name": "English (en_US-lessac-medium)",
        "files": [
            (
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
                "en_US-lessac-medium.onnx",
                63201294,
            ),
            (
                "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
                "en_US-lessac-medium.onnx.json",
                4885,
            ),
        ],
    },
    {
        "name": "Kannada (kn_IN-syspin_male-medium)",
        "files": [
            (
                "https://huggingface.co/micahchoo/piper-kn/resolve/main/kn_IN-syspin_male-medium.onnx",
                "kn_IN-syspin_male-medium.onnx",
                63516051,
            ),
            (
                "https://huggingface.co/micahchoo/piper-kn/resolve/main/kn_IN-syspin_male-medium.onnx.json",
                "kn_IN-syspin_male-medium.onnx.json",
                5268,
            ),
        ],
    },
]


def download_file(url: str, dest_path: Path, force: bool = False) -> None:
    """Download a file with streaming chunks and display progress."""
    if dest_path.exists() and not force:
        size = dest_path.stat().st_size
        if size > 1000:
            print(f"  [EXISTS] {dest_path.name} ({size:,} bytes)")
            return

    print(f"  [DOWNLOADING] {url} -> {dest_path}...")
    headers = {"User-Agent": "SmartTouristGuide-Setup/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest_path, "wb") as out_f:
        downloaded = 0
        while chunk := resp.read(1024 * 1024):
            out_f.write(chunk)
            downloaded += len(chunk)
            sys.stdout.write(f"\r    Progress: {downloaded / (1024 * 1024):.1f} MB")
            sys.stdout.flush()
    print(f"\n  [COMPLETED] {dest_path.name} ({dest_path.stat().st_size:,} bytes)")


def verify_models(models_dir: Path) -> bool:
    """Verify downloaded models by running a test synthesis on CPU."""
    try:
        from piper import PiperVoice
    except ImportError:
        print("[WARNING] piper-tts is not installed. Install via: pip install piper-tts")
        return False

    print("\n--- Verifying Offline Inference on CPU ---")
    all_ok = True

    # Test English
    en_path = models_dir / "en_US-lessac-medium.onnx"
    if en_path.exists():
        try:
            t0 = time.perf_counter()
            voice_en = PiperVoice.load(str(en_path), use_cuda=False)
            load_ms = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_f:
                voice_en.synthesize_wav("Welcome to Belur.", wav_f)
            syn_ms = (time.perf_counter() - t0) * 1000
            print(f"  [OK] English voice loaded in {load_ms:.1f}ms, synthesized in {syn_ms:.1f}ms ({len(buf.getvalue()):,} bytes WAV)")
        except Exception as e:
            print(f"  [FAILED] English synthesis error: {e}")
            all_ok = False
    else:
        print(f"  [MISSING] English model not found at {en_path}")
        all_ok = False

    # Test Kannada
    kn_path = models_dir / "kn_IN-syspin_male-medium.onnx"
    if kn_path.exists():
        try:
            t0 = time.perf_counter()
            voice_kn = PiperVoice.load(str(kn_path), use_cuda=False)
            load_ms = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_f:
                voice_kn.synthesize_wav("ಬೇಲೂರು ಚನ್ನಕೇಶವ ದೇವಾಲಯ.", wav_f)
            syn_ms = (time.perf_counter() - t0) * 1000
            print(f"  [OK] Kannada voice loaded in {load_ms:.1f}ms, synthesized in {syn_ms:.1f}ms ({len(buf.getvalue()):,} bytes WAV)")
        except Exception as e:
            print(f"  [FAILED] Kannada synthesis error: {e}")
            all_ok = False
    else:
        print(f"  [MISSING] Kannada model not found at {kn_path}")
        all_ok = False

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and verify offline Piper TTS models.")
    parser.add_argument("--dest", default="data/models/piper", help="Target destination directory")
    parser.add_argument("--force", action="store_true", help="Force redownload of existing files")
    args = parser.parse_args()

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Destination directory: {dest_dir.resolve()}")

    for item in MODELS:
        print(f"\nProcessing {item['name']}...")
        for url, filename, _ in item["files"]:
            dest_file = dest_dir / filename
            download_file(url, dest_file, force=args.force)

    verify_ok = verify_models(dest_dir)
    if verify_ok:
        print("\nAll TTS models provisioned and verified successfully! Platform is ready for offline TTS.")
    else:
        print("\nModel verification had warnings or failures. Check logs above.")


if __name__ == "__main__":
    main()
