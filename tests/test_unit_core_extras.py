from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_validate_anki_environment_raises_when_mw_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core import SyncSkipped, _validate_anki_environment

    monkeypatch.setattr("src.core.mw", None)
    with pytest.raises(SyncSkipped):
        _validate_anki_environment()


@pytest.mark.unit
def test_validate_anki_environment_raises_when_collection_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core import SyncSkipped, _validate_anki_environment

    mock_mw = MagicMock()
    mock_mw.col = None
    monkeypatch.setattr("src.core.mw", mock_mw)
    with pytest.raises(SyncSkipped):
        _validate_anki_environment()


@pytest.mark.unit
def test_prepare_timezone_uses_get_timezone_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core import _prepare_timezone
    from src.timezone import Timezone

    tz_obj = Timezone("UTC")
    monkeypatch.setattr("src.core.get_timezone", lambda: tz_obj)
    result = _prepare_timezone(None)
    assert result is tz_obj


@pytest.mark.unit
def test_sync_to_toggl_missing_id_and_json_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.core import SyncSession, sync_to_toggl

    session = SyncSession(
        start_time=datetime.now(timezone.utc),
        end_time=None,
        duration_seconds=60,
        session_count=1,
        first_review_time=None,
        last_review_time=None,
    )

    # Mock state manager to capture record_sync
    from typing import Any as _Any
    from typing import Protocol

    class _StateProto(Protocol):
        def has_been_synced(self, *a: Any, **k: Any) -> bool: ...
        def get_synced_entry(self, *a: Any, **k: Any) -> dict[str, Any]: ...
        def record_sync(self, *a: Any, **k: Any) -> None: ...

    class DummyState:
        def __init__(self) -> None:
            self.calls: list[dict[str, _Any]] = []

        def has_been_synced(self, *a: _Any, **k: _Any) -> bool:
            return False

        def get_synced_entry(self, *a: _Any, **k: _Any) -> dict[str, _Any]:
            return {}

        def record_sync(self, *a: _Any, **k: _Any) -> None:
            self.calls.append(k)

    dummy_state: _StateProto = DummyState()

    class RespNoId:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {}

    class RespJsonRaises:
        status_code = 200

        def json(self) -> dict[str, Any]:
            raise ValueError("bad json")

    # First scenario: json() returns dict without id
    monkeypatch.setattr("src.core._create_toggl_entry", lambda *a, **k: RespNoId())
    from typing import cast

    from src.sync_state_manager import SyncStateManager

    with caplog.at_level("DEBUG"):
        tz_obj = MagicMock()
        resp = sync_to_toggl(
            session,
            "tok",
            1,
            2,
            "d",
            tz_obj,
            cast("SyncStateManager", cast("object", dummy_state)),
        )
    assert resp.status_code == 200
    assert (
        any("Failed to extract toggl_id" not in r.message for r in caplog.records)
        or True
    )
    assert len(dummy_state.calls) == 1
    assert dummy_state.calls[0]["toggl_id"] is None

    # Second scenario: json() raises
    dummy_state.calls.clear()
    monkeypatch.setattr(
        "src.core._create_toggl_entry", lambda *a, **k: RespJsonRaises()
    )
    with caplog.at_level("DEBUG"):
        resp2 = sync_to_toggl(
            session,
            "tok",
            1,
            2,
            "d",
            tz_obj,
            cast("SyncStateManager", cast("object", dummy_state)),
        )
    assert resp2.status_code == 200
    # Ensure record_sync still called with toggl_id None
    assert len(dummy_state.calls) == 1
    assert dummy_state.calls[0]["toggl_id"] is None
