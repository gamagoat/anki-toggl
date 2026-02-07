"""
Anki Toggl Add-on

Automatically syncs your Anki review time to Toggl Track.
"""
from __future__ import annotations

import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

import logging
from typing import Any

from .anki_env import get_mw_or_none, require_mw, show_tooltip
from .config import get_timezone, get_toggl_credentials, is_configured
from .core import TogglSyncError, sync_review_time_to_toggl
from .logger import get_module_logger
from .sync_manager import setup_auto_sync

logger: logging.Logger = get_module_logger("main")


def _show_sync_failed_tooltip(parent: Any) -> None:
    show_tooltip("Sync failed - check logs for details", parent=parent)


def setup_submenu() -> None:
    try:
        mw = require_mw()
        logger.info("Setting up AnkiToggl submenu")

        anki_toggl_submenu = mw.form.menuTools.addMenu("AnkiToggl")

        if anki_toggl_submenu:
            settings_action = anki_toggl_submenu.addAction("Settings")
            if settings_action:
                settings_action.triggered.connect(open_config_dialog)
            logger.debug("Settings action created in AnkiToggl submenu")

            sync_action = anki_toggl_submenu.addAction("Sync to Toggl Now")
            if sync_action:
                sync_action.triggered.connect(sync_to_toggl)
            logger.debug("Sync action created in AnkiToggl submenu")

        logger.info("AnkiToggl submenu added to Tools menu successfully")

    except Exception as e:
        logger.error(f"Error setting up menu: {e}")


def sync_to_toggl() -> None:
    """Sync today's review time to Toggl."""
    logger.info("User initiated sync to Toggl")

    try:
        mw = require_mw()
        if not is_configured():
            logger.warning("Add-on not configured. Opening configuration dialog.")
            if open_config_dialog():
                sync_to_toggl()
            return
        timezone = get_timezone()
        logger.debug(f"Manual sync: Using timezone: {timezone.name}")
        credentials = get_toggl_credentials()
        if credentials is None:
            logger.error("Failed to get Toggl credentials")
            show_tooltip("Failed to get Toggl credentials", parent=mw)
            return
        from typing import cast

        config = credentials
        api_token = cast("str", config["api_token"])
        workspace_id = cast("int", config["workspace_id"])
        project_id = cast("int", config["project_id"])
        description = cast("str", config["description"])
        response = sync_review_time_to_toggl(
            api_token,
            workspace_id,
            project_id,
            description,
            timezone,
        )
        logger.debug(f"Response received: {response}")
        logger.debug(f"Response type: {type(response)}")
        if (
            response is not None
            and hasattr(response, "status_code")
            and response.status_code == 200
        ):
            if hasattr(response, "skipped") and getattr(response, "skipped", False):
                logger.info(
                    f"Sync skipped: {getattr(response, 'reason', 'Unknown reason')}"
                )
            else:
                logger.info("Sync completed successfully")
                show_tooltip("Successfully synced review time to Toggl", parent=mw)
        else:
            logger.warning(
                "Sync to Toggl was not successful. No response object was returned or status was not 200"
            )
            _show_sync_failed_tooltip(mw)
    except TogglSyncError as e:
        logger.error(f"TogglSyncError: {e}")
        _show_sync_failed_tooltip(get_mw_or_none())
    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}", exc_info=True)
        _show_sync_failed_tooltip(get_mw_or_none())


def open_config_dialog() -> bool:
    """Open the configuration dialog."""
    try:
        from .config_dialog import open_config_dialog

        mw = require_mw()
        logger.info("User opened configuration dialog")
        result = open_config_dialog(parent=mw)
        if result:
            logger.info("Configuration saved successfully")

        return bool(result)
    except Exception as e:
        logger.error(f"Error opening configuration dialog: {e}")
        return False


def update_config_field(field: str, value: str) -> bool:
    """
    Update a specific configuration field.

    Args:
        field: The field name to update
        value: The new value

    Returns:
        True if successful, False otherwise
    """
    from .config import get_config, save_config

    config = get_config()
    config[field] = value
    return save_config(config)


# Initialize the add-on when Anki loads
try:
    mw = get_mw_or_none()
    # Propagate mw into config module to avoid importing aqt there
    try:
        from . import config as _config_mod

        _config_mod.mw = mw  # type: ignore
    except Exception as e:
        logger.debug(f"Unable to propagate mw to config module: {e}")
    try:
        from . import core as _core_mod

        _core_mod.mw = mw  # type: ignore
    except Exception as e:
        logger.debug(f"Unable to propagate mw to core module: {e}")
    if mw is not None and hasattr(mw, "addonManager"):
        logger.info("Initializing Anki Toggl add-on")
        mw.addonManager.setWebExports(__name__, r"web/.*")
    else:
        logger.warning("Could not initialize add-on - mw or addonManager not available")
except Exception as e:
    logger.error(f"Error during add-on initialization: {e}", exc_info=True)

# Set up hooks - use only profile_did_open to avoid duplicates
try:
    from aqt import gui_hooks

    def on_profile_loaded() -> None:
        """Called when Anki profile is loaded."""
        try:
            logger.info("Profile loaded, setting up add-on")
            # Now that Anki is ready, propagate mw into modules that rely on it
            mw_ready = require_mw()
            try:
                from . import config as _config_mod

                _config_mod.mw = mw_ready  # type: ignore
            except Exception as e:
                logger.debug(f"Unable to propagate mw to config module after load: {e}")
            try:
                from . import core as _core_mod

                _core_mod.mw = mw_ready  # type: ignore
            except Exception as e:
                logger.debug(f"Unable to propagate mw to core module after load: {e}")
            setup_submenu()
            setup_auto_sync()
        except Exception as e:
            logger.error(f"Error in on_profile_loaded: {e}", exc_info=True)

    gui_hooks.profile_did_open.append(on_profile_loaded)
    logger.info("Hooks registered successfully")
except Exception as e:  # pragma: no cover - headless test environment
    logger.error(f"Error registering hooks: {e}", exc_info=True)

logger.info("Add-on initialization complete")
