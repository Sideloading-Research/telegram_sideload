"""
Cost-limit enforcement: checks whether daily/weekly/monthly budgets are
exceeded and computes the earliest date when the bot can respond again.
"""

from datetime import datetime, timedelta, date

from config import MAX_COST_PER_DAY_USD, MAX_COST_PER_WEEK_USD, MAX_COST_PER_MONTH_USD
from utils.time_utils import get_first_monday_on_or_after, get_next_month_first

# Imported as a module so that test patches on utils.usage_accounting.* take effect.
import utils.usage_accounting as _ua


def _get_weekly_cost_as_of(d: date) -> float:
    """Historical cost within d's calendar week (Mon 00:00 up to, not including, d 00:00)."""
    monday = d - timedelta(days=d.weekday())
    monday_dt = datetime(monday.year, monday.month, monday.day)
    d_dt = datetime(d.year, d.month, d.day)
    entries = _ua._read_month_file(d.year, d.month)
    if monday.month != d.month:
        entries += _ua._read_month_file(monday.year, monday.month)
    return sum(cost for ts, cost in entries if monday_dt <= ts < d_dt)


def _get_monthly_cost_as_of(d: date) -> float:
    """Historical cost within d's calendar month (1st 00:00 up to, not including, d 00:00)."""
    month_start = datetime(d.year, d.month, 1)
    d_dt = datetime(d.year, d.month, d.day)
    entries = _ua._read_month_file(d.year, d.month)
    return sum(cost for ts, cost in entries if month_start <= ts < d_dt)


def get_exceeded_period() -> str | None:
    """
    Checks daily, weekly, and monthly cost limits in order.
    Returns "day", "week", or "month" for the first exceeded limit, or None.
    Day is checked first since it recovers soonest.
    """
    if _ua.get_today_total() >= MAX_COST_PER_DAY_USD:
        return "day"
    if _ua.get_week_total() >= MAX_COST_PER_WEEK_USD:
        return "week"
    if _ua.get_current_month_total() >= MAX_COST_PER_MONTH_USD:
        return "month"
    return None


def is_unblocked_on(d: date) -> bool:
    """
    Returns True if, on future date d (with zero new spending that day),
    both weekly and monthly costs would be below their limits.
    Daily is not checked since a future date always has zero daily spend.
    """
    if _get_weekly_cost_as_of(d) >= MAX_COST_PER_WEEK_USD:
        return False
    if _get_monthly_cost_as_of(d) >= MAX_COST_PER_MONTH_USD:
        return False
    return True


def get_unblock_date() -> date | None:
    """
    Returns the earliest future date when all cost limits will be satisfied,
    or None if currently under all limits.

    Checks candidate dates in order: tomorrow, next Monday, 1st of next month,
    first Monday of next month. The last candidate always resets both the
    weekly and monthly windows, so it is a guaranteed fallback.
    """
    if get_exceeded_period() is None:
        return None

    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_monday = today + timedelta(days=7 - today.weekday())
    next_month_first = get_next_month_first(today)
    first_monday_next_month = get_first_monday_on_or_after(next_month_first)

    candidates = sorted(set([tomorrow, next_monday, next_month_first, first_monday_next_month]))
    for candidate in candidates:
        if is_unblocked_on(candidate):
            return candidate

    return first_monday_next_month  # guaranteed safe: new week + new month
