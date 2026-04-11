"""Pure date/time utilities with no cost-specific logic."""

from datetime import datetime, timedelta, date


def get_monday_of_current_week() -> datetime:
    """Returns Monday 00:00:00 of the current calendar week."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return datetime(monday.year, monday.month, monday.day)


def get_first_monday_on_or_after(d: date) -> date:
    """Returns the first Monday on or after the given date."""
    days_until_monday = (7 - d.weekday()) % 7
    return d + timedelta(days=days_until_monday)


def get_next_month_first(d: date) -> date:
    """Returns the 1st of the month following the given date."""
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def format_recovery_date(d: date) -> str:
    """Format a date as 'Month Day' with no leading zero, e.g. 'April 12'."""
    return f"{d.strftime('%B')} {d.day}"
