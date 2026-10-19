#!/usr/bin/env python3
"""Build script to package JellyEmu custom component into jellyemu.zip."""
import json
from pathlib import Path
import sys
import zipfile

IGNORED_NAMES = {"__pycache__", ".DS_Store", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def build_zip() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "custom_components" / "jellyemu"
    output_zip = repo_root / "jellyemu.zip"

    if not src_dir.is_dir():
        print(f"Error: Source directory not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    manifest_file = src_dir / "manifest.json"
    version = "unknown"
    if manifest_file.is_file():
        try:
            with open(manifest_file, encoding="utf-8") as f:
                version = json.load(f).get("version", "unknown")
        except Exception:
            pass

    print(f"Building JellyEmu v{version} distribution archive...")

    if output_zip.exists():
        output_zip.unlink()

    file_count = 0
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(part in IGNORED_NAMES for part in path.parts):
                continue
            if path.suffix.lower() in IGNORED_SUFFIXES:
                continue

            rel_path = path.relative_to(src_dir)
            arcname = f"jellyemu/{rel_path.as_posix()}"
            zf.write(path, arcname)
            file_count += 1
            print(f"  + {arcname}")

    size_kb = output_zip.stat().st_size / 1024
    print(f"\nSuccessfully created {output_zip.name} ({size_kb:.1f} KB, {file_count} files)")


if __name__ == "__main__":
    build_zip()
