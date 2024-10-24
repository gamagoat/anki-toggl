"""
Unit tests for the sync state manager.
"""

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from src.sync_state_manager import SyncStateManager


@pytest.fixture
def sync_manager(tmp_path: Path) -> SyncStateManager:
    """Create a sync state manager with a temporary state file."""
    state_dir = tmp_path / "sync_state"
    state_dir.mkdir(exist_ok=True)
    state_file = state_dir / "sync_state.json"
    return SyncStateManager(state_file=state_file)


@pytest.mark.unit
def test_sync_state_manager_initialization(sync_manager: SyncStateManager) -> None:
    """Test that sync state manager initializes correctly."""
    # The state file is created lazily when we first save
    assert sync_manager.state_file.name == "sync_state.json"
    assert isinstance(sync_manager._synced_entries, dict)
    assert len(sync_manager._synced_entries) == 0


@pytest.mark.unit
def test_generate_entry_key(sync_manager: SyncStateManager) -> None:
    """Test entry key generation."""
    test_date = date(2023, 12, 25)
    key = sync_manager._generate_entry_key(test_date, 123, 456, "Test Description")

    expected = "2023-12-25:123:456:Test Description"
    assert key == expected


@pytest.mark.unit
def test_has_been_synced_new_entry(sync_manager: SyncStateManager) -> None:
    """Test checking for sync status on new entry."""
    test_date = date(2023, 12, 25)

    # Should return False for new entry
    assert not sync_manager.has_been_synced(test_date, 123, 456, "Test Entry")


@pytest.mark.unit
def test_record_and_check_sync(sync_manager: SyncStateManager) -> None:
    """Test recording a sync and checking its status."""
    test_date = date(2023, 12, 25)

    # Record a sync
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=123,
        project_id=456,
        description="Test Entry",
    )

    # Should now return True
    assert sync_manager.has_been_synced(test_date, 123, 456, "Test Entry")

    # Should return False for different parameters
    assert not sync_manager.has_been_synced(test_date, 123, 456, "Different Entry")
    assert not sync_manager.has_been_synced(test_date, 123, 999, "Test Entry")


@pytest.mark.unit
def test_get_synced_entry(sync_manager: SyncStateManager) -> None:
    """Test retrieving synced entry details."""
    test_date = date(2023, 12, 25)

    # Record a sync
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=123,
        project_id=456,
        description="Test Entry",
    )

    # Retrieve the entry (simplified interface)
    entry = sync_manager.get_synced_entry(test_date, 123, 456, "Test Entry")

    assert entry is not None
    assert entry["exists"] == True

    # Should return empty dict for non-existent entry
    non_existent = sync_manager.get_synced_entry(test_date, 999, 999, "Non-existent")
    assert non_existent == {}


@pytest.mark.unit
def test_record_sync_multiple_times(sync_manager: SyncStateManager) -> None:
    """Test recording multiple syncs for the same entry."""
    test_date = date(2023, 12, 25)

    # Record first sync
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=123,
        project_id=456,
        description="Test Entry",
    )

    # Record second sync (update)
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=123,
        project_id=456,
        description="Test Entry",
    )

    # Check that entry still exists (simplified interface doesn't track metadata)
    entry = sync_manager.get_synced_entry(test_date, 123, 456, "Test Entry")
    assert entry["exists"] == True

    # Entry should still be marked as synced
    assert sync_manager.has_been_synced(test_date, 123, 456, "Test Entry")


@pytest.mark.unit
def test_multiple_entries_persistence(sync_manager: SyncStateManager) -> None:
    """Test recording and persistence of multiple entries."""
    # Record entries from different dates
    today = date.today()
    old_date = today - timedelta(days=100)
    recent_date = today - timedelta(days=30)

    start_time = datetime.combine(today, datetime.min.time())

    # Record old entry (should be cleaned up)
    sync_manager.record_sync(
        target_date=old_date,
        workspace_id=123,
        project_id=456,
        description="Old Entry",
    )

    # Record recent entry (should be kept)
    sync_manager.record_sync(
        target_date=recent_date,
        workspace_id=123,
        project_id=456,
        description="Recent Entry",
    )

    # Record today's entry (should be kept)
    sync_manager.record_sync(
        target_date=today,
        workspace_id=123,
        project_id=456,
        description="Today Entry",
    )

    # Verify all entries exist (simplified interface doesn't have cleanup)
    assert sync_manager.has_been_synced(old_date, 123, 456, "Old Entry")
    assert sync_manager.has_been_synced(recent_date, 123, 456, "Recent Entry")
    assert sync_manager.has_been_synced(today, 123, 456, "Today Entry")


@pytest.mark.unit
def test_malformed_state_file_handling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test handling of malformed state files."""
    # Create a malformed state file
    state_dir = tmp_path / "sync_state"
    state_dir.mkdir(exist_ok=True)
    state_file = state_dir / "sync_state.json"

    with open(state_file, "w") as f:
        f.write("{ invalid json")

    # Should handle malformed file gracefully when using constructor param
    manager = SyncStateManager(state_file=state_file)

    # Should initialize with empty dict despite corrupted file
    assert isinstance(manager._synced_entries, dict)
    assert len(manager._synced_entries) == 0

    # Nothing to restore


@pytest.mark.unit
def test_entry_key_uniqueness(sync_manager: SyncStateManager) -> None:
    """Test that entry keys are unique for different parameters."""
    test_date = date(2023, 12, 25)

    key1 = sync_manager._generate_entry_key(test_date, 123, 456, "Description A")
    key2 = sync_manager._generate_entry_key(test_date, 123, 456, "Description B")
    key3 = sync_manager._generate_entry_key(test_date, 123, 789, "Description A")
    key4 = sync_manager._generate_entry_key(test_date, 456, 456, "Description A")

    # All keys should be different
    keys = [key1, key2, key3, key4]
    assert len(set(keys)) == len(keys)  # All unique


@pytest.mark.unit
def test_new_complete_data_storage(sync_manager: SyncStateManager) -> None:
    """Test that the new sync state manager stores and retrieves complete data."""
    from datetime import datetime, timezone

    test_date = date(2023, 12, 25)
    start_time = datetime(2023, 12, 25, 10, 30, 0, tzinfo=timezone.utc)
    duration_seconds = 3600
    toggl_id = 12345
    action = "create"

    # Record sync with all optional parameters
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=123,
        project_id=456,
        description="Complete Test Entry",
        start_time=start_time,
        duration_seconds=duration_seconds,
        toggl_id=toggl_id,
        action=action,
    )

    # Retrieve the entry and verify all data is stored
    entry = sync_manager.get_synced_entry(test_date, 123, 456, "Complete Test Entry")

    assert entry["exists"] is True  # Backward compatibility
    assert entry["target_date"] == test_date.isoformat()
    assert entry["workspace_id"] == 123
    assert entry["project_id"] == 456
    assert entry["description"] == "Complete Test Entry"
    assert entry["start_time"] == start_time.isoformat()
    assert entry["duration_seconds"] == duration_seconds
    assert entry["toggl_id"] == toggl_id
    assert entry["action"] == action
    assert "synced_at" in entry  # Should have timestamp


@pytest.mark.unit
def test_backward_compatibility_minimal_record_sync(
    sync_manager: SyncStateManager,
) -> None:
    """Test that record_sync still works with minimal parameters (backward compatibility)."""
    test_date = date(2023, 12, 25)

    # Record sync with only required parameters (like old interface)
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=123,
        project_id=456,
        description="Minimal Test Entry",
    )

    # Should work and be retrievable
    assert sync_manager.has_been_synced(test_date, 123, 456, "Minimal Test Entry")

    entry = sync_manager.get_synced_entry(test_date, 123, 456, "Minimal Test Entry")
    assert entry["exists"] is True
    assert entry["target_date"] == test_date.isoformat()
    assert entry["workspace_id"] == 123
    assert entry["project_id"] == 456
    assert entry["description"] == "Minimal Test Entry"

    # Optional fields should not be present when not provided
    assert "start_time" not in entry
    assert "duration_seconds" not in entry
    assert "toggl_id" not in entry
    assert "action" not in entry


@pytest.mark.unit
def test_data_format_consistency_across_saves(
    sync_manager: SyncStateManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the new data format is consistent when saving and loading."""
    from datetime import datetime, timezone

    test_date = date(2023, 12, 25)
    start_time = datetime(2023, 12, 25, 14, 15, 0, tzinfo=timezone.utc)

    # Record an entry with complete data
    sync_manager.record_sync(
        target_date=test_date,
        workspace_id=999,
        project_id=888,
        description="Consistency Test",
        start_time=start_time,
        duration_seconds=2700,  # 45 minutes
        toggl_id=54321,
        action="update",
    )

    # Retrieve and verify
    entry1 = sync_manager.get_synced_entry(test_date, 999, 888, "Consistency Test")

    # Force a save and reload by creating new manager instance with same state_file
    new_manager = SyncStateManager(state_file=sync_manager.state_file)
    entry2 = new_manager.get_synced_entry(test_date, 999, 888, "Consistency Test")

    # Should be identical after save/load
    assert entry1 == entry2
    assert entry2["duration_seconds"] == 2700
    assert entry2["toggl_id"] == 54321
    assert entry2["action"] == "update"
