from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).with_name("manifest.json")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_addon_name_and_version() -> tuple[str, str]:
    manifest = load_manifest()
    name = str(manifest.get("name", "AnkiToggl"))
    # Anki manifest lacks an explicit version; derive from meta.json if present, else fallback
    meta_path = Path(__file__).with_name("meta.json")
    version = "0.0.0"
    try:
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            # meta.json may not include version; allow missing
            version = str(meta.get("mod", version))  # use mod timestamp as surrogate
    except Exception:
        pass
    return name, version
