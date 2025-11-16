import os
from openai import OpenAI
import requests
from config import MODELS_TO_ATTEMPT, DEFAULT_MAX_TOKENS, EXPENSIVE_SMART_MODELS
from utils.tokens import count_tokens
from utils.usage_accounting import add_cost  # NEW: aggregate per-round cost
from utils.usage_accounting import is_genius_mode7  # NEW: round-scoped GENIUS mode flag

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

# Add simple usage printing helper

def _get_from(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def print_openrouter_usage(completion):
    usage = getattr(completion, "usage", None)
    if usage is None:
        print("Usage info not available from OpenRouter.")
        return

    cost = _get_from(usage, "cost", None)
    total_tokens = _get_from(usage, "total_tokens", None)
    prompt_tokens = _get_from(usage, "prompt_tokens", None)
    completion_tokens = _get_from(usage, "completion_tokens", None)

    print("OpenRouter Usage:")
    if cost is not None:
        print(f"  Cost: {cost} credits")
    if total_tokens is not None:
        print(f"  Total Tokens: {total_tokens}")
    if prompt_tokens is not None:
        print(f"  Prompt Tokens: {prompt_tokens}")
    if completion_tokens is not None:
        print(f"  Completion Tokens: {completion_tokens}")

    # Add to per-round aggregator
    try:
        add_cost(cost)
    except Exception:
        # Be resilient to aggregator issues
        pass


def ask_open_router(messages, max_tokens=DEFAULT_MAX_TOKENS):
    """
    Tries to get an answer from a list of models, handling OpenRouter's fallback limit.

    Args:
        messages (list): A list of message dictionaries.
        max_tokens (int): The maximum number of tokens for the response.

    Returns:
        A tuple containing the answer content (str) and the model used (str), or (None, None) on failure.
    """
    # Build effective model list for this call (no global mutation)
    effective_models = list(MODELS_TO_ATTEMPT)
    if is_genius_mode7():
        print("GENIUS mode active: prioritizing expensive models for this round")
        # Replace first two entries if available
        if len(EXPENSIVE_SMART_MODELS) > 0:
            effective_models[0] = EXPENSIVE_SMART_MODELS[0]
        if len(EXPENSIVE_SMART_MODELS) > 1 and len(effective_models) > 1:
            effective_models[1] = EXPENSIVE_SMART_MODELS[1]

    model_chunks = [effective_models[i:i + 4] for i in range(0, len(effective_models), 4)]

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
                extra_body={
                    "models": fallback_models,
                    # Enable OpenRouter usage accounting
                    "usage": {"include": True},
                }
            )
            
            # Print usage/cost info after the call and aggregate cost
            print_openrouter_usage(completion)
            
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
