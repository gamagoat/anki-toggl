"""Timezone helpers: validation and conversion utilities."""

import datetime
from zoneinfo import ZoneInfo


class TimezoneError(Exception):
    """Raised when timezone operations fail."""

    pass


class Timezone:
    """Handles timezone validation and ZoneInfo creation."""

    def __init__(self, timezone_str: str):
        """
        Initialize with a timezone string.

        Args:
            timezone_str: IANA timezone name (e.g., "America/New_York")

        Raises:
            TimezoneError: If timezone string is invalid
        """
        self._timezone_str: str = timezone_str
        self._zone_info: ZoneInfo = self._validate_and_create_zoneinfo(timezone_str)

    def _validate_and_create_zoneinfo(self, timezone_str: str) -> ZoneInfo:
        """
        Validate timezone string and create ZoneInfo object.

        Args:
            timezone_str: Timezone string to validate

        Returns:
            ZoneInfo object

        Raises:
            TimezoneError: If timezone is invalid
        """
        try:
            return ZoneInfo(timezone_str)
        except (ValueError, KeyError) as e:
            raise TimezoneError(f"Invalid timezone '{timezone_str}': {e}")

    @property
    def zone_info(self) -> ZoneInfo:
        """Get the ZoneInfo object."""
        return self._zone_info

    @property
    def name(self) -> str:
        """Get the timezone name."""
        return self._timezone_str

    def make_aware(self, dt: datetime.datetime) -> datetime.datetime:
        """
        Make a datetime object timezone-aware using this timezone.

        Args:
            dt: datetime object (naive or aware)

        Returns:
            Timezone-aware datetime object
        """
        if dt.tzinfo is not None:
            return dt
        return dt.replace(tzinfo=self._zone_info)

    def __str__(self) -> str:
        """String representation."""
        return self._timezone_str

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Timezone('{self._timezone_str}')"


def validate_timezone_string(timezone_str: str) -> bool:
    """
    Validate that a timezone string is valid.

    Args:
        timezone_str: Timezone name to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        ZoneInfo(timezone_str)
        return True
    except (ValueError, KeyError):
        return False


def get_common_timezones() -> list[str]:
    """Get a list of common timezones for UI selection."""
    return [
        "UTC",
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Asia/Seoul",
        "Asia/Kolkata",
        "Australia/Sydney",
        "Australia/Melbourne",
    ]
