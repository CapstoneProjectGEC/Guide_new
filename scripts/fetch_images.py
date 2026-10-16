"""Download catalogued temple images with polite retry and metadata indexing.

Usage:
    python scripts/fetch_images.py
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import time
from urllib.parse import urlparse
import httpx


def parse_image_dimensions(data: bytes) -> tuple[int | None, int | None, str | None]:
    """Parse image dimensions and format from binary payload without external dependencies."""
    if not data or len(data) < 24:
        return None, None, None

    # PNG format
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w, h = struct.unpack(">LL", data[16:24])
        return int(w), int(h), "png"

    # JPEG format
    if data.startswith(b"\xff\xd8"):
        idx = 2
        while idx < len(data) - 4:
            marker, length = struct.unpack(">2sH", data[idx:idx + 4])
            if marker in (b"\xff\xc0", b"\xff\xc1", b"\xff\xc2"):
                if idx + 9 <= len(data):
                    h, w = struct.unpack(">HH", data[idx + 5:idx + 9])
                    return int(w), int(h), "jpeg"
            idx += 2 + length
        return None, None, "jpeg"

    # WebP format
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8 ":
            if len(data) >= 30:
                w, h = struct.unpack("<HH", data[26:30])
                return int(w & 0x3FFF), int(h & 0x3FFF), "webp"
        elif data[12:16] == b"VP8L":
            if len(data) >= 25:
                b0, b1, b2, b3 = data[21:25]
                w = 1 + (((b1 & 0x3F) << 8) | b0)
                h = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
                return int(w), int(h), "webp"
        elif data[12:16] == b"VP8X":
            if len(data) >= 30:
                w = 1 + struct.unpack("<I", data[24:27] + b"\x00")[0]
                h = 1 + struct.unpack("<I", data[27:30] + b"\x00")[0]
                return int(w), int(h), "webp"
        return None, None, "webp"

    # GIF format
    if data.startswith((b"GIF87a", b"GIF89a")):
        w, h = struct.unpack("<HH", data[6:10])
        return int(w), int(h), "gif"

    return None, None, None


def determine_file_extension(url: str, detected_format: str | None) -> str:
    """Determine file extension from URL or binary format."""
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        return ext
    if detected_format:
        if detected_format == "jpeg":
            return ".jpg"
        return f".{detected_format}"
    return ".jpg"


def fetch_all_images(
    catalogue_path: str = "data/kb/belur/image_catalogue.json",
    output_dir: str = "assets/belur/images",
    index_path: str = "assets/belur/image_index.json",
    delay_seconds: float = 0.5,
    force_download: bool = False,
) -> dict:
    """Download images in catalogue, record metadata, handle failures gracefully."""
    cat_file = Path(catalogue_path)
    if not cat_file.exists():
        raise FileNotFoundError(f"Catalogue file not found at: {catalogue_path}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with open(cat_file, "r", encoding="utf-8") as f:
        catalogue = json.load(f)

    print(f"Loaded {len(catalogue)} image records from {catalogue_path}")

    image_index = {}
    idx_file = Path(index_path)
    idx_file.parent.mkdir(parents=True, exist_ok=True)
    if idx_file.exists() and not force_download:
        try:
            with open(idx_file, "r", encoding="utf-8") as f:
                image_index = json.load(f)
        except Exception:
            image_index = {}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "BelurSmartGuide/1.0"
        ),
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }

    client = httpx.Client(headers=headers, timeout=15.0, follow_redirects=True)

    success_count = 0
    failure_count = 0
    skipped_count = 0

    try:
        for idx, item in enumerate(catalogue, start=1):
            image_id = item["image_id"]
            image_url = item["image_url"]

            print(f"[{idx}/{len(catalogue)}] Processing {image_id}: {image_url}")

            # Check if already downloaded
            existing_entry = image_index.get(image_id)
            if existing_entry and existing_entry.get("status") == "downloaded" and not force_download:
                existing_file = Path(existing_entry.get("local_file_path", ""))
                if existing_file.exists() and existing_file.stat().st_size > 0:
                    print(f"  -> Already exists locally: {existing_file}")
                    skipped_count += 1
                    continue

            # Polite delay
            if idx > 1 and delay_seconds > 0:
                time.sleep(delay_seconds)

            # Download with up to 3 polite retries
            download_success = False
            error_msg = None
            response_content = None

            for attempt in range(1, 4):
                try:
                    resp = client.get(image_url)
                    if resp.status_code == 200:
                        response_content = resp.content
                        download_success = True
                        break
                    elif resp.status_code == 404:
                        error_msg = f"HTTP 404 Not Found"
                        break  # No need to retry 404
                    else:
                        error_msg = f"HTTP {resp.status_code}"
                        time.sleep(1.0 * attempt)
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {str(exc)}"
                    time.sleep(1.0 * attempt)

            if download_success and response_content:
                width, height, fmt = parse_image_dimensions(response_content)
                ext = determine_file_extension(image_url, fmt)
                local_filename = f"{image_id}{ext}"
                local_filepath = out_path / local_filename

                with open(local_filepath, "wb") as img_f:
                    img_f.write(response_content)

                sha256_hash = hashlib.sha256(response_content).hexdigest()

                image_index[image_id] = {
                    "image_id": image_id,
                    "image_url": image_url,
                    "source_page_url": item.get("source_page_url", ""),
                    "section_id": item.get("section_id", ""),
                    "source_caption": item.get("source_caption", ""),
                    "source_alt_text": item.get("source_alt_text", ""),
                    "caption_derived_description": item.get("caption_derived_description", ""),
                    "status": "downloaded",
                    "local_file_path": str(local_filepath).replace("\\", "/"),
                    "local_filename": local_filename,
                    "width": width,
                    "height": height,
                    "format": fmt,
                    "file_size_bytes": len(response_content),
                    "sha256": sha256_hash,
                    "notes": item.get("notes", ""),
                    "is_metadata_only": (image_id == "IMG-0021"),
                }
                success_count += 1
                print(f"  -> Successfully saved: {local_filename} ({width}x{height}, {len(response_content)} bytes)")
            else:
                image_index[image_id] = {
                    "image_id": image_id,
                    "image_url": image_url,
                    "source_page_url": item.get("source_page_url", ""),
                    "section_id": item.get("section_id", ""),
                    "source_caption": item.get("source_caption", ""),
                    "status": f"failed_{error_msg}",
                    "error": error_msg,
                    "notes": item.get("notes", ""),
                    "is_metadata_only": (image_id == "IMG-0021"),
                }
                failure_count += 1
                print(f"  -> Failed to download: {error_msg}")

    finally:
        client.close()

    # Save index
    with open(idx_file, "w", encoding="utf-8") as f:
        json.dump(image_index, f, indent=2, ensure_ascii=False)

    print(
        f"\nDownload summary: {success_count} downloaded, {skipped_count} skipped, "
        f"{failure_count} failed. Index saved to {index_path}"
    )
    return image_index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch temple images and build index")
    parser.add_argument("--catalogue-path", default="data/kb/belur/image_catalogue.json")
    parser.add_argument("--output-dir", default="assets/belur/images")
    parser.add_argument("--index-path", default="assets/belur/image_index.json")
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    fetch_all_images(
        catalogue_path=args.catalogue_path,
        output_dir=args.output_dir,
        index_path=args.index_path,
        delay_seconds=args.delay,
        force_download=args.force,
    )
