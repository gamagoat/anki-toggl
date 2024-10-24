"""
Shared pytest fixtures for the Anki Toggl add-on test suite.

This module provides common fixtures to reduce duplication across test files.
"""

pytest_plugins = ["tests.test_shared_fixtures"]

import sys
import types
from datetime import datetime, timezone
from typing import Any, Callable, cast
from unittest.mock import MagicMock, Mock

import pytest

# Import constants directly to avoid triggering src package initialization
HTTP_BAD_REQUEST = 400
HTTP_OK = 200
from tests.test_constants import (
    MOCK_RESPONSE_ERROR_TEXT,
    MOCK_RESPONSE_OK_TEXT,
    TEST_DURATION_1_MIN_MS,
    TEST_RESPONSE_ID,
)

# Provide a minimal stub for the aqt module in headless CI so tests can patch
# and import without pulling in PyQt6.
if "aqt" not in sys.modules:
    aqt_stub = types.ModuleType("aqt")
    aqt_stub.mw = None  # will be patched by tests

    utils_stub = types.ModuleType("aqt.utils")

    def _noop_tooltip(message: str, parent: Any = None) -> None:
        return

    utils_stub.tooltip = _noop_tooltip  # type: ignore[attr-defined]
    aqt_stub.utils = utils_stub  # type: ignore[attr-defined]

    qt_stub = types.ModuleType("aqt.qt")
    aqt_stub.qt = qt_stub  # type: ignore[attr-defined]

    sys.modules["aqt"] = aqt_stub
    sys.modules["aqt.utils"] = utils_stub
    sys.modules["aqt.qt"] = qt_stub


@pytest.fixture(scope="session")
def mock_anki_mw() -> MagicMock:
    """Create a mock Anki main window with database."""
    mock_mw = MagicMock()
    mock_col = MagicMock()
    mock_db = MagicMock()
    mock_db.scalar.return_value = TEST_DURATION_1_MIN_MS
    mock_col.db = mock_db
    mock_mw.col = mock_col
    return mock_mw


@pytest.fixture(scope="session")
def mock_anki_mw_no_collection() -> MagicMock:
    """Create a mock Anki main window without collection (None)."""
    mock_mw = MagicMock()
    mock_mw.col = None
    return mock_mw


@pytest.fixture
def mock_sync_state_manager() -> Mock:
    """Create a mock sync state manager with common methods."""
    mock_manager = Mock()
    mock_manager.has_been_synced.return_value = False
    mock_manager.record_sync.return_value = None
    mock_manager.get_synced_entry.return_value = {}
    return mock_manager


@pytest.fixture
def mock_sync_state_manager_already_synced() -> Mock:
    """Create a mock sync state manager that returns True for has_been_synced."""
    mock_manager = Mock()
    mock_manager.has_been_synced.return_value = True
    mock_manager.record_sync.return_value = None
    mock_manager.get_synced_entry.return_value = {"exists": True}
    return mock_manager


@pytest.fixture(scope="session")
def sample_session_info() -> dict[str, Any]:
    """Create sample session info with realistic datetime values."""
    mock_first_review = datetime(2023, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    mock_last_review = datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    return {
        "first_review_time": mock_first_review,
        "last_review_time": mock_last_review,
        "total_duration_ms": 60000,
        "session_count": 10,
    }


@pytest.fixture(scope="session")
def sample_session_info_with_range() -> dict[str, Any]:
    """Create sample session info spanning multiple time periods."""
    morning_start = datetime(2023, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    afternoon_end = datetime(2023, 1, 15, 15, 30, 0, tzinfo=timezone.utc)
    return {
        "first_review_time": morning_start,
        "last_review_time": afternoon_end,
        "total_duration_ms": 120000,  # 2 minutes
        "session_count": 20,
    }


@pytest.fixture(scope="session")
def empty_session_info() -> dict[str, Any]:
    """Create empty session info with no review time."""
    return {
        "first_review_time": None,
        "last_review_time": None,
        "total_duration_ms": 0,
        "session_count": 0,
    }


@pytest.fixture
def mock_http_response() -> Mock:
    """Create a mock HTTP response with status 200."""
    mock_response = Mock()
    mock_response.status_code = HTTP_OK
    mock_response.text = "OK"
    mock_response.json.return_value = []
    return mock_response


@pytest.fixture
def mock_toggl_creator() -> type[Any]:
    """Create a mock TogglTrackEntryCreator class with successful responses."""

    class DummyTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            mock_response = Mock()
            mock_response.status_code = HTTP_OK
            mock_response.text = MOCK_RESPONSE_OK_TEXT
            return mock_response

        def create_or_update_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            mock_response = Mock()
            mock_response.status_code = HTTP_OK
            mock_response.text = MOCK_RESPONSE_OK_TEXT
            return mock_response

        def update_entry(
            self,
            entry_id: Any,
            duration: Any,
            start_time: Any,
            timezone_str: Any = None,
        ) -> Mock:
            mock_response = Mock()
            mock_response.status_code = HTTP_OK
            mock_response.text = MOCK_RESPONSE_OK_TEXT
            return mock_response

    return DummyTogglCreator


@pytest.fixture
def mock_toggl_creator_error() -> type[Any]:
    """Create a mock TogglTrackEntryCreator class with error responses."""

    class DummyTogglCreatorError:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            mock_response = Mock()
            mock_response.status_code = HTTP_BAD_REQUEST
            mock_response.text = MOCK_RESPONSE_ERROR_TEXT
            return mock_response

        def create_or_update_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            mock_response = Mock()
            mock_response.status_code = HTTP_BAD_REQUEST
            mock_response.text = MOCK_RESPONSE_ERROR_TEXT
            return mock_response

        def update_entry(
            self,
            entry_id: Any,
            duration: Any,
            start_time: Any,
            timezone_str: Any = None,
        ) -> Mock:
            mock_response = Mock()
            mock_response.status_code = HTTP_BAD_REQUEST
            mock_response.text = MOCK_RESPONSE_ERROR_TEXT
            return mock_response

    return DummyTogglCreatorError


@pytest.fixture
def mock_toggl_creator_with_tracking() -> type[Any]:
    """Create a mock TogglTrackEntryCreator class that tracks calls."""

    class DummyTogglCreatorWithTracking:
        called = False

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            DummyTogglCreatorWithTracking.called = True
            mock_response = Mock()
            mock_response.status_code = HTTP_OK
            mock_response.text = MOCK_RESPONSE_OK_TEXT
            return mock_response

        def create_or_update_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            DummyTogglCreatorWithTracking.called = True
            mock_response = Mock()
            mock_response.status_code = HTTP_OK
            mock_response.text = MOCK_RESPONSE_OK_TEXT
            return mock_response

        def update_entry(
            self,
            entry_id: Any,
            duration: Any,
            start_time: Any,
            timezone_str: Any = None,
        ) -> Mock:
            DummyTogglCreatorWithTracking.called = True
            mock_response = Mock()
            mock_response.status_code = HTTP_OK
            mock_response.text = MOCK_RESPONSE_OK_TEXT
            return mock_response

    return DummyTogglCreatorWithTracking


@pytest.fixture
def mock_anki_review_tracker() -> Callable[[Any], Callable[[Any], MagicMock]]:
    """Create a mock AnkiReviewTracker factory function."""

    def create_tracker(session_info: dict[str, Any]) -> Callable[[Any], MagicMock]:
        def tracker_factory(mw: Any) -> MagicMock:
            def get_session_info() -> dict[str, Any]:
                return session_info

            return MagicMock(get_todays_review_session_info=get_session_info)

        return tracker_factory

    return create_tracker


@pytest.fixture
def mock_session_request(mocker: Any) -> MagicMock:
    """Mock the requests.Session.request method for HTTP testing."""
    mock_request = cast("MagicMock", mocker.patch("requests.Session.request"))
    mock_response = Mock()
    mock_response.status_code = HTTP_OK
    mock_response.json.return_value = []
    mock_request.return_value = mock_response
    return mock_request


@pytest.fixture
def dummy_toggl_response() -> type[Any]:
    """Create a dummy Toggl API response for testing."""

    class DummyResponse:
        status_code = HTTP_OK
        text = MOCK_RESPONSE_OK_TEXT

        def json(self) -> dict[str, int]:
            return {"id": TEST_RESPONSE_ID}

    return DummyResponse


@pytest.fixture
def dummy_toggl_creator(dummy_toggl_response: type[Any]) -> type[Any]:
    """Create a dummy TogglTrackEntryCreator for testing."""

    class DummyTogglCreator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            return dummy_toggl_response()

        def create_or_update_entry(
            self, start_time: Any, duration: Any, timezone_str: Any = None
        ) -> Mock:
            return dummy_toggl_response()

        def update_entry(
            self,
            entry_id: Any,
            duration: Any,
            start_time: Any,
            timezone_str: Any = None,
        ) -> Mock:
            return dummy_toggl_response()

    return DummyTogglCreator
