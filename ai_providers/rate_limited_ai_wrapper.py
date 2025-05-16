import time
from functools import wraps
from collections import deque
from utils.creds_handler import CREDS
from utils.constants import c


from ai_providers.anthropic_ai_provider import ask_anthropic
from ai_providers.open_ai_provider import ask_open_ai
from ai_providers.google_ai_provider import ask_google
from utils.tokens import is_token_limit_of_request_exceeded
from utils.message_reducer import reduce_context_in_messages

MAX_CALLS_PER_PERIOD = 10000
RATE_LIMIT_PERIOD_S = 60  # 1 min

MAX_RETRIES = 10
DELAY_CONSTANT_S = 1

PROVIDER_FROM_ENV = CREDS.get("AI_PROVIDER", "google")


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


@rate_limit(max_calls=MAX_CALLS_PER_PERIOD, period=RATE_LIMIT_PERIOD_S, stop_on_limit=True)
def ask_gpt_multi_message(messages, max_length, user_defined_provider=None):
    retries = 0
    retry_info = ""

    if is_token_limit_of_request_exceeded(messages):
        print("Token limit exceeded, attempting to reduce context...")
        reduced_messages, success = reduce_context_in_messages(messages)
        
        if success:
            print("Successfully reduced context, proceeding with reduced messages")
            messages = reduced_messages
        else:
            print("Failed to reduce context sufficiently")
            return "Token limit exceeded - Context could not be reduced sufficiently"
    
    while retries <= MAX_RETRIES:
        try:
            if user_defined_provider is None:
                provider = PROVIDER_FROM_ENV
            else:
                provider = user_defined_provider
            print(f"Using provider: {provider}")

            if provider == "openai":
                answer, success = ask_open_ai(messages, max_length)
            elif provider == "anthropic":
                answer, success = ask_anthropic(messages, max_length)
            elif provider == "google":
                answer, success = ask_google(messages, max_length)
            else:
                answer = f"unknown AI provider: {PROVIDER_FROM_ENV}"
                success = False

            if success:
                print(f"AI response: {answer}")
                return answer
            else:
                retries += 1
                if retries > MAX_RETRIES:
                    retry_info = f" (after {MAX_RETRIES} unsuccessful exponential retries)"
                    print(f"Failed to get successful response{retry_info}: {answer}")
                    return f"{answer}{retry_info}"
                
                # Exponential backoff: 2^retries * 100ms
                delay = (2 ** retries) * DELAY_CONSTANT_S
                print(f"Attempt {retries}/{MAX_RETRIES} failed. Retrying in {delay:.2f}s...")
                time.sleep(delay)
                
        except Exception as e:
            retries += 1
            if retries > MAX_RETRIES:
                msg = f"Error while sending to AI provider (after {MAX_RETRIES} retries): {e}"
                msg += f"If it's the AI provider refusing to answer, try to reset the dialog with the command: {c.reset_dialog_command}"
                print(msg)
                return msg
            
            # Exponential backoff: 2^retries * 100ms
            delay = (2 ** retries) * DELAY_CONSTANT_S
            print(f"Attempt {retries}/{MAX_RETRIES} failed with exception: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)




