"""
This module contains sanity checks for the configuration settings.
"""

import os
import config
from utils.tokens import count_tokens


def run_sanity_checks():
    """
    Runs all configuration sanity checks.
    Raises ValueError if any check fails.
    """
    print("Running configuration sanity checks...")

    # --- Tag format checks ---
    if not config.SOURCE_TAG_OPEN.startswith("<"):
        raise ValueError("SOURCE_TAG_OPEN must start with '<'")
    if not config.SOURCE_TAG_CLOSE.startswith("</"):
        raise ValueError("SOURCE_TAG_CLOSE must start with '</'")

    # --- Safety margin checks ---
    if config.TOKEN_SAFETY_MARGIN <= 1.0:
        raise ValueError("TOKEN_SAFETY_MARGIN must be greater than 1.0")

    # --- Min context window size for integration ---
    if config.MAX_TOKENS_ALLOWED_IN_REQUEST < 100000:
        raise ValueError(
            """MAX_TOKENS_ALLOWED_IN_REQUEST must be at least 100k for the 
            integration worker to function properly, as per our experiments.
            Set it higher, and use a model with a larger context window!
            """
        )

    # --- Context window check ---
    # The context window should be WORKERS_CONTEXT_WINDOW_MARGINE times larger
    # than the length of WORKERS_OBLIGATORY_PARTS combined.
    obligatory_parts_content = ""
    for part in config.WORKERS_OBLIGATORY_PARTS:
        file_path = os.path.join(config.DATASET_LOCAL_REPO_DIR_PATH, f"{part}.txt")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                obligatory_parts_content += f.read()
        else:
            # This is not a fatal error, so we just print a warning.
            print(f"Warning: Obligatory mindfile part not found at {file_path}")

    obligatory_parts_tokens = count_tokens(obligatory_parts_content)
    required_tokens = obligatory_parts_tokens * config.WORKERS_CONTEXT_WINDOW_MARGINE
    required_tokens = int(config.TOKEN_SAFETY_MARGIN * required_tokens)
    required_tokens_in_mln = round(required_tokens / 1000000, 2)

    if (
        not config.ULTRA_SMALL_CONTEXT_WINDOW_MODE7
        and config.MAX_TOKENS_ALLOWED_IN_REQUEST < required_tokens
    ):
        raise ValueError(
            f"""MAX_TOKENS_ALLOWED_IN_REQUEST ({config.MAX_TOKENS_ALLOWED_IN_REQUEST}) is not large enough.
            It must be at least {config.WORKERS_CONTEXT_WINDOW_MARGINE} times the total size of the obligatory worker parts ({config.WORKERS_OBLIGATORY_PARTS}), plus the safety margin of {config.TOKEN_SAFETY_MARGIN}.
            Set it higher, and use a model with a larger context window! In your case, the model should have the window of at least {required_tokens} tokens (that's {required_tokens_in_mln}M tokens).
            But if you're desprate, and really can't use a better model, just reduce the size of the aforementioned obligatory files, by moving their parts to other mindfolder files.
            Alternatively, you can try ULTRA_SMALL_CONTEXT_WINDOW_MODE7 .
            """
        )

    print("All configuration sanity checks passed.")
