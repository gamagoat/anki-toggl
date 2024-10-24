"""Review helpers for extracting today's session data from Anki."""

from datetime import datetime, timezone
from typing import Any, Optional

from .constants import MS_TO_SECONDS_DIVISOR, SECONDS_PER_DAY
from .logger import get_module_logger


class AnkiReviewTracker:
    # Injecting the mw because it makes our tests simpler
    def __init__(self, mw: Any) -> None:
        self.mw: Any = mw
        self.logger: Any = get_module_logger("anki_review_tracker")
        self.logger.debug("AnkiReviewTracker initialized")

    def _get_start_of_today_ms(self) -> int:
        if self.mw.col is not None:
            # Newer Anki: use start_of_today() if available
            if hasattr(self.mw.col, "start_of_today"):
                start_of_today_s = self.mw.col.start_of_today()
            # Older Anki: use day_cutoff - 86400
            elif hasattr(self.mw.col, "sched") and hasattr(
                self.mw.col.sched, "day_cutoff"
            ):
                start_of_today_s = self.mw.col.sched.day_cutoff - SECONDS_PER_DAY
            else:
                return 0
            start_ms = int(start_of_today_s * MS_TO_SECONDS_DIVISOR)
            self.logger.debug(
                f"Start of today (Anki profile): {start_of_today_s} (s), {start_ms} (ms)"
            )
            return start_ms
        return 0

    def get_todays_review_time_milliseconds(self) -> int:
        """Return total review time today in milliseconds."""
        try:
            if self.mw.col is None or self.mw.col.db is None:
                self.logger.warning("No collection or database available")
                return 0
            today_start_time = self._get_start_of_today_ms()
            query = "SELECT SUM(time) FROM revlog WHERE id > ?"
            total_time_ms: Optional[int] = self.mw.col.db.scalar(
                query, today_start_time
            )
            self.logger.info(f"Total review time for today: {total_time_ms or 0} ms")
            return total_time_ms or 0
        except AttributeError as e:
            self.logger.warning(f"Anki collection became unavailable: {e}")
            return 0
        except Exception as e:
            self.logger.error(
                "Unexpected error getting today's review time: %s",
                str(e),
                exc_info=True,
            )
            return 0

    def get_todays_review_session_info(self) -> dict[str, Any]:
        """
        Get detailed information about today's review sessions.

        Returns:
            Dictionary with session info including first_review_time, last_review_time,
            total_duration_ms, and session_count
        """
        if self.mw.col is None or self.mw.col.db is None:
            self.logger.warning("No collection or database available")
            return {
                "first_review_time": None,
                "last_review_time": None,
                "total_duration_ms": 0,
                "session_count": 0,
            }

        today_start_time = self._get_start_of_today_ms()

        # Get first and last review times for today
        first_review_query = (
            "SELECT id, time FROM revlog WHERE id > ? ORDER BY id ASC LIMIT 1"
        )
        last_review_query = (
            "SELECT id, time FROM revlog WHERE id > ? ORDER BY id DESC LIMIT 1"
        )
        total_time_query = "SELECT SUM(time) FROM revlog WHERE id > ?"
        count_query = "SELECT COUNT(*) FROM revlog WHERE id > ?"

        first_review = self.mw.col.db.first(first_review_query, today_start_time)
        last_review = self.mw.col.db.first(last_review_query, today_start_time)
        total_time_ms = self.mw.col.db.scalar(total_time_query, today_start_time) or 0
        session_count = self.mw.col.db.scalar(count_query, today_start_time) or 0

        # Convert timestamps to datetime objects
        first_review_time = None
        last_review_time = None

        if first_review:
            # The id field is milliseconds since epoch
            first_review_time = datetime.fromtimestamp(
                first_review[0] / MS_TO_SECONDS_DIVISOR, timezone.utc
            )
            self.logger.debug(f"First review today: {first_review_time} UTC")

        if last_review:
            # The id field is milliseconds since epoch
            last_review_time = datetime.fromtimestamp(
                last_review[0] / MS_TO_SECONDS_DIVISOR, timezone.utc
            )
            self.logger.debug(f"Last review today: {last_review_time} UTC")

        session_info = {
            "first_review_time": first_review_time,
            "last_review_time": last_review_time,
            "total_duration_ms": total_time_ms,
            "session_count": session_count,
        }

        self.logger.info(
            f"Today's review session info: {session_count} reviews, {total_time_ms}ms total"
        )
        return session_info
