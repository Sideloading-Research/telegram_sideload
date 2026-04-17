import os
import unittest

SAMPLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "test_data", "fallback_versions", "micro_sideload.txt"
)

ALL_SECTION_FILENAMES = [
    "structured_self_facts",
    "consumed_media_list",
    "dialogs",
    "dreams",
    "interviews_etc",
    "writings_fiction",
    "writings_non_fiction",
    "structured_memories",
]


class TestExtractSystemMessage(unittest.TestCase):

    def setUp(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        self.sections = parse_micro_sideload(SAMPLE_FILE)

    def test_system_message_is_present(self):
        self.assertIn("system_message", self.sections)

    def test_system_message_is_non_empty(self):
        self.assertTrue(len(self.sections["system_message"]) > 0)

    def test_system_message_does_not_contain_self_description_open_tag(self):
        self.assertNotIn("<self-description>", self.sections["system_message"])

    def test_system_message_does_not_contain_self_description_close_tag(self):
        self.assertNotIn("</self-description>", self.sections["system_message"])

    def test_system_message_contains_expected_content(self):
        # The system prompt starts with the goals section
        self.assertIn("<goals>", self.sections["system_message"])


class TestExtractSections(unittest.TestCase):

    def setUp(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        self.sections = parse_micro_sideload(SAMPLE_FILE)

    def test_all_expected_sections_present(self):
        for name in ALL_SECTION_FILENAMES:
            with self.subTest(section=name):
                self.assertIn(name, self.sections)

    def test_all_sections_non_empty(self):
        for name in ALL_SECTION_FILENAMES:
            with self.subTest(section=name):
                self.assertTrue(len(self.sections[name]) > 0)

    def test_structured_self_facts_starts_with_legend(self):
        content = self.sections["structured_self_facts"]
        self.assertTrue(content.startswith("# Legend"))

    def test_structured_self_facts_has_no_surrounding_tags(self):
        content = self.sections["structured_self_facts"]
        self.assertNotIn("<self-description>", content)
        self.assertNotIn("</self-description>", content)

    def test_structured_memories_has_no_surrounding_tags(self):
        content = self.sections["structured_memories"]
        self.assertNotIn("<structured_memories>", content)
        self.assertNotIn("</structured_memories>", content)

    def test_dialogs_has_no_surrounding_tags(self):
        content = self.sections["dialogs"]
        self.assertNotIn("<dialogs>", content)
        self.assertNotIn("</dialogs>", content)

    def test_total_sections_count(self):
        # system_message + 8 data sections
        self.assertEqual(len(self.sections), 9)


class TestExtractInnerContent(unittest.TestCase):

    def setUp(self):
        from utils.micro_sideload_parser import _extract_inner_content
        self.extract = _extract_inner_content

    def test_extracts_simple_content(self):
        text = "prefix\n<mytag>\nhello world\n</mytag>\nsuffix"
        result = self.extract(text, "mytag")
        self.assertEqual(result, "hello world")

    def test_strips_surrounding_whitespace(self):
        text = "<mytag>\n\n  content  \n\n</mytag>"
        result = self.extract(text, "mytag")
        self.assertEqual(result, "content")

    def test_returns_none_when_open_tag_missing(self):
        result = self.extract("no tags here", "missing")
        self.assertIsNone(result)

    def test_returns_none_when_close_tag_missing(self):
        result = self.extract("<mytag>content without close", "mytag")
        self.assertIsNone(result)

    def test_multiline_content_preserved(self):
        text = "<sec>\nline1\nline2\nline3\n</sec>"
        result = self.extract(text, "sec")
        self.assertIn("line1", result)
        self.assertIn("line2", result)
        self.assertIn("line3", result)


class TestExtractSystemMessageHelper(unittest.TestCase):

    def setUp(self):
        from utils.micro_sideload_parser import _extract_system_message
        self.extract = _extract_system_message

    def test_returns_content_before_self_description(self):
        text = "system content\n<self-description>\nfacts\n</self-description>"
        result = self.extract(text)
        self.assertEqual(result, "system content")

    def test_returns_whole_text_if_no_self_description_tag(self):
        text = "just some text"
        result = self.extract(text)
        self.assertEqual(result, "just some text")

    def test_strips_trailing_whitespace(self):
        text = "system content   \n\n<self-description>\nfacts\n</self-description>"
        result = self.extract(text)
        self.assertEqual(result, "system content")


if __name__ == "__main__":
    unittest.main()
