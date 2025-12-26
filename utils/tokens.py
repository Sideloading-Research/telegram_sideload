from config import (
    CHARS_PER_TOKEN,
    MAX_TOKENS_ALLOWED_IN_REQUEST,
    TOKEN_SAFETY_MARGIN,
    WORKERS_OBLIGATORY_PARTS,
    DATASET_LOCAL_REPO_DIR_PATH,
)
import os
from utils.env_and_prints import dedent_and_strip


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

    #if res:
    #    print(f"Token limit exceeded: {res}")
    #    print(f"Total tokens in messages (estimated): {total_tokens}")
    # print(f"Safety margin: {safety_margin}")
    # print(f"Max tokens allowed in request: {MAX_TOKENS_ALLOWED_IN_REQUEST}")
    return res


def get_max_chars_allowed(
    consider_obligatory_worker_parts7: bool = False,
    files_content_override: dict[str, str] | None = None,
):
    absolute_max_chars = MAX_TOKENS_ALLOWED_IN_REQUEST * CHARS_PER_TOKEN

    max_chars = int(absolute_max_chars / TOKEN_SAFETY_MARGIN)

    if consider_obligatory_worker_parts7:
        obligatory_parts_len = 0
        part_details = []
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
            part_details.append(f"  - {part}.txt: {part_len} chars")

        max_chars -= obligatory_parts_len

    if max_chars < 0:
        initial_max_chars = int(absolute_max_chars / TOKEN_SAFETY_MARGIN)
        if consider_obligatory_worker_parts7:
            part_details_str = "\\n".join(part_details)
            error_message = f"""
                max_chars is negative: {max_chars}.

                This is because the total size of the 'obligatory worker parts' is too large for the current token limit settings.

                Calculated initial max characters: {initial_max_chars}
                Total size of obligatory parts: {obligatory_parts_len} chars

                Culprit files (from WORKERS_OBLIGATORY_PARTS in config.py):
                {part_details_str}

                To resolve this, you can:
                1. Reduce the size of the above files.
                2. Use a model with a larger context window, and increase `MAX_TOKENS_ALLOWED_IN_REQUEST` in `config.py`.
            """
            raise ValueError(dedent_and_strip(error_message))
        else:
            raise ValueError(
                f"max_chars is negative: {max_chars}. "
                "This is likely due to your settings in config.py. "
                f"MAX_TOKENS_ALLOWED_IN_REQUEST ({MAX_TOKENS_ALLOWED_IN_REQUEST}) might be too small "
                f"or TOKEN_SAFETY_MARGIN ({TOKEN_SAFETY_MARGIN}) might be too large."
            )

    return max_chars
