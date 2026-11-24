from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def business_date(now: datetime | None = None) -> date:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("Business date calculation requires a timezone-aware datetime")
    return current_time.astimezone(ZoneInfo(settings.business_timezone)).date()
