from datetime import datetime, timezone

import pytest


@pytest.mark.unit
def test_timezone_invalid_name_raises() -> None:
    from src.timezone import Timezone, TimezoneError

    with pytest.raises(TimezoneError):
        Timezone("Invalid/Timezone")


@pytest.mark.unit
def test_make_aware_behaviour() -> None:
    from src.timezone import Timezone

    tz = Timezone("UTC")
    aware = datetime.now(timezone.utc)
    naive = datetime(2024, 1, 1, 12, 0, 0)

    assert tz.make_aware(aware) is aware
    result = tz.make_aware(naive)
    assert result.tzinfo is not None
