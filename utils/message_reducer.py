import copy
from utils.tokens import count_tokens, is_token_limit_of_request_exceeded, MAX_TOKENS_ALLOWED_IN_REQUEST
from utils.mindfile import split_context_by_importance
from utils.text_shrinkage import shrink_text
from config import TOKEN_SAFETY_MARGIN


def find_context_message_index(messages):
    """Find the index of the assistant message containing context."""
    for i, msg in enumerate(messages):
        if msg.get("role") == "assistant" and "<source:" in msg.get("content", ""):
            return i
    return None


def calculate_message_tokens(messages):
    """Calculate the total number of tokens in all messages."""
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


def calculate_reduction_target():
    """Calculate the target token count with safety margin applied."""
    return int(MAX_TOKENS_ALLOWED_IN_REQUEST / TOKEN_SAFETY_MARGIN)


def calculate_chars_to_reduce(expendable, tokens_to_reduce):
    """Calculate how many characters need to be removed from expendable content."""
    tokens_per_char = count_tokens(expendable) / max(1, len(expendable))
    return int((tokens_to_reduce * TOKEN_SAFETY_MARGIN) / tokens_per_char)


def reduce_expendable_content(expendable, tokens_to_reduce):
    """Reduce the expendable content to meet token requirements."""
    chars_to_reduce = calculate_chars_to_reduce(expendable, tokens_to_reduce)
    target_expendable_chars = max(0, len(expendable) - chars_to_reduce)
    
    print(f"Reducing expendable part from {len(expendable)} to {target_expendable_chars} chars")
    return shrink_text(expendable, target_expendable_chars), target_expendable_chars


def try_context_reduction(messages, context_idx, before_expendable, expendable, after_expendable, tokens_to_reduce):
    """Try to reduce context and check if successful."""
    reduced_expendable, target_chars = reduce_expendable_content(expendable, tokens_to_reduce)
    
    # Reconstruct the context
    new_context = before_expendable + reduced_expendable + after_expendable
    
    # Update the context message
    messages[context_idx]["content"] = new_context
    
    # Check if the reduction was successful
    success = not is_token_limit_of_request_exceeded(messages)
    
    return messages, success, reduced_expendable, target_chars, new_context


def try_aggressive_reduction(messages, context_idx, before_expendable, expendable, after_expendable, target_chars):
    """Try a more aggressive reduction when the first attempt isn't sufficient."""
    print("First reduction not sufficient, trying more aggressive reduction...")
    # Reduce to half of the previous target
    target_expendable_chars = max(0, target_chars // 2)
    print(f"Reducing expendable part further to {target_expendable_chars} chars")
    
    reduced_expendable = shrink_text(expendable, target_expendable_chars)
    new_context = before_expendable + reduced_expendable + after_expendable
    messages[context_idx]["content"] = new_context
    
    # Check again
    success = not is_token_limit_of_request_exceeded(messages)
    
    return messages, success, new_context


def reduce_context_in_messages(messages):
    """
    Reduce the context in messages to fit within token limits.
    
    This function:
    1. Makes a deep copy of the messages list
    2. Finds the assistant message containing the context
    3. Extracts and splits the context by importance
    4. Shrinks the expendable part to fit within token limits
    5. Reconstructs the message with the reduced context
    
    Args:
        messages: List of messages in the chat format
        
    Returns:
        Tuple of (reduced_messages, success) where:
        - reduced_messages is a new message list with reduced context
        - success is a boolean indicating if reduction was successful
    """
    # Make a deep copy to avoid modifying the original
    reduced_messages = copy.deepcopy(messages)
    
    # Find the assistant message with context
    context_message_idx = find_context_message_index(reduced_messages)
    
    if context_message_idx is None:
        print("No context message found to reduce")
        return reduced_messages, False
    
    # Extract context from the message
    context = reduced_messages[context_message_idx]["content"]
    
    # Split the context into critical and expendable parts
    before_expendable, expendable, after_expendable = split_context_by_importance(context)
    
    if not expendable:
        print("No expendable content found to reduce")
        return reduced_messages, False
    
    # Calculate the current token count and target
    current_tokens = calculate_message_tokens(reduced_messages)
    target_tokens = calculate_reduction_target()
    tokens_to_reduce = current_tokens - target_tokens
    
    if tokens_to_reduce <= 0:
        print("No token reduction needed")
        return reduced_messages, True
    
    print(f"Current tokens: {current_tokens}, Target tokens: {target_tokens}")
    print(f"Tokens to reduce: {tokens_to_reduce}")
    
    # Try the initial reduction
    reduced_messages, success, reduced_expendable, target_chars, new_context = try_context_reduction(
        reduced_messages, context_message_idx, before_expendable, expendable, after_expendable, tokens_to_reduce
    )
    
    # If not successful and we have expendable content left, try a more aggressive reduction
    if not success and len(reduced_expendable) > 10:
        reduced_messages, success, new_context = try_aggressive_reduction(
            reduced_messages, context_message_idx, before_expendable, expendable, after_expendable, target_chars
        )
    
    # Log the results
    reduction_percentage = 100 - (len(new_context) / len(context) * 100)
    print(f"Context reduction: {reduction_percentage:.2f}% of original size")
    print(f"Reduction successful: {success}")
    
    return reduced_messages, success 