import os
import unittest

SAMPLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "test_data", "fallback_versions", "micro_sideload.txt"
)

DIALOGS_WITH_QUOTES = '''\
Some context line.
QUOTE: "First quote here"
More context.
QUOTE: "Second quote here"
End.
'''

DIALOGS_NO_QUOTES = '''\
Some context line.
No quotes at all.
Another line.
'''

DIALOGS_MULTILINE_QUOTE = '''\
Context.
QUOTE: "This quote
spans multiple
lines"
More context.
QUOTE: "Single line quote"
'''

DIALOGS_MID_LINE_QUOTE = '''\
text before QUOTE: "should not match"
QUOTE: "should match"
'''


class TestFindQuoteStartPositions(unittest.TestCase):

    def setUp(self):
        from utils.style_samples_builder import _find_quote_start_positions
        self.find = _find_quote_start_positions

    def test_finds_line_start_quotes(self):
        positions = self.find(DIALOGS_WITH_QUOTES)
        self.assertEqual(len(positions), 2)

    def test_does_not_match_mid_line_quote(self):
        positions = self.find(DIALOGS_MID_LINE_QUOTE)
        self.assertEqual(len(positions), 1)

    def test_returns_empty_for_no_quotes(self):
        positions = self.find(DIALOGS_NO_QUOTES)
        self.assertEqual(positions, [])

    def test_finds_multiline_quotes(self):
        positions = self.find(DIALOGS_MULTILINE_QUOTE)
        self.assertEqual(len(positions), 2)


class TestCleanRawQuote(unittest.TestCase):

    def setUp(self):
        from utils.style_samples_builder import _clean_raw_quote
        self.clean = _clean_raw_quote

    def test_strips_wrapping_double_quotes(self):
        result = self.clean('"hello world"')
        self.assertEqual(result, "hello world")

    def test_strips_surrounding_whitespace(self):
        result = self.clean('  "  content  "  ')
        self.assertEqual(result, "content")

    def test_handles_missing_closing_quote(self):
        result = self.clean('"no closing quote')
        self.assertEqual(result, "no closing quote")

    def test_handles_missing_opening_quote(self):
        result = self.clean('no opening quote"')
        # rfind finds the trailing quote; no leading strip needed
        self.assertNotIn('"', result)

    def test_preserves_multiline_content(self):
        raw = '"line one\nline two\nline three"'
        result = self.clean(raw)
        self.assertIn("line one", result)
        self.assertIn("line two", result)
        self.assertIn("line three", result)


class TestExtractQuotes(unittest.TestCase):

    def setUp(self):
        from utils.style_samples_builder import extract_quotes
        self.extract = extract_quotes

    def test_extracts_two_quotes(self):
        quotes = self.extract(DIALOGS_WITH_QUOTES)
        self.assertEqual(len(quotes), 2)

    def test_quote_content_correct(self):
        quotes = self.extract(DIALOGS_WITH_QUOTES)
        self.assertEqual(quotes[0], "First quote here")
        self.assertEqual(quotes[1], "Second quote here")

    def test_returns_empty_list_for_no_quotes(self):
        quotes = self.extract(DIALOGS_NO_QUOTES)
        self.assertEqual(quotes, [])

    def test_multiline_quote_is_one_block(self):
        quotes = self.extract(DIALOGS_MULTILINE_QUOTE)
        self.assertEqual(len(quotes), 2)
        multiline = quotes[0]
        self.assertIn("spans multiple", multiline)
        self.assertIn("lines", multiline)

    def test_no_quote_prefix_in_output(self):
        quotes = self.extract(DIALOGS_WITH_QUOTES)
        for q in quotes:
            self.assertNotIn("QUOTE:", q)

    def test_no_wrapping_quotes_in_output(self):
        quotes = self.extract(DIALOGS_WITH_QUOTES)
        for q in quotes:
            self.assertFalse(q.startswith('"'))
            self.assertFalse(q.endswith('"'))


class TestBuildStyleSamplesContent(unittest.TestCase):

    def setUp(self):
        from utils.style_samples_builder import build_style_samples_content
        self.build = build_style_samples_content

    def test_returns_none_when_no_quotes(self):
        result = self.build(DIALOGS_NO_QUOTES)
        self.assertIsNone(result)

    def test_returns_string_when_quotes_exist(self):
        result = self.build(DIALOGS_WITH_QUOTES)
        self.assertIsInstance(result, str)

    def test_quotes_separated_by_double_newline(self):
        result = self.build(DIALOGS_WITH_QUOTES)
        self.assertIn("\n\n", result)

    def test_all_quote_content_present(self):
        result = self.build(DIALOGS_WITH_QUOTES)
        self.assertIn("First quote here", result)
        self.assertIn("Second quote here", result)

    def test_no_quote_prefix_in_result(self):
        result = self.build(DIALOGS_WITH_QUOTES)
        self.assertNotIn("QUOTE:", result)


class TestBuildStyleSamplesFromRealFile(unittest.TestCase):

    def setUp(self):
        from utils.micro_sideload_parser import parse_micro_sideload
        from utils.style_samples_builder import build_style_samples_content
        sections = parse_micro_sideload(SAMPLE_FILE)
        self.dialogs = sections["dialogs"]
        self.build = build_style_samples_content

    def test_real_dialogs_has_quotes(self):
        result = self.build(self.dialogs)
        self.assertIsNotNone(result)

    def test_real_result_has_no_quote_prefix(self):
        result = self.build(self.dialogs)
        self.assertNotIn("QUOTE:", result)

    def test_real_result_is_non_empty(self):
        result = self.build(self.dialogs)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
