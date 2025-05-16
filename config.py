REPO_URL = "https://github.com/RomanPlusPlus/open-source-human-mind.git"

DATASET_DIR_NAME_IN_REPO = "full_dataset"

DATASET_LOCAL_DIR_PATH = "./MINDFILE_FROM_GITHUB/full_dataset"

PLATFORM_SPECIFIC_PROMPT_ADDITION="Note: this is an instant messaging chat, so keep your answers short."

SYSTEM_MESSAGE_FILE_WITHOUT_EXT = "system_message"

# While working with a very long context, the start and the end of the context
# are typically better remembered by an LLM than the middle.
# Thus, we place these these two as the first and last items in the context.
STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT = "structured_self_facts" 
STRUCTURED_MEMORIES_FILE_WITHOUT_EXT = "structured_memories"

# How often to check if the mindfile has changed in the repo.
REFRESH_EVERY_N_REQUESTS = 10

ENABLE_USER_DEFINED_AI_PROVIDERS7 = False # keep False, not fully implemented yet

# Removed only from the answer visible to the user. Both will still be used internally.
REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7 = True
REMOVE_INTERNAL_DIALOG_FROM_ANSWER7 = True

BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 = True

MAX_TELEGRAM_MESSAGE_LEN = 4096 # hardcoded by Telegram

CHARS_PER_TOKEN = 3584718 / 1064452 # experimental values for Gemini 2.5

MAX_TOKENS_ALLOWED_IN_REQUEST = 1048576 # got it from Google's error message

EXPENDABLE_MINDFILE_PART = "dialogs"

# Safety margin for token limit calculations
TOKEN_SAFETY_MARGIN = 1.2