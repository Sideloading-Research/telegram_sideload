from config import MAX_TELEGRAM_MESSAGE_LEN, REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7, REMOVE_INTERNAL_DIALOG_FROM_ANSWER7


def remove_section_by_tags(answer, start_tag, end_tag):
    """Remove a section enclosed by the given start and end tags."""
    start_idx = answer.lower().find(start_tag.lower())
    if start_idx == -1:
        return answer

    end_idx = answer.lower().find(end_tag.lower(), start_idx)
    if end_idx == -1:
        return answer

    return (
        answer[:start_idx].rstrip()
        + "\n"
        + answer[end_idx + len(end_tag):].lstrip()
    )


def clean_whitespace(answer):
    """Remove extra whitespace and empty lines from the answer."""
    return "\n".join(line for line in answer.splitlines() if line.strip())


def extract_content_from_tag(answer, tag_identifier):
    """Extract content within standardized tags."""
    start_tag = f"<{tag_identifier}>"
    end_tag = f"</{tag_identifier}>"
    
    start_idx = answer.lower().find(start_tag.lower())
    if start_idx == -1:
        # Try with "my" prefix
        start_tag = f"<my {tag_identifier}>"
        end_tag = f"</my {tag_identifier}>"
        start_idx = answer.lower().find(start_tag.lower())
        if start_idx == -1:
            return None
            
    end_idx = answer.lower().find(end_tag.lower(), start_idx)
    if end_idx == -1:
        return None
        
    content = answer[start_idx + len(start_tag):end_idx].strip()
    return content


def remove_tag_section(answer, tag_identifier):
    """Remove a section with standardized tags."""
    # Try standard format
    result = remove_section_by_tags(
        answer,
        f"<{tag_identifier}>",
        f"</{tag_identifier}>"
    )
    
    # If unchanged, try with "my" prefix
    if result == answer:
        result = remove_section_by_tags(
            answer,
            f"<my {tag_identifier}>",
            f"</my {tag_identifier}>"
        )
        
    return result


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
        if remove_cot7:
            answer = remove_tag_section(answer, "chain of thought")

        if remove_internal_dialog7:
            answer = remove_tag_section(answer, "internal dialog")

        answer = clean_whitespace(answer)

        # Only keep content from the "answer to the user" section if both CoT and internal dialog are removed
        if remove_cot7 and remove_internal_dialog7:
            # Try to extract just the answer part if it exists
            extracted = extract_content_from_tag(answer, "answer to the user")

            # print(f"Extracted: {extracted}")

            if extracted:
                return extracted
            else:
                # Special case: If the tag exists but has no closing tag, just remove the opening tag
                answer = answer.replace("<my answer to the user>", "")
            
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
