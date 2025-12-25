#!/usr/bin/env python3
"""
Test script for credential loading functionality.
This tests the new .env loading behavior.
"""

import os
import sys
from unittest.mock import patch, mock_open, MagicMock

# Mock the dotenv import
sys.modules['dotenv'] = MagicMock()
sys.modules['dotenv'].load_dotenv = MagicMock()

def get_creds():
    """Copy of the get_creds function for testing"""
    # Mock keys_dict for testing
    keys_dict = {
        "AI_PROVIDER": "",  # Optional, falls back to default in config.py
        "GOOGLE_API_KEY": "dummy", # Required if AI_PROVIDER is "google"
        "GOOGLE_MODEL_NAME": "dummy", # Required if AI_PROVIDER is "google"
        "ALLOWED_USER_IDS": None,  # Required
        "ALLOWED_GROUP_IDS": None,  # Required
        "TELEGRAM_LLM_BOT_TOKEN": None,  # Required
        "ANTHROPIC_MODEL": "dummy",  # Required if AI_PROVIDER is "anthropic"
        "ANTHROPIC_API_KEY": "dummy",  # Required if AI_PROVIDER is "anthropic"
        "OPENAI_MODEL": "dummy",  # Required if AI_PROVIDER is "openai"
        "OPENAI_API_KEY": "dummy",  # Required if AI_PROVIDER is "openai"
        "OPENROUTER_KEY": None, # Required if AI_PROVIDER is "openrouter"
        "USERS_INFO": "", # Optional, information about users
        "TRIGGER_WORDS": "", # Optional, trigger words for the bot
    }

    creds = {}
    successful_keys = []
    missing_keys = []

    # First, check what required credentials are missing from environment
    required_keys = [key for key, default_value in keys_dict.items() if default_value is None]

    for key, default_value in keys_dict.items():
        if key in os.environ:
            creds[key] = os.environ[key]
            successful_keys.append(key)
        elif default_value is not None:
            creds[key] = default_value
            successful_keys.append(key)
        else:
            missing_keys.append(key)

    # If any required credentials are missing, try to load from .env
    if missing_keys:
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_file_path):
            # Load .env file
            from dotenv import load_dotenv
            load_dotenv(env_file_path)

            # Check if .env contains ALL required credentials
            env_creds = {}
            env_missing_keys = []

            for key in required_keys:
                if key in os.environ:
                    env_creds[key] = os.environ[key]
                else:
                    env_missing_keys.append(key)

            if env_missing_keys:
                raise Exception(f".env file is missing required credentials: {', '.join(env_missing_keys)}. All required credentials must be present in .env when falling back to .env loading.")

            # Load all credentials from environment (including newly loaded .env values)
            creds = {}
            for key, default_value in keys_dict.items():
                if key in os.environ:
                    creds[key] = os.environ[key]
                elif default_value is not None:
                    creds[key] = default_value
                else:
                    # This should not happen since we verified all required keys are in .env
                    raise Exception(f"Unexpected missing key after .env loading: {key}")
        else:
            msg = f"Required keys not found in environment variables: {', '.join(missing_keys)}."
            if successful_keys:
                msg += f" These keys were found: {', '.join(successful_keys)}"
            raise Exception(msg)

    return creds

def test_creds_loading():

    print("Testing credential loading functionality...")

    # Test 1: All required credentials present in environment
    print("\nTest 1: All required credentials present in environment")
    test_env = {
        'ALLOWED_USER_IDS': '123,456',
        'ALLOWED_GROUP_IDS': '-789,-101',
        'TELEGRAM_LLM_BOT_TOKEN': 'test_token',
        'OPENROUTER_KEY': 'test_openrouter_key'
    }

    with patch.dict(os.environ, test_env, clear=True):
        try:
            creds = get_creds()
            print("✓ Successfully loaded credentials from environment")
            assert 'ALLOWED_USER_IDS' in creds
            assert 'TELEGRAM_LLM_BOT_TOKEN' in creds
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False

    # Test 2: Missing required credentials, no .env file
    print("\nTest 2: Missing required credentials, no .env file")
    incomplete_env = {
        'ALLOWED_USER_IDS': '123,456',
        # Missing TELEGRAM_LLM_BOT_TOKEN and others
    }

    with patch.dict(os.environ, incomplete_env, clear=True):
        with patch('os.path.exists', return_value=False):
            try:
                creds = get_creds()
                print("✗ Should have failed but didn't")
                return False
            except Exception as e:
                print(f"✓ Correctly failed with: {e}")

    # Test 3: Missing required credentials, .env exists but incomplete
    print("\nTest 3: Missing required credentials, .env exists but incomplete")
    with patch.dict(os.environ, incomplete_env, clear=True):
        # Mock .env file that doesn't have all required credentials
        mock_env_content = "ALLOWED_USER_IDS=123,456\nALLOWED_GROUP_IDS=-789\n"
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_env_content)):

            # Mock load_dotenv to not add missing keys
            with patch('dotenv.load_dotenv'):
                try:
                    creds = get_creds()
                    print("✗ Should have failed but didn't")
                    return False
                except Exception as e:
                    print(f"✓ Correctly failed with: {e}")

    # Test 4: Missing required credentials, .env exists and complete
    print("\nTest 4: Missing required credentials, .env exists and complete")
    with patch.dict(os.environ, incomplete_env, clear=True):
        # Mock complete .env file
        mock_env_content = """ALLOWED_USER_IDS=123,456
ALLOWED_GROUP_IDS=-789,-101
TELEGRAM_LLM_BOT_TOKEN=test_token
OPENROUTER_KEY=test_openrouter_key
"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_env_content)):

            def side_effect(dotenv_path):
                # Simulate loading .env - add the missing keys to environment
                os.environ['ALLOWED_GROUP_IDS'] = '-789,-101'
                os.environ['TELEGRAM_LLM_BOT_TOKEN'] = 'test_token'
                os.environ['OPENROUTER_KEY'] = 'test_openrouter_key'

            with patch('dotenv.load_dotenv', side_effect=side_effect):
                try:
                    creds = get_creds()
                    print("✓ Successfully loaded credentials from .env")
                    assert 'TELEGRAM_LLM_BOT_TOKEN' in creds
                    assert 'OPENROUTER_KEY' in creds
                except Exception as e:
                    print(f"✗ Failed: {e}")
                    return False

    print("\n✓ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_creds_loading()
    sys.exit(0 if success else 1)
