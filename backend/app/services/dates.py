from datetime import date, timedelta
from typing import Literal

Period = Literal["30d", "quarter", "year"]
PERIOD_DAYS: dict[str, int] = {"30d": 30, "quarter": 90, "year": 365}


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, n: int) -> date:
    """First day of the month `n` months after `d`'s month (n may be negative)."""
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def period_bounds(period: str, today: date | None = None) -> tuple[date, date, date, date]:
    """
    Rolling window ending today, plus the equally long window before it.
    Returns (start, end, prev_start, prev_end), all inclusive.
    """
    today = today or date.today()
    days = PERIOD_DAYS[period]
    start = today - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return start, today, prev_start, prev_end
