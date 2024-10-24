from datetime import datetime, timezone
from typing import Any, cast
from unittest.mock import MagicMock, Mock, patch
from zoneinfo import ZoneInfo

import pytest

from src.constants import HTTP_OK
from src.toggl_track_entry_creator import TogglTrackEntryCreator
from tests.test_constants import (
    TEST_DESCRIPTION,
    TEST_DIFFERENT_PROJECT_ID,
    TEST_DURATION_1_HOUR,
    TEST_DURATION_30_MIN,
    TEST_DURATION_40_MIN,
    TEST_DURATION_50_MIN,
    TEST_ENTRY_ID_1,
    TEST_ENTRY_ID_2,
    TEST_PROJECT_ID,
    TEST_WORKSPACE_ID,
)


@pytest.fixture
def mock_session_request(mocker: MagicMock) -> MagicMock:
    """Mock the requests.Session.request method."""
    mock_request = cast("MagicMock", mocker.patch("requests.Session.request"))
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_request.return_value = mock_response
    return mock_request


@pytest.fixture
def entry_creator() -> TogglTrackEntryCreator:
    return TogglTrackEntryCreator(
        api_token="dummy_token",
        workspace_id=TEST_WORKSPACE_ID,
        project_id=TEST_PROJECT_ID,
        description=TEST_DESCRIPTION,
    )


def assert_json_call_arg(mock: MagicMock, key: str, value: Any) -> None:
    assert key in mock.call_args.kwargs["json"]
    assert mock.call_args.kwargs["json"][key] == value


@pytest.mark.unit
@pytest.mark.parametrize("duration", [TEST_DURATION_1_HOUR, 3600])
def test_create_entry_well_formed(
    mock_session_request: MagicMock,
    entry_creator: TogglTrackEntryCreator,
    duration: int,
) -> None:
    start_time = datetime.now(timezone.utc)

    response = entry_creator.create_entry(start_time, duration)

    assert response.status_code == HTTP_OK
    mock_session_request.assert_called_once()

    expected_url = f"https://api.track.toggl.com/api/v9/workspaces/{entry_creator.workspace_id}/time_entries"
    assert mock_session_request.call_args[0][1] == expected_url
    assert mock_session_request.call_args[0][0] == "post"

    assert_json_call_arg(mock_session_request, "duration", duration)
    assert_json_call_arg(mock_session_request, "start", start_time.isoformat())
    assert_json_call_arg(mock_session_request, "description", entry_creator.description)
    assert_json_call_arg(mock_session_request, "project_id", entry_creator.project_id)
    assert_json_call_arg(
        mock_session_request, "created_with", entry_creator.created_with
    )
    assert_json_call_arg(
        mock_session_request, "workspace_id", entry_creator.workspace_id
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "duration,datetime_type",
    [
        (TEST_DURATION_30_MIN, "utc"),
        (TEST_DURATION_40_MIN, "timezone_aware"),
        (TEST_DURATION_50_MIN, "naive"),
    ],
)
def test_add_entry_with_different_datetime_types(
    mock_session_request: MagicMock,
    entry_creator: TogglTrackEntryCreator,
    duration: int,
    datetime_type: str,
) -> None:
    """Test create_entry with different datetime types."""
    if datetime_type == "utc":
        start_time = datetime.now(timezone.utc)
    elif datetime_type == "timezone_aware":
        ny_tz = ZoneInfo("America/New_York")
        start_time = datetime(2024, 3, 15, 14, 30, 0, tzinfo=ny_tz)
    else:  # naive
        start_time = datetime(2024, 3, 15, 14, 30, 0)

    response = entry_creator.create_entry(start_time, duration)

    assert response.status_code == HTTP_OK
    mock_session_request.assert_called_once()

    # Check that timezone-aware datetime is used
    call_args = mock_session_request.call_args.kwargs["json"]
    start_time_sent = call_args["start"]

    # Should be ISO format with timezone info
    assert "T" in start_time_sent
    # Should have timezone offset or Z for UTC
    assert (
        "+" in start_time_sent
        or "-" in start_time_sent
        or start_time_sent.endswith("Z")
    )


@pytest.mark.unit
def test_add_entry_preserves_timezone_behavior(
    mock_session_request: MagicMock, entry_creator: TogglTrackEntryCreator
) -> None:
    """create_entry works without explicit timezone parameter."""
    start_time = datetime.now(timezone.utc)
    duration = TEST_DURATION_1_HOUR

    response = entry_creator.create_entry(start_time, duration)

    assert response.status_code == HTTP_OK
    mock_session_request.assert_called_once()


@pytest.mark.unit
def test_find_existing_entry_found(entry_creator: TogglTrackEntryCreator) -> None:
    """Test finding an existing entry successfully."""
    mock_entries = [
        {
            "id": TEST_ENTRY_ID_1,
            "description": TEST_DESCRIPTION,  # Matches our description
            "project_id": TEST_PROJECT_ID,  # Matches our project_id
            "duration": TEST_DURATION_1_HOUR,
        },
        {
            "id": TEST_ENTRY_ID_2,
            "description": "Different Description",
            "project_id": TEST_DIFFERENT_PROJECT_ID,
            "duration": TEST_DURATION_30_MIN,
        },
    ]

    with patch("requests.Session.request") as mock_request:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_entries
        mock_request.return_value = mock_response

        found_entry = entry_creator.find_existing_entry()

        assert found_entry is not None
        assert found_entry["id"] == TEST_ENTRY_ID_1
        assert found_entry["description"] == TEST_DESCRIPTION
        assert found_entry["project_id"] == TEST_PROJECT_ID


@pytest.mark.unit
def test_find_existing_entry_not_found(entry_creator: TogglTrackEntryCreator) -> None:
    """Test finding no existing entry."""
    mock_entries = [
        {
            "id": 456,
            "description": "Different Description",
            "project_id": 99999,
            "duration": 1800,
        },
    ]

    with patch("requests.Session.request") as mock_request:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_entries
        mock_request.return_value = mock_response

        found_entry = entry_creator.find_existing_entry()

        assert found_entry is None


@pytest.mark.unit
def test_update_entry_success(entry_creator: TogglTrackEntryCreator) -> None:
    """Test updating an entry successfully."""
    entry_id = 12345
    duration = 7200
    start_time = datetime(2023, 1, 15, 9, 0, 0)

    with patch("requests.Session.request") as mock_request:
        # Only one call is the actual update request (PUT /api/v9/workspaces/.../time_entries/...)
        mock_response = Mock()
        mock_response.status_code = 200

        mock_request.return_value = mock_response

        response = entry_creator.update_entry(entry_id, duration, start_time)

        assert response.status_code == HTTP_OK
        assert mock_request.call_count == 1

        # Check that the call was a PUT request (update)
        call = mock_request.call_args_list[0]
        assert call[0][0] == "put"  # Method
        expected_url = f"https://api.track.toggl.com/api/v9/workspaces/{entry_creator.workspace_id}/time_entries/{entry_id}"
        assert call[0][1] == expected_url  # URL

        # Check the JSON data
        json_data = call.kwargs["json"]
        assert json_data["duration"] == duration
        assert json_data["description"] == entry_creator.description
        assert json_data["project_id"] == entry_creator.project_id


@pytest.mark.unit
def test_update_entry_failure(entry_creator: TogglTrackEntryCreator) -> None:
    """Test handling failure when updating an entry."""
    entry_id = 12345
    duration = 7200
    start_time = datetime(2023, 1, 15, 9, 0, 0)

    with patch("requests.Session.request") as mock_request:
        # Only one call is the actual update request (PUT /api/v9/workspaces/.../time_entries/...)
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Entry not found"

        mock_request.return_value = mock_response

        response = entry_creator.update_entry(entry_id, duration, start_time)

        assert response.status_code == 404
        assert mock_request.call_count == 1


@pytest.mark.unit
def test_create_or_update_entry_updates_existing(
    entry_creator: TogglTrackEntryCreator,
) -> None:
    """Test create_or_update_entry updates existing entry."""
    mock_entries = [
        {
            "id": 123,
            "description": "Test Description",
            "project_id": 67890,
            "duration": 3600,
        }
    ]

    with patch("requests.Session.request") as mock_request:
        # First call: find_existing_entry -> get_time_entries_for_date (GET /api/v9/workspaces/.../time_entries)
        # Second call: update request (PUT /api/v9/workspaces/.../time_entries/...)
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = mock_entries

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"timezone": "UTC"}

        mock_response3 = Mock()
        mock_response3.status_code = 200

        mock_request.side_effect = [mock_response1, mock_response2, mock_response3]

        response = entry_creator.create_or_update_entry(datetime.now(), 3600)

        assert response.status_code == HTTP_OK
        assert mock_request.call_count == 2

        # Check that the second call was a PUT request (update)
        second_call = mock_request.call_args_list[1]
        assert second_call[0][0] == "put"


@pytest.mark.unit
def test_create_or_update_entry_creates_new(
    entry_creator: TogglTrackEntryCreator,
) -> None:
    """Test create_or_update_entry creates new entry when none exists."""
    with patch("requests.Session.request") as mock_request:
        # First call: find_existing_entry -> get_time_entries_for_date (GET /api/v9/workspaces/.../time_entries)
        # Second call: create request (POST /api/v9/workspaces/.../time_entries)
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = []

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {"timezone": "UTC"}

        mock_response3 = Mock()
        mock_response3.status_code = 200

        mock_request.side_effect = [mock_response1, mock_response2, mock_response3]

        response = entry_creator.create_or_update_entry(datetime.now(), 3600)

        assert response.status_code == HTTP_OK
        assert mock_request.call_count == 2

        # Check that the second call was a POST request (create)
        second_call = mock_request.call_args_list[1]
        assert second_call[0][0] == "post"
