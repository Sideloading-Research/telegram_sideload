import os
from openai import OpenAI  # pip install openai

MODEL_CLASSES = ["o1", "4o"]

MODELS_NOT_SUPPORTING_SYS_MSG = ["o1"]

# OpenAI recommends reserving at least 25,000 tokens for reasoning and outputs
# https://platform.openai.com/docs/guides/reasoning/how-reasoning-works?reasoning-prompt-examples=research 
MODEL_SPECIFIC_LIMITS = {"o1": 30000}


def build_client():
    key = os.environ["OPENAI_API_KEY"]
    client = OpenAI(api_key=key)
    return client


def build_model_handle():
    handle = os.environ["OPENAI_MODEL"]  # e.g. "gpt-4o"
    return handle


if os.environ["AI_PROVIDER"] == "openai":
    MODEL = build_model_handle()
    CLIENT = build_client()
    print(f"Loaded OpenAI model: {MODEL}")
    print(f"Loaded OpenAI client: {CLIENT}")
else:
    MODEL = None
    CLIENT = None


def identify_model_class(model):
    for model_class in MODEL_CLASSES:
        if model_class.lower() in model.lower():
            return model_class
    return None

def sys_msg_conditional_removal(messages):
    # Create a new list to store modified messages
    modified_messages = []
    model_class = identify_model_class(MODEL)
    
    for message in messages:
        if model_class in MODELS_NOT_SUPPORTING_SYS_MSG and message["role"] == "system":
            # If the model doesn't support system messages, change role to "assistant"
            modified_messages.append({"role": "assistant", "content": message["content"]})
        else:
            # Otherwise, add the message as-is
            modified_messages.append(message.copy())
    
    print(f"Messages after conditional removal: {modified_messages}")
    return modified_messages


def ask_open_ai(messages, max_length):
    modified_messages = sys_msg_conditional_removal(messages)
    try:
        model_class = identify_model_class(MODEL)
        if model_class in MODEL_SPECIFIC_LIMITS:
            max_length = MODEL_SPECIFIC_LIMITS[model_class]

        # Note: for some models it's max_tokens, not max_completion_tokens
        completion = CLIENT.chat.completions.create(
            model=MODEL,
            messages=modified_messages,
            max_completion_tokens=max_length,
        )
        answer = completion.choices[0].message.content
        print(f"OpenAI response: {answer}")
    except Exception as e:
        msg = f"Error while sending to OpenAI: {e}"
        print(msg)
        answer = msg
    return answer
