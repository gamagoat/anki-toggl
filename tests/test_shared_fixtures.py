"""
Additional shared fixtures for consolidating duplicate mock classes.

This module provides parameterized and specialized fixtures to reduce duplication
across test files.
"""

from datetime import date, datetime
from typing import Any, Callable, Optional, Union

import pytest
import requests

from src.constants import HTTP_BAD_REQUEST, HTTP_OK
from tests.test_constants import (
    MOCK_RESPONSE_ERROR_TEXT,
    MOCK_RESPONSE_NOT_FOUND_TEXT,
    MOCK_RESPONSE_OK_TEXT,
    TEST_ENTRY_ID,
    TEST_RESPONSE_ID,
)


@pytest.fixture(params=["success", "error", "not_found"])
def mock_response_parameterized(request: Any) -> type[Any]:
    """Create a parameterized mock response class for different scenarios."""
    scenario = request.param

    class MockResponse:
        def __init__(
            self,
            status_code: Optional[int] = None,
            json_data: Optional[dict[str, Any]] = None,
        ):
            if scenario == "success":
                self.status_code = status_code or HTTP_OK
                self.text = MOCK_RESPONSE_OK_TEXT
                self._json_data = json_data or {"id": TEST_RESPONSE_ID}
            elif scenario == "error":
                self.status_code = status_code or HTTP_BAD_REQUEST
                self.text = MOCK_RESPONSE_ERROR_TEXT
                self._json_data = json_data or {}
            elif scenario == "not_found":
                self.status_code = status_code or 404
                self.text = MOCK_RESPONSE_NOT_FOUND_TEXT
                self._json_data = json_data or {}

        def json(self) -> dict[str, Any]:
            return self._json_data

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(
                    f"{self.status_code} Client Error: {self.text}"
                )

    return MockResponse


@pytest.fixture
def mock_toggl_creator_with_tracking_calls() -> type[Any]:
    """Create a mock TogglTrackEntryCreator that tracks API calls."""

    class MockTogglCreatorWithCalls:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.api_calls: list[tuple[Any, ...]] = []

        def create_entry(
            self,
            start_time: datetime,
            duration: int,
            timezone_str: Union[str, None] = None,
        ) -> Any:
            self.api_calls.append(("create", duration))

            class MockResponse:
                status_code = HTTP_OK
                text = MOCK_RESPONSE_OK_TEXT

                def json(self) -> dict[str, int]:
                    return {"id": TEST_ENTRY_ID}

            return MockResponse()

        def update_entry(
            self,
            entry_id: int,
            duration: int,
            start_time: datetime,
            timezone_str: Union[str, None] = None,
        ) -> Any:
            self.api_calls.append(("update", entry_id, duration))

            class MockResponse:
                status_code = HTTP_OK
                text = MOCK_RESPONSE_OK_TEXT

                def json(self) -> dict[str, int]:
                    return {"id": entry_id}

            return MockResponse()

        def find_existing_entry(self, target_date: Optional[date] = None) -> None:
            self.api_calls.append(("find_existing_entry_called", "unexpected"))
            return None

    return MockTogglCreatorWithCalls


@pytest.fixture
def mock_response_factory() -> Callable[[int, Optional[dict[str, Any]]], type[Any]]:
    """Factory fixture for creating mock responses with custom status codes and data."""

    def create_response(
        status_code: int = HTTP_OK, json_data: Optional[dict[str, Any]] = None
    ) -> type[Any]:
        class MockResponse:
            def __init__(self):
                self.status_code = status_code
                self.text = (
                    MOCK_RESPONSE_OK_TEXT
                    if status_code == HTTP_OK
                    else (
                        MOCK_RESPONSE_ERROR_TEXT
                        if status_code == HTTP_BAD_REQUEST
                        else (
                            MOCK_RESPONSE_NOT_FOUND_TEXT
                            if status_code == 404
                            else "Unknown Status"
                        )
                    )
                )
                self._json_data = json_data or {"id": TEST_RESPONSE_ID}

            def json(self) -> dict[str, Any]:
                return self._json_data

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(
                        f"{self.status_code} Client Error: {self.text}"
                    )

        return MockResponse

    return create_response


@pytest.fixture
def mock_api_call_tracker() -> Callable[[], list[tuple[str, ...]]]:
    """Factory for creating API call trackers for testing."""

    def create_tracker() -> list[tuple[str, ...]]:
        return []

    return create_tracker


@pytest.fixture
def mock_toggl_creator_with_custom_behavior() -> Callable[
    [list[tuple[Any, ...]]], type[Any]
]:
    """Factory for creating TogglTrackEntryCreator mocks with custom behavior."""

    def create_mock(api_calls: list[tuple[Any, ...]]) -> type[Any]:
        class MockTogglCreatorCustom:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def create_entry(
                self,
                start_time: datetime,
                duration: int,
                timezone_str: Union[str, None] = None,
            ) -> Any:
                api_calls.append(("create", duration))

                class MockResponse:
                    status_code = HTTP_OK
                    text = MOCK_RESPONSE_OK_TEXT

                    def json(self) -> dict[str, int]:
                        return {"id": TEST_ENTRY_ID}

                return MockResponse()

            def update_entry(
                self,
                entry_id: int,
                duration: int,
                start_time: datetime,
                timezone_str: Union[str, None] = None,
            ) -> Any:
                api_calls.append(("update", entry_id, duration))

                class MockResponse:
                    status_code = HTTP_OK
                    text = MOCK_RESPONSE_OK_TEXT

                    def json(self) -> dict[str, int]:
                        return {"id": entry_id}

                return MockResponse()

            def find_existing_entry(self, target_date: Optional[date] = None) -> None:
                api_calls.append(("find_existing_entry_called", "unexpected"))
                return None

        return MockTogglCreatorCustom

    return create_mock
