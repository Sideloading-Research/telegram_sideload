import unittest
import os
import time
from unittest.mock import patch

from utils import rate_limiter

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_rate_limit.txt"
        self.warning_file = "test_warning_timestamp.txt"
        # Ensure clean state
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.warning_file):
            os.remove(self.warning_file)
            
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.warning_file):
            os.remove(self.warning_file)

    @patch('utils.rate_limiter.GLOBAL_RATE_LIMIT_REQUESTS_PER_MINUTE', 2)
    @patch('utils.rate_limiter.RATE_LIMIT_FILE_PATH', "test_rate_limit.txt")
    @patch('utils.rate_limiter.WARNING_TIMESTAMP_FILE_PATH', "test_warning_timestamp.txt")
    def test_rate_limit_enforcement(self):
        # 1st request - allowed
        is_limited, should_warn = rate_limiter.is_global_rate_limited()
        self.assertFalse(is_limited)
        self.assertFalse(should_warn)
        
        # 2nd request - allowed
        is_limited, should_warn = rate_limiter.is_global_rate_limited()
        self.assertFalse(is_limited)
        self.assertFalse(should_warn)
        
        # 3rd request - blocked (limit is 2)
        # Should warn on first block
        is_limited, should_warn = rate_limiter.is_global_rate_limited()
        self.assertTrue(is_limited)
        self.assertTrue(should_warn)

        # 4th request - blocked
        # Should NOT warn again immediately
        is_limited, should_warn = rate_limiter.is_global_rate_limited()
        self.assertTrue(is_limited)
        self.assertFalse(should_warn)
        
    @patch('utils.rate_limiter.GLOBAL_RATE_LIMIT_REQUESTS_PER_MINUTE', 1)
    @patch('utils.rate_limiter.RATE_LIMIT_FILE_PATH', "test_rate_limit.txt")
    @patch('utils.rate_limiter.WARNING_TIMESTAMP_FILE_PATH', "test_warning_timestamp.txt")
    def test_rate_limit_expiry(self):
        # 1st request - allowed
        self.assertFalse(rate_limiter.is_global_rate_limited()[0])
        
        # Immediate 2nd request - blocked
        self.assertTrue(rate_limiter.is_global_rate_limited()[0])
        
        # Simulate time passing (older than 60 seconds)
        real_time = time.time()
        with patch('time.time') as mock_time:
            # Set current time to 65 seconds later than initial real time
            mock_time.return_value = real_time + 65
            
            # Should be allowed now as the previous request expired
            is_limited, should_warn = rate_limiter.is_global_rate_limited()
            self.assertFalse(is_limited)

    @patch('utils.rate_limiter.GLOBAL_RATE_LIMIT_REQUESTS_PER_MINUTE', 1)
    @patch('utils.rate_limiter.RATE_LIMIT_FILE_PATH', "test_rate_limit.txt")
    @patch('utils.rate_limiter.WARNING_TIMESTAMP_FILE_PATH', "test_warning_timestamp.txt")
    def test_warning_cooldown(self):
        # 1st request - allowed
        rate_limiter.is_global_rate_limited()
        
        # 2nd request - blocked & warns
        is_limited, should_warn = rate_limiter.is_global_rate_limited()
        self.assertTrue(is_limited)
        self.assertTrue(should_warn)
        
        # 3rd request - blocked & NO warn
        is_limited, should_warn = rate_limiter.is_global_rate_limited()
        self.assertTrue(is_limited)
        self.assertFalse(should_warn)
        
        # Simulate time passing (30 seconds) - still NO warn
        real_time = time.time()
        with patch('time.time') as mock_time:
            mock_time.return_value = real_time + 30
            is_limited, should_warn = rate_limiter.is_global_rate_limited()
            self.assertTrue(is_limited)
            self.assertFalse(should_warn)
            
        # Simulate time passing (65 seconds) - Warns again
        with patch('time.time') as mock_time:
            mock_time.return_value = real_time + 65
            # Note: Since the original request is also > 60s old, 
            # normally this request would be ALLOWED (expiry test).
            # But here we want to test WARNING cooldown specifically.
            # However, if the request is allowed, we don't warn.
            # To test warning cooldown, we need the request to be BLOCKED.
            # But blocking depends on valid_timestamps.
            # The valid_timestamps are read from file.
            # We need to populate the file with RECENT timestamps relative to the mocked time.
            
            # Let's manually write a "fresh" timestamp to the file relative to our future time
            with open("test_rate_limit.txt", "w") as f:
                f.write(f"{real_time + 64}\n") # Just 1 second old in this future
                
            is_limited, should_warn = rate_limiter.is_global_rate_limited()
            self.assertTrue(is_limited)
            self.assertTrue(should_warn)
