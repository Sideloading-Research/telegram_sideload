from bot_config import get_user_descriptions

def format_user_info_prompt():
    """Formats the user descriptions into a string for the prompt."""
    user_descriptions_dict = get_user_descriptions()
    if not user_descriptions_dict:
        return ""
    
    formatted_items = []
    for user_id, description in user_descriptions_dict.items():
        formatted_items.append(f"- {user_id}: {description}")
    
    return "Some known users:\n" + "\n".join(formatted_items)


def build_initial_conversation_history(system_message: str, context: str | None = None, user_prompt: str | None = None) -> list[dict[str, str]]:
    """
    Builds the initial conversation history with a system message and optional context.
    Context is placed in an assistant message, which is a better practice than stuffing it into the system prompt.
    """
    messages = [{"role": "system", "content": system_message}]
    
    if context:
        messages.append({"role": "assistant", "content": context})
    
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
        
    return messages


def extract_conversational_messages(messages_history: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Extracts only the actual conversational messages from the full messages_history.
    
    The full messages_history structure from ConversationManager is:
    - Index 0: System message
    - Index 1+: Actual user/assistant conversation
    
    This function returns only the actual conversation (index 1+), skipping the
    initial system message.
    
    Args:
        messages_history: Full message history from ConversationManager
        
    Returns:
        List of conversational messages only (no system prompt)
    """
    if len(messages_history) <= 1:
        return []
    return messages_history[1:]
