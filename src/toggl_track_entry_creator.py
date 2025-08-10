from base64 import b64encode
from datetime import date, datetime
from typing import Any, Optional, Union

import requests

from .config import get_timezone
from .constants import (
    REQUEST_CONNECT_TIMEOUT_S,
    REQUEST_READ_TIMEOUT_S,
    TOGGL_API_BASE_URL,
    TOGGL_USER_ENDPOINT,
    USER_AGENT_TEMPLATE,
)
from .logger import get_module_logger
from .manifest_utils import get_addon_name_and_version
from .timezone import Timezone


class TogglTrackEntryCreator:
    """Unified Toggl Track API client and entry creator."""

    def __init__(
        self,
        api_token: str,
        workspace_id: int,
        project_id: int,
        description: str,
        created_with: str = "AnkiToggl",
        timezone: Optional[Union[Timezone, str]] = None,
    ):
        self.api_token: str = api_token
        self.workspace_id: int = workspace_id
        self.project_id: int = project_id
        self.description: str = description
        self.created_with: str = created_with
        self.base_url: str = (
            f"{TOGGL_API_BASE_URL}/workspaces/{workspace_id}/time_entries"
        )
        self.user_api_url: str = f"{TOGGL_API_BASE_URL}/{TOGGL_USER_ENDPOINT}"
        self.session: requests.Session = requests.Session()
        if timezone is None:
            self.timezone = get_timezone()
        elif isinstance(timezone, str):
            self.timezone = Timezone(timezone)
        else:
            self.timezone: Timezone = timezone
        self.logger: Any = get_module_logger("toggl_track_entry_creator")
        self.logger.debug(
            f"TogglTrackEntryCreator initialized for workspace {workspace_id}, project {project_id}, timezone {self.timezone.name}"
        )

    def close(self) -> None:
        self.session.close()

    def _headers(self) -> dict[str, str]:
        token = b64encode(f"{self.api_token}:api_token".encode()).decode("utf-8")
        name, version = get_addon_name_and_version()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT_TEMPLATE.format(name=name, version=version),
        }

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        headers = kwargs.pop("headers", None) or self._headers()
        timeout = kwargs.pop(
            "timeout", (REQUEST_CONNECT_TIMEOUT_S, REQUEST_READ_TIMEOUT_S)
        )
        try:
            self.logger.debug(f"{method.upper()} {url}")
            response = self.session.request(
                method, url, headers=headers, timeout=timeout, **kwargs
            )
            self.logger.debug(f"Response status: {response.status_code}")
            if response.status_code >= 400:
                self.logger.error(
                    f"Toggl API error: {response.status_code} - {response.text}"
                )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(
                "Network error during Toggl API call: %s", str(e), exc_info=e
            )
            raise

    def get_user_info(self) -> dict[str, Any]:
        response = self._request("get", self.user_api_url)
        return response.json()

    def create_time_entry(self, entry_data: dict[str, Any]) -> requests.Response:
        self.logger.debug(f"Creating time entry with data: {entry_data}")
        return self._request("post", self.base_url, json=entry_data)

    def update_time_entry(
        self, entry_id: int, entry_data: dict[str, Any]
    ) -> requests.Response:
        update_url = f"{self.base_url}/{entry_id}"
        self.logger.debug(f"Updating time entry {entry_id} with data: {entry_data}")
        return self._request("put", update_url, json=entry_data)

    def get_time_entries_for_date(self, target_date: date) -> list[dict[str, Any]]:
        date_str = target_date.isoformat()
        params = {"start_date": date_str, "end_date": date_str}
        self.logger.debug(f"Fetching time entries for date: {date_str}")
        response = self._request("get", self.base_url, params=params)
        if response.status_code == 200:
            entries = response.json()
            self.logger.debug(f"Found {len(entries)} entries for {date_str}")
            return entries
        else:
            self.logger.error(
                f"Failed to fetch entries: {response.status_code} - {response.text}"
            )
            return []

    def _build_entry_data(self, start_time: datetime, duration: int) -> dict[str, Any]:
        return {
            "start": start_time.isoformat(),
            "duration": duration,
            "description": self.description,
            "project_id": self.project_id,
            "created_with": self.created_with,
            "workspace_id": self.workspace_id,
        }

    def create_entry(self, start_time: datetime, duration: int) -> requests.Response:
        self.logger.info(
            f"Creating Toggl entry: duration={duration}s, description='{self.description}'"
        )
        aware_start = self.timezone.make_aware(start_time)
        self.logger.debug(
            f"Using timezone: {self.timezone.name} for start_time: {aware_start}"
        )
        data = self._build_entry_data(aware_start, duration)
        return self.create_time_entry(data)

    def find_existing_entry(
        self, target_date: Optional[date] = None
    ) -> Optional[dict[str, Any]]:
        if target_date is None:
            target_date = date.today()
        entries = self.get_time_entries_for_date(target_date)
        for entry in entries:
            entry_project_id = entry.get("project_id")
            entry_description = entry.get("description")
            self.logger.debug(
                f"Checking entry {entry.get('id')}: project_id={entry_project_id}, description='{entry_description}'"
            )
            if (
                entry_project_id == self.project_id
                and entry_description == self.description
            ):
                self.logger.info(
                    f"Found existing entry: {entry['id']} with duration {entry.get('duration', 0)}s, start: {entry.get('start', 'N/A')}"
                )
                return entry
        self.logger.info(
            f"No existing entry found for project_id={self.project_id}, description='{self.description}' on {target_date or date.today()}"
        )
        return None

    def update_entry(
        self, entry_id: int, duration: int, start_time: datetime
    ) -> requests.Response:
        self.logger.info(
            f"Updating existing Toggl entry {entry_id}: duration={duration}s"
        )
        aware_start = self.timezone.make_aware(start_time)
        data = self._build_entry_data(aware_start, duration)
        return self.update_time_entry(entry_id, data)

    def create_or_update_entry(
        self, start_time: datetime, duration: int
    ) -> requests.Response:
        existing_entry = self.find_existing_entry()
        if existing_entry:
            entry_id = existing_entry["id"]
            if not isinstance(entry_id, int) and isinstance(entry_id, str):
                try:
                    entry_id = int(entry_id)
                except Exception as e:
                    self.logger.error(f"Failed to convert entry_id to int: {e}")
                    raise ValueError(f"Invalid entry id: {entry_id}")
            self.logger.info(
                f"Found existing entry {entry_id}, updating instead of creating new one"
            )
            return self.update_entry(entry_id, duration, start_time)
        else:
            self.logger.info("No existing entry found, creating new one")
            return self.create_entry(start_time, duration)
