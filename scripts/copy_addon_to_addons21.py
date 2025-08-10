#!/usr/bin/env python3
import json
import os
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path

DEFAULT_DEST = Path.home() / "Library/Application Support/Anki2/addons21/anki_toggl_dev"
SRC_DIR = Path(__file__).parent.parent / "src"
EXTRA_FILES: tuple[str, ...] = ("manifest.json", "meta.json")


def _iter_src_files() -> Iterable[Path]:
    for child in SRC_DIR.iterdir():
        if child.is_file() and (child.suffix == ".py" or child.name in EXTRA_FILES):
            yield child


def _load_env() -> dict[str, str]:
    env_path = Path(__file__).parent.parent / ".env"
    values: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip('"').strip("'")
    values.update(os.environ)
    return values


def _write_config_from_env(dest_dir: Path, env: dict[str, str]) -> None:
    mapping = {
        "TOGGL_API_TOKEN": "api_token",
        "TOGGL_WORKSPACE_ID": "workspace_id",
        "TOGGL_PROJECT_ID": "project_id",
        "TOGGL_DESCRIPTION": "description",
        "ANKI_TOGGL_AUTO_SYNC": "auto_sync",
        "ANKI_TOGGL_TIMEZONE": "timezone",
    }

    cfg_path = dest_dir / "config.json"
    current: dict[str, object] = {}
    if cfg_path.exists():
        try:
            current = json.loads(cfg_path.read_text())
        except Exception:
            current = {}

    updated = False
    for env_key, cfg_key in mapping.items():
        raw = env.get(env_key)
        if not raw:
            continue
        val: object = raw
        if cfg_key in {"workspace_id", "project_id"}:
            try:
                val = int(raw)
            except Exception:
                continue
        elif cfg_key == "auto_sync":
            val = str(raw).lower() in {"true", "1", "yes", "on"}
        if current.get(cfg_key) != val:
            current[cfg_key] = val
            updated = True

    if updated or not cfg_path.exists():
        cfg_path.write_text(json.dumps(current, indent=2))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"--help", "-h"}:
        print("Usage: python scripts/copy_addon_to_addons21.py [destination_path]")
        print(f"Default: {DEFAULT_DEST}")
        return

    dest_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST

    if dest_path.exists():
        shutil.rmtree(dest_path)
    dest_path.mkdir(parents=True, exist_ok=True)

    for src_file in _iter_src_files():
        shutil.copy2(src_file, dest_path / src_file.name)

    env = _load_env()
    _write_config_from_env(dest_path, env)
    print(f"Copied add-on to {dest_path}")


if __name__ == "__main__":
    main()
