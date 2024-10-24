from base64 import b64decode
from unittest.mock import MagicMock

import pytest

from src.toggl_track_entry_creator import TogglTrackEntryCreator


@pytest.fixture
def entry_creator() -> TogglTrackEntryCreator:
    return TogglTrackEntryCreator(
        api_token="apitoken123",
        workspace_id=1,
        project_id=2,
        description="d",
    )


@pytest.mark.unit
def test_headers_produces_valid_basic_auth(entry_creator):  # type: ignore[no-redef]
    headers = entry_creator._headers()
    assert "Authorization" in headers
    scheme, token = headers["Authorization"].split(" ")
    assert scheme == "Basic"
    decoded = b64decode(token.encode()).decode()
    assert decoded == "apitoken123:api_token"


@pytest.mark.unit
def test_request_error_paths_logged_and_raise(mocker: MagicMock, entry_creator):  # type: ignore[no-redef]
    import requests

    # 4xx/5xx path
    mock_request = mocker.patch("requests.Session.request")
    bad = MagicMock()
    bad.status_code = 500
    bad.text = "ERR"

    # raise_for_status triggers RequestException
    def raise_http() -> None:
        raise requests.HTTPError("boom", response=bad)

    bad.raise_for_status.side_effect = raise_http
    mock_request.return_value = bad

    with pytest.raises(requests.HTTPError):
        entry_creator._request("get", entry_creator.user_api_url)

    # RequestException thrown directly
    mock_request.side_effect = requests.RequestException("net")
    with pytest.raises(requests.RequestException):
        entry_creator._request("get", entry_creator.user_api_url)


@pytest.mark.unit
def test_get_user_info_calls_me_and_returns_json(mocker: MagicMock, entry_creator):  # type: ignore[no-redef]
    from src.constants import TOGGL_API_BASE_URL, TOGGL_USER_ENDPOINT

    mock_request = mocker.patch("requests.Session.request")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"user": 1}
    mock_request.return_value = resp

    data = entry_creator.get_user_info()
    assert data == {"user": 1}
    assert mock_request.call_args[0][0] == "get"
    assert mock_request.call_args[0][1] == f"{TOGGL_API_BASE_URL}/{TOGGL_USER_ENDPOINT}"
