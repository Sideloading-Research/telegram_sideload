import unittest
from utils.diag_utils import format_diag_info
import config

class TestDiagFormatting(unittest.TestCase):
    def test_format_diag_info_normal_mode(self):
        config.DATA_SOURCE_MODE = "NORMAL"
        diag_info = {
            "retries": 0,
            "scores": {"sys_message_compliance": 10, "self_description_correctness": 10},
            "models_used": {"google/gemini-2.5-flash"},
            "request_type": "ANSWER",
            "style_iterations": 2,
        }
        formatted = format_diag_info(diag_info)
        # Should NOT contain "me" or "m" (for mode)
        self.assertNotIn("me:", formatted)
        # It will contain "m" for models, truncated to 6 chars after vowel removal: "gmn2.5"
        self.assertIn("m:gmn2.5", formatted)
        self.assertNotIn("flsh", formatted) # "flsh" should be truncated

    def test_format_diag_info_nano_mode(self):
        config.DATA_SOURCE_MODE = "NANO"
        diag_info = {
            "retries": 0,
            "scores": {"sys_message_compliance": 10, "self_description_correctness": 10},
            "models_used": {"google/gemini-2.5-flash"},
            "request_type": "ANSWER",
            "style_iterations": 2,
        }
        # In NANO mode, it should add md:nano. 
        # remove_vowels transforms "md:nano" -> "md:nn"
        formatted = format_diag_info(diag_info)
        
        # Check that "md:nn" is present
        self.assertIn("md:nn", formatted)
        
    def test_format_diag_info_quick_test_mode(self):
        config.DATA_SOURCE_MODE = "QUICK_TEST"
        diag_info = {
            "retries": 0,
            "scores": {"sys_message_compliance": 10, "self_description_correctness": 10},
            "models_used": {"google/gemini-2.5-flash"},
            "request_type": "ANSWER",
            "style_iterations": 2,
        }
        # QUICK_TEST is mapped to "qt". "md:qt" stays "md:qt".
        formatted = format_diag_info(diag_info)
        self.assertIn("md:qt", formatted)

if __name__ == "__main__":
    unittest.main()
