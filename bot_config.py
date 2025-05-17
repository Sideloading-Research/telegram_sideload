import os
from utils.creds_handler import CREDS
from config import ENABLE_USER_DEFINED_AI_PROVIDERS7, MAX_TELEGRAM_MESSAGE_LEN, PLATFORM_SPECIFIC_PROMPT_ADDITION # Assuming these are still relevant here or will be used by other modules

# --- Telegram Bot Token ---
TOKEN = CREDS.get("TELEGRAM_LLM_BOT_TOKEN")
if not TOKEN:
    raise ValueError(
        "No token provided. Set the TELEGRAM_LLM_BOT_TOKEN environment variable."
    )

# --- Allowed User and Group IDs ---
allowed_ids_str = CREDS.get("ALLOWED_USER_IDS")
if not allowed_ids_str:
    raise ValueError(
        "No ALLOWED_USER_IDS provided. Set the ALLOWED_USER_IDS environment variable."
    )
ALLOWED_USER_IDS = [int(user_id.strip()) for user_id in allowed_ids_str.split(",")]

allowed_groups_str = CREDS.get("ALLOWED_GROUP_IDS", "")
ALLOWED_GROUP_IDS = [int(group_id.strip()) for group_id in allowed_groups_str.split(",") if group_id.strip()]


# --- User Descriptions ---
USER_DESCRIPTIONS_FROM_ENV = {}
raw_users_info = CREDS.get("USERS_INFO", "")
if raw_users_info:
    try:
        user_entries = raw_users_info.split(';')
        for entry in user_entries:
            if entry.strip(): # Ensure entry is not just whitespace
                parts = entry.split(':', 1)
                if len(parts) == 2:
                    user_id_key = parts[0].strip()
                    description = parts[1].strip()
                    if user_id_key and description: # Ensure both user_id and description are non-empty
                        USER_DESCRIPTIONS_FROM_ENV[user_id_key] = description
                else:
                    print(f"Warning: Malformed entry in USERS_INFO: '{entry}'")
    except Exception as e:
        print(f"Warning: Could not parse USERS_INFO environment variable: {e}")

# --- AI Provider Settings ---
PROVIDER_INDICATORS = {  # the indicators are case-insensitive
    "openai": ["o:", "о:"],  # Russian and Latin
    "anthropic": ["a:", "а:", "c:", "с:"],  # Russian and Latin
}
# PROVIDER_FROM_ENV is imported where ask_gpt_multi_message is called, usually ai_service or directly.
# We'll assume ai_service will handle the default provider logic.

# --- Conversation Settings ---
MAX_MESSAGES_NUM = 50

# --- Exported existing config values (if they are meant to be globally available) ---
# These were in main.py's import from config, so making them available from here.
# If their use is more localized, they might not need to be here.
# For now, including them for completeness based on original main.py imports.
GLOBAL_ENABLE_USER_DEFINED_AI_PROVIDERS7 = ENABLE_USER_DEFINED_AI_PROVIDERS7
GLOBAL_MAX_TELEGRAM_MESSAGE_LEN = MAX_TELEGRAM_MESSAGE_LEN
GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION = PLATFORM_SPECIFIC_PROMPT_ADDITION

# Note: Constants from utils.constants (like c.reset_dialog_command) are not global config,
# they are specific constants for features and should be imported where used.

def get_user_descriptions():
    return USER_DESCRIPTIONS_FROM_ENV

def get_provider_indicators():
    return PROVIDER_INDICATORS

def get_token():
    return TOKEN

def get_allowed_user_ids():
    return ALLOWED_USER_IDS

def get_allowed_group_ids():
    return ALLOWED_GROUP_IDS

def get_max_messages_num():
    return MAX_MESSAGES_NUM

# --- Trigger Words ---
TRIGGER_WORDS_STR = CREDS.get("TRIGGER_WORDS", "")
print(f"Trigger words string: {TRIGGER_WORDS_STR}")
TRIGGER_WORDS = []
if TRIGGER_WORDS_STR:
    TRIGGER_WORDS = [word.strip().lower() for word in TRIGGER_WORDS_STR.split(';') if word.strip()]

print("Trigger words:")
for word in TRIGGER_WORDS:
    print(word)
print("--------------------------------")

def get_trigger_words():
    return TRIGGER_WORDS

# Example of how other modules might access these:
# from bot_config import get_token, GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION 