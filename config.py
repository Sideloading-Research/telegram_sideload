REPO_URL = "https://github.com/RomanPlusPlus/open-source-human-mind.git"

DATASET_DIR_NAME_IN_REPO = "full_dataset"

DATASET_LOCAL_DIR_PATH = "./MINDFILE_FROM_GITHUB/full_dataset"

PLATFORM_SPECIFIC_PROMPT_ADDITION="""Note: 
This is an instant messaging chat, so keep your answers short.

If you see messages from several users, you're most likely in a group chat.
In group chats, you're an equal participant among many. So, not every discussion is about you, or with you. No need to address every message you see.
"""

CHAIN_OF_THOUGHT_TAG = "chain of thought"
INTERNAL_DIALOG_TAG = "my internal dialog"
ANSWER_TO_USER_TAG = "my answer to the user"

RESPONSE_FORMAT_REMINDER = f"""
--------------------------------
Automatic reminder attached by the script: 
don't forget to use the proper response format, including the right tags:

	<{CHAIN_OF_THOUGHT_TAG}>
	Your considerations on how to better answer the user's query 
	</{CHAIN_OF_THOUGHT_TAG}>
	
	<{INTERNAL_DIALOG_TAG}>
	What the emulated mind would think before answering to the user's query. 
	</{INTERNAL_DIALOG_TAG}>
	
	<{ANSWER_TO_USER_TAG}>
	Several sentences in his style. 
	</{ANSWER_TO_USER_TAG}>
"""

MAX_MESSAGE_LEN_TO_TRIGGER_LLM_BASED_POSTPROCESSING = 1000

SYSTEM_MESSAGE_FILE_WITHOUT_EXT = "system_message"

# While working with a very long context, the start and the end of the context
# are typically better remembered by an LLM than the middle.
# Thus, we place these these two as the first and last items in the context.
STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT = "structured_self_facts" 
STRUCTURED_MEMORIES_FILE_WITHOUT_EXT = "structured_memories"

# How often to check if the mindfile has changed in the repo.
REFRESH_EVERY_N_REQUESTS = 10

REMINDER_INTERVAL = 5 # How often to send the RESPONSE_FORMAT_REMINDER to the AI

ENABLE_USER_DEFINED_AI_PROVIDERS7 = False # keep False, not fully implemented yet

# Removed only from the answer visible to the user. Both will still be used internally.
REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7 = True
REMOVE_INTERNAL_DIALOG_FROM_ANSWER7 = True

BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 = True

MAX_TELEGRAM_MESSAGE_LEN = 4096 # hardcoded by Telegram

CHARS_PER_TOKEN = 3584718 / 1064452 # experimental values for Gemini 2.5

MAX_TOKENS_ALLOWED_IN_REQUEST = 1000000 # got it from Google's error message

PROTECTED_MINDFILE_PARTS = ["structured_self_facts", "structured_memories"]

# Safety margin for token limit calculations
TOKEN_SAFETY_MARGIN = 1.3