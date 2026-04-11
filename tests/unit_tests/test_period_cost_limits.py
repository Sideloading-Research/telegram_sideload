"""
Tests for the daily / weekly / monthly cost-limit feature.

Covers:
  - usage_accounting: _read_month_file, get_today_total, get_week_total, get_current_month_total
  - cost_limiter: get_exceeded_period, _get_weekly_cost_as_of, _get_monthly_cost_as_of,
                  is_unblocked_on, get_unblock_date
  - time_utils: format_recovery_date
  - app_logic: _get_cost_limit_message
"""

import os
import unittest
import tempfile
from datetime import datetime, timedelta, date
from unittest.mock import patch

import utils.usage_accounting as ua
import utils.cost_limiter as cl
import utils.time_utils as tu
from config import (
    MAX_COST_PER_DAY_USD,
    MAX_COST_PER_WEEK_USD,
    MAX_COST_PER_MONTH_USD,
    TOO_MUCH_COST_MESSAGE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_cost_file(directory: str, year: int, month: int, entries: list[tuple[datetime, float]]) -> str:
    path = os.path.join(directory, f"{year}_{month:02d}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for ts, cost in entries:
            f.write(f"{ts.isoformat()} - {cost}\n")
    return path


def _today() -> datetime:
    return datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)


def _monday_this_week() -> datetime:
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    return datetime(monday.year, monday.month, monday.day, 12, 0, 0)


def _last_monday() -> datetime:
    return _monday_this_week() - timedelta(weeks=1)


# ---------------------------------------------------------------------------
# Tests for usage_accounting: _read_month_file
# ---------------------------------------------------------------------------

class TestReadMonthFile(unittest.TestCase):

    def test_returns_empty_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                result = ua._read_month_file(2026, 1)
        self.assertEqual(result, [])

    def test_parses_valid_entries(self):
        ts = datetime(2026, 4, 10, 14, 0, 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, 2026, 4, [(ts, 5.5)])
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                result = ua._read_month_file(2026, 4)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][1], 5.5)

    def test_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "2026_04.txt")
            with open(path, "w") as f:
                f.write("not a valid line\n")
                f.write(f"{datetime(2026,4,10).isoformat()} - 3.0\n")
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                result = ua._read_month_file(2026, 4)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][1], 3.0)


# ---------------------------------------------------------------------------
# Tests for usage_accounting: get_today_total
# ---------------------------------------------------------------------------

class TestGetTodayTotal(unittest.TestCase):

    def test_returns_zero_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertEqual(ua.get_today_total(), 0.0)

    def test_counts_only_todays_entries(self):
        today = _today()
        entries = [(today, 10.0), (today - timedelta(days=1), 99.0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, today.year, today.month, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(ua.get_today_total(), 10.0)

    def test_sums_multiple_entries_today(self):
        today = _today()
        entries = [(today.replace(hour=9), 5.0), (today.replace(hour=17), 7.5)]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, today.year, today.month, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(ua.get_today_total(), 12.5)


# ---------------------------------------------------------------------------
# Tests for usage_accounting: get_week_total
# ---------------------------------------------------------------------------

class TestGetWeekTotal(unittest.TestCase):

    def test_returns_zero_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertEqual(ua.get_week_total(), 0.0)

    def test_counts_entries_since_monday(self):
        monday = _monday_this_week()
        before_monday = monday - timedelta(days=1)  # Previous Sunday
        entries = [(monday, 20.0), (before_monday, 999.0)]
        now = datetime.now()
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, now.year, now.month, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(ua.get_week_total(), 20.0)

    def test_excludes_last_week_entry(self):
        monday = _monday_this_week()
        entries = [(monday, 15.0), (_last_monday(), 500.0)]
        now = datetime.now()
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, now.year, now.month, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(ua.get_week_total(), 15.0)

    def test_reads_previous_month_when_week_spans_boundary(self):
        monday_in_prev_month = datetime(2026, 3, 30, 12, 0, 0)
        entry_in_april = datetime(2026, 4, 1, 10, 0, 0)
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, 2026, 3, [(monday_in_prev_month, 8.0)])
            _write_cost_file(tmpdir, 2026, 4, [(entry_in_april, 12.0)])
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                with patch("utils.usage_accounting.get_monday_of_current_week",
                           return_value=monday_in_prev_month):
                    with patch("utils.usage_accounting.datetime") as mock_dt:
                        mock_dt.now.return_value = entry_in_april
                        mock_dt.fromisoformat = datetime.fromisoformat
                        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
                        total = ua.get_week_total()
        self.assertAlmostEqual(total, 20.0)


# ---------------------------------------------------------------------------
# Tests for usage_accounting: get_current_month_total (regression)
# ---------------------------------------------------------------------------

class TestGetCurrentMonthTotal(unittest.TestCase):

    def test_sums_all_entries_in_month(self):
        now = datetime.now()
        entries = [(now.replace(day=1, hour=10), 10.0), (now.replace(day=5, hour=14), 20.5)]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, now.year, now.month, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(ua.get_current_month_total(), 30.5)

    def test_returns_zero_for_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertEqual(ua.get_current_month_total(), 0.0)


# ---------------------------------------------------------------------------
# Tests for cost_limiter: get_exceeded_period
# ---------------------------------------------------------------------------

class TestGetExceededPeriod(unittest.TestCase):

    def _patch_totals(self, day=0.0, week=0.0, month=0.0):
        # cost_limiter calls these via _ua.*, so patching in ua module works
        return (
            patch.object(ua, "get_today_total", return_value=day),
            patch.object(ua, "get_week_total", return_value=week),
            patch.object(ua, "get_current_month_total", return_value=month),
        )

    def test_returns_none_when_all_within_budget(self):
        p1, p2, p3 = self._patch_totals(day=1.0, week=5.0, month=10.0)
        with p1, p2, p3:
            self.assertIsNone(cl.get_exceeded_period())

    def test_returns_day_when_daily_limit_hit(self):
        p1, p2, p3 = self._patch_totals(day=MAX_COST_PER_DAY_USD)
        with p1, p2, p3:
            self.assertEqual(cl.get_exceeded_period(), "day")

    def test_returns_week_when_only_weekly_limit_hit(self):
        p1, p2, p3 = self._patch_totals(week=MAX_COST_PER_WEEK_USD)
        with p1, p2, p3:
            self.assertEqual(cl.get_exceeded_period(), "week")

    def test_returns_month_when_only_monthly_limit_hit(self):
        p1, p2, p3 = self._patch_totals(month=MAX_COST_PER_MONTH_USD)
        with p1, p2, p3:
            self.assertEqual(cl.get_exceeded_period(), "month")

    def test_day_takes_priority_over_week_and_month(self):
        p1, p2, p3 = self._patch_totals(
            day=MAX_COST_PER_DAY_USD + 1,
            week=MAX_COST_PER_WEEK_USD + 1,
            month=MAX_COST_PER_MONTH_USD + 1,
        )
        with p1, p2, p3:
            self.assertEqual(cl.get_exceeded_period(), "day")

    def test_week_takes_priority_over_month(self):
        p1, p2, p3 = self._patch_totals(week=MAX_COST_PER_WEEK_USD + 1, month=MAX_COST_PER_MONTH_USD + 1)
        with p1, p2, p3:
            self.assertEqual(cl.get_exceeded_period(), "week")

    def test_boundary_exactly_at_limit_is_exceeded(self):
        p1, p2, p3 = self._patch_totals(day=MAX_COST_PER_DAY_USD)
        with p1, p2, p3:
            self.assertEqual(cl.get_exceeded_period(), "day")

    def test_just_below_limit_is_not_exceeded(self):
        p1, p2, p3 = self._patch_totals(
            day=MAX_COST_PER_DAY_USD - 0.01,
            week=MAX_COST_PER_WEEK_USD - 0.01,
            month=MAX_COST_PER_MONTH_USD - 0.01,
        )
        with p1, p2, p3:
            self.assertIsNone(cl.get_exceeded_period())


# ---------------------------------------------------------------------------
# Tests for cost_limiter: _get_weekly_cost_as_of / _get_monthly_cost_as_of
# ---------------------------------------------------------------------------

class TestCostAsOf(unittest.TestCase):

    def test_weekly_excludes_costs_on_target_date(self):
        target = date(2026, 4, 13)   # Monday — window is empty (start == end)
        entries = [(datetime(2026, 4, 13, 10, 0), 20.0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, 2026, 4, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(cl._get_weekly_cost_as_of(target), 0.0)

    def test_weekly_includes_earlier_days_in_same_week(self):
        target = date(2026, 4, 16)   # Thursday
        entries = [
            (datetime(2026, 4, 13, 10, 0), 10.0),   # Monday — included
            (datetime(2026, 4, 15, 10, 0), 15.0),   # Wednesday — included
            (datetime(2026, 4, 16, 10, 0), 99.0),   # Thursday (target) — excluded
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, 2026, 4, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(cl._get_weekly_cost_as_of(target), 25.0)

    def test_monthly_excludes_costs_on_target_date(self):
        target = date(2026, 5, 1)
        entries = [(datetime(2026, 5, 1, 8, 0), 50.0)]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, 2026, 5, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(cl._get_monthly_cost_as_of(target), 0.0)

    def test_monthly_sums_earlier_days(self):
        target = date(2026, 4, 15)
        entries = [
            (datetime(2026, 4, 1, 10, 0), 30.0),
            (datetime(2026, 4, 10, 10, 0), 20.0),
            (datetime(2026, 4, 15, 10, 0), 99.0),  # excluded
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_cost_file(tmpdir, 2026, 4, entries)
            with patch.object(ua, "_COSTS_DIR", tmpdir):
                self.assertAlmostEqual(cl._get_monthly_cost_as_of(target), 50.0)


# ---------------------------------------------------------------------------
# Tests for cost_limiter: is_unblocked_on
# ---------------------------------------------------------------------------

class TestIsUnblockedOn(unittest.TestCase):

    def _patch_costs(self, weekly=0.0, monthly=0.0):
        return (
            patch.object(cl, "_get_weekly_cost_as_of", return_value=weekly),
            patch.object(cl, "_get_monthly_cost_as_of", return_value=monthly),
        )

    def test_unblocked_when_both_under_limit(self):
        p1, p2 = self._patch_costs(weekly=10.0, monthly=50.0)
        with p1, p2:
            self.assertTrue(cl.is_unblocked_on(date(2026, 4, 13)))

    def test_blocked_when_weekly_at_limit(self):
        p1, p2 = self._patch_costs(weekly=MAX_COST_PER_WEEK_USD)
        with p1, p2:
            self.assertFalse(cl.is_unblocked_on(date(2026, 4, 13)))

    def test_blocked_when_monthly_at_limit(self):
        p1, p2 = self._patch_costs(monthly=MAX_COST_PER_MONTH_USD)
        with p1, p2:
            self.assertFalse(cl.is_unblocked_on(date(2026, 4, 13)))

    def test_blocked_when_both_at_limit(self):
        p1, p2 = self._patch_costs(weekly=MAX_COST_PER_WEEK_USD, monthly=MAX_COST_PER_MONTH_USD)
        with p1, p2:
            self.assertFalse(cl.is_unblocked_on(date(2026, 4, 13)))


# ---------------------------------------------------------------------------
# Tests for cost_limiter: get_unblock_date
# ---------------------------------------------------------------------------

class TestGetUnblockDate(unittest.TestCase):

    def _run(self, today: date, unblocked_from: date) -> date:
        def mock_is_unblocked(d):
            return d >= unblocked_from

        with patch.object(cl, "get_exceeded_period", return_value="day"), \
             patch("utils.cost_limiter.date") as mock_date, \
             patch.object(cl, "is_unblocked_on", side_effect=mock_is_unblocked):
            mock_date.today.return_value = today
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            return cl.get_unblock_date()

    def test_returns_none_when_not_blocked(self):
        with patch.object(cl, "get_exceeded_period", return_value=None):
            self.assertIsNone(cl.get_unblock_date())

    def test_returns_tomorrow_when_sufficient(self):
        today = date(2026, 4, 10)    # Friday
        result = self._run(today, unblocked_from=date(2026, 4, 11))
        self.assertEqual(result, date(2026, 4, 11))

    def test_skips_to_monday_when_tomorrow_still_blocked(self):
        # Key double-block scenario: daily limit Friday, weekly still over on Saturday
        today = date(2026, 4, 10)      # Friday
        result = self._run(today, unblocked_from=date(2026, 4, 13))
        self.assertEqual(result, date(2026, 4, 13))  # next Monday

    def test_skips_to_next_month_first_when_it_is_a_monday(self):
        # June 1 2026 is a Monday — resets both weekly and monthly
        today = date(2026, 5, 30)
        result = self._run(today, unblocked_from=date(2026, 6, 1))
        self.assertEqual(result, date(2026, 6, 1))

    def test_skips_to_first_monday_of_next_month_when_1st_is_mid_week(self):
        today = date(2026, 4, 30)   # Thursday
        result = self._run(today, unblocked_from=date(2026, 5, 4))
        self.assertEqual(result, date(2026, 5, 4))  # First Monday of May

    def test_december_rolls_to_january(self):
        today = date(2026, 12, 28)
        result = self._run(today, unblocked_from=date(2027, 1, 4))
        self.assertEqual(result, date(2027, 1, 4))  # First Monday of January


# ---------------------------------------------------------------------------
# Tests for time_utils: format_recovery_date
# ---------------------------------------------------------------------------

class TestFormatRecoveryDate(unittest.TestCase):

    def test_formats_without_leading_zero(self):
        self.assertEqual(tu.format_recovery_date(date(2026, 4, 5)), "April 5")

    def test_formats_double_digit_day(self):
        self.assertEqual(tu.format_recovery_date(date(2026, 4, 12)), "April 12")

    def test_formats_january(self):
        self.assertEqual(tu.format_recovery_date(date(2027, 1, 1)), "January 1")


# ---------------------------------------------------------------------------
# Tests for app_logic: _get_cost_limit_message
# ---------------------------------------------------------------------------

class TestGetCostLimitMessage(unittest.TestCase):

    def _import_helper(self):
        from app_logic import _get_cost_limit_message
        return _get_cost_limit_message

    def test_returns_none_when_not_blocked(self):
        fn = self._import_helper()
        with patch("app_logic.get_unblock_date", return_value=None):
            self.assertIsNone(fn())

    def test_returns_message_with_formatted_date(self):
        fn = self._import_helper()
        with patch("app_logic.get_unblock_date", return_value=date(2026, 4, 13)), \
             patch("app_logic.format_recovery_date", return_value="April 13"):
            self.assertEqual(fn(), TOO_MUCH_COST_MESSAGE + "April 13")

    def test_message_uses_unblock_date_not_period_name(self):
        fn = self._import_helper()
        with patch("app_logic.get_unblock_date", return_value=date(2026, 5, 1)), \
             patch("app_logic.format_recovery_date", return_value="May 1"):
            msg = fn()
        self.assertIn("May 1", msg)
        self.assertNotIn("month", msg)


if __name__ == "__main__":
    unittest.main()
