from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_sync_to_toggl_success_uses_show_tooltip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.__init__ as init_mod

    # Arrange
    monkeypatch.setattr(init_mod, "require_mw", lambda: MagicMock())
    monkeypatch.setattr(init_mod, "is_configured", lambda: True)
    monkeypatch.setattr(
        init_mod,
        "get_toggl_credentials",
        lambda: {
            "api_token": "tok",
            "workspace_id": 1,
            "project_id": 2,
            "description": "desc",
        },
    )

    class DummyResponse:
        status_code = 200
        text = "OK"

    monkeypatch.setattr(init_mod, "get_timezone", lambda: MagicMock(name="UTC"))
    monkeypatch.setattr(
        init_mod, "sync_review_time_to_toggl", lambda *a, **k: DummyResponse()
    )

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_show_tooltip(message: str, parent: Any = None) -> None:
        calls.append(((message,), {"parent": parent}))

    monkeypatch.setattr(init_mod, "show_tooltip", fake_show_tooltip)

    # Act
    init_mod.sync_to_toggl()

    # Assert
    assert any(
        "Successfully synced review time to Toggl" in args[0] for (args, _) in calls
    )


@pytest.mark.unit
def test_sync_to_toggl_failure_uses_show_tooltip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.__init__ as init_mod
    from src.core import TogglSyncError

    # Arrange
    monkeypatch.setattr(init_mod, "require_mw", lambda: MagicMock())
    monkeypatch.setattr(init_mod, "is_configured", lambda: True)
    monkeypatch.setattr(
        init_mod,
        "get_toggl_credentials",
        lambda: {
            "api_token": "tok",
            "workspace_id": 1,
            "project_id": 2,
            "description": "desc",
        },
    )
    monkeypatch.setattr(init_mod, "get_timezone", lambda: MagicMock(name="UTC"))

    def raise_sync_error(*a: Any, **k: Any) -> None:
        raise TogglSyncError(500, "server boom")

    monkeypatch.setattr(init_mod, "sync_review_time_to_toggl", raise_sync_error)

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_show_tooltip(message: str, parent: Any = None) -> None:
        calls.append(((message,), {"parent": parent}))

    monkeypatch.setattr(init_mod, "show_tooltip", fake_show_tooltip)

    # Act
    init_mod.sync_to_toggl()

    # Assert
    assert any("Sync failed" in args[0] for (args, _) in calls)


@pytest.mark.unit
def test_sync_to_toggl_missing_credentials_uses_show_tooltip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.__init__ as init_mod

    # Arrange
    monkeypatch.setattr(init_mod, "require_mw", lambda: MagicMock())
    monkeypatch.setattr(init_mod, "is_configured", lambda: True)
    monkeypatch.setattr(init_mod, "get_toggl_credentials", lambda: None)

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_show_tooltip(message: str, parent: Any = None) -> None:
        calls.append(((message,), {"parent": parent}))

    monkeypatch.setattr(init_mod, "show_tooltip", fake_show_tooltip)

    # Act
    init_mod.sync_to_toggl()

    # Assert
    assert any("Failed to get Toggl credentials" in args[0] for (args, _) in calls)
