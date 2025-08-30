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
