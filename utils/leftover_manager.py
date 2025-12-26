import os
import shutil

from utils.tokens import count_tokens
from utils.text_utils import truncate_text_by_tokens


def get_leftover_cache_dir() -> str:
    """Returns path to cache directory for generated leftover files."""
    cache_dir = os.path.join(os.getcwd(), ".telegram_sideload_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def cleanup_leftover_files():
    """Removes all leftover cache files."""
    cache_dir = os.path.join(os.getcwd(), ".telegram_sideload_cache")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print("Leftover cache cleaned up")


def write_leftover_to_file(leftover_content: str) -> str:
    """
    Writes leftover content to a cache file and returns the file path.
    
    Args:
        leftover_content: The content to write
        
    Returns:
        Full path to the created leftover file
    """
    cache_dir = get_leftover_cache_dir()
    leftover_path = os.path.join(cache_dir, "structured_self_facts_leftover.txt")
    
    with open(leftover_path, "w", encoding="utf-8") as f:
        f.write(leftover_content)
    
    leftover_tokens = count_tokens(leftover_content)
    print(f"Leftover saved to: {leftover_path}")
    print(f"Leftover size: {leftover_tokens} tokens ({len(leftover_content)} chars)")
    
    return leftover_path


def calculate_truncation_limit(
    system_message_content: str,
    ultra_small_mode7: bool,
    max_tokens_allowed: int
) -> int:
    """
    Calculates the token limit for structured_self_facts truncation.
    
    Args:
        system_message_content: Content of system message (for ultra-small mode calculation)
        ultra_small_mode7: Whether ultra-small context window mode is enabled
        max_tokens_allowed: Maximum tokens allowed in request
        
    Returns:
        Final token limit for structured_self_facts
    """
    final_token_limit = int(0.3 * max_tokens_allowed)
    
    if ultra_small_mode7:
        max_tokens_for_combo = max_tokens_allowed / 2
        system_message_tokens = count_tokens(system_message_content)
        small_mode_token_limit = max(0, int(max_tokens_for_combo - system_message_tokens))
        
        if small_mode_token_limit < final_token_limit:
            final_token_limit = small_mode_token_limit
    
    return final_token_limit


def is_truncation_needed(content: str, token_limit: int) -> bool:
    """
    Checks if content exceeds the token limit and needs truncation.
    
    Args:
        content: The content to check
        token_limit: Token limit to check against
        
    Returns:
        True if truncation is needed, False otherwise
    """
    content_tokens = count_tokens(content)
    return content_tokens > token_limit


def extract_leftover_content(full_content: str, token_limit: int) -> tuple[str, str]:
    """
    Splits content into truncated part and leftover part.
    
    Args:
        full_content: The full content to split
        token_limit: Maximum tokens for truncated part
        
    Returns:
        Tuple of (truncated_content, leftover_content)
    """
    truncated_content = truncate_text_by_tokens(full_content, token_limit)
    leftover_content = full_content[len(truncated_content):].strip()
    
    return truncated_content, leftover_content


def process_and_generate_leftover(
    facts_content: str,
    system_message_content: str,
    ultra_small_mode7: bool,
    max_tokens_allowed: int,
    leftover_filename_key: str
) -> dict[str, str] | None:
    """
    Main function to detect truncation, generate leftover, and return file mapping.
    
    This is the primary entry point for leftover generation. It checks if
    structured_self_facts needs truncation, and if so, extracts the leftover
    and saves it to a file.
    
    Args:
        facts_content: Content of structured_self_facts
        system_message_content: Content of system_message
        ultra_small_mode7: Whether ultra-small context window mode is enabled
        max_tokens_allowed: Maximum tokens allowed in request
        leftover_filename_key: Key to use in files_dict for leftover file
        
    Returns:
        Dict with {leftover_filename_key: leftover_filepath} if leftover was generated,
        None if no truncation needed
    """
    original_tokens = count_tokens(facts_content)
    token_limit = calculate_truncation_limit(
        system_message_content,
        ultra_small_mode7,
        max_tokens_allowed
    )
    
    if not is_truncation_needed(facts_content, token_limit):
        # print("No truncation needed - structured_self_facts fits within limits")
        return None
    
    print(f"Truncation detected: {original_tokens} tokens > {token_limit} token limit")
    
    truncated_content, leftover_content = extract_leftover_content(
        facts_content,
        token_limit
    )
    
    leftover_tokens = count_tokens(leftover_content)
    percentage_saved = (leftover_tokens / original_tokens) * 100
    
    print(f"Leftover statistics:")
    print(f"  Original: {original_tokens} tokens (100%)")
    print(f"  Truncated: {count_tokens(truncated_content)} tokens ({100-percentage_saved:.1f}%)")
    print(f"  Leftover: {leftover_tokens} tokens ({percentage_saved:.1f}%)")
    
    leftover_filepath = write_leftover_to_file(leftover_content)
    
    return {leftover_filename_key: leftover_filepath}

