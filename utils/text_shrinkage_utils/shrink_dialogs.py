import random
import re

# TODO: move all the hardcoded substrings to config.py

def remove_metadata_lines(lines, placeholder, metadata_prefixes):
    """
    Remove lines that match metadata prefixes and replace them with placeholders.
    
    Args:
        lines: List of text lines
        placeholder: Placeholder text to use for removed lines
        metadata_prefixes: List of prefixes that identify metadata lines
        
    Returns:
        Tuple of (current_len, lines) where current_len is the updated text length
    """
    current_len = len("\n".join(lines))
    
    # Process all lines once to remove metadata
    for i in range(len(lines)):
        # Skip lines that are already placeholders
        if lines[i] == placeholder:
            continue
            
        # Check if the line is a metadata line
        if any(lines[i].startswith(prefix) for prefix in metadata_prefixes):
            # Calculate length difference after replacement
            old_line_len = len(lines[i])
            new_line_len = len(placeholder)
            len_diff = old_line_len - new_line_len
            
            # Replace the line with placeholder
            lines[i] = placeholder
            current_len -= len_diff
    
    return current_len, lines


def identify_valuable_lines(lines, placeholder, valuable_patterns):
    """
    Identify valuable lines based on the patterns dictionary.
    
    Args:
        lines: List of text lines
        placeholder: Placeholder text to skip already processed lines
        valuable_patterns: Dictionary mapping patterns to their detection method
        
    Returns:
        Set of line indices considered valuable
    """
    valuable_indices = set()
    for i in range(len(lines)):
        # Skip placeholder lines
        if lines[i] == placeholder:
            continue
            
        # Check if current line matches any valuable pattern
        for pattern, method in valuable_patterns.items():
            if (method == "start" and lines[i].startswith(pattern)) or (
                method == "contains" and pattern in lines[i]
            ):
                valuable_indices.add(i)
                # Also mark the next line as valuable if it exists
                if i + 1 < len(lines):
                    valuable_indices.add(i + 1)
                break  # Once we've found a matching pattern, no need to check others
    
    return valuable_indices


def remove_lines(lines, indices_to_use, current_len, target_len, placeholder):
    """
    Remove lines from the specified indices until target length is reached.
    
    Args:
        lines: List of text lines
        indices_to_use: List of indices that can be replaced
        current_len: Current text length
        target_len: Target text length
        placeholder: Placeholder to use for removed lines
        
    Returns:
        Tuple of (current_len, lines, indices_used) with updated values
    """
    indices_used = []
    indices_to_use = indices_to_use.copy()  # Make a copy to avoid modifying the original
    
    while current_len > target_len and indices_to_use:
        # Select a random line to replace
        idx = random.choice(indices_to_use)
        
        # Calculate length difference after replacement
        old_line_len = len(lines[idx])
        new_line_len = len(placeholder)
        len_diff = old_line_len - new_line_len
        
        # Replace the line with placeholder
        lines[idx] = placeholder
        
        # Update current length and indices
        current_len -= len_diff
        indices_to_use.remove(idx)
        indices_used.append(idx)
    
    return current_len, lines, indices_used


def consolidate_placeholders(lines, placeholder):
    """
    Replace consecutive placeholders (with or without empty lines between them) with a single placeholder.
    
    Args:
        lines: List of text lines
        placeholder: The placeholder text to consolidate
        
    Returns:
        Tuple of (new_lines, chars_saved) with consolidated placeholders
    """
    if not lines:
        return lines, 0
        
    new_lines = []
    chars_saved = 0
    i = 0
    
    while i < len(lines):
        # Add current line to new lines
        new_lines.append(lines[i])
        
        # If current line is a placeholder, check for consecutive placeholders
        if lines[i] == placeholder:
            # Skip all consecutive placeholders and empty lines
            consecutive_count = 0
            placeholder_len = len(placeholder)
            
            j = i + 1
            while j < len(lines) and (lines[j] == placeholder or not lines[j].strip()):
                # Count how many placeholders we're skipping
                if lines[j] == placeholder:
                    consecutive_count += 1
                    chars_saved += placeholder_len
                else:  # Empty line
                    chars_saved += len(lines[j])
                j += 1
                
            # If we found consecutive placeholders, skip them
            if consecutive_count > 0:
                i = j  # Skip to the position after consecutive placeholders
                continue
        
        i += 1
    
    return new_lines, chars_saved


def remove_other_people_messages(lines, placeholder, target_len):
    """
    Identify and remove entire messages from other people in Telegram chatlogs.
    
    A message starts with a line matching "msg ####: [date] Person wrote:" and continues
    until the next message header, a document marker, or end of text.
    
    Document markers include lines starting with:
    - "# Written no later than "
    - "Content from data gathering portion "
    
    Prioritizes removing longer messages first to maximize space savings.
    Completely removes messages (including headers) and replaces each with a single placeholder.
    
    Args:
        lines: List of text lines
        placeholder: Placeholder text for removed messages
        target_len: Target length in characters
        
    Returns:
        Tuple of (current_len, lines, messages_removed) with updated values
    """
    # Message header pattern (e.g., "msg 5149: [12 April 2025 16:34] Alex wrote:")
    msg_header_pattern = re.compile(r"^msg \d+: \[\d+ \w+ \d+ \d+:\d+\] .+wrote:")
    
    # Document section markers that indicate the end of a message block
    document_markers = [
        "# Written no later than ",
        "Content from data gathering portion "
    ]
    
    # Current text length
    current_len = len("\n".join(lines))
    
    # Find all message blocks
    message_blocks = []  # List of (start_idx, end_idx, is_from_me)
    current_block_start = None
    
    # Find message blocks
    for i, line in enumerate(lines):
        # Check if this line starts a new message
        if msg_header_pattern.match(line):
            # End previous block if there was one
            if current_block_start is not None:
                message_blocks.append((current_block_start, i - 1, "<me> wrote:" in lines[current_block_start]))
            
            # Start new block
            current_block_start = i
        # Check if this line starts a new document section
        elif any(line.startswith(marker) for marker in document_markers):
            # End previous block if there was one
            if current_block_start is not None:
                message_blocks.append((current_block_start, i - 1, "<me> wrote:" in lines[current_block_start]))
                current_block_start = None  # Reset as this isn't a message header
    
    # Add the last block if there is one
    if current_block_start is not None:
        message_blocks.append((
            current_block_start, 
            len(lines) - 1, 
            "<me> wrote:" in lines[current_block_start]
        ))
    
    # Filter for messages not from me
    other_people_blocks = [block for block in message_blocks if not block[2]]
    
    # No messages from others to remove
    if not other_people_blocks:
        return current_len, lines, 0
    
    # Calculate message lengths and sort blocks by length (longest first)
    blocks_with_length = []
    for start_idx, end_idx, is_from_me in other_people_blocks:
        # Calculate length of this block
        block_len = sum(len(lines[i]) for i in range(start_idx, end_idx + 1))
        block_len += end_idx - start_idx  # Account for newlines
        blocks_with_length.append((start_idx, end_idx, is_from_me, block_len))
    
    # Sort by length (descending)
    sorted_blocks = sorted(blocks_with_length, key=lambda x: x[3], reverse=True)
    
    # Create a map of which indices to replace with placeholders and which to remove
    to_replace_with_placeholder = set()
    to_remove = set()
    messages_removed = 0
    
    for start_idx, end_idx, _, block_len in sorted_blocks:
        # Mark the start index to be replaced with a placeholder
        to_replace_with_placeholder.add(start_idx)
        
        # Mark all subsequent indices in this block for removal
        for i in range(start_idx + 1, end_idx + 1):
            to_remove.add(i)
        
        # Calculate space saved
        # Block length minus one placeholder
        saved_len = block_len - len(placeholder)
        current_len -= saved_len
        messages_removed += 1
        
        # Stop if target reached
        if current_len <= target_len:
            break
    
    # Create a new lines list with placeholders and without removed lines
    new_lines = []
    for i, line in enumerate(lines):
        if i in to_replace_with_placeholder:
            new_lines.append(placeholder)
        elif i not in to_remove:
            new_lines.append(line)
    
    return current_len, new_lines, messages_removed


def consolidate_empty_messages(lines, placeholder):
    """
    Remove empty messages that consist of just a header followed by a placeholder, 
    but only when followed by another message header.
    
    Args:
        lines: List of text lines
        placeholder: The placeholder text
        
    Returns:
        Tuple of (new_lines, chars_saved) with empty messages removed
    """
    if len(lines) < 3:  # Need at least 3 lines for this pattern
        return lines, 0
    
    # Message header pattern
    msg_header_pattern = re.compile(r"^msg \d+: \[\d+ \w+ \d+ \d+:\d+\] .+wrote:")
    
    new_lines = []
    chars_saved = 0
    i = 0
    
    while i < len(lines):
        # Check for pattern: header -> placeholder -> header
        if (i + 2 < len(lines) and 
            msg_header_pattern.match(lines[i]) and 
            lines[i+1] == placeholder and 
            msg_header_pattern.match(lines[i+2])):
            
            # Skip the header and placeholder
            chars_saved += len(lines[i]) + len(lines[i+1]) + 2  # +2 for newlines
            i += 2  # Skip to the next header
        else:
            new_lines.append(lines[i])
            i += 1
    
    return new_lines, chars_saved


def shrink_dialogs_text(text, target_len_chars):
    """
    Iteratively remove random lines from text until it reaches the target length.
    Removed lines are replaced with <...>
    
    Prioritizes removing entire messages from other people in Telegram chatlogs first,
    then metadata lines, then non-valuable lines, and valuable lines as a last resort.
    
    Args:
        text: The text to shrink
        target_len_chars: Target length in characters
        
    Returns:
        Shrunk text with removed lines replaced by <...>
    """
    # If text is already shorter than target, return as is
    if len(text) <= target_len_chars:
        return text
    
    # Split into lines
    lines = text.split("\n")
    placeholder = "<...>"
    
    # Step 0: First try to remove entire messages from other people
    current_len, lines, messages_removed = remove_other_people_messages(
        lines, placeholder, target_len_chars
    )
    
    # If we've reached the target length after removing other people's messages, return early
    if current_len <= target_len_chars:
        consolidated_lines, _ = consolidate_placeholders(lines, placeholder)
        consolidated_lines, _ = consolidate_empty_messages(consolidated_lines, placeholder)
        return "\n".join(consolidated_lines)
    
    # Step 1: Remove metadata lines
    metadata_prefixes = [
        "└─ In reply to msg",
        "[Photo: ",
        "(telegram record ",
        "<mySummaryMode",
    ]
    
    current_len, lines = remove_metadata_lines(lines, placeholder, metadata_prefixes)
    
    # If we've reached the target length after removing metadata, return early
    if current_len <= target_len_chars:
        consolidated_lines, _ = consolidate_placeholders(lines, placeholder)
        consolidated_lines, _ = consolidate_empty_messages(consolidated_lines, placeholder)
        return "\n".join(consolidated_lines)
    
    # Step 2: Identify valuable lines
    valuable_patterns = {
        "You sent  ": "start",  # Check if line starts with this
        "[me] ": "start",
        "[me]\n": "start",
        "<me> wrote:": "contains",  # Check if line contains this
        "] <me>: ": "contains",
    }
    valuable_indices = identify_valuable_lines(lines, placeholder, valuable_patterns)
    
    # Step 3: Separate replaceable lines into valuable and non-valuable
    non_valuable_indices = [
        i
        for i in range(len(lines))
        if lines[i] != placeholder and lines[i].strip() and i not in valuable_indices
    ]
    valuable_replaceable_indices = [
        i for i in valuable_indices if lines[i] != placeholder and lines[i].strip()
    ]
    
    # Step 4: First try to remove non-valuable lines
    current_len, lines, _ = remove_lines(
        lines, non_valuable_indices, current_len, target_len_chars, placeholder
    )
    
    # Step 5: If we still need to shrink, start removing valuable lines as a last resort
    if current_len > target_len_chars:
        current_len, lines, _ = remove_lines(
            lines, valuable_replaceable_indices, current_len, target_len_chars, placeholder
        )
    
    # Step 6: Consolidate consecutive placeholders to save space
    consolidated_lines, chars_saved = consolidate_placeholders(lines, placeholder)
    
    # Step 7: Remove empty messages (header + placeholder) followed by another header
    consolidated_lines, more_chars_saved = consolidate_empty_messages(consolidated_lines, placeholder)
    chars_saved += more_chars_saved
    
    # If consolidation saved enough chars and we're still over target, try removing more lines
    if chars_saved > 0 and (current_len - chars_saved) > target_len_chars:
        # Recursively shrink the consolidated text further if needed
        return shrink_dialogs_text("\n".join(consolidated_lines), target_len_chars)
    
    # Rejoin the text
    return "\n".join(consolidated_lines)