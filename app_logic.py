from conversation_manager import ConversationManager
from ai_service import get_ai_response # No longer need update_provider_from_user_input directly here
from utils.answer_modifications import modify_answer_before_sending_to_telegram
from utils.constants import c # For c.reset_dialog_command
from config import (
    BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7,
    SHOW_DIAG_INFO7
)
from telegram.constants import ChatType # ADDED - for explicit comparison
from workers.integration_worker import IntegrationWorker


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

    def _generate_and_verify_answer(self, messages_history: list[dict[str, str]], raw_user_message: str) -> tuple[str, str | None, dict]:
        """
        Generates an AI response by invoking the IntegrationWorker.
        Returns the best answer, the provider report, and a dictionary with diagnostic info.
        """
        mindfile_instance = self.conversation_manager.mind_manager.get_mindfile()
        integration_worker = IntegrationWorker(mindfile=mindfile_instance)
        
        final_ai_answer, provider_report, diag_info = integration_worker.process(
            messages_history=messages_history,
            raw_user_message=raw_user_message
        )
        
        return final_ai_answer, provider_report, diag_info

    def check_authorization(self, chat_type: str, user_id: int, chat_id: int) -> bool:
        """Checks if the user or chat is authorized based on type and IDs."""
        if chat_type == ChatType.PRIVATE: # Using ChatType constant
            return user_id in self.allowed_user_ids
        elif chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Using ChatType constants
            return chat_id in self.allowed_group_ids
        return False

    def process_user_request(self, 
                             user_id: int, 
                             raw_user_message: str, 
                             chat_id: int,             # ADDED
                             chat_type: str,           # ADDED
                             generate_ai_reply: bool,   # ADDED
                             username: str = None, 
                             first_name: str = None, 
                             last_name: str = None) -> tuple[str | None, str | None]: # Modified return type
        """
        Processes the user's request. Adds user message to history.
        If generate_ai_reply is True, calls AI, adds AI response to history, and returns answer.
        Otherwise, returns (None, None).
        
        Returns:
            tuple[str | None, str | None]: (answer_to_send, provider_report_message_or_none)
        """
        # Determine the conversation key based on chat type and config
        if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP] and BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
            conversation_key = str(chat_id)
            print(f"Using CHAT_ID ({chat_id}) as conversation key for group chat.")
        else:
            conversation_key = str(user_id)
            if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                 print(f"Using USER_ID ({user_id}) as conversation key for group chat (BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 is False).")
            else:
                 print(f"Using USER_ID ({user_id}) as conversation key for private chat.")

        effective_username = _get_effective_username(user_id, username, first_name, last_name)
        print(f"Processing request from user: {effective_username} in context of conversation_key: {conversation_key}. Generate AI reply: {generate_ai_reply}")

        # Handle reset command
        if raw_user_message.lower() == c.reset_dialog_command:
            if self.conversation_manager.reset_conversation(conversation_key):
                # Reset commands always provide a direct response, not from AI.
                return "Dialog has been reset.", None
            else:
                return "No active dialog to reset. Starting a new one now.", None

        formatted_user_message = f"{effective_username} wrote: {raw_user_message}"
        
        self.conversation_manager.add_user_message(conversation_key, formatted_user_message)
        
        print(f"Added user message from {effective_username} to history for key {conversation_key}.")

        if not generate_ai_reply:
            print(f"AI reply generation skipped for key {conversation_key} as per request.")
            return None, None

        # Proceed with AI response generation
        messages_history = self.conversation_manager.get_conversation_messages(conversation_key)
        
        final_ai_answer, provider_report, diag_info = self._generate_and_verify_answer(messages_history, raw_user_message)
        
        self.conversation_manager.add_assistant_message(conversation_key, final_ai_answer)
        
        print(f"Current conversation length for key {conversation_key}: {self.conversation_manager.get_conversation_length(conversation_key)}")

        final_answer = modify_answer_before_sending_to_telegram(final_ai_answer)

        if SHOW_DIAG_INFO7:
            retries = diag_info.get("retries", "N/A")
            sys_compl = diag_info.get("scores", {}).get("sys_message_compliance", "N/A")
            self_desc = diag_info.get("scores", {}).get("self_description_correctness", "N/A")
            
            diag_str = f"[quality_retries:{retries}; sys_msg_compl:{sys_compl}; self:{self_desc}]"
            
            final_answer += f"\n\n{diag_str}"
        
        return final_answer, provider_report 