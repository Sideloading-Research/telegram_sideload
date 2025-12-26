import os
import anthropic
from utils.creds_handler import CREDS
from config import DEFAULT_MAX_TOKENS


def build_model_handle():
    handle = CREDS.get("ANTHROPIC_MODEL")  # e.g. "claude-3-5-sonnet"
    return handle


def build_client():
    key = CREDS.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key)
    return client


if CREDS.get("AI_PROVIDER") == "anthropic":
    MODEL = build_model_handle()
    CLIENT = build_client()
    pass
else:
    MODEL = None
    CLIENT = None


def extract_and_remove_system_message(messages):
    system_message = None
    user_messages = []
    for message in messages:
        if message.get("role") == "system":
            system_message = message.get("content")
        else:
            user_messages.append(message)
    return system_message, user_messages


def ask_anthropic(messages, max_tokens=DEFAULT_MAX_TOKENS):
    """
    Sends a request to the Anthropic API.
    """
    model_name = CREDS.get("ANTHROPIC_MODEL")
    api_key = CREDS.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    system_message = ""
    if messages and messages[0]["role"] == "system":
        system_message = messages[0]["content"]
        messages = messages[1:]

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            system=system_message,
            messages=messages,
        )
        return response.content[0].text, model_name
    except Exception as e:
        print(f"An error occurred in ask_anthropic: {e}")
        return f"Error in ask_anthropic: {e}", model_name
