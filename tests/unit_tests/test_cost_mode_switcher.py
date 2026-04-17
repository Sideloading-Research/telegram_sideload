"""
Tests for cost_mode_switcher: automatic DATA_SOURCE_MODE selection
based on monthly spend, with user override support.
"""

import unittest
from datetime import date
from unittest.mock import patch, MagicMock

import utils.cost_mode_switcher as cms
import utils.usage_accounting as ua
import config


def _reset_override():
    """Reset override state between tests."""
    cms._override_mode = None
    cms._override_date = None


class TestIsCostSwitchingEnabled(unittest.TestCase):

    def setUp(self):
        _reset_override()

    def test_enabled_when_original_mode_is_normal(self):
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", "NORMAL"):
            self.assertTrue(cms.is_cost_switching_enabled())

    def test_disabled_when_original_mode_is_nano(self):
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", "NANO"):
            self.assertFalse(cms.is_cost_switching_enabled())

    def test_disabled_when_original_mode_is_micro(self):
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", "MICRO"):
            self.assertFalse(cms.is_cost_switching_enabled())

    def test_disabled_when_original_mode_is_quick_test(self):
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", "QUICK_TEST"):
            self.assertFalse(cms.is_cost_switching_enabled())


class TestGetCostBasedMode(unittest.TestCase):

    def setUp(self):
        _reset_override()

    def _run(self, monthly_total: float) -> str:
        with patch.object(ua, "get_current_month_total", return_value=monthly_total):
            return cms.get_cost_based_mode()

    def test_returns_normal_when_below_micro_threshold(self):
        threshold = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT
        self.assertEqual(self._run(threshold - 0.01), "NORMAL")

    def test_returns_micro_at_micro_threshold(self):
        threshold = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT
        self.assertEqual(self._run(threshold), "MICRO")

    def test_returns_micro_between_thresholds(self):
        micro_t = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT
        nano_t = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_NANO_THRESHOLD_PCT
        midpoint = (micro_t + nano_t) / 2
        self.assertEqual(self._run(midpoint), "MICRO")

    def test_returns_nano_at_nano_threshold(self):
        threshold = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_NANO_THRESHOLD_PCT
        self.assertEqual(self._run(threshold), "NANO")

    def test_returns_nano_above_nano_threshold(self):
        threshold = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_NANO_THRESHOLD_PCT
        self.assertEqual(self._run(threshold + 1.0), "NANO")

    def test_returns_normal_when_cost_is_zero(self):
        self.assertEqual(self._run(0.0), "NORMAL")


class TestSetUserOverride(unittest.TestCase):

    def setUp(self):
        _reset_override()

    def test_sets_override_mode(self):
        cms.set_user_override("NANO")
        self.assertEqual(cms._override_mode, "NANO")

    def test_sets_override_date_to_today(self):
        cms.set_user_override("MICRO")
        self.assertEqual(cms._override_date, date.today())

    def test_override_replaces_previous(self):
        cms.set_user_override("NANO")
        cms.set_user_override("MICRO")
        self.assertEqual(cms._override_mode, "MICRO")


class TestIsOverrideActive(unittest.TestCase):

    def setUp(self):
        _reset_override()

    def test_false_when_no_override(self):
        self.assertFalse(cms.is_override_active())

    def test_true_when_set_today(self):
        cms.set_user_override("NANO")
        self.assertTrue(cms.is_override_active())

    def test_false_when_set_yesterday(self):
        cms._override_mode = "NANO"
        cms._override_date = date(2026, 1, 1)  # clearly in the past
        self.assertFalse(cms.is_override_active())


class TestApplyCostBasedMode(unittest.TestCase):

    def setUp(self):
        _reset_override()
        self.mock_mind_manager = MagicMock()

    def _run(self, original_mode: str, current_mode: str, monthly_cost: float):
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", original_mode), \
             patch.object(config, "DATA_SOURCE_MODE", current_mode), \
             patch.object(ua, "get_current_month_total", return_value=monthly_cost), \
             patch.object(config, "set_data_source_mode") as mock_set:
            cms.apply_cost_based_mode(self.mock_mind_manager)
            return mock_set

    def test_does_nothing_when_switching_disabled(self):
        mock_set = self._run(original_mode="NANO", current_mode="NANO", monthly_cost=999.0)
        mock_set.assert_not_called()
        self.mock_mind_manager.force_refresh.assert_not_called()

    def test_switches_to_micro_when_above_50pct(self):
        cost = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT
        mock_set = self._run(original_mode="NORMAL", current_mode="NORMAL", monthly_cost=cost)
        mock_set.assert_called_once_with("MICRO")
        self.mock_mind_manager.force_refresh.assert_called_once()

    def test_switches_to_nano_when_above_75pct(self):
        cost = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_NANO_THRESHOLD_PCT
        mock_set = self._run(original_mode="NORMAL", current_mode="NORMAL", monthly_cost=cost)
        mock_set.assert_called_once_with("NANO")
        self.mock_mind_manager.force_refresh.assert_called_once()

    def test_switches_to_normal_when_below_50pct(self):
        cost = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT - 0.01
        mock_set = self._run(original_mode="NORMAL", current_mode="MICRO", monthly_cost=cost)
        mock_set.assert_called_once_with("NORMAL")
        self.mock_mind_manager.force_refresh.assert_called_once()

    def test_does_not_refresh_when_mode_unchanged(self):
        cost = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT
        mock_set = self._run(original_mode="NORMAL", current_mode="MICRO", monthly_cost=cost)
        mock_set.assert_not_called()
        self.mock_mind_manager.force_refresh.assert_not_called()

    def test_override_active_prevents_switch(self):
        cms.set_user_override("NANO")
        cost = 0.0  # would normally trigger NORMAL
        mock_set = self._run(original_mode="NORMAL", current_mode="NANO", monthly_cost=cost)
        mock_set.assert_not_called()
        self.mock_mind_manager.force_refresh.assert_not_called()

    def test_expired_override_is_cleared_and_mode_applied(self):
        cms._override_mode = "NANO"
        cms._override_date = date(2026, 1, 1)  # yesterday
        cost = 0.0  # cost-based mode: NORMAL
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", "NORMAL"), \
             patch.object(config, "DATA_SOURCE_MODE", "NANO"), \
             patch.object(ua, "get_current_month_total", return_value=cost), \
             patch.object(config, "set_data_source_mode") as mock_set:
            cms.apply_cost_based_mode(self.mock_mind_manager)
        mock_set.assert_called_once_with("NORMAL")
        self.mock_mind_manager.force_refresh.assert_called_once()
        self.assertIsNone(cms._override_mode)

    def test_same_day_override_survives_into_next_check(self):
        cms.set_user_override("MICRO")
        # Simulate a second call same day — should still respect override
        cost = 0.0  # would switch to NORMAL without override
        with patch.object(config, "ORIGINAL_DATA_SOURCE_MODE", "NORMAL"), \
             patch.object(config, "DATA_SOURCE_MODE", "MICRO"), \
             patch.object(ua, "get_current_month_total", return_value=cost), \
             patch.object(config, "set_data_source_mode") as mock_set:
            cms.apply_cost_based_mode(self.mock_mind_manager)
        mock_set.assert_not_called()


if __name__ == "__main__":
    unittest.main()
