import os
import anthropic
from utils.creds_handler import CREDS


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
    print(f"Loaded Anthropic model: {MODEL}")
    print(f"Loaded Anthropic client: {CLIENT}")
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


def ask_anthropic(messages, max_length):
    system_message, clean_messages = extract_and_remove_system_message(messages)

    message = CLIENT.messages.create(
        model=MODEL,
        system=system_message,
        max_tokens=max_length,
        messages=clean_messages
    )
    # answer = message.content
    # print("answer", answer)

    # The content is a list of TextBlock objects
    text_blocks = message.content

    # Extract text from the first TextBlock
    if text_blocks and hasattr(text_blocks[0], 'text'):
        answer = text_blocks[0].text
    else:
        answer = "<non textual answer, not supported yet>"  # or some default value

    success7 = True # TODO: check if the answer is successful
    return answer, success7
