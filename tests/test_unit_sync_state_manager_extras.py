import json
import os
from datetime import date
from pathlib import Path

import pytest


@pytest.mark.unit
def test_clear_stale_entry_removes_and_noop(tmp_path: Path) -> None:
    from src.sync_state_manager import SyncStateManager

    mgr = SyncStateManager(state_file=tmp_path / "sync_state" / "state.json")
    d = date(2024, 1, 1)
    mgr.record_sync(d, 1, 2, "desc")

    assert mgr.has_been_synced(d, 1, 2, "desc") is True

    mgr.clear_stale_entry(d, 1, 2, "desc")
    assert mgr.has_been_synced(d, 1, 2, "desc") is False

    # No error when entry missing
    mgr.clear_stale_entry(d, 1, 2, "desc")


@pytest.mark.unit
def test_save_synced_entries_atomic(tmp_path: Path) -> None:
    from src.sync_state_manager import SyncStateManager

    state_file = tmp_path / "sync_state" / "state.json"
    mgr = SyncStateManager(state_file=state_file)
    d = date(2024, 1, 2)
    mgr.record_sync(d, 9, 8, "x")

    # File should exist and contain json
    assert state_file.exists()
    with open(state_file, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)

    # Atomic assurance: directory should not contain tmp file leftovers
    names = os.listdir(state_file.parent)
    assert all(
        not n.startswith("sync_state_") or not n.endswith(".json") for n in names
    )
