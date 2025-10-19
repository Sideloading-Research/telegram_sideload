from config import (
    CHARS_PER_TOKEN,
    MAX_TOKENS_ALLOWED_IN_REQUEST,
    TOKEN_SAFETY_MARGIN,
    WORKERS_OBLIGATORY_PARTS,
    DATASET_LOCAL_REPO_DIR_PATH,
)
import os


def count_tokens(text):
    res = len(text) / CHARS_PER_TOKEN
    res = int(res) + 1  # round up
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
    # print(f"Safety margin: {safety_margin}")
    # print(f"Max tokens allowed in request: {MAX_TOKENS_ALLOWED_IN_REQUEST}")
    return res


def get_max_chars_allowed(
    consider_obligatory_worker_parts7: bool = False,
    files_content_override: dict[str, str] | None = None,
):
    absolute_max_chars = MAX_TOKENS_ALLOWED_IN_REQUEST * CHARS_PER_TOKEN

    max_chars = int(absolute_max_chars / TOKEN_SAFETY_MARGIN)
    print(f"initial max_chars: {max_chars}")

    if consider_obligatory_worker_parts7:
        obligatory_parts_len = 0
        for part in WORKERS_OBLIGATORY_PARTS:
            part_len = 0
            if files_content_override and part in files_content_override:
                part_len = len(files_content_override[part])
            else:
                file_path = os.path.join(DATASET_LOCAL_REPO_DIR_PATH, f"{part}.txt")
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        part_len = len(f.read())
            
            obligatory_parts_len += part_len
            print(f"{part} part_len: {part_len}")

        print(f"obligatory_parts_len: {obligatory_parts_len}")
        max_chars -= obligatory_parts_len

    print(f"max_chars: {max_chars}")

    if max_chars < 0:
        raise ValueError(f"max_chars is negative: {max_chars}")

    return max_chars
