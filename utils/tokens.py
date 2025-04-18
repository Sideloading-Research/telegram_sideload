from config import CHARS_PER_TOKEN, MAX_TOKENS_ALLOWED_IN_REQUEST, TOKEN_SAFETY_MARGIN


def count_tokens(text):
    res = len(text) / CHARS_PER_TOKEN
    res = int(res) + 1 # round up
    return res

def is_token_limit_of_text_exceeded(text, safety_margin=None):
    if safety_margin is None:
        safety_margin = TOKEN_SAFETY_MARGIN
    return count_tokens(text) * safety_margin > MAX_TOKENS_ALLOWED_IN_REQUEST

def is_token_limit_of_request_exceeded(messages, safety_margin=None):
    """
    Takes a list of messages and returns True if the total number of tokens in the request exceeds the limit.

    See main.py for the format of the messages.
    """
    if safety_margin is None:
        safety_margin = TOKEN_SAFETY_MARGIN
        
    total_tokens = 0
    
    for message in messages:
        content = message.get("content", "")
        
        # Handle content whether it's a string or a list of content parts
        if isinstance(content, str):
            total_tokens += count_tokens(content)
        else:
            # If content is a list of content parts
            for content_part in content:
                if content_part.get("type") == "text":
                    total_tokens += count_tokens(content_part.get("text", ""))


    res = total_tokens * safety_margin > MAX_TOKENS_ALLOWED_IN_REQUEST
    print(f"Token limit exceeded: {res}")
    print(f"Total tokens in messages (estimated): {total_tokens}")
    print(f"Safety margin: {safety_margin}")
    print(f"Max tokens allowed in request: {MAX_TOKENS_ALLOWED_IN_REQUEST}")
    return res