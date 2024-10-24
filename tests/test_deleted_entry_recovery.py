"""
Test for handling deleted Toggl entries gracefully.

When a user deletes an entry in Toggl UI but sync state still has the toggl_id,
the system should handle the 404 error and either find another entry or create a new one.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import Mock

import pytest
import requests

from src.core import SyncSession, sync_to_toggl
from tests.test_constants import (
    TEST_DELETED_ENTRY_ID,
    TEST_REAL_PROJECT_ID,
    TEST_REAL_WORKSPACE_ID,
    TEST_REVIEW_COUNT,
)


@pytest.mark.unit
def test_handles_deleted_toggl_entry_gracefully(
    monkeypatch: pytest.MonkeyPatch,
    mock_api_call_tracker: Any,
    mock_toggl_creator_with_custom_behavior: Any,
) -> None:
    """
    Test that the system handles a 404 error when trying to update a deleted entry.

    Scenario:
    1. Sync state has a toggl_id for an entry
    2. User deletes that entry in Toggl UI
    3. System tries to update the deleted entry -> 404 error
    4. System should handle this gracefully by creating a new entry
    """

    # Track API calls using shared fixture
    api_calls = mock_api_call_tracker()

    # Create mock with custom behavior for deleted entry
    MockTogglCreator = mock_toggl_creator_with_custom_behavior(api_calls)

    # Override update_entry to simulate 404 for deleted entry
    original_update_entry = MockTogglCreator.update_entry

    def update_entry_with_404(
        self: Any,
        entry_id: int,
        duration: int,
        start_time: datetime,
        timezone_str: Optional[str] = None,
    ) -> Any:
        api_calls.append(("update", entry_id, duration))
        # Simulate 404 error for deleted entry
        if entry_id == TEST_DELETED_ENTRY_ID:
            raise requests.exceptions.HTTPError(
                f"404 Client Error: Not Found for url: https://api.track.toggl.com/api/v9/workspaces/{TEST_REAL_WORKSPACE_ID}/time_entries/{TEST_DELETED_ENTRY_ID}"
            )
        return original_update_entry(self, entry_id, duration, start_time, timezone_str)

    MockTogglCreator.update_entry = update_entry_with_404

    # Create sync state that has a stale toggl_id (entry was deleted in Toggl UI)
    mock_sync_manager = Mock()
    mock_sync_manager.has_been_synced.return_value = True
    mock_sync_manager.get_synced_entry.return_value = {
        "duration_seconds": 60,  # Previous sync
        "toggl_id": TEST_DELETED_ENTRY_ID,  # This entry was deleted in Toggl UI!
        "start_time": "2023-01-18T09:00:00+00:00",
    }
    mock_sync_manager.record_sync.return_value = None

    # Mock the dependencies
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", MockTogglCreator)
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_manager)

    # Create a session with new review time
    session = SyncSession(
        start_time=datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2023, 1, 18, 10, 0, 0, tzinfo=timezone.utc),
        duration_seconds=109,  # New review time from the error log
        session_count=TEST_REVIEW_COUNT,
        first_review_time=datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc),
        last_review_time=datetime(2023, 1, 18, 10, 0, 0, tzinfo=timezone.utc),
    )

    # This should handle the 404 error gracefully and create a new entry
    from src.timezone import Timezone

    response = sync_to_toggl(
        session=session,
        api_token="test_token",
        workspace_id=TEST_REAL_WORKSPACE_ID,
        project_id=TEST_REAL_PROJECT_ID,
        description="Anki Review Session",
        timezone=Timezone("Asia/Seoul"),
        sync_state_manager=mock_sync_manager,
    )

    # ASSERTIONS:
    # 1. Should try to update the stale entry first (and get 404)
    assert len(api_calls) >= 1
    assert api_calls[0] == ("update", TEST_DELETED_ENTRY_ID, 109)

    # 2. After 404 error, should create a new entry directly (no search for replacements)
    assert len(api_calls) == 2, (
        f"Expected 2 API calls (update + create), got: {api_calls}"
    )
    assert api_calls[1] == (
        "create",
        109,
    ), f"Expected create call after 404, got: {api_calls[1]}"

    # 3. Should NOT call find_existing_entry (simplified approach)
    find_calls = [call for call in api_calls if "find_existing_entry" in str(call)]
    assert len(find_calls) == 0, (
        f"Should not search for existing entries, but got: {find_calls}"
    )
