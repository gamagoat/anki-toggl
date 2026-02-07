#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
DEFAULT_DIST_DIR = REPO_ROOT / "dist"


def _load_manifest() -> dict:
    manifest_path = SRC_DIR / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _iter_files_to_package() -> list[Path]:
    files: list[Path] = []

    for child in SRC_DIR.iterdir():
        if child.name == "manifest.json":
            continue

        if child.is_dir():
            # Package vendored dependencies (e.g. vendor/tzdata)
            if child.name == "vendor":
                for p in child.rglob("*"):
                    if p.is_file():
                        files.append(p)
            continue

        if child.suffix in (".py", ".json", ".md"):
            files.append(child)

    return files


def _write_manifest_into_zip(zf: ZipFile, base_manifest: dict) -> None:
    manifest = dict(base_manifest) if base_manifest else {}
    manifest.setdefault("name", "Anki Toggl")
    manifest.setdefault("package", "anki_toggl")
    # Update mod to current epoch seconds for outside-AnkiWeb installs; harmless on AnkiWeb
    manifest["mod"] = int(time.time())
    data = json.dumps(manifest, separators=(",", ":"))
    zf.writestr("manifest.json", data.encode("utf-8"), compress_type=ZIP_DEFLATED)


def build(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest()
    files = _iter_files_to_package()

    with ZipFile(output_path, mode="w", compression=ZIP_DEFLATED) as zf:
        # Ensure no top-level folder in archive (per AnkiWeb docs)
        _write_manifest_into_zip(zf, manifest)
        for file_path in files:
            # arcname relative to src/ so there's no top-level directory
           zf.write(file_path, arcname=str(file_path.relative_to(SRC_DIR)))



def main() -> None:
    parser = argparse.ArgumentParser(description="Build .ankiaddon package from src/")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output .ankiaddon path (default: dist/<package>.ankiaddon)",
    )
    args = parser.parse_args()

    manifest = _load_manifest()
    package_name = manifest.get("package") or "anki_toggl"
    default_output = DEFAULT_DIST_DIR / f"{package_name}.ankiaddon"

    output_path = Path(args.output) if args.output else default_output
    build(output_path)
    print(f"Built {output_path}")


if __name__ == "__main__":
    main()
