import unittest
import os
import shutil
import json
from utils import chat_logger

# Define a temporary directory for testing
TEST_LOG_DIR = "tests/test_data/temp_chat_logs"

class TestChatLogger(unittest.TestCase):
    def setUp(self):
        # Create the directory if it doesn't exist
        if not os.path.exists(TEST_LOG_DIR):
            os.makedirs(TEST_LOG_DIR)
        
        # Override the log directory in the module for testing
        self.original_log_dir = chat_logger.CHAT_LOGS_DIR
        chat_logger.CHAT_LOGS_DIR = TEST_LOG_DIR

    def tearDown(self):
        # Restore original log directory
        chat_logger.CHAT_LOGS_DIR = self.original_log_dir
        
        # Clean up test files
        if os.path.exists(TEST_LOG_DIR):
            shutil.rmtree(TEST_LOG_DIR)

    def test_append_and_load_messages(self):
        key = "user_test_1"
        
        # Append some messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I am fine."},
        ]
        
        for msg in messages:
            chat_logger.append_message(key, msg["role"], msg["content"])
            
        # Load all messages
        loaded_messages = chat_logger.load_chat_history(key, limit=10)
        self.assertEqual(len(loaded_messages), 4)
        self.assertEqual(loaded_messages[0]["content"], "Hello")
        self.assertEqual(loaded_messages[3]["content"], "I am fine.")

    def test_load_limit(self):
        key = "user_test_limit"
        
        # Append 10 messages
        for i in range(10):
            chat_logger.append_message(key, "user", f"msg_{i}")
            
        # Load only last 3
        loaded_messages = chat_logger.load_chat_history(key, limit=3)
        self.assertEqual(len(loaded_messages), 3)
        self.assertEqual(loaded_messages[0]["content"], "msg_7")
        self.assertEqual(loaded_messages[2]["content"], "msg_9")

    def test_archive_log(self):
        key = "user_test_archive"
        chat_logger.append_message(key, "user", "msg_to_archive")
        
        log_file = os.path.join(TEST_LOG_DIR, f"{key}.jsonl")
        self.assertTrue(os.path.exists(log_file))
        
        chat_logger.archive_chat_log(key)
        
        # Original file should be gone (or empty/recreated later, but logic usually renames)
        self.assertFalse(os.path.exists(log_file))
        
        # Find archived file
        files = os.listdir(TEST_LOG_DIR)
        archived_files = [f for f in files if f.startswith(f"{key}_archive_")]
        self.assertEqual(len(archived_files), 1)
        
        # Check content of archived file
        with open(os.path.join(TEST_LOG_DIR, archived_files[0]), 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("msg_to_archive", lines[0])

    def test_load_non_existent(self):
        key = "non_existent"
        loaded = chat_logger.load_chat_history(key, limit=5)
        self.assertEqual(loaded, [])

    def test_special_characters_robustness(self):
        """Test handling of quotes, newlines, unicode, and emojis."""
        key = "user_test_special"
        
        # Content with:
        # 1. Double quotes (JSON delimiter)
        # 2. Backslashes (JSON escape char)
        # 3. Newlines (should be escaped to \n in file)
        # 4. Russian text (Unicode)
        # 5. Emojis
        complex_content = 'Said "hello" to C:\\Path.\nNew line.\nРусский текст: эти вопросы.\nEmoji: 🚀✨'
        
        chat_logger.append_message(key, "user", complex_content)
        
        loaded = chat_logger.load_chat_history(key, limit=1)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["content"], complex_content)
        
        # Verify raw file content integrity
        log_file = os.path.join(TEST_LOG_DIR, f"{key}.jsonl")
        with open(log_file, 'r', encoding='utf-8') as f:
            line = f.readline()
            # Ensure it's all on one line (no physical newline from content)
            self.assertNotIn('\n', line.rstrip('\n')) 
            # Ensure proper JSON escaping
            self.assertIn('\\"', line) # Quotes escaped
            self.assertIn('\\\\', line) # Backslashes escaped
            self.assertIn('\\n', line) # Newlines escaped
            # Ensure unicode is NOT escaped (as per ensure_ascii=False)
            self.assertIn('Русский текст', line)

if __name__ == '__main__':
    unittest.main()
