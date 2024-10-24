from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock, Mock

import pytest

from src.constants import HTTP_BAD_REQUEST, HTTP_OK, HTTP_SERVICE_UNAVAILABLE
from src.core import (
    SyncSession,
    SyncSkipped,
    TogglSyncError,
    get_review_session,
    sync_review_time_to_toggl,
    validate_session,
)
from src.timezone import Timezone
from tests.test_constants import (
    TEST_CORE_DESCRIPTION,
    TEST_CORE_PROJECT_ID,
    TEST_CORE_TOKEN,
    TEST_CORE_WORKSPACE_ID,
    TEST_DURATION_1_MIN,
    TEST_DURATION_1_MIN_MS,
    TEST_SESSION_COUNT,
)


@pytest.mark.unit
def test_sync_review_time_to_toggl_success(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    sample_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_toggl_creator: MagicMock,
    mock_anki_review_tracker: MagicMock,
) -> None:
    # Use shared fixtures instead of local mocks
    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", mock_toggl_creator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(sample_session_info)
    )
    monkeypatch.setattr(
        "src.core.SyncStateManager",
        lambda: mock_sync_state_manager,  # type: ignore
    )

    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    assert response is not None
    assert response.status_code == HTTP_OK


@pytest.mark.unit
@pytest.mark.parametrize(
    "timezone_str,expected_status",
    [
        (None, HTTP_OK),
        ("Asia/Seoul", HTTP_OK),
    ],
)
def test_sync_review_time_to_toggl_success_scenarios(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    sample_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_toggl_creator: MagicMock,
    mock_anki_review_tracker: MagicMock,
    timezone_str: Optional[str],
    expected_status: int,
) -> None:
    # Use shared fixtures for testing different timezone scenarios
    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", mock_toggl_creator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(sample_session_info)
    )
    monkeypatch.setattr(
        "src.core.SyncStateManager",
        lambda: mock_sync_state_manager,  # type: ignore
    )

    from src.timezone import Timezone

    timezone_obj = Timezone(timezone_str) if timezone_str else None
    response = sync_review_time_to_toggl("token", 1, 2, "desc", timezone_obj)

    assert response is not None
    assert response.status_code == expected_status


@pytest.mark.unit
def test_sync_review_time_to_toggl_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    sample_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_toggl_creator_error: MagicMock,
    mock_anki_review_tracker: MagicMock,
) -> None:
    # Use shared fixtures for error testing
    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", mock_toggl_creator_error)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(sample_session_info)
    )
    monkeypatch.setattr(
        "src.core.SyncStateManager",
        lambda: mock_sync_state_manager,  # type: ignore
    )

    with pytest.raises(TogglSyncError) as exc_info:
        sync_review_time_to_toggl("token", 1, 2, "desc")

    # Verify specific error attributes
    assert exc_info.value.status_code == HTTP_BAD_REQUEST
    assert "Bad Request" in exc_info.value.response_text


@pytest.mark.unit
def test_sync_review_time_to_toggl_no_review_time(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    empty_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_toggl_creator_with_tracking: MagicMock,
    mock_anki_review_tracker: MagicMock,
) -> None:
    # Use shared fixtures for no review time testing
    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr(
        "src.core.TogglTrackEntryCreator", mock_toggl_creator_with_tracking
    )
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(empty_session_info)
    )
    monkeypatch.setattr(
        "src.core.SyncStateManager",
        lambda: mock_sync_state_manager,  # type: ignore
    )

    # Patch get_review_session to return a zero-duration session
    def get_zero_duration_session(mw: Any, tz: str) -> SyncSession:
        return SyncSession(
            start_time=datetime.now(timezone.utc),
            end_time=None,
            duration_seconds=0,
            session_count=0,
            first_review_time=None,
            last_review_time=None,
        )

    monkeypatch.setattr(
        "src.core.get_review_session",
        get_zero_duration_session,
    )

    mock_toggl_creator_with_tracking.called = False
    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    assert response is None
    assert mock_toggl_creator_with_tracking.called is False


@pytest.mark.unit
@pytest.mark.parametrize(
    "mw_value,expected_response",
    [
        (None, None),  # No mw
        ("no_collection", None),  # mw with no collection
    ],
)
def test_sync_review_time_to_toggl_no_mw_or_collection(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw_no_collection: MagicMock,
    mw_value: Optional[str],
    expected_response: None,
) -> None:
    if mw_value is None:
        monkeypatch.setattr("src.core.mw", None)
    else:
        # Use shared fixture for testing when Anki collection is None
        monkeypatch.setattr("src.core.mw", mock_anki_mw_no_collection)

    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    assert response is expected_response


@pytest.mark.unit
def test_sync_review_time_to_toggl_uses_fallback_timezone(
    monkeypatch: pytest.MonkeyPatch, mock_anki_mw: MagicMock, mock_response_factory: Any
) -> None:
    mock_mw = mock_anki_mw
    monkeypatch.setattr("src.core.mw", mock_mw)

    class DummyResponse:
        status_code: int = 200
        text: str = "OK"

    class DummyTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

        def create_or_update_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

        def update_entry(
            self,
            entry_id: int,
            duration: int,
            start_time: datetime,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

    # Mock session info with no first review time (to trigger fallback)
    mock_session_info = {
        "first_review_time": None,
        "last_review_time": datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        "total_duration_ms": TEST_DURATION_1_MIN_MS,
        "session_count": TEST_SESSION_COUNT,
    }

    # Create a fresh sync state manager for this test

    mock_sync_manager = Mock()
    mock_sync_manager.has_been_synced.return_value = False
    mock_sync_manager.record_sync.return_value = None

    # Mock get_timezone_config to return a specific timezone
    monkeypatch.setattr("src.core.get_timezone", lambda: Timezone("Asia/Seoul"))

    monkeypatch.setattr("src.core.TogglTrackEntryCreator", DummyTogglCreator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker",
        lambda mw: MagicMock(get_todays_review_session_info=lambda: mock_session_info),
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_manager)

    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    assert response is not None
    assert response.status_code == HTTP_OK


@pytest.mark.unit
def test_sync_review_time_to_toggl_prevents_duplicates(
    monkeypatch: pytest.MonkeyPatch, mock_anki_mw: MagicMock
) -> None:
    """Test that sync_review_time_to_toggl prevents duplicate entries."""
    mock_mw = mock_anki_mw
    monkeypatch.setattr("src.core.mw", mock_mw)

    class DummyResponse:
        status_code: int = 200
        text: str = "OK"

    class DummyTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

        def create_or_update_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

        def update_entry(
            self,
            entry_id: int,
            duration: int,
            start_time: datetime,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

    # Mock session info
    mock_session_info = {
        "first_review_time": datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc),
        "last_review_time": datetime(2023, 1, 18, 10, 0, 0, tzinfo=timezone.utc),
        "total_duration_ms": TEST_DURATION_1_MIN_MS,
        "session_count": TEST_SESSION_COUNT,
    }

    # Create a sync state manager that indicates entry already exists

    mock_sync_manager = Mock()
    mock_sync_manager.has_been_synced.return_value = True
    mock_sync_manager.get_synced_entry.return_value = {
        "duration_seconds": 60,  # Same duration
        "toggl_id": 12345,
    }
    mock_sync_manager.record_sync.return_value = None

    monkeypatch.setattr("src.core.TogglTrackEntryCreator", DummyTogglCreator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker",
        lambda mw: MagicMock(get_todays_review_session_info=lambda: mock_session_info),
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_manager)

    # This should perform an update to prevent duplicate entries
    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    assert response is not None
    assert response.status_code == HTTP_OK


def test_sync_preserves_original_start_time_on_update(
    monkeypatch: pytest.MonkeyPatch, mock_anki_mw: MagicMock
) -> None:
    """Test that when updating an existing entry, the original start time is preserved."""
    mock_mw = mock_anki_mw
    monkeypatch.setattr("src.core.mw", mock_mw)

    # Track what start_time was passed to update_entry
    captured_update_calls = []

    class DummyResponse:
        status_code: int = 200
        text: str = "OK"

        def json(self) -> dict[str, Any]:
            return {"id": 12345}

    class DummyTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

        def create_or_update_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            return DummyResponse()

        def update_entry(
            self,
            entry_id: int,
            duration: int,
            start_time: datetime,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            # Capture the call for verification
            captured_update_calls.append(
                {
                    "entry_id": entry_id,
                    "duration": duration,
                    "start_time": start_time,
                    "timezone_str": timezone_str,
                }
            )
            return DummyResponse()

    # Mock session info - afternoon session with morning first_review_time
    morning_start = datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc)
    afternoon_end = datetime(2023, 1, 18, 15, 30, 0, tzinfo=timezone.utc)

    mock_session_info = {
        "first_review_time": morning_start,  # This is from morning session
        "last_review_time": afternoon_end,  # This is from afternoon session
        "total_duration_ms": 3600000,  # 1 hour total (updated duration)
        "session_count": 20,
    }

    # Original start time from the first sync (should be preserved)
    original_start_time = datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc)

    # Create a sync state manager that indicates entry already exists

    mock_sync_manager = Mock()
    mock_sync_manager.has_been_synced.return_value = True
    # Patch get_review_session to return a session with duration_seconds=3600
    monkeypatch.setattr(
        "src.core.get_review_session",
        lambda mw, tz: SyncSession(
            start_time=morning_start,
            end_time=afternoon_end,
            duration_seconds=3600,
            session_count=20,
            first_review_time=morning_start,
            last_review_time=afternoon_end,
        ),
    )
    # Set previous duration to 60 (difference is 3540 > 5)
    mock_sync_manager.get_synced_entry.return_value = {
        "duration_seconds": 60,
        "toggl_id": 12345,
        "start_time": original_start_time.isoformat(),
    }
    mock_sync_manager.record_sync.return_value = None

    monkeypatch.setattr("src.core.TogglTrackEntryCreator", DummyTogglCreator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker",
        lambda mw: MagicMock(get_todays_review_session_info=lambda: mock_session_info),
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_manager)

    # Perform the sync
    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    # Verify the response was successful
    assert response is not None
    assert response.status_code == HTTP_OK

    # Verify that update_entry was called exactly once
    assert len(captured_update_calls) == 1

    # Verify that the original start time was preserved (not the new first_review_time)
    update_call = captured_update_calls[0]
    assert update_call["entry_id"] == 12345
    assert update_call["duration"] == 3600  # Updated duration
    assert (
        update_call["start_time"] == original_start_time
    )  # PRESERVED original start time

    # Verify that record_sync was called with the preserved start time
    mock_sync_manager.record_sync.assert_called_once()
    record_call_args = mock_sync_manager.record_sync.call_args[1]
    assert record_call_args["start_time"] == original_start_time
    assert record_call_args["duration_seconds"] == 3600
    assert record_call_args["action"] == "update"


def test_sync_fallback_start_time_when_no_original(
    monkeypatch: pytest.MonkeyPatch, mock_anki_mw: MagicMock
) -> None:
    """Test fallback behavior when original start time is not available."""
    mock_mw = mock_anki_mw
    monkeypatch.setattr("src.core.mw", mock_mw)

    # Track what start_time was passed to update_entry
    captured_update_calls = []

    class DummyResponse:
        status_code: int = 200
        text: str = "OK"

        def json(self) -> dict[str, Any]:
            return {"id": 12345}

    class DummyTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def update_entry(
            self,
            entry_id: int,
            duration: int,
            start_time: datetime,
            timezone_str: Optional[str] = None,
        ) -> DummyResponse:
            captured_update_calls.append(
                {
                    "entry_id": entry_id,
                    "duration": duration,
                    "start_time": start_time,
                    "timezone_str": timezone_str,
                }
            )
            return DummyResponse()

    # Mock session info
    current_start = datetime(2023, 1, 18, 9, 0, 0, tzinfo=timezone.utc)
    last_review_time = datetime(2023, 1, 18, 10, 0, 0, tzinfo=timezone.utc)
    mock_session_info = {
        "first_review_time": current_start,
        "last_review_time": last_review_time,
        "total_duration_ms": 3600000,  # 1 hour
        "session_count": 20,
    }

    # Create sync state manager with existing entry but NO start_time field

    mock_sync_manager = Mock()
    mock_sync_manager.has_been_synced.return_value = True
    mock_sync_manager.get_synced_entry.return_value = {
        "duration_seconds": 1800,
        "toggl_id": 12345,
        # Missing "start_time" field to test fallback
    }
    mock_sync_manager.record_sync.return_value = None

    monkeypatch.setattr("src.core.TogglTrackEntryCreator", DummyTogglCreator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker",
        lambda mw: MagicMock(get_todays_review_session_info=lambda: mock_session_info),
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_manager)

    # Patch get_review_session to return a session with duration_seconds=3600
    monkeypatch.setattr(
        "src.core.get_review_session",
        lambda mw, tz: SyncSession(
            start_time=current_start,
            end_time=last_review_time,
            duration_seconds=3600,
            session_count=20,
            first_review_time=current_start,
            last_review_time=last_review_time,
        ),
    )
    # Perform the sync
    response = sync_review_time_to_toggl(
        TEST_CORE_TOKEN,
        TEST_CORE_WORKSPACE_ID,
        TEST_CORE_PROJECT_ID,
        TEST_CORE_DESCRIPTION,
    )

    # Verify the response was successful
    assert response is not None
    assert response.status_code == HTTP_OK

    # Verify that update_entry was called
    assert len(captured_update_calls) == 1

    # Should fall back to current start time (from session info)
    update_call = captured_update_calls[0]
    assert update_call["duration"] == 3600
    assert update_call["start_time"] == current_start


@pytest.mark.unit
def test_get_review_session_returns_syncsession(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_mw = MagicMock()
    mock_first_review = datetime(2023, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    mock_last_review = datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    mock_session_info = {
        "first_review_time": mock_first_review,
        "last_review_time": mock_last_review,
        "total_duration_ms": TEST_DURATION_1_MIN_MS,
        "session_count": TEST_SESSION_COUNT,
    }
    # Patch AnkiReviewTracker to return our mock_session_info
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker",
        lambda mw: MagicMock(get_todays_review_session_info=lambda: mock_session_info),
    )
    # Patch mock_mw.col.db.scalar to return 60000 for session_count and 10 for total_duration_ms
    mock_col = MagicMock()
    mock_col.db.scalar.side_effect = [60000, 10]
    # Patch mock_mw.col.db.first to return correct timestamps for first and last review
    mock_col.db.first.side_effect = [
        (int(mock_first_review.timestamp() * 1000), 0),
        (int(mock_last_review.timestamp() * 1000), 0),
    ]
    mock_mw.col = mock_col
    session = get_review_session(mock_mw, Timezone("UTC"))
    assert isinstance(session, SyncSession)
    assert session.duration_seconds == TEST_DURATION_1_MIN
    assert session.session_count == TEST_SESSION_COUNT
    assert session.first_review_time == mock_first_review
    assert session.last_review_time == mock_last_review


@pytest.mark.unit
def test_validate_session_zero_duration_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    session = SyncSession(
        start_time=datetime.now(timezone.utc),
        end_time=None,
        duration_seconds=0,
        session_count=0,
        first_review_time=None,
        last_review_time=None,
    )
    mock_sync_manager = MagicMock()
    with pytest.raises(SyncSkipped):
        validate_session(session, mock_sync_manager, 1, 2, "desc")


@pytest.mark.unit
def test_validate_session_allows_resync_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SyncSession(
        start_time=datetime.now(timezone.utc),
        end_time=None,
        duration_seconds=60,
        session_count=1,
        first_review_time=None,
        last_review_time=None,
    )
    mock_sync_manager = MagicMock()
    mock_sync_manager.has_been_synced.return_value = True
    mock_sync_manager.get_synced_entry.return_value = {"duration_seconds": 60}
    validate_session(session, mock_sync_manager, 1, 2, "desc")


def test_sync_review_time_to_toggl_network_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    sample_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_anki_review_tracker: MagicMock,
) -> None:
    """Test network error handling with specific RequestException."""
    import requests

    # Mock TogglTrackEntryCreator to raise network error
    class NetworkErrorTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> None:
            raise requests.ConnectionError("Network connection failed")

    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", NetworkErrorTogglCreator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(sample_session_info)
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_state_manager)

    with pytest.raises(TogglSyncError) as exc_info:
        sync_review_time_to_toggl("token", 1, 2, "desc")

    # Verify it's a network error specifically
    assert exc_info.value.status_code == HTTP_SERVICE_UNAVAILABLE
    assert "Network error" in exc_info.value.response_text
    assert "Network connection failed" in exc_info.value.response_text


def test_sync_review_time_to_toggl_invalid_input_error(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
) -> None:
    """Test handling of invalid input with specific ValueError."""

    # Mock AnkiReviewTracker to raise ValueError
    def mock_review_tracker_invalid(mw: Any) -> MagicMock:
        def get_session_info() -> dict[str, Any]:
            raise ValueError("Invalid timestamp format")

        return MagicMock(get_todays_review_session_info=get_session_info)

    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.AnkiReviewTracker", mock_review_tracker_invalid)

    with pytest.raises(TogglSyncError) as exc_info:
        sync_review_time_to_toggl("token", 1, 2, "desc")

    # Verify it's an input validation error
    assert exc_info.value.status_code == HTTP_BAD_REQUEST
    assert "Invalid input" in exc_info.value.response_text
    assert "Invalid timestamp format" in exc_info.value.response_text


def test_sync_review_time_to_toggl_logs_correctly(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    sample_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_toggl_creator: MagicMock,
    mock_anki_review_tracker: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that sync_review_time_to_toggl logs correctly at different levels."""
    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", mock_toggl_creator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(sample_session_info)
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_state_manager)

    with caplog.at_level("DEBUG"):
        response = sync_review_time_to_toggl(
            TEST_CORE_TOKEN,
            TEST_CORE_WORKSPACE_ID,
            TEST_CORE_PROJECT_ID,
            TEST_CORE_DESCRIPTION,
        )

    # Check that INFO level messages are logged
    info_messages = [record for record in caplog.records if record.levelname == "INFO"]
    assert len(info_messages) >= 1

    # Check for presence of key fragments rather than exact strings
    log_messages = [record.message for record in caplog.records]
    lower_messages = [msg.lower() for msg in log_messages]
    assert any("sync" in msg for msg in lower_messages)
    assert any("toggl" in msg for msg in lower_messages)

    # Check DEBUG level logging
    debug_messages = [
        record for record in caplog.records if record.levelname == "DEBUG"
    ]
    assert len(debug_messages) >= 1

    assert response is not None
    assert response.status_code == HTTP_OK


def test_sync_review_time_to_toggl_logs_error_correctly(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    sample_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_anki_review_tracker: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that errors are logged correctly with ERROR level."""
    import requests

    # Mock TogglTrackEntryCreator to raise network error
    class NetworkErrorTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> None:
            raise requests.ConnectionError("Network connection failed")

    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", NetworkErrorTogglCreator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(sample_session_info)
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_state_manager)

    with caplog.at_level("ERROR"):
        with pytest.raises(TogglSyncError):
            sync_review_time_to_toggl("token", 1, 2, "desc")

    # Check that ERROR level messages are logged
    error_messages = [
        record for record in caplog.records if record.levelname == "ERROR"
    ]
    assert len(error_messages) >= 1

    # Check for error fragments
    error_log_messages = [
        record.message for record in caplog.records if record.levelname == "ERROR"
    ]
    lower_error_messages = [msg.lower() for msg in error_log_messages]
    assert any("network error" in msg for msg in lower_error_messages)
    assert any("sync" in msg for msg in lower_error_messages)


def test_sync_review_time_to_toggl_logs_skip_correctly(
    monkeypatch: pytest.MonkeyPatch,
    mock_anki_mw: MagicMock,
    empty_session_info: dict[str, Any],
    mock_sync_state_manager: MagicMock,
    mock_toggl_creator: MagicMock,
    mock_anki_review_tracker: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that skipped syncs are logged correctly with INFO level."""
    monkeypatch.setattr("src.core.mw", mock_anki_mw)
    monkeypatch.setattr("src.core.TogglTrackEntryCreator", mock_toggl_creator)
    monkeypatch.setattr(
        "src.core.AnkiReviewTracker", mock_anki_review_tracker(empty_session_info)
    )
    monkeypatch.setattr("src.core.SyncStateManager", lambda: mock_sync_state_manager)

    # Patch get_review_session to return a zero-duration session
    def get_zero_duration_session(mw: Any, tz: Any) -> SyncSession:
        return SyncSession(
            start_time=datetime.now(timezone.utc),
            end_time=None,
            duration_seconds=0,
            session_count=0,
            first_review_time=None,
            last_review_time=None,
        )

    monkeypatch.setattr("src.core.get_review_session", get_zero_duration_session)

    with caplog.at_level("INFO"):
        response = sync_review_time_to_toggl(
            TEST_CORE_TOKEN,
            TEST_CORE_WORKSPACE_ID,
            TEST_CORE_PROJECT_ID,
            TEST_CORE_DESCRIPTION,
        )

    # Check that INFO level skip message is logged
    info_messages = [record for record in caplog.records if record.levelname == "INFO"]
    skip_messages = [msg for msg in info_messages if "Sync skipped" in msg.message]
    assert len(skip_messages) >= 1

    # Verify specific skip reason
    skip_message = skip_messages[0].message
    assert "No review time logged" in skip_message

    assert response is None
