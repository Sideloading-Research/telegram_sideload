from utils.mind_data_manager import MindDataManager
from bot_config import (
    get_max_messages_num,
    GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION
)
from utils.prompt_utils import format_user_info_prompt, build_initial_conversation_history

def _build_initial_assistant_messages(mind_manager: MindDataManager):
    """Returns the initial messages that should be present in every conversation."""
    system_message, context = mind_manager.get_current_data()

    user_info_prompt_addition = format_user_info_prompt()
    # print(f"User info prompt addition: {user_info_prompt_addition}") # Optional debug

    full_system_message = system_message
    if GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION:
        full_system_message += "\n\n" + GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION
    if user_info_prompt_addition:
        full_system_message += "\n\n" + user_info_prompt_addition
    
    # Debug print
    # print(f"Full system message being used:\n{full_system_message}")

    return build_initial_conversation_history(system_message=full_system_message, context=context)

class Conversation:
    def __init__(self, mind_manager: MindDataManager):
        self.mind_manager = mind_manager
        self.messages = _build_initial_assistant_messages(self.mind_manager)
        self.max_messages_num = get_max_messages_num()

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._trim_history()

    def add_assistant_message(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self._trim_history()

    def get_messages(self):
        return self.messages.copy() # Return a copy to prevent external modification

    def reset(self):
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
            self._conversations[conversation_key] = Conversation(self.mind_manager)
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

# Example Usage (for testing or if this module were run directly)
# if __name__ == '''__main__''':
#     class MockMindManager:
#         def get_current_data(self):
#             return "System Prompt from Mock", "Initial Assistant context from Mock"

#     mock_mm = MockMindManager()
#     cm = ConversationManager(mind_manager=mock_mm)

#     user1_key = "user123"
#     conv1 = cm.get_or_create_conversation(user1_key)
#     print(f"Initial messages for {user1_key}: {conv1.get_messages()}")

#     cm.add_user_message(user1_key, "Hello there!")
#     print(f"After user message for {user1_key}: {conv1.get_messages()}")
#     cm.add_assistant_message(user1_key, "General Kenobi!")
#     print(f"After assistant message for {user1_key}: {conv1.get_messages()}")

#     cm.reset_conversation(user1_key)
#     print(f"After reset for {user1_key}: {conv1.get_messages()}")

#     # Test trimming
#     # Override max_messages_num for testing (in a real scenario, this comes from config)
#     conv1.max_messages_num = 5 # System, Assistant, User, Assistant, User (trim next)
#     print(f"Set max messages to {conv1.max_messages_num} for {user1_key}")
    
#     # Rebuild initial messages as reset does this.
#     # The _trim_history logic assumes initial messages are present.
#     # The trim function now rebuilds initial_messages correctly
    
#     cm.add_user_message(user1_key, "User Q1")
#     cm.add_assistant_message(user1_key, "Assistant A1")
#     print(f"Len: {cm.get_conversation_length(user1_key)}, Messages: {conv1.get_messages()}")
#     cm.add_user_message(user1_key, "User Q2") # This should trigger a trim if MAX is 5 (sys, assist, q1, a1, q2)
#     print(f"Len: {cm.get_conversation_length(user1_key)}, Messages after Q2 for {user1_key}: {conv1.get_messages()}")
#     cm.add_assistant_message(user1_key, "Assistant A2")
#     print(f"Len: {cm.get_conversation_length(user1_key)}, Messages after A2 for {user1_key}: {conv1.get_messages()}")
#     cm.add_user_message(user1_key, "User Q3")
#     print(f"Len: {cm.get_conversation_length(user1_key)}, Messages after Q3 for {user1_key}: {conv1.get_messages()}")

#     # Expected: System, Assistant, Q2, A2, Q3 (if max is 5 and includes 2 initial) 