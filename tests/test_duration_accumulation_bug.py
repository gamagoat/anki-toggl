"""
Test for the duration accumulation bug where multiple entries are created instead of updating existing ones.
"""

from datetime import date, datetime, timezone
from typing import Any, Optional
from unittest.mock import Mock

import pytest

from src.core import SyncSession, sync_to_toggl
from tests.test_constants import (
    TEST_DURATION_1_HOUR,
    TEST_DURATION_30_MIN,
    TEST_PROJECT_ID,
    TEST_SESSION_COUNT_LARGE,
    TEST_WORKSPACE_ID,
)


def test_duration_accumulation_bug_missing_toggl_id(
    monkeypatch: pytest.MonkeyPatch, mock_api_call_tracker: Any
) -> None:
    """
    Test that reproduces the duration accumulation bug.

    When sync state exists but toggl_id is missing, the system should
    find the existing entry in Toggl and update it, not create a new one.
    """

    # Track API calls using shared fixture
    api_calls = mock_api_call_tracker()

    # Create a Toggl creator mock that finds an existing entry and updates it
    class MockTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Any = None,
        ) -> Any:
            api_calls.append(("create", duration))

            class MockResponse:
                status_code = 200

                def json(self) -> dict[str, int]:
                    return {"id": 999}

            return MockResponse()

        def update_entry(
            self,
            entry_id: int,
            duration: int,
            start_time: datetime,
            timezone_str: Any = None,
        ) -> Any:
            api_calls.append(("update", entry_id, duration))

            class MockResponse:
                status_code = 200

                def json(self) -> dict[str, int]:
                    return {"id": entry_id}

            return MockResponse()

        def find_existing_entry(
            self, target_date: Optional[date] = None
        ) -> dict[str, Any]:
            api_calls.append(("find_existing_entry", str(target_date)))
            return {
                "id": 777,
                "project_id": TEST_PROJECT_ID,
                "description": "Anki Review Session",
            }

    # Create a sync state manager that indicates entry exists but has no toggl_id
    mock_sync_manager = Mock()
    mock_sync_manager.has_been_synced.return_value = True
    mock_sync_manager.get_synced_entry.return_value = {
        "duration_seconds": TEST_DURATION_30_MIN,  # 30 minutes previously synced
        "toggl_id": None,  # Missing toggl_id - this triggers the bug!
        "start_time": "2023-01-18T09:00:00+00:00",
    }
    mock_sync_manager.record_sync.return_value = None

    # Mock the dependencies
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", MockTogglCreator)
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_manager)

    # Create a session with 60 minutes total (30 minutes more than before)
    session = SyncSession(
        start_time=datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2023, 1, 18, 10, 0, 0, tzinfo=timezone.utc),
        duration_seconds=TEST_DURATION_1_HOUR,  # 60 minutes total
        session_count=TEST_SESSION_COUNT_LARGE,
        first_review_time=datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc),
        last_review_time=datetime(2023, 1, 18, 10, 0, 0, tzinfo=timezone.utc),
    )

    # This should UPDATE the existing entry, not CREATE a new one
    from src.timezone import Timezone

    response = sync_to_toggl(
        session=session,
        api_token="test_token",
        workspace_id=TEST_WORKSPACE_ID,
        project_id=TEST_PROJECT_ID,
        description="Anki Review Session",
        timezone=Timezone("UTC"),
        sync_state_manager=mock_sync_manager,
    )

    # ASSERTIONS: Should search and then update existing entry, not create a new one
    assert any(c[0] == "find_existing_entry" for c in api_calls), api_calls
    assert any(
        c[0] == "update" and c[1] == 777 and c[2] == TEST_DURATION_1_HOUR
        for c in api_calls
    ), api_calls
    assert not any(c[0] == "create" for c in api_calls), api_calls
