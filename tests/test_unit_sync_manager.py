from typing import Any

import pytest


@pytest.mark.unit
def test_setup_hooks_registers_on_anki_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.sync_manager import SyncManager

    calls: dict[str, Any] = {"called": False}

    class DummyGuiHooks:
        def __init__(self) -> None:
            self.sync_did_finish: list[Any] = []

    dummy_hooks = DummyGuiHooks()
    sm = SyncManager()

    # Replace gui_hooks with dummy
    monkeypatch.setattr("src.sync_manager.gui_hooks", dummy_hooks)

    # Spy on _perform_sync_if_configured to ensure the bound method works if invoked
    def spy(_event: str) -> None:
        calls["called"] = True

    monkeypatch.setattr(sm, "_perform_sync_if_configured", spy)

    sm.setup_hooks()

    assert len(dummy_hooks.sync_did_finish) == 1
    # Invoke the hook to ensure the bound method is correct
    dummy_hooks.sync_did_finish[0]()
    assert calls["called"] is True


@pytest.mark.unit
def test_perform_sync_if_configured_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.constants import CONFIG_AUTO_SYNC
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: "dummy_mw")

    # Auto-sync disabled
    monkeypatch.setattr(
        "src.sync_manager.get_config", lambda: {CONFIG_AUTO_SYNC: False}
    )
    # Ensure no background thread is created
    created = {"thread": False}

    class DummyThread:
        def __init__(self, target=None, daemon=False) -> None:
            created["thread"] = True
            self.target = target
            self.daemon = daemon

        def start(self) -> None:
            if self.target:
                self.target()

    monkeypatch.setattr("src.sync_manager.threading.Thread", DummyThread)

    sm._perform_sync_if_configured("Test")
    assert created["thread"] is False


@pytest.mark.unit
def test_perform_sync_if_configured_warns_when_not_configured(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.constants import CONFIG_AUTO_SYNC
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: "dummy_mw")

    monkeypatch.setattr("src.sync_manager.get_config", lambda: {CONFIG_AUTO_SYNC: True})
    monkeypatch.setattr("src.sync_manager.is_configured", lambda: False)

    created = {"thread": False}

    class DummyThread:
        def __init__(self, target=None, daemon=False) -> None:
            created["thread"] = True
            self.target = target
            self.daemon = daemon

        def start(self) -> None:
            if self.target:
                self.target()

    monkeypatch.setattr("src.sync_manager.threading.Thread", DummyThread)

    with caplog.at_level("DEBUG"):
        sm._perform_sync_if_configured("Test")

    assert created["thread"] is False
    assert any("Toggl not configured" in r.message for r in caplog.records)


@pytest.mark.unit
def test_perform_sync_if_configured_starts_background_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.constants import CONFIG_AUTO_SYNC
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: "dummy_mw")

    monkeypatch.setattr("src.sync_manager.get_config", lambda: {CONFIG_AUTO_SYNC: True})
    monkeypatch.setattr("src.sync_manager.is_configured", lambda: True)

    called = {"auto": False}
    monkeypatch.setattr(
        sm, "_perform_auto_sync", lambda: called.__setitem__("auto", True)
    )

    class DummyThread:
        def __init__(self, target=None, daemon=False) -> None:
            self.target = target
            self.daemon = daemon

        def start(self) -> None:
            if self.target:
                self.target()

    monkeypatch.setattr("src.sync_manager.threading.Thread", DummyThread)

    sm._perform_sync_if_configured("Test")
    assert called["auto"] is True


@pytest.mark.unit
def test_perform_auto_sync_success(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: "dummy_mw")

    # Provide credentials and timezone
    monkeypatch.setattr(
        "src.sync_manager.get_toggl_credentials",
        lambda: {
            "api_token": "tok",
            "workspace_id": 1,
            "project_id": 2,
            "description": "d",
        },
    )
    monkeypatch.setattr("src.sync_manager.get_timezone", lambda: "UTC")

    class DummyResp:
        status_code = 200
        text = "OK"

    monkeypatch.setattr(
        "src.sync_manager.sync_review_time_to_toggl", lambda *a, **k: DummyResp()
    )

    with caplog.at_level("INFO"):
        sm._perform_auto_sync()

    assert any("Successfully synced review time" in r.message for r in caplog.records)


@pytest.mark.unit
def test_perform_auto_sync_handles_toggl_sync_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.core import TogglSyncError
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: "dummy_mw")

    monkeypatch.setattr(
        "src.sync_manager.get_toggl_credentials",
        lambda: {
            "api_token": "tok",
            "workspace_id": 1,
            "project_id": 2,
            "description": "d",
        },
    )
    monkeypatch.setattr("src.sync_manager.get_timezone", lambda: "UTC")
    monkeypatch.setattr(
        "src.sync_manager.sync_review_time_to_toggl",
        lambda *a, **k: (_ for _ in ()).throw(TogglSyncError(503, "boom")),
    )

    with caplog.at_level("ERROR"):
        sm._perform_auto_sync()

    assert any("Network error during auto-sync" in r.message for r in caplog.records)


@pytest.mark.unit
def test_perform_auto_sync_handles_config_validation_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.config import ConfigValidationError
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: "dummy_mw")

    # Raise during credentials retrieval
    monkeypatch.setattr(
        "src.sync_manager.get_toggl_credentials",
        lambda: (_ for _ in ()).throw(ConfigValidationError("bad config")),
    )

    with caplog.at_level("ERROR"):
        sm._perform_auto_sync()

    assert any("ConfigValidationError" in r.message for r in caplog.records)


@pytest.mark.unit
def test_perform_sync_if_configured_skips_when_mw_unavailable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as NOT available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: None)

    with caplog.at_level("DEBUG"):
        sm._perform_sync_if_configured("Test")

    assert any("Anki main window not available" in r.message for r in caplog.records)


@pytest.mark.unit
def test_perform_auto_sync_aborts_when_mw_unavailable(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from src.sync_manager import SyncManager

    sm = SyncManager()

    # Mock mw as NOT available
    monkeypatch.setattr("src.anki_env.get_mw_or_none", lambda: None)

    with caplog.at_level("DEBUG"):
        sm._perform_auto_sync()

    assert any(
        "Anki main window no longer available" in r.message for r in caplog.records
    )
