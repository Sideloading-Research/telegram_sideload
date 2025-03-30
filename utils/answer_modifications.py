from config import MAX_TELEGRAM_MESSAGE_LEN, REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7, REMOVE_INTERNAL_DIALOG_FROM_ANSWER7


def remove_chain_of_thought(answer):
    """Remove the chain of thought section from the answer if present."""
    start_tag = "<chain of thought>"
    end_tag = "</chain of thought>"
    start_idx = answer.find(start_tag)
    end_idx = answer.find(end_tag)

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return (
            answer[:start_idx].rstrip()
            + "\n"
            + answer[end_idx + len(end_tag):].lstrip()
        )
    return answer

def find_internal_dialog_positions(answer):
    """Find positions of internal dialog tags in the answer."""
    lower_answer = answer.lower()
    start_idx = lower_answer.find("<")
    positions = []
    
    while start_idx != -1:
        end_idx = lower_answer.find(">", start_idx)
        if end_idx != -1 and "internal dialog>" in lower_answer[start_idx:end_idx + 1]:
            positions.append(start_idx)
        start_idx = lower_answer.find("<", start_idx + 1)
    
    return positions

def remove_internal_dialog_section(answer, start_pos):
    """Remove a single internal dialog section starting from the given position."""
    tag_start = answer.find("<", start_pos)
    tag_end = answer.find(">", tag_start)
    if tag_start == -1 or tag_end == -1:
        return answer

    opening_tag = answer[tag_start:tag_end + 1]
    if "internal dialog>" not in opening_tag.lower():
        return answer

    # Extract the name part more reliably
    name_start = opening_tag.find("<") + 1
    name_end = opening_tag.lower().find("'s internal dialog>")
    if name_end == -1:
        return answer
        
    name_part = opening_tag[name_start:name_end]
    closing_tag = f"</{name_part}'s internal dialog>"

    section_end = answer.find(closing_tag, tag_end)
    if section_end == -1:
        return answer

    return (
        answer[:tag_start].rstrip()
        + "\n"
        + answer[section_end + len(closing_tag):].lstrip()
    )

def remove_internal_dialog(answer):
    """Remove the first valid internal dialog section from the answer."""
    possible_starts = find_internal_dialog_positions(answer)
    
    for start_pos in possible_starts:
        try:
            new_answer = remove_internal_dialog_section(answer, start_pos)
            if new_answer != answer:
                return new_answer
        except Exception:
            continue
    return answer

def clean_whitespace(answer):
    """Remove extra whitespace and empty lines from the answer."""
    return "\n".join(line for line in answer.splitlines() if line.strip())

def remove_answer_tags(answer):
    """Remove the 'answer to the user' tags if present."""
    lower_answer = answer.lower()
    start_idx = lower_answer.find("<")
    
    while start_idx != -1:
        end_idx = lower_answer.find(">", start_idx)
        if end_idx != -1 and "answer to the user>" in lower_answer[start_idx:end_idx + 1]:
            # Find and remove the closing tag first
            name_start = start_idx + 1
            name_end = lower_answer.find("'s answer to the user>", start_idx)
            if name_end != -1:
                name_part = answer[name_start:name_end]
                closing_tag = f"</{name_part}'s answer to the user>"
                closing_idx = answer.find(closing_tag)
                if closing_idx != -1:
                    answer = (
                        answer[:start_idx].rstrip() 
                        + "\n" 
                        + answer[end_idx + 1:closing_idx].strip() 
                        + "\n" 
                        + answer[closing_idx + len(closing_tag):].lstrip()
                    )
                    break
        start_idx = lower_answer.find("<", start_idx + 1)
    
    return answer

def find_tag_positions(answer, tag_identifier):
    """Find positions of tags containing the specified identifier."""
    lower_answer = answer.lower()
    start_idx = lower_answer.find("<")
    positions = []
    
    while start_idx != -1:
        end_idx = lower_answer.find(">", start_idx)
        if end_idx != -1 and tag_identifier in lower_answer[start_idx:end_idx + 1]:
            positions.append(start_idx)
        start_idx = lower_answer.find("<", start_idx + 1)
    
    return positions

def remove_tagged_section(answer, start_pos, tag_info):
    """
    Remove a section enclosed in tags.
    tag_info is a tuple of (identifier, prefix, suffix) where:
    - identifier: string to identify the tag (e.g., "internal dialog")
    - prefix: string before the identifier (e.g., "'s ")
    - suffix: string after the identifier (e.g., ">")
    """
    identifier, prefix, suffix = tag_info
    tag_start = answer.find("<", start_pos)
    tag_end = answer.find(">", tag_start)
    if tag_start == -1 or tag_end == -1:
        return answer

    opening_tag = answer[tag_start:tag_end + 1]
    if identifier not in opening_tag.lower():
        return answer

    # Extract the name/content part
    name_start = opening_tag.find("<") + 1
    name_end = opening_tag.lower().find(prefix + identifier + suffix)
    if name_end == -1:
        return answer
        
    name_part = opening_tag[name_start:name_end]
    closing_tag = f"</{name_part}{prefix}{identifier}{suffix}"

    section_end = answer.find(closing_tag, tag_end)
    if section_end == -1:
        # If no closing tag is found, just remove the opening tag
        # (special case for proper answer tags)
        if identifier == "answer to the user":
            return (
                answer[:tag_start].rstrip()
                + "\n"
                + answer[tag_end + 1:].lstrip()
            )
        return answer

    return (
        answer[:tag_start].rstrip()
        + "\n"
        + answer[section_end + len(closing_tag):].lstrip()
    )

def remove_sections_by_tag(answer, tag_info):
    """Remove all sections with the specified tag information."""
    possible_starts = find_tag_positions(answer, tag_info[0])
    
    for start_pos in possible_starts:
        try:
            new_answer = remove_tagged_section(answer, start_pos, tag_info)
            if new_answer != answer:
                return new_answer
        except Exception:
            continue
    return answer

def optionally_remove_answer_sections(
    answer, remove_cot7=False, remove_internal_dialog7=False
):
    """
    Remove specified sections from the answer (chain of thought and/or internal dialog).
    Returns the modified answer with cleaned whitespace.
    """
    if not isinstance(answer, str):
        return str(answer)

    try:
        # Define tag information tuples: (identifier, prefix, suffix)
        COT_TAG = ("chain of thought", "", ">")
        INTERNAL_DIALOG_TAG = ("internal dialog", "'s ", ">")
        PROPER_ANSWER_TAG = ("answer to the user", "'s ", ">")

        if remove_cot7:
            answer = remove_sections_by_tag(answer, COT_TAG)

        if remove_internal_dialog7:
            answer = remove_sections_by_tag(answer, INTERNAL_DIALOG_TAG)

        answer = clean_whitespace(answer)

        if remove_cot7 and remove_internal_dialog7:
            answer = remove_sections_by_tag(answer, PROPER_ANSWER_TAG)

        return answer

    except Exception as e:
        msg = f"Error processing answer: {str(e)}"
        print(msg)
        return msg + "\n" + str(answer)


def reduce_answer_len_to_comply_with_telegram_limit(answer):
    if len(answer) > MAX_TELEGRAM_MESSAGE_LEN:
        print(
            f"Answer is too long. Cutting it to {MAX_TELEGRAM_MESSAGE_LEN} characters."
        )
        answer = answer[:MAX_TELEGRAM_MESSAGE_LEN]
    return answer


def modify_answer_before_sending_to_telegram(answer):
    answer = optionally_remove_answer_sections(
        answer,
        remove_cot7=REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7,
        remove_internal_dialog7=REMOVE_INTERNAL_DIALOG_FROM_ANSWER7,
    )
    answer = reduce_answer_len_to_comply_with_telegram_limit(answer)
    return answer
