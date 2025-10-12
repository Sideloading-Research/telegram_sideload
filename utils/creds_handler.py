import os



keys_dict = {
    "AI_PROVIDER": "",  # Optional, falls back to default in config.py
    "GOOGLE_API_KEY": "dummy", # Required if AI_PROVIDER is "google"
    "GOOGLE_MODEL_NAME": "dummy", # Required if AI_PROVIDER is "google"
    "ALLOWED_USER_IDS": None,  # Required
    "ALLOWED_GROUP_IDS": None,  # Required
    "TELEGRAM_LLM_BOT_TOKEN": None,  # Required
    "ANTHROPIC_MODEL": "dummy",  # Required if AI_PROVIDER is "anthropic"
    "ANTHROPIC_API_KEY": "dummy",  # Required if AI_PROVIDER is "anthropic"
    "OPENAI_MODEL": "dummy",  # Required if AI_PROVIDER is "openai"
    "OPENAI_API_KEY": "dummy",  # Required if AI_PROVIDER is "openai"
    "OPENROUTER_KEY": None, # Required if AI_PROVIDER is "openrouter"
    "USERS_INFO": "", # Optional, information about users
    "TRIGGER_WORDS": "", # Optional, trigger words for the bot
}


def get_creds():
    creds = {}
    successful_keys = []
    missing_keys = []
    
    for key, default_value in keys_dict.items():
        if key in os.environ:
            creds[key] = os.environ[key]
            successful_keys.append(key)
        elif default_value is not None:
            creds[key] = default_value
            successful_keys.append(key)
        else:
            missing_keys.append(key)
    
    if missing_keys:
        msg = f"Required keys not found in environment variables: {', '.join(missing_keys)}."
        if successful_keys:
            msg += f" These keys were found: {', '.join(successful_keys)}"
        raise Exception(msg)
            
    return creds


CREDS = get_creds()
