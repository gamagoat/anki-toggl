"""
Simple sync state tracking for the Anki Toggl add-on.

Prevents duplicate Toggl entries by tracking what has been synced.

Sync State File Format:
The sync state is stored in JSON format at `src/sync_state/sync_state.json`:

{
  "entries": {
    "2024-01-15:12345:67890:Anki Review Session": {
      "exists": true,
      "start_time": "2024-01-15T10:30:00+00:00",
      "duration_seconds": 1800,
      "toggl_id": 123456789,
      "action": "create"
    }
  }
}

Key format: "{date}:{workspace_id}:{project_id}:{description}"
Entry data includes all information needed for duplicate detection and updates.
"""

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, Union

from .logger import get_module_logger


class SyncStateManager:
    """Simple sync state tracker to prevent duplicate Toggl entries."""

    def __init__(self, state_file: Optional[Union[str, Path]] = None):
        # Initialize logger first to allow logging during load
        self.logger: Any = get_module_logger("sync_state_manager")

        if state_file is not None:
            self.state_file = Path(state_file)
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            addon_dir = Path(__file__).parent
            default_dir = addon_dir / "sync_state"
            default_dir.mkdir(parents=True, exist_ok=True)
            self.state_file = default_dir / "sync_state.json"
        self._synced_entries: dict[str, Any] = self._load_synced_entries()

    def _load_synced_entries(self):
        try:
            if self.state_file.exists():
                with open(self.state_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.logger.debug(
                            f"Loaded sync state from {self.state_file} with {len(data)} top-level keys"
                        )
                        return data
                    else:
                        return {}
            return {}
        except (
            FileNotFoundError,
            PermissionError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as e:
            self.logger.warning(f"Failed to load sync state: {e}")
            return {}
        except Exception as e:
            self.logger.error(
                f"Unexpected error loading sync state: {e}", exc_info=True
            )
            return {}

    def _save_synced_entries(self) -> None:
        try:
            # Atomic write: write to temp file then replace
            state_dir = self.state_file.parent
            state_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                prefix="sync_state_", suffix=".json", dir=str(state_dir)
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                    json.dump(self._synced_entries, tmp_file, indent=2, default=str)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_path, self.state_file)
            finally:
                # In case of error before replace
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            self.logger.debug(
                f"Saved {len(self._synced_entries)} synced entries atomically"
            )
        except (PermissionError, OSError, TypeError) as e:
            self.logger.error(f"Failed to save sync state: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error saving sync state: {e}", exc_info=True)
            raise

    def _generate_entry_key(
        self, target_date: date, workspace_id: int, project_id: int, description: str
    ) -> str:
        return f"{target_date.isoformat()}:{workspace_id}:{project_id}:{description}"

    def has_been_synced(
        self, target_date: date, workspace_id: int, project_id: int, description: str
    ) -> bool:
        key = self._generate_entry_key(
            target_date, workspace_id, project_id, description
        )
        exists = key in self._synced_entries
        self.logger.debug(
            f"Sync check for {key}: {'EXISTS' if exists else 'NOT FOUND'}"
        )
        return exists

    def get_synced_entry(
        self, target_date: date, workspace_id: int, project_id: int, description: str
    ):
        key = self._generate_entry_key(
            target_date, workspace_id, project_id, description
        )
        return self._synced_entries.get(key, {})

    def record_sync(
        self,
        target_date: date,
        workspace_id: int,
        project_id: int,
        description: str,
        start_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        toggl_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> None:
        key = self._generate_entry_key(
            target_date, workspace_id, project_id, description
        )
        entry_data = {
            "exists": True,
            "target_date": target_date.isoformat(),
            "workspace_id": workspace_id,
            "project_id": project_id,
            "description": description,
            "synced_at": datetime.now().isoformat(),
        }
        if start_time is not None:
            entry_data["start_time"] = start_time.isoformat()
        if duration_seconds is not None:
            entry_data["duration_seconds"] = duration_seconds
        if toggl_id is not None:
            entry_data["toggl_id"] = toggl_id
        if action is not None:
            entry_data["action"] = action
        self._synced_entries[key] = entry_data
        self._save_synced_entries()
        self.logger.info(
            f"Recorded sync for {key} (action: {action}, toggl_id: {toggl_id})"
        )

    def clear_stale_entry(
        self, target_date: date, workspace_id: int, project_id: int, description: str
    ) -> None:
        key = self._generate_entry_key(
            target_date, workspace_id, project_id, description
        )
        if key in self._synced_entries:
            self.logger.info(f"Clearing stale sync state for {key}")
            del self._synced_entries[key]
            self._save_synced_entries()
        else:
            self.logger.debug(f"No sync state found to clear for {key}")
