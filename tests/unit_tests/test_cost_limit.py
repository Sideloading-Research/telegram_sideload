"""
Tests for the MAX_COST_PER_ANSWER_USD cost limit feature.

Verifies that the retry loop in IntegrationWorker stops early and returns
the best answer so far when accumulated round cost exceeds the configured limit.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock

import utils.usage_accounting as usage_accounting
from config import MAX_COST_PER_ANSWER_USD


# --- Helpers ---

def make_mindfile_mock():
    mindfile = Mock()
    mindfile.files_dict = {}
    mindfile.get_mindfile_data_packed_into_compendiums = Mock(return_value=[])
    return mindfile


def make_integration_worker(mindfile=None):
    """Create an IntegrationWorker with a minimal mock mindfile."""
    from workers.integration_worker import IntegrationWorker
    if mindfile is None:
        mindfile = make_mindfile_mock()
    return IntegrationWorker(mindfile=mindfile)


def make_quality_scores(score=5):
    """Quality scores that do NOT meet MIN_ANSWER_QUALITY_SCORE (forces retries)."""
    return {"sys_message_compliance": score, "self_description_correctness": score}


def make_passing_quality_scores():
    """Quality scores that DO meet MIN_ANSWER_QUALITY_SCORE (stops retries)."""
    return {"sys_message_compliance": 10, "self_description_correctness": 10}


# --- Unit tests for is_cost_limit_exceeded ---

class TestIsCostLimitExceeded(unittest.TestCase):

    def setUp(self):
        self.worker = make_integration_worker()

    @patch("workers.integration_worker.get_round_cost", return_value=0.0)
    def test_returns_false_when_cost_is_zero(self, _):
        self.assertFalse(self.worker.is_cost_limit_exceeded())

    @patch("workers.integration_worker.get_round_cost", return_value=MAX_COST_PER_ANSWER_USD - 0.01)
    def test_returns_false_when_cost_is_below_limit(self, _):
        self.assertFalse(self.worker.is_cost_limit_exceeded())

    @patch("workers.integration_worker.get_round_cost", return_value=MAX_COST_PER_ANSWER_USD)
    def test_returns_true_when_cost_equals_limit(self, _):
        self.assertTrue(self.worker.is_cost_limit_exceeded())

    @patch("workers.integration_worker.get_round_cost", return_value=MAX_COST_PER_ANSWER_USD + 10.0)
    def test_returns_true_when_cost_exceeds_limit(self, _):
        self.assertTrue(self.worker.is_cost_limit_exceeded())


# --- Integration tests for the retry loop behaviour ---

ACCOUNTING_PATCHES = [
    patch("workers.integration_worker.start_round"),
    patch("workers.integration_worker.end_round_print"),
    patch("workers.integration_worker.record_round_cost_to_disk"),
    patch("workers.integration_worker.print_current_month_total"),
    patch("workers.integration_worker.set_genius_mode7"),
    patch("workers.integration_worker.clear_genius_mode7"),
    patch("workers.integration_worker.clear_fixed_model_for_round"),
    patch("workers.integration_worker.get_quality_retries_for_round", return_value=None),
    patch("workers.integration_worker.clear_quality_retries_for_round"),
]


def apply_patches(patches):
    """Context manager that applies a list of patches."""
    import contextlib
    return contextlib.ExitStack()


class TestCostLimitRetryLoop(unittest.TestCase):
    """Tests that verify the retry loop respects MAX_COST_PER_ANSWER_USD."""

    def _run_process(self, worker, cost_side_effect, num_retries=3, quality_scores=None):
        """
        Run IntegrationWorker._process() with controlled cost and retry conditions.

        cost_side_effect: list of values returned by get_round_cost on successive calls
        num_retries: how many attempts the config allows
        quality_scores: scores returned by quality worker (low = forces retries)
        """
        if quality_scores is None:
            quality_scores = make_quality_scores(score=5)

        messages = [{"role": "user", "content": "test question"}]
        raw_message = "test question"

        attempt_counter = {"count": 0}

        def mock_get_initial_answer(msgs, raw, deep_dive7):
            attempt_counter["count"] += 1
            return f"answer_{attempt_counter['count']}", None, set()

        def mock_apply_style(answer, msgs):
            return answer, "mock_model", 1

        def mock_evaluate_quality(msgs, answer):
            return quality_scores, "mock_quality_model"

        def mock_initialize_workers():
            worker.quality_worker = Mock()
            worker.style_worker = Mock()
            worker.generalist_data_worker = Mock()
            worker.doorman_worker = Mock()
            worker.doorman_worker.process = Mock(return_value="shallow")
            worker.compendium_data_workers = []
            worker.user_info_prompt = None

        patches = [
            patch("workers.integration_worker.start_round"),
            patch("workers.integration_worker.end_round_print"),
            patch("workers.integration_worker.record_round_cost_to_disk"),
            patch("workers.integration_worker.print_current_month_total"),
            patch("workers.integration_worker.set_genius_mode7"),
            patch("workers.integration_worker.clear_genius_mode7"),
            patch("workers.integration_worker.clear_fixed_model_for_round"),
            patch("workers.integration_worker.get_quality_retries_for_round", return_value=num_retries),
            patch("workers.integration_worker.clear_quality_retries_for_round"),
            patch("workers.integration_worker.get_round_cost", side_effect=cost_side_effect),
            patch.object(worker, "_initialize_workers", side_effect=mock_initialize_workers),
            patch.object(worker, "_get_initial_answer", side_effect=mock_get_initial_answer),
            patch.object(worker, "_apply_style", side_effect=mock_apply_style),
            patch.object(worker, "_evaluate_quality", side_effect=mock_evaluate_quality),
        ]

        with patches[0], patches[1], patches[2], patches[3], patches[4], \
             patches[5], patches[6], patches[7], patches[8], patches[9], \
             patches[10], patches[11], patches[12], patches[13]:
            final_answer, _, _ = worker._process(messages, raw_message)

        return final_answer, attempt_counter["count"]

    def test_first_attempt_always_runs_even_if_cost_high(self):
        """First attempt must always execute regardless of accumulated cost."""
        worker = make_integration_worker()

        # Cost is already over the limit before any attempt runs.
        # get_round_cost is called at the top of each loop iteration after attempt 0.
        # For attempt 0, the check is skipped, so only 1 call happens (the print in the break).
        # Actually: attempt 0 skips the check. Attempt 1 calls is_cost_limit_exceeded()
        # which calls get_round_cost() once. Provide enough values.
        high_cost = [MAX_COST_PER_ANSWER_USD + 1] * 10

        _, attempts_made = self._run_process(
            worker,
            cost_side_effect=high_cost,
            num_retries=3,
            quality_scores=make_quality_scores(score=5),
        )

        self.assertEqual(attempts_made, 1, "First attempt must always run")

    def test_retries_stop_when_cost_limit_exceeded(self):
        """After 1 successful attempt, cost limit is hit: no further retries."""
        worker = make_integration_worker()

        # First call to get_round_cost (attempt 1 check): over the limit
        cost_values = [MAX_COST_PER_ANSWER_USD + 5] * 10

        _, attempts_made = self._run_process(
            worker,
            cost_side_effect=cost_values,
            num_retries=3,
            quality_scores=make_quality_scores(score=5),
        )

        self.assertEqual(attempts_made, 1)

    def test_retries_continue_while_cost_is_below_limit(self):
        """All configured retries run when cost stays below the limit."""
        worker = make_integration_worker()

        # Cost stays below limit on every check
        low_cost = [MAX_COST_PER_ANSWER_USD - 0.01] * 10

        _, attempts_made = self._run_process(
            worker,
            cost_side_effect=low_cost,
            num_retries=3,
            quality_scores=make_quality_scores(score=5),
        )

        self.assertEqual(attempts_made, 3)

    def test_cost_limit_stops_at_second_of_three_attempts(self):
        """Cost exceeds limit after first attempt: only 2 attempts total."""
        worker = make_integration_worker()

        # First check (start of attempt 1): below limit
        # Second check (start of attempt 2): over limit
        cost_values = [MAX_COST_PER_ANSWER_USD - 1, MAX_COST_PER_ANSWER_USD + 1] * 5

        _, attempts_made = self._run_process(
            worker,
            cost_side_effect=cost_values,
            num_retries=3,
            quality_scores=make_quality_scores(score=5),
        )

        self.assertEqual(attempts_made, 2)

    def test_best_answer_returned_when_cost_limit_hit(self):
        """The best answer from completed attempts is returned after cost cutoff."""
        worker = make_integration_worker()

        # One attempt completes, then cost limit is triggered
        cost_values = [MAX_COST_PER_ANSWER_USD + 1] * 10

        final_answer, attempts_made = self._run_process(
            worker,
            cost_side_effect=cost_values,
            num_retries=3,
            quality_scores=make_quality_scores(score=5),
        )

        self.assertEqual(attempts_made, 1)
        self.assertIsNotNone(final_answer)
        self.assertNotEqual(final_answer, "")

    def test_quality_threshold_still_stops_loop_before_cost_limit(self):
        """If quality passes on attempt 1, loop stops without checking cost at all."""
        worker = make_integration_worker()

        # Cost is under limit — wouldn't block anyway, but quality passes first
        cost_values = [MAX_COST_PER_ANSWER_USD - 1] * 10

        _, attempts_made = self._run_process(
            worker,
            cost_side_effect=cost_values,
            num_retries=3,
            quality_scores=make_passing_quality_scores(),
        )

        # Quality met on first attempt → loop exits immediately
        self.assertEqual(attempts_made, 1)


# --- Unit tests for usage_accounting module ---

class TestUsageAccounting(unittest.TestCase):
    """Tests for the get_round_cost helper used by the cost limit check."""

    def setUp(self):
        usage_accounting.start_round()

    def tearDown(self):
        usage_accounting.is_tracking7 = False
        usage_accounting._total_cost_for_round = 0.0

    def test_get_round_cost_starts_at_zero(self):
        self.assertEqual(usage_accounting.get_round_cost(), 0.0)

    def test_get_round_cost_accumulates(self):
        usage_accounting.add_cost(5.0)
        usage_accounting.add_cost(3.5)
        self.assertAlmostEqual(usage_accounting.get_round_cost(), 8.5)

    def test_get_round_cost_resets_on_new_round(self):
        usage_accounting.add_cost(10.0)
        usage_accounting.start_round()
        self.assertEqual(usage_accounting.get_round_cost(), 0.0)

    def test_add_cost_ignored_when_not_tracking(self):
        usage_accounting.is_tracking7 = False
        usage_accounting._total_cost_for_round = 0.0
        usage_accounting.add_cost(99.0)
        self.assertEqual(usage_accounting.get_round_cost(), 0.0)

    def test_add_cost_ignores_none(self):
        usage_accounting.add_cost(None)
        self.assertEqual(usage_accounting.get_round_cost(), 0.0)


if __name__ == "__main__":
    unittest.main()
