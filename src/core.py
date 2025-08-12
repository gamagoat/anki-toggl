from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import requests

from .anki_review_tracker import AnkiReviewTracker
from .config import get_timezone
from .constants import (
    DEFAULT_USER_AGENT,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND,
    HTTP_SERVICE_UNAVAILABLE,
    MS_TO_SECONDS_DIVISOR,
)
from .logger import get_module_logger
from .sync_state_manager import SyncStateManager
from .timezone import Timezone
from .toggl_track_entry_creator import TogglTrackEntryCreator


class TogglSyncError(Exception):
    """Raised when syncing to Toggl fails."""

    def __init__(self, status_code: int, response_text: str):
        super().__init__(
            f"Toggl sync failed with status {status_code}: {response_text}"
        )
        self.status_code: int = status_code
        self.response_text: str = response_text


@dataclass
class SyncSession:
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: int
    session_count: int
    first_review_time: Optional[datetime]
    last_review_time: Optional[datetime]
    # Add more fields as needed for future extensibility


# NOTE: Avoid importing `aqt` at module import time so tests remain headless.
# Tests patch this symbol directly (e.g., `monkeypatch.setattr("src.core.mw", ...)`).
mw: Optional[Any] = None


def get_review_session(mw: Any, timezone: Timezone) -> SyncSession:
    """
    Extract and validate review session data from Anki.
    Raises SyncSkipped if session should not be synced.
    """
    # Extract session data from Anki
    review_tracker = AnkiReviewTracker(mw)
    session_info = review_tracker.get_todays_review_session_info()

    review_time_ms = session_info["total_duration_ms"]
    duration_seconds = review_time_ms // MS_TO_SECONDS_DIVISOR
    session_count = session_info["session_count"]
    first_review_time = session_info["first_review_time"]
    last_review_time = session_info["last_review_time"]

    # Determine start_time and end_time
    if first_review_time is not None:
        start_time = first_review_time.astimezone(timezone.zone_info)
    else:
        start_time = datetime.now(timezone.zone_info)

    end_time = last_review_time

    session = SyncSession(
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration_seconds,
        session_count=session_count,
        first_review_time=first_review_time,
        last_review_time=last_review_time,
    )
    logger = get_module_logger("core.get_review_session")
    logger.debug(
        f"Session summary: duration_s={duration_seconds}, count={session_count}, "
        f"first={first_review_time}, last={last_review_time}, start={start_time}, end={end_time}"
    )
    return session


class SyncSkipped(Exception):
    """Raised when a sync should be skipped (e.g., zero duration, duplicate)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason: str = reason


def validate_session(
    session: SyncSession,
    sync_state_manager: SyncStateManager,
    workspace_id: int,
    project_id: int,
    description: str,
) -> None:
    """
    Check if the session should be synced. Raise SyncSkipped if not.
    """
    if session.duration_seconds == 0:
        raise SyncSkipped("No review time logged for today in Anki.")


def _create_toggl_entry(
    toggl_creator: "TogglTrackEntryCreator",
    session: SyncSession,
) -> requests.Response:
    return toggl_creator.create_entry(session.start_time, session.duration_seconds)


def _update_toggl_entry(
    toggl_creator: "TogglTrackEntryCreator",
    toggl_id: int,
    session: SyncSession,
    update_start_time: datetime,
) -> requests.Response:
    return toggl_creator.update_entry(
        toggl_id, session.duration_seconds, update_start_time
    )


def sync_to_toggl(
    session: SyncSession,
    api_token: str,
    workspace_id: int,
    project_id: int,
    description: str,
    timezone: Timezone,
    sync_state_manager: SyncStateManager,
) -> "requests.Response":
    """
    Sync session data to Toggl, handling create/update and state management.
    """
    logger = get_module_logger("core.sync_to_toggl")
    toggl_creator = TogglTrackEntryCreator(
        api_token, workspace_id, project_id, description, DEFAULT_USER_AGENT, timezone
    )
    target_date = session.start_time.date()
    has_been_synced = sync_state_manager.has_been_synced(
        target_date, workspace_id, project_id, description
    )
    logger.debug(
        f"has_been_synced={has_been_synced} for {target_date} ({workspace_id}/{project_id}/{description})"
    )
    update_start_time = session.start_time
    action = None
    toggl_id: Optional[int] = None
    response = None

    if has_been_synced:
        existing_entry = sync_state_manager.get_synced_entry(
            target_date, workspace_id, project_id, description
        )
        if existing_entry:
            toggl_id = existing_entry.get("toggl_id")
            previous_start_time = existing_entry.get("start_time")
            if previous_start_time and isinstance(previous_start_time, str):
                try:
                    update_start_time = datetime.fromisoformat(previous_start_time)
                except ValueError:
                    pass
            if toggl_id is not None and isinstance(toggl_id, int):
                try:
                    response = _update_toggl_entry(
                        toggl_creator, toggl_id, session, update_start_time
                    )
                    action = "update"
                except requests.HTTPError as e:
                    status_code = getattr(
                        getattr(e, "response", None), "status_code", None
                    )
                    is_not_found = status_code == HTTP_NOT_FOUND or (
                        status_code is None
                        and ("404" in str(e) or "Not Found" in str(e))
                    )
                    if is_not_found:
                        sync_state_manager.clear_stale_entry(
                            target_date, workspace_id, project_id, description
                        )
                        response = _create_toggl_entry(toggl_creator, session)
                        action = "create"
                    else:
                        raise
            else:
                # No toggl_id recorded locally; attempt to find existing entry on Toggl
                try:
                    found = toggl_creator.find_existing_entry(target_date)
                except Exception:
                    found = None
                if found:
                    found_id = found.get("id")
                    if isinstance(found_id, str):
                        try:
                            found_id = int(found_id)
                        except Exception:
                            found_id = None
                    if isinstance(found_id, int):
                        toggl_id = found_id
                        logger.debug(
                            f"Performing update for toggl_id={found_id} starting {update_start_time}"
                        )
                        response = _update_toggl_entry(
                            toggl_creator, found_id, session, update_start_time
                        )
                        action = "update"
                    else:
                        logger.debug("No suitable existing entry ID; performing create")
                        response = _create_toggl_entry(toggl_creator, session)
                        action = "create"
                else:
                    logger.debug("No existing entry stored locally; performing create")
                    response = _create_toggl_entry(toggl_creator, session)
                    action = "create"
        else:
            logger.debug("No prior sync recorded; performing create")
            response = _create_toggl_entry(toggl_creator, session)
            action = "create"
    else:
        logger.debug("First sync for date; performing create")
        response = _create_toggl_entry(toggl_creator, session)
        action = "create"

    if response and hasattr(response, "json"):
        try:
            extracted_id = response.json().get("id")
            if isinstance(extracted_id, int):
                toggl_id = extracted_id
        except Exception as e:
            logger.debug(f"Failed to extract toggl_id from response: {e}")
    sync_state_manager.record_sync(
        target_date,
        workspace_id,
        project_id,
        description,
        start_time=session.start_time,
        duration_seconds=session.duration_seconds,
        toggl_id=toggl_id,
        action=action,
    )
    logger.debug(
        f"Sync action result: action={action}, toggl_id={toggl_id}, status={getattr(response, 'status_code', 'N/A')}"
    )
    return response


def _validate_anki_environment() -> None:
    """Validate that Anki environment is ready for sync operations."""
    logger = get_module_logger("core._validate_anki_environment")
    if mw is None:
        logger.info(
            "Anki main window not available - skipping sync until Anki is ready"
        )
        raise SyncSkipped("Anki main window not available")

    if mw.col is None:
        logger.info(
            "No Anki collection loaded - skipping sync until a collection is opened"
        )
        raise SyncSkipped("No Anki collection loaded")


def _prepare_timezone(timezone: Optional[Timezone]) -> Timezone:
    """Prepare timezone for sync operation."""
    logger = get_module_logger("core._prepare_timezone")
    if timezone is None:
        timezone = get_timezone()
    logger.debug(f"Using timezone: {timezone.name}")
    return timezone


def _perform_sync_operation(
    api_token: str,
    workspace_id: int,
    project_id: int,
    description: str,
    timezone: Timezone,
) -> requests.Response:
    """Perform the core sync operation."""
    logger = get_module_logger("core._perform_sync_operation")
    session = get_review_session(mw, timezone)
    sync_state_manager = SyncStateManager()
    validate_session(session, sync_state_manager, workspace_id, project_id, description)
    response = sync_to_toggl(
        session,
        api_token,
        workspace_id,
        project_id,
        description,
        timezone,
        sync_state_manager,
    )
    logger.info("Successfully synced review time to Toggl!")
    return response


def sync_review_time_to_toggl(
    api_token: str,
    workspace_id: int,
    project_id: int,
    description: str,
    timezone: Optional[Timezone] = None,
) -> Optional[requests.Response]:
    """
    Sync today's review time to Toggl Track.

    Args:
        api_token: Toggl API token
        workspace_id: Toggl workspace ID
        project_id: Toggl project ID
        description: Description for the time entry
        timezone: Timezone to use (defaults to config timezone)

    Returns:
        Response object on success, None if skipped

    Raises:
        TogglSyncError: On sync failures
    """
    logger = get_module_logger("core")
    logger.info("sync_review_time_to_toggl called")
    logger.debug(f"mw is None: {mw is None}")
    logger.debug(f"mw.col is None: {mw.col is None if mw else 'N/A'}")

    try:
        _validate_anki_environment()
        timezone = _prepare_timezone(timezone)
        response = _perform_sync_operation(
            api_token, workspace_id, project_id, description, timezone
        )
        # If Toggl API reported an error (4xx/5xx), convert to TogglSyncError
        if response is not None and hasattr(response, "status_code"):
            if getattr(response, "status_code", 200) >= 400:
                raise TogglSyncError(
                    getattr(response, "status_code", HTTP_BAD_REQUEST),
                    getattr(response, "text", ""),
                )
        return response
    except SyncSkipped as e:
        logger.info(f"Sync skipped: {e.reason}")
        return None
    except (AttributeError, ValueError, TypeError) as e:
        logger.error("Invalid input or state during sync: %s", str(e), exc_info=True)
        raise TogglSyncError(HTTP_BAD_REQUEST, f"Invalid input: {e!s}")
    except requests.RequestException as e:
        logger.error("Network error during sync: %s", str(e), exc_info=True)
        raise TogglSyncError(HTTP_SERVICE_UNAVAILABLE, f"Network error: {e!s}")
    except Exception as e:
        logger.error("Unexpected error during sync: %s", str(e), exc_info=True)
        raise
