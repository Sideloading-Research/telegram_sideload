import copy
from utils.text_shrinkage_utils.controller import shrink_any_text
from utils.tokens import count_tokens, is_token_limit_of_request_exceeded, MAX_TOKENS_ALLOWED_IN_REQUEST
from config import TOKEN_SAFETY_MARGIN, PROTECTED_MINDFILE_PARTS, SOURCE_TAG_OPEN, SOURCE_TAG_CLOSE, CHARS_PER_TOKEN
import re


def find_context_message_index(messages):
    """Find the index of the message containing context."""
    for i, msg in enumerate(messages):
        if msg.get("role") in ["assistant", "system"] and SOURCE_TAG_OPEN in msg.get("content", ""):
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
    
    reduced = shrink_any_text(expendable, target_expendable_chars, source_type="dialogs")
    return reduced, target_expendable_chars


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
    
    reduced_expendable = shrink_any_text(expendable, target_expendable_chars, source_type="dialogs")
    new_context = before_expendable + reduced_expendable + after_expendable
    messages[context_idx]["content"] = new_context
    
    # Check again
    success = not is_token_limit_of_request_exceeded(messages)
    
    return messages, success, new_context


def truncate_context_if_needed(reduced_messages, context_message_idx):
    """Truncate the context if it's still too large after reduction."""
    success = not is_token_limit_of_request_exceeded(reduced_messages)
    if success:
        return reduced_messages, True

    print("# Context still too large after iterative reduction. Truncating.")
    total_tokens = calculate_message_tokens(reduced_messages)
    target_tokens = calculate_reduction_target()

    context_content = reduced_messages[context_message_idx]["content"]
    context_tokens = count_tokens(context_content)

    other_tokens = total_tokens - context_tokens
    max_context_tokens = target_tokens - other_tokens
    
    # Subtract a small buffer to be safe
    max_context_tokens = max(0, max_context_tokens - 5)

    max_len = max(0, int((max_context_tokens - 1) * CHARS_PER_TOKEN))
    
    if max_len < len(context_content):
        new_context = context_content[:max_len]
        reduced_messages[context_message_idx]["content"] = new_context
        success = not is_token_limit_of_request_exceeded(reduced_messages)
        print(f"# Truncation success: {success}")

    return reduced_messages, success


def reduce_context_in_messages(messages):
    """
    Reduce the context in messages to fit within token limits.
    
    This function:
    1. Makes a deep copy of the messages list
    2. Finds the assistant message containing the context
    3. Parses the context into segments
    4. Shrinks the expendable segments
    5. Reconstructs the message with the reduced context
    
    Args:
        messages: List of messages in the chat format
        
    Returns:
        Tuple of (reduced_messages, success) where:
        - reduced_messages is a new message list with reduced context
        - success is a boolean indicating if reduction was successful
    """
    # print("Reducing context")

    # Make a deep copy to avoid modifying the original
    reduced_messages = copy.deepcopy(messages)
    
    # Find the assistant message with context
    context_message_idx = find_context_message_index(reduced_messages)
    
    if context_message_idx is None:
        print("No context message found to reduce")
        return reduced_messages, False
    
    # Extract context from the message
    context = reduced_messages[context_message_idx]["content"]
    
    open_tag_base = re.escape(SOURCE_TAG_OPEN)
    close_tag_base = re.escape(SOURCE_TAG_CLOSE)
    
    SEG_PATTERN = re.compile(rf"{open_tag_base}(?P<tag>[^>]+)>.*?{close_tag_base}\1>", re.DOTALL)

    # Build ordered list of segments: either raw (untagged) or tagged blocks.
    segments = []  # list of dicts {type: 'raw'|'tagged', 'text': str, 'tag': str|None}
    last_end = 0
    for m in SEG_PATTERN.finditer(context):
        # raw text before this tagged block
        if m.start() > last_end:
            segments.append({"type": "raw", "text": context[last_end : m.start()]})

        tag = m.group("tag")
        full_block = m.group(0)
        segments.append({"type": "tagged", "tag": tag, "text": full_block})

        last_end = m.end()

    # trailing raw
    if last_end < len(context):
        segments.append({"type": "raw", "text": context[last_end:]})

    # Identify shrinkable tagged segments
    shrinkable_segments = []  # list of segment dict references (same objects)
    for seg in segments:
        if seg["type"] == "tagged" and seg["tag"] not in PROTECTED_MINDFILE_PARTS:
            shrinkable_segments.append(seg)

    # Record original lengths per tag for reporting later
    original_lengths = {}
    for seg in segments:
        if seg["type"] == "tagged":
            original_lengths[seg["tag"]] = original_lengths.get(seg["tag"], 0) + len(seg["text"])

    if not shrinkable_segments:
        print("No shrinkable tagged content found to reduce")
        return reduced_messages, False

    placeholder_len = len("<...>")

    # Helper to rebuild the context from segments
    def _rebuild_context() -> str:
        return "".join(seg.get("text") for seg in segments)

    # Iterative 10% reduction loop
    iteration = 0
    while is_token_limit_of_request_exceeded(reduced_messages):
        iteration += 1
        # print(f"Reduction iteration {iteration}: applying 10% shrink to each source")

        any_shrunk = False
        for seg in shrinkable_segments:
            cur_len = len(seg["text"])
            min_len = placeholder_len + 1
            if cur_len <= min_len:
                continue  # cannot shrink further

            new_len = max(int(cur_len * 0.9), min_len)

            # Determine source_type
            source_type = "dialogs" if seg["tag"] == "dialogs" else "generic"

            # Extract inner content (without wrapping tags) to shrink, then rewrap
            inner_pattern = re.compile(rf"{open_tag_base}{seg['tag']}>\s*(.*?)\s*{close_tag_base}{seg['tag']}>", re.DOTALL)
            inner_match = inner_pattern.match(seg["text"])
            if not inner_match:
                # Fallback: shrink whole block as plain text
                inner_content = seg["text"]
                new_inner = shrink_any_text(inner_content, new_len, source_type=source_type)
                seg["text"] = new_inner
            else:
                inner_content = inner_match.group(1)
                new_inner = shrink_any_text(inner_content, new_len, source_type=source_type)
                seg["text"] = f"{SOURCE_TAG_OPEN}{seg['tag']}>\n\n{new_inner}\n\n{SOURCE_TAG_CLOSE}{seg['tag']}>"

            if len(seg["text"]) < cur_len:
                any_shrunk = True

        if not any_shrunk:
            print("No further shrink possible; stopping.")
            break

        # Update context and messages
        new_context = _rebuild_context()
        reduced_messages[context_message_idx]["content"] = new_context

    reduced_messages, success = truncate_context_if_needed(reduced_messages, context_message_idx)

    # Logging
    final_context = reduced_messages[context_message_idx]["content"]
    reduction_percentage = 100 - (len(final_context) / len(context) * 100)
    print(f"Context reduction: {reduction_percentage:.2f}% of original size")
    if not success:
        print(f"Context reduction failed")

    # Per-source length report
    final_lengths = {}
    for seg in segments:
        if seg["type"] == "tagged":
            final_lengths[seg["tag"]] = final_lengths.get(seg["tag"], 0) + len(seg["text"])

    """
    print("Per-source length changes:")
    for tag in sorted(original_lengths.keys()):
        orig = original_lengths[tag]
        final = final_lengths.get(tag, 0)
        saved = orig - final
        pct = (saved / orig * 100) if orig > 0 else 0
        print(f"  {tag}: {orig} → {final} (−{saved} chars, {pct:.1f}% shrink)")
    """

    return reduced_messages, success 