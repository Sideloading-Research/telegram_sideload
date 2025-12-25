import os
import sys
import importlib.util
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
from utils.diag_utils import format_diag_info
from plugins import config_plugins

# Dynamic Plugin Loading
PLUGINS = []
PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "plugins")

def load_plugins():
    """Dynamically load all enabled plugins from the plugins directory."""
    global PLUGINS
    PLUGINS = []
    if not os.path.exists(PLUGINS_DIR):
        print(f"Plugins directory not found: {PLUGINS_DIR}")
        return

    for plugin_name in os.listdir(PLUGINS_DIR):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        if os.path.isdir(plugin_path):
            # Check if plugin is enabled in config
            if not config_plugins.is_plugin_enabled(plugin_name):
                print(f"Plugin {plugin_name} is disabled in config.")
                continue
                
            main_py = os.path.join(plugin_path, "main.py")
            if os.path.exists(main_py):
                try:
                    spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", main_py)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"plugins.{plugin_name}"] = module
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "is_plugin_applicable") and hasattr(module, "process_messages"):
                        PLUGINS.append(module)
                        print(f"Loaded plugin: {plugin_name}")
                    else:
                        print(f"Plugin {plugin_name} missing required functions.")
                except Exception as e:
                    print(f"Error loading plugin {plugin_name}: {e}")

# Load plugins at module initialization
load_plugins()


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
        self.current_provider = None  # Track current AI provider for plugins
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

    def _get_answer_from_ai(self, messages_history):
        """
        A wrapper for ai_service.get_ai_response.
        It's not used anymore, because we switched to the worker-based architecture.
        But let's keep it here for now, for debugging purposes.
        """
        answer, report, model_name = get_ai_response(
            messages_history, self.user_input_for_provider_selection
        )
        diag_info = {"model_name": model_name}
        return answer, report, diag_info

    def check_authorization(self, chat_type: str, user_id: int, chat_id: int) -> bool:
        """Checks if the user or chat is authorized based on type and IDs."""
        if chat_type == "API":
            return True
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
                             last_name: str = None) -> tuple[str | None, str | None, dict]: # Modified return type
        """
        Processes the user's request. Adds user message to history.
        If generate_ai_reply is True, calls AI, adds AI response to history, and returns answer.
        Otherwise, returns (None, None, {}).
        
        Returns:
            tuple[str | None, str | None, dict]: (answer_to_send, provider_report_message_or_none, diag_info)
        """
        # Determine the conversation key based on chat type and config
        if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP] and BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
            conversation_key = str(chat_id)
            print(f"Using CHAT_ID ({chat_id}) as conversation key for group chat.")
        else:
            conversation_key = str(user_id)
            if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                 print(f"Using USER_ID ({user_id}) as conversation key for group chat (BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 is False).")
            elif chat_type == "API":
                 print(f"Using USER_ID ({user_id}) as conversation key for API request.")
            else:
                 print(f"Using USER_ID ({user_id}) as conversation key for private chat.")

        effective_username = _get_effective_username(user_id, username, first_name, last_name)
        print(f"Processing request from user: {effective_username} in context of conversation_key: {conversation_key}. Generate AI reply: {generate_ai_reply}")

        # Handle reset command
        if raw_user_message.lower() == c.reset_dialog_command:
            if self.conversation_manager.reset_conversation(conversation_key):
                # Reset commands always provide a direct response, not from AI.
                return "Dialog has been reset.", None, {}
            else:
                return "No active dialog to reset. Starting a new one now.", None, {}

        formatted_user_message = f"{effective_username} wrote: {raw_user_message}"
        
        self.conversation_manager.add_user_message(conversation_key, formatted_user_message)
        
        print(f"Added user message from {effective_username} to history for key {conversation_key}.")

        if not generate_ai_reply:
            print(f"AI reply generation skipped for key {conversation_key} as per request.")
            return None, None, {}

        # Proceed with AI response generation

        # Proceed with AI response generation
        messages_history = self.conversation_manager.get_conversation_messages(conversation_key)
        
        # Plugin processing - preprocess messages before sending to AI
        plugin_processed = False
        current_provider = self.current_provider or "openai"  # Default provider
        
        for plugin in PLUGINS:
            try:
                if plugin.is_plugin_applicable(messages_history, current_provider):
                    plugin_name = plugin.__name__.split('.')[-1]
                    print(f"Plugin {plugin_name} triggered.")
                    
                    # Process messages through plugin
                    updated_messages = plugin.process_messages(messages_history, current_provider)
                    if updated_messages:
                        messages_history = updated_messages
                        plugin_processed = True
                        print(f"Messages processed by plugin: {plugin_name}")
                        break  # Only first applicable plugin processes
            except Exception as e:
                print(f"Error executing plugin {plugin.__name__}: {e}")
        
        final_ai_answer, provider_report, diag_info = self._generate_and_verify_answer(messages_history, raw_user_message)

        final_answer = modify_answer_before_sending_to_telegram(final_ai_answer)

        # Save only the user-facing answer to conversation history (not the full AI response with chain of thought)
        self.conversation_manager.add_assistant_message(conversation_key, final_answer)

        print(f"Current conversation length for key {conversation_key}: {self.conversation_manager.get_conversation_length(conversation_key)}")

        if SHOW_DIAG_INFO7:
            diag_str = format_diag_info(diag_info)
            final_answer += f"\n\n{diag_str}"
        
        return final_answer, provider_report, diag_info
    
    # Plugin Management Methods
    def get_plugin_status(self) -> dict:
        """Get the current status of all plugins."""
        return config_plugins.get_plugin_status()
    
    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a specific plugin and reload plugins."""
        if config_plugins.enable_plugin(plugin_name):
            load_plugins()
            return True
        return False
    
    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a specific plugin and reload plugins."""
        if config_plugins.disable_plugin(plugin_name):
            load_plugins()
            return True
        return False
    
    def enable_all_plugins(self) -> None:
        """Enable all plugins and reload."""
        config_plugins.enable_all_plugins()
        load_plugins()
    
    def disable_all_plugins(self) -> None:
        """Disable all plugins and reload."""
        config_plugins.disable_all_plugins()
        load_plugins() 