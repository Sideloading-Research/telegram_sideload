import os
import time
from functools import wraps
from collections import deque

from ai_providers.anthropic_ai_provider import ask_anthropic
from ai_providers.open_ai_provider import ask_open_ai
from ai_providers.google_ai_provider import ask_google

MAX_CALLS_PER_PERIOD = 10000
PERIOD_S = 60  # 1 min

PROVIDER_FROM_ENV = os.environ.get("AI_PROVIDER", "google")


class RateLimitExceededError(Exception):
    pass


def rate_limit(max_calls, period, stop_on_limit=True):
    calls = deque()
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove calls older than the period
            while calls and calls[0] <= now - period:
                calls.popleft()
            
            if len(calls) >= max_calls:
                if stop_on_limit:
                    raise RateLimitExceededError(f"Rate limit of {max_calls} calls per {period} seconds exceeded")
                else:
                    sleep_time = calls[0] - (now - period)
                    time.sleep(sleep_time)
            
            result = func(*args, **kwargs)
            calls.append(now)
            
            # Calculate and print the current rate
            current_rate = len(calls) / period * 60  # Convert to calls per min
            print(f"Current rate: {current_rate:.2f} calls/min")
            
            return result
        return wrapper
    return decorator


@rate_limit(max_calls=MAX_CALLS_PER_PERIOD, period=PERIOD_S, stop_on_limit=True)
def ask_gpt_multi_message(messages, max_length, user_defined_provider=None):
    try:

        if user_defined_provider is None:
            provider = PROVIDER_FROM_ENV
        else:
            provider = user_defined_provider
        print(f"Using provider: {provider}")

        if provider == "openai":
            answer = ask_open_ai(messages, max_length)
        elif provider == "anthropic":
            answer = ask_anthropic(messages, max_length)
        elif provider == "google":
            answer = ask_google(messages, max_length)
        else:
            answer = f"unknown AI provider: {PROVIDER_FROM_ENV}"

        print(f"AI response: {answer}")
    except Exception as e:
        msg = f"Error while sending to AI provider: {e}"
        print(msg)
        answer = msg
    return answer




