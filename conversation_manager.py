from utils.mind_data_manager import MindDataManager
from bot_config import (
    get_max_messages_num,
    GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION
)
from config import RESPONSE_FORMAT_REMINDER, REMINDER_INTERVAL
from utils.prompt_utils import format_user_info_prompt, build_initial_conversation_history
from utils import chat_logger

def _build_initial_assistant_messages(mind_manager: MindDataManager):
    """
    Returns the initial messages that should be present in every conversation.
    
    Note: This only stores the system message, NOT the full mindfile context.
    Each worker will load its own context as needed based on its specific requirements.
    """
    system_message, _ = mind_manager.get_current_data()  # Ignore context, workers will load it

    user_info_prompt_addition = format_user_info_prompt()
    # print(f"User info prompt addition: {user_info_prompt_addition}") # Optional debug

    full_system_message = system_message
    if GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION:
        full_system_message += "\n\n" + GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION
    if user_info_prompt_addition:
        full_system_message += "\n\n" + user_info_prompt_addition
    
    # Debug print
    # print(f"Full system message being used:\n{full_system_message}")

    # Don't pass context - workers will load what they need
    return build_initial_conversation_history(system_message=full_system_message, context=None)

class Conversation:
    def __init__(self, mind_manager: MindDataManager, conversation_key: str):
        self.mind_manager = mind_manager
        self.conversation_key = conversation_key
        self.max_messages_num = get_max_messages_num()
        self.messages = _build_initial_assistant_messages(self.mind_manager)
        self.user_message_counter = 0
        self._load_history_from_disk()

    def _load_history_from_disk(self):
        initial_messages_len = len(self.messages)
        limit = self.max_messages_num - initial_messages_len
        if limit <= 0:
            limit = 0
            
        history = chat_logger.load_chat_history(self.conversation_key, limit=limit)
        self.messages.extend(history)

    def add_user_message(self, content: str):
        chat_logger.append_message(self.conversation_key, "user", content)
        
        self.user_message_counter += 1
        if REMINDER_INTERVAL > 0 and self.user_message_counter % REMINDER_INTERVAL == 0:
            content += f"\n\n{RESPONSE_FORMAT_REMINDER}"
            print(f"---- Added RESPONSE_FORMAT_REMINDER (user message #{self.user_message_counter}) ----")

        self.messages.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        chat_logger.append_message(self.conversation_key, "assistant", content)
        self.messages.append({"role": "assistant", "content": content})
        self._trim_history()

    def get_messages(self):
        return self.messages.copy() # Return a copy to prevent external modification

    def reset(self):
        chat_logger.archive_chat_log(self.conversation_key)
        self.messages = _build_initial_assistant_messages(self.mind_manager)

    def _trim_history(self):
        # Keeps the last MAX_MESSAGES_NUM messages, plus initial system/assistant messages
        if len(self.messages) > self.max_messages_num:
            # The initial messages are always kept at the beginning
            initial_messages = _build_initial_assistant_messages(self.mind_manager)
            num_initial_messages = len(initial_messages)
            
            # Calculate how many non-initial messages to keep
            messages_to_keep_count = self.max_messages_num - num_initial_messages
            
            if messages_to_keep_count < 0: # Should not happen if max_messages_num is reasonable
                messages_to_keep_count = 0

            # Keep initial messages + the tail of other messages
            relevant_messages = self.messages[num_initial_messages:]
            self.messages = initial_messages + relevant_messages[-messages_to_keep_count:]


class ConversationManager:
    def __init__(self, mind_manager: MindDataManager):
        self._conversations = {} # conversation_key -> Conversation object
        self.mind_manager = mind_manager

    def get_or_create_conversation(self, conversation_key: str) -> Conversation:
        if conversation_key not in self._conversations:
            self._conversations[conversation_key] = Conversation(self.mind_manager, conversation_key)
        return self._conversations[conversation_key]

    def reset_conversation(self, conversation_key: str) -> bool:
        if conversation_key in self._conversations:
            self._conversations[conversation_key].reset()
            return True
        return False

    def get_conversation_messages(self, conversation_key: str) -> list:
        conversation = self.get_or_create_conversation(conversation_key)
        return conversation.get_messages()

    def add_user_message(self, conversation_key: str, content: str):
        conversation = self.get_or_create_conversation(conversation_key)
        conversation.add_user_message(content)

    def add_assistant_message(self, conversation_key: str, content: str):
        conversation = self.get_or_create_conversation(conversation_key)
        conversation.add_assistant_message(content)
        
    def get_conversation_length(self, conversation_key: str) -> int:
        if conversation_key in self._conversations:
            return len(self._conversations[conversation_key].get_messages())
        return 0
