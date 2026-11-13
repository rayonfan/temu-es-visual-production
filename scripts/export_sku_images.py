#!/usr/bin/env python3
"""Copy ordered final images into a new SKU folder without overwriting history."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def export_images(sku, destination, images, expected_count=7):
    sku = sku.strip()
    if not sku or sku in {".", ".."} or any(
        char in "/\\" or ord(char) < 32 for char in sku
    ):
        raise ValueError("SKU must be a single valid folder name, without path separators.")
    if expected_count < 1 or len(images) != expected_count:
        raise ValueError(f"Expected {expected_count} final images, received {len(images)}.")

    parent = Path(destination).expanduser()
    if not parent.is_absolute():
        raise ValueError("Resolve the selected destination to an absolute path or ~/ path first.")
    parent = parent.resolve()
    if parent.exists() and not parent.is_dir():
        raise ValueError("The selected destination is not a directory.")

    sources = [Path(image).expanduser().resolve(strict=True) for image in images]
    if len(set(sources)) != expected_count:
        raise ValueError("Each final image must have a distinct source file.")
    for source in sources:
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f"Missing or empty image: {source}")
        if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError(f"Unsupported image extension: {source.name}")
    hashes = [digest(source) for source in sources]

    parent.mkdir(parents=True, exist_ok=True)
    suffix = 1
    while True:
        folder = parent / (sku if suffix == 1 else f"{sku}-{suffix}")
        try:
            folder.mkdir()
            break
        except FileExistsError:
            suffix += 1

    outputs = []
    for index, (source, expected_hash) in enumerate(zip(sources, hashes), start=1):
        stem = "01-main" if index == 1 else f"{index:02d}-detail-{index - 1:02d}"
        target = folder / (stem + source.suffix.lower())
        shutil.copy2(source, target)
        if digest(target) != expected_hash:
            raise OSError(f"Copied image checksum mismatch: {target}")
        outputs.append({"file": str(target), "sha256": expected_hash})
    if len(list(folder.iterdir())) != expected_count:
        raise OSError(f"Unexpected contents in the new SKU folder: {folder}")
    return {"sku": sku, "folder": str(folder), "image_count": len(outputs), "files": outputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--destination", required=True, help="Selected parent directory.")
    parser.add_argument("--images", required=True, nargs="+", help="Main image, then details in order.")
    parser.add_argument("--expected-count", type=int, default=7)
    args = parser.parse_args()
    try:
        result = export_images(args.sku, args.destination, args.images, args.expected_count)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Export failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
