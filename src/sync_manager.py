"""Auto-sync orchestration for Toggl updates on Anki sync events."""

import threading
from typing import Any, ClassVar, Optional

try:
    # Import only when available (inside Anki). Tests patch this symbol directly.
    from aqt import gui_hooks  # type: ignore
except Exception:  # pragma: no cover - headless test environment

    class _DummyHooks:  # minimal surface for tests to monkeypatch
        sync_did_finish: ClassVar[list[Any]] = []

    gui_hooks = _DummyHooks()  # type: ignore

from .config import (
    ConfigValidationError,
    get_config,
    get_timezone,
    get_toggl_credentials,
    is_configured,
)
from .constants import CONFIG_AUTO_SYNC
from .core import TogglSyncError, sync_review_time_to_toggl
from .logger import get_module_logger


class SyncManager:
    """Manages automatic synchronization to Toggl on Anki sync events."""

    def __init__(self) -> None:
        self.logger: Any = get_module_logger("sync_manager")
        self._setup_complete: bool = False

    def setup_hooks(self) -> None:
        """Set up hooks for auto-sync functionality."""
        try:
            # Register for sync completion events (when user clicks Anki sync button)
            gui_hooks.sync_did_finish.append(self.on_anki_sync)

            self._setup_complete = True
            self.logger.info("Auto-sync hooks registered successfully")
        except Exception as e:
            self.logger.error(
                "Unexpected error registering auto-sync hooks: %s",
                str(e),
                exc_info=True,
            )

    def on_anki_sync(self) -> None:
        """Called when Anki sync is performed."""
        try:
            self.logger.debug("Anki sync detected")
            self._perform_sync_if_configured("Anki sync")
        except Exception as e:
            self.logger.error(
                "Unexpected error in on_anki_sync: %s", str(e), exc_info=True
            )

    def _perform_sync_if_configured(self, trigger_event: str) -> None:
        """
        Perform sync if configured and enabled.

        Args:
            trigger_event: Description of what triggered the sync (for logging)
        """
        try:
            # Import here to check if mw is available
            from .anki_env import get_mw_or_none

            # Skip auto-sync if Anki main window is not available
            if get_mw_or_none() is None:
                self.logger.debug(
                    f"Anki main window not available, skipping auto-sync for {trigger_event}"
                )
                return

            # Check if auto-sync is enabled
            config = get_config()
            if not config.get(CONFIG_AUTO_SYNC, False):
                self.logger.debug(f"Auto-sync is disabled for {trigger_event}")
                return

            # Check if configured
            if not is_configured():
                self.logger.debug(
                    f"Toggl not configured, skipping auto-sync for {trigger_event}"
                )
                return

            # Run sync in background to avoid blocking UI
            threading.Thread(target=self._perform_auto_sync, daemon=True).start()
        except Exception as e:
            self.logger.debug(f"Auto-sync skipped for {trigger_event} due to: {e}")

    def _perform_auto_sync(self) -> None:
        """Perform the actual auto-sync in a background thread."""
        self.logger.debug("Starting auto-sync...")
        try:
            # Double-check that mw is still available in background thread
            from .anki_env import get_mw_or_none

            if get_mw_or_none() is None:
                self.logger.debug(
                    "Auto-sync: Anki main window no longer available, aborting"
                )
                return

            credentials = get_toggl_credentials()
            if not credentials:
                self.logger.debug("Auto-sync: Failed to get credentials, skipping")
                return

            timezone = get_timezone()
            from typing import cast

            api_token = cast("str", credentials["api_token"])
            workspace_id = cast("int", credentials["workspace_id"])
            project_id = cast("int", credentials["project_id"])
            description = cast("str", credentials["description"])
            tz_name = getattr(timezone, "name", str(timezone))
            self.logger.debug(
                f"Auto-sync params: workspace_id={workspace_id}, project_id={project_id}, description='{description}', timezone={tz_name}"
            )
            response = sync_review_time_to_toggl(
                api_token,
                workspace_id,
                project_id,
                description,
                timezone,
            )
            if response is None:
                self.logger.info(
                    "Auto-sync: Skipped sync (no review time, duplicate, or config issue)"
                )
                return
            if hasattr(response, "status_code") and response.status_code == 200:
                self.logger.info("Auto-sync: Successfully synced review time to Toggl")
            else:
                self.logger.warning(
                    f"Auto-sync: Sync completed but got unexpected response: {response}"
                )
            if hasattr(response, "status_code"):
                self.logger.debug(f"Auto-sync response status: {response.status_code}")
        except TogglSyncError as e:
            self.logger.error(
                "Network error during auto-sync: %s", str(e), exc_info=True
            )
        except ConfigValidationError as e:
            self.logger.error(f"Auto-sync: ConfigValidationError: {e}")
        except Exception as e:
            self.logger.error(
                "Unexpected error during auto-sync: %s", str(e), exc_info=True
            )


# Global sync manager instance
_sync_manager: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    """Get the global sync manager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager


def setup_auto_sync() -> None:
    """Set up auto-sync functionality."""
    sync_manager = get_sync_manager()
    if sync_manager is not None:
        sync_manager.setup_hooks()
