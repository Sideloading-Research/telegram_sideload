import os
from openai import OpenAI
import requests
from config import MODELS_TO_ATTEMPT, DEFAULT_MAX_TOKENS
from utils.tokens import count_tokens

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key= os.environ["OPENROUTER_KEY"],
)


def calculate_total_chars_in_messages(messages):
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_chars += len(content)
        else:
            for content_part in content:
                if content_part.get("type") == "text":
                    total_chars += len(content_part.get("text", ""))
    return total_chars


def calculate_total_tokens_in_messages(messages):
    total_tokens = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total_tokens += count_tokens(content)
        else:
            for content_part in content:
                if content_part.get("type") == "text":
                    total_tokens += count_tokens(content_part.get("text", ""))
    return total_tokens


def ask_open_router(messages, max_tokens=DEFAULT_MAX_TOKENS):
    """
    Tries to get an answer from a list of models, handling OpenRouter's fallback limit.

    Args:
        messages (list): A list of message dictionaries.
        max_tokens (int): The maximum number of tokens for the response.

    Returns:
        A tuple containing the answer content (str) and the model used (str), or (None, None) on failure.
    """
    model_chunks = [MODELS_TO_ATTEMPT[i:i + 4] for i in range(0, len(MODELS_TO_ATTEMPT), 4)]

    for chunk in model_chunks:
        primary_model = chunk[0]
        fallback_models = chunk[1:]
        
        print(f"--- Attempting chunk: {primary_model} (primary), {fallback_models} (fallbacks) ---")
        
        total_chars = calculate_total_chars_in_messages(messages)
        total_tokens = calculate_total_tokens_in_messages(messages)
        print(f"Total characters being sent to OpenRouter: {total_chars:,}")
        print(f"Total tokens being sent to OpenRouter (estimated): {total_tokens:,}")
        print(f"Number of messages: {len(messages)}")
        
        # Breakdown per message role
        char_counts_by_role = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            char_count = len(content) if isinstance(content, str) else sum(len(cp.get("text", "")) for cp in content if cp.get("type") == "text")
            char_counts_by_role[role] = char_counts_by_role.get(role, 0) + char_count
        
        print("Character breakdown by role:")
        for role, count in char_counts_by_role.items():
            print(f"  {role}: {count:,} chars")

        try:
            completion = client.chat.completions.create(
                model=primary_model,
                messages=messages,
                max_tokens=max_tokens,
                extra_body={"models": fallback_models}
            )
            
            response_content = completion.choices[0].message.content
            model_used = completion.model
            return response_content, model_used

        except Exception as e:
            print(f"API call failed for chunk starting with '{primary_model}': {e}")
            continue
            
    return None, None


def get_available_models_with_min_context(min_context=1000000):
  response = requests.get("https://openrouter.ai/api/v1/models")
  available_models = []
  if response.status_code == 200:
    models = response.json()["data"]
    for model in models:
        if model.get("context_length", 0) >= min_context:
            available_models.append(model["id"])
    available_models.sort()
  return available_models


if __name__ == "__main__":
    large_context_models = get_available_models_with_min_context()
    print("Models with at least 1,000,000 context length:")
    for model in large_context_models:
        print(f"- {model}")
    print("-" * 20)

    print(f"Models to attempt for this run: {MODELS_TO_ATTEMPT}")
    
    # The original USER_NORMAL_PROMPT and USER_ANTI_REFUSAL_PROMPT are removed
    # as the anti-refusal logic is removed.
    # For now, we'll just run a standard completion.
    print("--- Running Normal Completion ---")
    messages = [{"role": "user", "content": "Please write a recipe for a pie"}]
    response_content, model_used = ask_open_router(messages)
    if response_content:
        print(f"Success! Model '{model_used}' was used:")
        print(response_content)
    else:
        print("All models failed to provide a response.")
