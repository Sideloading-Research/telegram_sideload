"""
Tests for NANO mode: parsing nano_sideload.txt, building files_dict,
validation, and the refresh pipeline.
"""
import os
import tempfile
import unittest
import unittest.mock

NANO_SAMPLE = os.path.join(
    os.path.dirname(__file__), "..", "test_data", "fallback_versions", "nano_sideload.txt"
)
NANO_EXPECTED_KEYS = {"system_message", "structured_self_facts"}


class TestNanoSideloadParsing(unittest.TestCase):

    def test_nano_produces_only_expected_keys(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        parsed = parse_micro_sideload(NANO_SAMPLE)
        self.assertEqual(set(parsed.keys()), NANO_EXPECTED_KEYS)

    def test_nano_system_message_is_non_empty(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        parsed = parse_micro_sideload(NANO_SAMPLE)
        self.assertGreater(len(parsed["system_message"]), 0)

    def test_nano_structured_self_facts_is_non_empty(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        parsed = parse_micro_sideload(NANO_SAMPLE)
        self.assertGreater(len(parsed["structured_self_facts"]), 0)

    def test_nano_has_no_dialogs(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        parsed = parse_micro_sideload(NANO_SAMPLE)
        self.assertNotIn("dialogs", parsed)

    def test_nano_has_no_structured_memories(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        parsed = parse_micro_sideload(NANO_SAMPLE)
        self.assertNotIn("structured_memories", parsed)


class TestNanoBuildFilesDict(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_build_returns_expected_keys(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(NANO_SAMPLE, self.tmpdir)
        self.assertEqual(set(files_dict.keys()), NANO_EXPECTED_KEYS)

    def test_all_files_exist_on_disk(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(NANO_SAMPLE, self.tmpdir)
        for key, path in files_dict.items():
            with self.subTest(section=key):
                self.assertTrue(os.path.exists(path))

    def test_build_passes_mandatory_validation(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        from utils.startup_checks import check_worker_mindfile_parts
        files_dict = build_sideload_files_dict(NANO_SAMPLE, self.tmpdir)
        valid7, error_report, _ = check_worker_mindfile_parts(files_dict)
        self.assertTrue(valid7, f"Validation failed: {error_report}")

    def test_build_warns_about_missing_optional_parts(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        from utils.startup_checks import check_worker_mindfile_parts
        files_dict = build_sideload_files_dict(NANO_SAMPLE, self.tmpdir)
        _, _, warning_report = check_worker_mindfile_parts(files_dict)
        self.assertGreater(len(warning_report), 0)

    def test_no_style_samples_generated(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(NANO_SAMPLE, self.tmpdir)
        self.assertNotIn("style_samples", files_dict)


class TestRefreshNanoMindfileData(unittest.TestCase):
    """Tests refresh_nano_mindfile_data with FALLBACKS_LOCAL_DIR_PATH pointing to test data."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_fallbacks = None
        self._orig_nano_dir = None

    def tearDown(self):
        import shutil
        import config
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self._orig_fallbacks is not None:
            config.FALLBACKS_LOCAL_DIR_PATH = self._orig_fallbacks
        if self._orig_nano_dir is not None:
            config.NANO_MINDFILE_TEMP_DIR = self._orig_nano_dir

    def _point_fallbacks_to_test_data(self):
        import config
        self._orig_fallbacks = config.FALLBACKS_LOCAL_DIR_PATH
        self._orig_nano_dir = config.NANO_MINDFILE_TEMP_DIR
        config.FALLBACKS_LOCAL_DIR_PATH = os.path.join(
            os.path.dirname(__file__), "..", "test_data", "fallback_versions"
        )
        config.NANO_MINDFILE_TEMP_DIR = os.path.join(self.tmpdir, "nano_mindfile")

    def test_returns_non_empty_files_dict(self):
        from utils.dataset_files import refresh_nano_mindfile_data
        self._point_fallbacks_to_test_data()
        files_dict = refresh_nano_mindfile_data("unused_url", self.tmpdir)
        self.assertGreater(len(files_dict), 0)

    def test_returns_expected_keys(self):
        from utils.dataset_files import refresh_nano_mindfile_data
        self._point_fallbacks_to_test_data()
        files_dict = refresh_nano_mindfile_data("unused_url", self.tmpdir)
        self.assertEqual(set(files_dict.keys()), NANO_EXPECTED_KEYS)

    def test_raises_if_nano_file_missing(self):
        from utils.dataset_files import refresh_nano_mindfile_data
        import config
        self._orig_fallbacks = config.FALLBACKS_LOCAL_DIR_PATH
        config.FALLBACKS_LOCAL_DIR_PATH = self.tmpdir  # empty dir — no nano_sideload.txt
        with unittest.mock.patch("utils.dataset_files._clone_repo_and_copy_fallbacks"):
            with self.assertRaises(FileNotFoundError):
                refresh_nano_mindfile_data("unused_url", self.tmpdir)


class TestNanoModeDispatch(unittest.TestCase):
    """Verify set_data_source_mode handles NANO and mind_data_manager dispatches it."""

    def test_set_data_source_mode_nano(self):
        import config
        orig = config.DATA_SOURCE_MODE
        try:
            config.set_data_source_mode("NANO")
            self.assertEqual(config.DATA_SOURCE_MODE, "NANO")
        finally:
            config.set_data_source_mode(orig)

    def test_mind_data_manager_calls_refresh_nano(self):
        import config
        from utils import mind_data_manager as mdm_module
        from utils import dataset_files as df_module
        orig_mode = config.DATA_SOURCE_MODE
        try:
            config.DATA_SOURCE_MODE = "NANO"
            with unittest.mock.patch.object(mdm_module, "refresh_nano_mindfile_data") as mock_nano:
                mock_nano.return_value = {
                    "system_message": __file__,
                    "structured_self_facts": __file__,
                }
                with unittest.mock.patch("utils.mind_data_manager.get_system_message_and_context", return_value=("sys", "ctx")):
                    with unittest.mock.patch("utils.leftover_manager.cleanup_leftover_files"):
                        manager = object.__new__(mdm_module.MindDataManager)
                        manager._system_message = None
                        manager._context = None
                        manager._files_dict = {}
                        manager._request_counter = 0
                        import threading
                        manager._counter_lock = threading.Lock()
                        manager._refresh_data()
            mock_nano.assert_called_once()
        finally:
            config.DATA_SOURCE_MODE = orig_mode


if __name__ == "__main__":
    unittest.main()
