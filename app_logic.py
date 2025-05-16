from conversation_manager import ConversationManager
from ai_service import get_ai_response # No longer need update_provider_from_user_input directly here
from utils.answer_modifications import modify_answer_before_sending_to_telegram
from utils.constants import c # For c.reset_dialog_command


def _get_effective_username(user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> str:
    """Constructs a comprehensive username string for logging and context."""
    user_id_str = f"{user_id}"
    effective_username = f"id_{user_id_str}"
    if username:
        effective_username += f" @{username}"
    if first_name:
        effective_username += f" {first_name}"
    if last_name:
        effective_username += f" {last_name}"
    return effective_username


class AppLogic:
    def __init__(self, conversation_manager: ConversationManager, allowed_user_ids: list[int], allowed_group_ids: list[int]):
        self.conversation_manager = conversation_manager
        self.allowed_user_ids = allowed_user_ids
        self.allowed_group_ids = allowed_group_ids
        # ai_service is not stored as it's stateless for now, get_ai_response is called directly.
        # mind_manager is managed by conversation_manager for initial prompts.

    def check_authorization(self, chat_type: str, user_id: int, chat_id: int) -> bool:
        """Checks if the user or chat is authorized based on type and IDs."""
        if chat_type == 'private':
            return user_id in self.allowed_user_ids
        elif chat_type in ['group', 'supergroup']:
            return chat_id in self.allowed_group_ids
        return False

    def process_user_request(self, 
                             user_id: int, 
                             raw_user_message: str, 
                             username: str = None, 
                             first_name: str = None, 
                             last_name: str = None) -> tuple[str, str | None]:
        """
        Processes the user's request and returns the bot's answer and a potential provider switch report.
        
        Returns:
            tuple[str, str | None]: (answer_to_send, provider_report_message_or_none)
        """
        user_id_str = str(user_id) # ConversationManager uses string IDs
        # Authorization check should ideally happen before processing
        # However, the call to this function in main.py is already inside an is_allowed check.
        # If we want AppLogic to be fully self-contained for this, the check could be duplicated here
        # or is_allowed could be called from here. For now, keeping it as is since main.py handles the guard.

        effective_username = _get_effective_username(user_id, username, first_name, last_name)
        print(f"Processing request from user: {effective_username}")

        # Handle reset command
        if raw_user_message.lower() == c.reset_dialog_command:
            if self.conversation_manager.reset_conversation(user_id_str):
                return "Dialog has been reset.", None
            else:
                return "No active dialog to reset. Starting a new one now.", None

        formatted_user_message = f"{effective_username} wrote: {raw_user_message}"
        
        self.conversation_manager.add_user_message(user_id_str, formatted_user_message)
        
        messages_history = self.conversation_manager.get_conversation_messages(user_id_str)
        
        ai_answer, provider_report = get_ai_response(messages_history, raw_user_message, max_length=500)
        
        self.conversation_manager.add_assistant_message(user_id_str, ai_answer)
        
        print(f"Current conversation length for user {user_id_str}: {self.conversation_manager.get_conversation_length(user_id_str)}")

        final_answer = modify_answer_before_sending_to_telegram(ai_answer)
        
        return final_answer, provider_report 