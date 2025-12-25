import os
from dotenv import load_dotenv



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

    # First, check what required credentials are missing from environment
    required_keys = [key for key, default_value in keys_dict.items() if default_value is None]

    for key, default_value in keys_dict.items():
        if key in os.environ:
            creds[key] = os.environ[key]
            successful_keys.append(key)
        elif default_value is not None:
            creds[key] = default_value
            successful_keys.append(key)
        else:
            missing_keys.append(key)

    # If any required credentials are missing, try to load from .env
    if missing_keys:
        print("Environ variables are missing some required credentials. Trying to load from .env file...")
        env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_file_path):
            # Load .env file
            load_dotenv(env_file_path)

            # Check if .env contains ALL required credentials
            env_creds = {}
            env_missing_keys = []

            for key in required_keys:
                if key in os.environ:
                    env_creds[key] = os.environ[key]
                else:
                    env_missing_keys.append(key)

            if env_missing_keys:
                raise Exception(f".env file is missing required credentials: {', '.join(env_missing_keys)}. All required credentials must be present in .env when falling back to .env loading.")
            else:
                print("All required credentials are present in .env file.")

            # Load all credentials from environment (including newly loaded .env values)
            creds = {}
            for key, default_value in keys_dict.items():
                if key in os.environ:
                    creds[key] = os.environ[key]
                elif default_value is not None:
                    creds[key] = default_value
                else:
                    # This should not happen since we verified all required keys are in .env
                    raise Exception(f"Unexpected missing key after .env loading: {key}")
        else:
            msg = f"Required keys not found in environment variables: {', '.join(missing_keys)}."
            if successful_keys:
                msg += f" These keys were found: {', '.join(successful_keys)}"
            raise Exception(msg)

    return creds


CREDS = get_creds()
