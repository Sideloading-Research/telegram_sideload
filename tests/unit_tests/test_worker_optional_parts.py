"""
Tests that data_worker and style_worker tolerate absent structured_memories / dialogs.
These cover the NANO mode scenario where only system_message + structured_self_facts exist.
"""
import unittest
from unittest.mock import MagicMock, patch


NANO_FILES = {"system_message": "/p", "structured_self_facts": "/p"}
FULL_FILES = {
    "system_message": "/p",
    "structured_self_facts": "/p",
    "structured_memories": "/p",
    "dialogs": "/p",
}


def make_mock_mindfile(files: dict) -> MagicMock:
    mindfile = MagicMock()
    mindfile.files_dict = files
    mindfile.get_context = MagicMock(return_value="context")
    mindfile.get_system_message = MagicMock(return_value="sys")
    return mindfile


def make_data_worker(mindfile) -> object:
    from workers.data_worker import DataWorker
    with patch.object(DataWorker, '__init__', lambda self, mf, **kw: None):
        worker = DataWorker.__new__(DataWorker)
    worker.mindfile = mindfile
    worker.custom_worker_context = None
    worker.worker_name = "data_worker"
    worker.group_settings = None
    worker.collect_diagnostics7 = False
    worker._diag_events = []
    from worker_config import WORKERS_CONFIG
    worker.config = WORKERS_CONFIG["data_worker"]
    worker.mindfile_parts = (
        worker.config.get("mindfile_parts", [])
        + worker.config.get("mindfile_parts_optional", [])
    )
    return worker


def make_style_worker(mindfile) -> object:
    from workers.style_worker import StyleWorker
    with patch.object(StyleWorker, '__init__', lambda self, mf, gs=None: None):
        worker = StyleWorker.__new__(StyleWorker)
    worker.mindfile = mindfile
    worker.worker_name = "style_worker"
    worker.group_settings = None
    worker.collect_diagnostics7 = False
    worker._diag_events = []
    from worker_config import WORKERS_CONFIG
    worker.config = WORKERS_CONFIG["style_worker"]
    worker.mindfile_parts = (
        worker.config.get("mindfile_parts", [])
        + worker.config.get("mindfile_parts_optional", [])
    )
    return worker


class TestDataWorkerWithoutMemories(unittest.TestCase):

    def test_structured_memories_not_in_mandatory_parts(self):
        from worker_config import WORKERS_CONFIG
        mandatory = WORKERS_CONFIG["data_worker"]["mindfile_parts"]
        self.assertNotIn("structured_memories", mandatory)

    def test_structured_memories_in_optional_parts(self):
        from worker_config import WORKERS_CONFIG
        optional = WORKERS_CONFIG["data_worker"]["mindfile_parts_optional"]
        self.assertIn("structured_memories", optional)

    def test_get_worker_context_does_not_raise_without_memories(self):
        worker = make_data_worker(make_mock_mindfile(NANO_FILES))
        try:
            worker.get_worker_context()
        except Exception as e:
            self.fail(f"get_worker_context raised {e} without structured_memories")

    def test_get_worker_context_calls_get_context(self):
        mindfile = make_mock_mindfile(NANO_FILES)
        worker = make_data_worker(mindfile)
        worker.get_worker_context()
        mindfile.get_context.assert_called_once()

    def test_obligatory_parts_always_in_parts_list(self):
        from config import WORKERS_OBLIGATORY_PARTS
        worker = make_data_worker(make_mock_mindfile(NANO_FILES))
        for part in WORKERS_OBLIGATORY_PARTS:
            with self.subTest(part=part):
                self.assertIn(part, worker.mindfile_parts)


class TestStyleWorkerWithoutDialogs(unittest.TestCase):

    def test_dialogs_not_in_mandatory_parts(self):
        from worker_config import WORKERS_CONFIG
        mandatory = WORKERS_CONFIG["style_worker"]["mindfile_parts"]
        self.assertNotIn("dialogs", mandatory)

    def test_dialogs_in_optional_parts(self):
        from worker_config import WORKERS_CONFIG
        optional = WORKERS_CONFIG["style_worker"]["mindfile_parts_optional"]
        self.assertIn("dialogs", optional)

    def test_get_style_context_parts_without_dialogs_or_style_samples(self):
        mindfile = make_mock_mindfile(NANO_FILES)
        worker = make_style_worker(mindfile)
        parts = worker._get_style_context_parts()
        self.assertNotIn("style_samples", parts)
        self.assertNotIn("dialogs", parts)

    def test_get_worker_context_does_not_raise_without_dialogs(self):
        worker = make_style_worker(make_mock_mindfile(NANO_FILES))
        try:
            worker.get_worker_context()
        except Exception as e:
            self.fail(f"get_worker_context raised {e} without dialogs")

    def test_obligatory_parts_always_in_parts_list(self):
        from config import WORKERS_OBLIGATORY_PARTS
        worker = make_style_worker(make_mock_mindfile(NANO_FILES))
        for part in WORKERS_OBLIGATORY_PARTS:
            with self.subTest(part=part):
                self.assertIn(part, worker.mindfile_parts)


class TestStartupValidationWithNanoFiles(unittest.TestCase):
    """Verify that NANO-like files_dict passes validation (no mandatory errors)."""

    def test_nano_files_dict_passes_mandatory_check(self):
        from utils.startup_checks import check_worker_mindfile_parts
        valid7, error_report, _ = check_worker_mindfile_parts(NANO_FILES)
        self.assertTrue(valid7, f"Validation failed: {error_report}")

    def test_nano_files_dict_warns_about_missing_optional(self):
        from utils.startup_checks import check_worker_mindfile_parts
        _, _, warning_report = check_worker_mindfile_parts(NANO_FILES)
        self.assertTrue(len(warning_report) > 0)


if __name__ == "__main__":
    unittest.main()
