from datetime import datetime, timezone
from typing import Optional, Tuple
from unittest.mock import MagicMock, Mock

import pytest

from src.anki_review_tracker import AnkiReviewTracker


@pytest.mark.unit
def test_get_todays_review_time_ms(mocker: MagicMock) -> None:
    # Have to mock at this level rather than "aqt.mw.col" so mw is not None
    mock_mw = mocker.patch("aqt.mw", autospec=True)

    mock_mw.col.db.scalar.return_value = 300000
    mock_mw.col.db.first.return_value = (1728313200001, 1000)  # id, time

    # Use a predictable timestamp
    mocker.patch(
        "src.anki_review_tracker.AnkiReviewTracker._get_start_of_today_ms",
        return_value=int(datetime(2024, 10, 8).timestamp() * 1000),
    )

    tracker = AnkiReviewTracker(mock_mw)

    expected_review_time_ms = mock_mw.col.db.scalar.return_value
    result = tracker.get_todays_review_time_milliseconds()

    assert expected_review_time_ms == result


@pytest.mark.unit
@pytest.mark.parametrize(
    "col_value,db_value,expected",
    [
        (None, None, 0),  # mw.col is None
        ("mock_col", None, 0),  # mw.col.db is None
    ],
)
def test_get_todays_review_time_ms_returns_zero_on_none_conditions(
    col_value: Optional[str], db_value: Optional[str], expected: int
) -> None:
    mock_mw = MagicMock()

    if col_value is None:
        mock_mw.col = None
    else:
        mock_col = MagicMock()
        mock_col.db = None if db_value is None else MagicMock()
        mock_mw.col = mock_col

    tracker = AnkiReviewTracker(mock_mw)
    result = tracker.get_todays_review_time_milliseconds()

    assert result == expected


@pytest.mark.unit
def test_anki_review_tracker_get_todays_review_time_milliseconds_with_large_values() -> (
    None
):
    """Test get_todays_review_time_milliseconds with large time values."""
    mock_mw = MagicMock()
    mock_col = MagicMock()
    mock_db = MagicMock()

    # Test with large time value (24 hours)
    large_time_ms = 24 * 60 * 60 * 1000  # 24 hours in milliseconds
    mock_db.scalar.return_value = large_time_ms
    mock_db.first.return_value = (1728313200001, 1000)

    mock_col.db = mock_db
    mock_mw.col = mock_col

    tracker = AnkiReviewTracker(mock_mw)
    result = tracker.get_todays_review_time_milliseconds()

    assert result == large_time_ms


@pytest.mark.unit
@pytest.mark.parametrize(
    "db_first_side_effect,db_scalar_side_effect,expected_duration,expected_count",
    [
        (
            [
                (1642233600000, 5000),
                (1642237200000, 3000),
            ],  # First and last review timestamps
            [60000, 10],  # Total time, count
            60000,
            10,
        ),
        ([None, None], [0, 0], 0, 0),  # No reviews found  # No time, no count
    ],
)
def test_get_todays_review_session_info_scenarios(
    db_first_side_effect: list[Optional[Tuple[int, int]]],
    db_scalar_side_effect: list[int],
    expected_duration: int,
    expected_count: int,
) -> None:
    """Test get_todays_review_session_info with different data scenarios."""
    mock_mw = Mock()
    mock_col = Mock()
    mock_db = Mock()

    # Mock the database responses based on test parameters
    mock_db.first.side_effect = db_first_side_effect
    mock_db.scalar.side_effect = db_scalar_side_effect

    mock_col.db = mock_db
    mock_col.start_of_today.return_value = 1642204800  # Start of day timestamp
    mock_mw.col = mock_col

    tracker = AnkiReviewTracker(mock_mw)
    session_info = tracker.get_todays_review_session_info()

    assert session_info["total_duration_ms"] == expected_duration
    assert session_info["session_count"] == expected_count

    if expected_duration > 0:
        # Should have review times when duration > 0
        assert session_info["first_review_time"] is not None
        assert session_info["last_review_time"] is not None

        # Check that the timestamps were converted correctly
        first_time = session_info["first_review_time"]
        last_time = session_info["last_review_time"]

        # These should be datetime objects in UTC
        assert isinstance(first_time, datetime)
        assert isinstance(last_time, datetime)
        assert first_time.tzinfo == timezone.utc
        assert last_time.tzinfo == timezone.utc
    else:
        # Should have None when no reviews
        assert session_info["first_review_time"] is None
        assert session_info["last_review_time"] is None

    # Verify the database was called correctly
    assert mock_db.first.call_count == len(db_first_side_effect)
    assert mock_db.scalar.call_count == len(db_scalar_side_effect)


@pytest.mark.unit
def test_get_todays_review_session_info_no_collection() -> None:
    """Test get_todays_review_session_info when no collection is available."""
    mock_mw = Mock()
    mock_mw.col = None

    tracker = AnkiReviewTracker(mock_mw)
    session_info = tracker.get_todays_review_session_info()

    assert session_info["total_duration_ms"] == 0
    assert session_info["session_count"] == 0
    assert session_info["first_review_time"] is None
    assert session_info["last_review_time"] is None
