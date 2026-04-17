import os
import tempfile
import unittest

SAMPLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "test_data", "fallback_versions", "micro_sideload.txt"
)

EXPECTED_KEYS = {
    "system_message",
    "structured_self_facts",
    "consumed_media_list",
    "dialogs",
    "dreams",
    "interviews_etc",
    "writings_fiction",
    "writings_non_fiction",
    "structured_memories",
    "style_samples",
}


class TestWriteSectionToFile(unittest.TestCase):

    def test_creates_file_with_correct_content(self):
        from utils.micro_mindfile_builder import _write_section_to_file
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_section_to_file(tmpdir, "my_section", "hello content")
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "hello content")

    def test_filename_has_txt_extension(self):
        from utils.micro_mindfile_builder import _write_section_to_file
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_section_to_file(tmpdir, "my_section", "content")
            self.assertTrue(path.endswith("my_section.txt"))

    def test_returns_full_path(self):
        from utils.micro_mindfile_builder import _write_section_to_file
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_section_to_file(tmpdir, "sec", "data")
            self.assertTrue(os.path.isabs(path))


class TestSectionsToFilesDict(unittest.TestCase):

    def test_all_sections_written(self):
        from utils.micro_mindfile_builder import _sections_to_files_dict
        sections = {"sec_a": "content a", "sec_b": "content b"}
        with tempfile.TemporaryDirectory() as tmpdir:
            files_dict = _sections_to_files_dict(sections, tmpdir)
            self.assertEqual(set(files_dict.keys()), {"sec_a", "sec_b"})
            for key, path in files_dict.items():
                self.assertTrue(os.path.exists(path))

    def test_file_contents_match_sections(self):
        from utils.micro_mindfile_builder import _sections_to_files_dict
        sections = {"alpha": "alpha content", "beta": "beta content"}
        with tempfile.TemporaryDirectory() as tmpdir:
            files_dict = _sections_to_files_dict(sections, tmpdir)
            for key, path in files_dict.items():
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), sections[key])


class TestBuildMicroFilesDict(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_all_expected_keys(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        self.assertEqual(set(files_dict.keys()), EXPECTED_KEYS)

    def test_all_paths_exist_on_disk(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        for key, path in files_dict.items():
            with self.subTest(section=key):
                self.assertTrue(os.path.exists(path), f"Missing file for section: {key}")

    def test_creates_output_dir_if_missing(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        new_dir = os.path.join(self.tmpdir, "nested", "output")
        self.assertFalse(os.path.exists(new_dir))
        build_sideload_files_dict(SAMPLE_FILE, new_dir)
        self.assertTrue(os.path.exists(new_dir))

    def test_system_message_file_content_is_non_empty(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        with open(files_dict["system_message"], encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(len(content) > 0)

    def test_structured_self_facts_content_matches_parsed(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        from utils.micro_sideload_parser import parse_micro_sideload
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        parsed = parse_micro_sideload(SAMPLE_FILE)
        with open(files_dict["structured_self_facts"], encoding="utf-8") as f:
            on_disk = f.read()
        self.assertEqual(on_disk, parsed["structured_self_facts"])

    def test_structured_memories_content_matches_parsed(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        from utils.micro_sideload_parser import parse_micro_sideload
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        parsed = parse_micro_sideload(SAMPLE_FILE)
        with open(files_dict["structured_memories"], encoding="utf-8") as f:
            on_disk = f.read()
        self.assertEqual(on_disk, parsed["structured_memories"])

    def test_overwrites_existing_files(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        # Run twice — second call should overwrite cleanly
        build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        self.assertEqual(set(files_dict.keys()), EXPECTED_KEYS)

    def test_style_samples_generated(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        self.assertIn("style_samples", files_dict)
        self.assertTrue(os.path.exists(files_dict["style_samples"]))

    def test_style_samples_has_no_quote_prefix(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        with open(files_dict["style_samples"], encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("QUOTE:", content)

    def test_style_samples_is_non_empty(self):
        from utils.micro_mindfile_builder import build_sideload_files_dict
        files_dict = build_sideload_files_dict(SAMPLE_FILE, self.tmpdir)
        with open(files_dict["style_samples"], encoding="utf-8") as f:
            content = f.read()
        self.assertGreater(len(content), 0)


class TestMaybeAddStyleSamples(unittest.TestCase):

    def test_returns_style_samples_when_quotes_present(self):
        from utils.micro_mindfile_builder import _maybe_add_style_samples
        sections = {"dialogs": 'QUOTE: "a quote"\nsome text'}
        result = _maybe_add_style_samples(sections)
        self.assertIn("style_samples", result)

    def test_returns_empty_when_no_quotes(self):
        from utils.micro_mindfile_builder import _maybe_add_style_samples
        sections = {"dialogs": "no quotes here"}
        result = _maybe_add_style_samples(sections)
        self.assertEqual(result, {})

    def test_returns_empty_when_dialogs_missing(self):
        from utils.micro_mindfile_builder import _maybe_add_style_samples
        result = _maybe_add_style_samples({})
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
