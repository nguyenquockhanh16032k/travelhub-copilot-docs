from datetime import date, datetime, timezone

import pytest

from app.core.business_time import business_date
from app.core.config import settings


def test_business_date_changes_at_configured_local_midnight(monkeypatch) -> None:
    monkeypatch.setattr(settings, "business_timezone", "Asia/Ho_Chi_Minh")

    before_midnight_utc = datetime(2026, 1, 1, 16, 59, tzinfo=timezone.utc)
    at_midnight_utc = datetime(2026, 1, 1, 17, 0, tzinfo=timezone.utc)

    assert business_date(before_midnight_utc) == date(2026, 1, 1)
    assert business_date(at_midnight_utc) == date(2026, 1, 2)


def test_business_date_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        business_date(datetime(2026, 1, 1))
