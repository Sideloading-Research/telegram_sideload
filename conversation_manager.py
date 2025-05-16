from utils.mind_data_manager import MindDataManager
from bot_config import (
    get_user_descriptions, 
    get_max_messages_num,
    GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION
)

def _format_user_info_prompt():
    user_descriptions_dict = get_user_descriptions()
    if not user_descriptions_dict:
        return ""
    
    formatted_items = []
    for user_id, description in user_descriptions_dict.items():
        formatted_items.append(f"- {user_id}: {description}")
    
    return "Some known users:\n" + "\n".join(formatted_items)

def _build_initial_assistant_messages(mind_manager: MindDataManager):
    """Returns the initial messages that should be present in every conversation."""
    system_message, context = mind_manager.get_current_data()

    user_info_prompt_addition = _format_user_info_prompt()
    # print(f"User info prompt addition: {user_info_prompt_addition}") # Optional debug

    full_system_message = system_message
    if GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION:
        full_system_message += "\n\n" + GLOBAL_PLATFORM_SPECIFIC_PROMPT_ADDITION
    if user_info_prompt_addition:
        full_system_message += "\n\n" + user_info_prompt_addition
    
    # Debug print
    # print(f"Full system message being used:\n{full_system_message}")

    return [
        {"role": "system", "content": full_system_message},
        {"role": "assistant", "content": context}
    ]

class Conversation:
    def __init__(self, user_id: str, mind_manager: MindDataManager):
        self.user_id = user_id
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
        self._conversations = {} # user_id -> Conversation object
        self.mind_manager = mind_manager

    def get_or_create_conversation(self, user_id: str) -> Conversation:
        if user_id not in self._conversations:
            self._conversations[user_id] = Conversation(user_id, self.mind_manager)
        return self._conversations[user_id]

    def reset_conversation(self, user_id: str) -> bool:
        if user_id in self._conversations:
            self._conversations[user_id].reset()
            return True
        return False

    def get_conversation_messages(self, user_id: str) -> list:
        conversation = self.get_or_create_conversation(user_id)
        return conversation.get_messages()

    def add_user_message(self, user_id: str, content: str):
        conversation = self.get_or_create_conversation(user_id)
        conversation.add_user_message(content)

    def add_assistant_message(self, user_id: str, content: str):
        conversation = self.get_or_create_conversation(user_id)
        conversation.add_assistant_message(content)
        
    def get_conversation_length(self, user_id: str) -> int:
        if user_id in self._conversations:
            return len(self._conversations[user_id].get_messages())
        return 0

# Example Usage (for testing or if this module were run directly)
# if __name__ == '''__main__''':
#     class MockMindManager:
#         def get_current_data(self):
#             return "System Prompt from Mock", "Initial Assistant context from Mock"

#     mock_mm = MockMindManager()
#     cm = ConversationManager(mind_manager=mock_mm)

#     user1 = "user123"
#     conv1 = cm.get_or_create_conversation(user1)
#     print(f"Initial messages for {user1}: {conv1.get_messages()}")

#     cm.add_user_message(user1, "Hello there!")
#     print(f"After user message for {user1}: {conv1.get_messages()}")
#     cm.add_assistant_message(user1, "General Kenobi!")
#     print(f"After assistant message for {user1}: {conv1.get_messages()}")

#     cm.reset_conversation(user1)
#     print(f"After reset for {user1}: {conv1.get_messages()}")

#     # Test trimming
#     # Override max_messages_num for testing (in a real scenario, this comes from config)
#     conv1.max_messages_num = 5 # System, Assistant, User, Assistant, User (trim next)
#     print(f"Set max messages to {conv1.max_messages_num} for {user1}")
    
#     # Rebuild initial messages as reset does this.
#     # The _trim_history logic assumes initial messages are present.
#     # The trim function now rebuilds initial_messages correctly
    
#     cm.add_user_message(user1, "User Q1")
#     cm.add_assistant_message(user1, "Assistant A1")
#     print(f"Len: {cm.get_conversation_length(user1)}, Messages: {conv1.get_messages()}")
#     cm.add_user_message(user1, "User Q2") # This should trigger a trim if MAX is 5 (sys, assist, q1, a1, q2)
#     print(f"Len: {cm.get_conversation_length(user1)}, Messages after Q2 for {user1}: {conv1.get_messages()}")
#     cm.add_assistant_message(user1, "Assistant A2")
#     print(f"Len: {cm.get_conversation_length(user1)}, Messages after A2 for {user1}: {conv1.get_messages()}")
#     cm.add_user_message(user1, "User Q3")
#     print(f"Len: {cm.get_conversation_length(user1)}, Messages after Q3 for {user1}: {conv1.get_messages()}")

#     # Expected: System, Assistant, Q2, A2, Q3 (if max is 5 and includes 2 initial) 