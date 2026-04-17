import unittest
from unittest.mock import MagicMock, patch


def make_mock_mindfile(has_style_samples7: bool) -> MagicMock:
    mindfile = MagicMock()
    files = {"system_message": "/p", "structured_self_facts": "/p", "dialogs": "/p"}
    if has_style_samples7:
        files["style_samples"] = "/p"
    mindfile.files_dict = files
    mindfile.get_context = MagicMock(return_value="context")
    return mindfile


def make_style_worker(mindfile) -> object:
    from workers.style_worker import StyleWorker
    with patch.object(StyleWorker, '__init__', lambda self, mf, gs=None: None):
        worker = StyleWorker.__new__(StyleWorker)
    worker.mindfile = mindfile
    worker.worker_name = "style_worker"
    from worker_config import WORKERS_CONFIG
    worker.config = WORKERS_CONFIG["style_worker"]
    worker.mindfile_parts = (
        worker.config.get("mindfile_parts", [])
        + worker.config.get("mindfile_parts_optional", [])
    )
    return worker


class TestGetStyleContextParts(unittest.TestCase):

    def test_uses_style_samples_when_available(self):
        from workers.style_worker import StyleWorker
        worker = make_style_worker(make_mock_mindfile(has_style_samples7=True))
        parts = worker._get_style_context_parts()
        self.assertIn("style_samples", parts)
        self.assertNotIn("dialogs", parts)

    def test_uses_dialogs_when_style_samples_absent(self):
        from workers.style_worker import StyleWorker
        worker = make_style_worker(make_mock_mindfile(has_style_samples7=False))
        parts = worker._get_style_context_parts()
        self.assertIn("dialogs", parts)
        self.assertNotIn("style_samples", parts)

    def test_prints_fallback_message_when_no_style_samples(self):
        worker = make_style_worker(make_mock_mindfile(has_style_samples7=False))
        with patch("builtins.print") as mock_print:
            worker._get_style_context_parts()
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("dialogs", printed)

    def test_obligatory_parts_always_present(self):
        from config import WORKERS_OBLIGATORY_PARTS
        worker = make_style_worker(make_mock_mindfile(has_style_samples7=True))
        parts = worker._get_style_context_parts()
        for part in WORKERS_OBLIGATORY_PARTS:
            with self.subTest(part=part):
                self.assertIn(part, parts)

    def test_get_worker_context_calls_get_context_with_substituted_parts(self):
        mindfile = make_mock_mindfile(has_style_samples7=True)
        worker = make_style_worker(mindfile)
        worker.get_worker_context()
        called_parts = mindfile.get_context.call_args[0][0]
        self.assertIn("style_samples", called_parts)
        self.assertNotIn("dialogs", called_parts)


if __name__ == "__main__":
    unittest.main()
