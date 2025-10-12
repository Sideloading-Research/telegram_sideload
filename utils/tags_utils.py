from dataclasses import dataclass


from config import (
    SOURCE_TAG_CLOSE,
    SOURCE_TAG_OPEN,
    DESIGN_LINE,
    ANSWER_TO_USER_TAG,
    CHAIN_OF_THOUGHT_TAG,
    INTERNAL_DIALOG_TAG,
)


from utils.text_utils import (
    split_text_into_rougthly_same_size_parts_context_aware,
    verify_chunk_lengths,
)


@dataclass
class Text_chunk:
    text: str
    header: str


def build_source_tags(filename):
    open_tag = f"{SOURCE_TAG_OPEN}{filename}>"
    close_tag = f"{SOURCE_TAG_CLOSE}{filename}>"
    return open_tag, close_tag


SENTINEL_MARKER = "DESIGN_LINE DETECTED"


def is_closing_delimiter(delimiter: str) -> bool:
    return delimiter.startswith("</")


def classify_delimiter_line(
    line_text: str, start_delimiter: str, end_delimiters: list[str]
) -> tuple[str, str]:
    """
    Returns a tuple of (kind, matched_prefix) where kind is one of:
    - "start": matches the start delimiter prefix
    - "end_open": matches a non-closing end delimiter prefix
    - "end_close": matches a closing end delimiter prefix (starts with "</")
    - "none": no delimiter matched
    """
    if start_delimiter and line_text.startswith(start_delimiter):
        return "start", start_delimiter

    for d in end_delimiters:
        if d and line_text.startswith(d):
            if is_closing_delimiter(d):
                return "end_close", d
            return "end_open", d

    return "none", ""


def _is_design_line(line_with_newline: str) -> bool:
    if not line_with_newline:
        return False
    if line_with_newline.endswith("\n"):
        return line_with_newline[:-1] == DESIGN_LINE
    return line_with_newline == DESIGN_LINE


def _preprocess_design_wrapped_delimiters(
    text: str, start_delimiter: str, end_delimiters: list[str]
) -> str:
    if not text:
        return text

    lines = text.splitlines(keepends=True)
    to_remove: set[int] = set()

    for i in range(len(lines)):
        if i in to_remove:
            continue
        line = lines[i]
        line_no_nl = line[:-1] if line.endswith("\n") else line
        kind, _ = classify_delimiter_line(line_no_nl, start_delimiter, end_delimiters)
        if kind == "none":
            continue

        has_prev = i - 1 >= 0 and _is_design_line(lines[i - 1])
        has_next = i + 1 < len(lines) and _is_design_line(lines[i + 1])
        if has_prev and has_next:
            # Append sentinel to the delimiter line, keep prefix intact for startswith checks
            if line.endswith("\n"):
                lines[i] = f"{line_no_nl} {SENTINEL_MARKER}\n"
            else:
                lines[i] = f"{line_no_nl} {SENTINEL_MARKER}"
            to_remove.add(i - 1)
            to_remove.add(i + 1)

    preprocessed = "".join(lines[j] for j in range(len(lines)) if j not in to_remove)
    return preprocessed


def _split_core_by_delimiters(
    text: str, start_delimiter: str, end_delimiters: list[str]
) -> list[Text_chunk]:
    chunks: list[Text_chunk] = []
    if text is None or len(text) == 0:
        return chunks

    text_len = len(text)
    pos = 0
    active_chunk_start_idx: int | None = None
    active_chunk_header: str | None = None

    while pos < text_len:
        next_nl = text.find("\n", pos)
        line_end = next_nl if next_nl != -1 else text_len
        line_end_with_nl = (line_end + 1) if next_nl != -1 else line_end
        line_text = text[pos:line_end]

        kind, _ = classify_delimiter_line(line_text, start_delimiter, end_delimiters)

        if kind == "start" or kind == "end_open":
            if active_chunk_start_idx is not None and active_chunk_header is not None:
                chunks.append(
                    Text_chunk(
                        text=text[active_chunk_start_idx:pos],
                        header=active_chunk_header,
                    )
                )
            active_chunk_start_idx = pos
            active_chunk_header = line_text

        elif kind == "end_close":
            if active_chunk_start_idx is None or active_chunk_header is None:
                active_chunk_start_idx = pos
                active_chunk_header = "EMPTY HEADER"

            chunks.append(
                Text_chunk(
                    text=text[active_chunk_start_idx:line_end_with_nl],
                    header=active_chunk_header,
                )
            )
            active_chunk_start_idx = None
            active_chunk_header = None

        else:
            if active_chunk_start_idx is None or active_chunk_header is None:
                active_chunk_start_idx = pos
                active_chunk_header = "EMPTY HEADER"

        pos = line_end_with_nl

    if active_chunk_start_idx is not None and active_chunk_header is not None:
        chunks.append(
            Text_chunk(
                text=text[active_chunk_start_idx:text_len], header=active_chunk_header
            )
        )

    return chunks


def _postprocess_restore_design_wrapped(chunks: list[Text_chunk]) -> list[Text_chunk]:
    if not chunks:
        return chunks

    restored: list[Text_chunk] = []
    for ch in chunks:
        # Sanitize header: remove sentinel if present
        header = ch.header.replace(f" {SENTINEL_MARKER}", "").replace(
            SENTINEL_MARKER, ""
        )

        # Expand sentinel back into DESIGN_LINE wrappers in text
        lines = ch.text.splitlines(keepends=True)
        new_lines: list[str] = []
        for line in lines:
            has_nl = line.endswith("\n")
            nl = "\n" if has_nl else ""
            core = line[:-1] if has_nl else line
            if SENTINEL_MARKER in core:
                core_no_sentinel = core.replace(f" {SENTINEL_MARKER}", "").replace(
                    SENTINEL_MARKER, ""
                )
                new_lines.append(f"{DESIGN_LINE}{nl}")
                new_lines.append(f"{core_no_sentinel}{nl}")
                new_lines.append(f"{DESIGN_LINE}{nl}")
            else:
                new_lines.append(line)

        restored_text = "".join(new_lines)
        restored.append(Text_chunk(text=restored_text, header=header))

    return restored


def _line_core_without_nl_and_sentinel(line_with_newline: str) -> str:
    has_nl = line_with_newline.endswith("\n")
    core = line_with_newline[:-1] if has_nl else line_with_newline
    core = core.replace(f" {SENTINEL_MARKER}", "").replace(SENTINEL_MARKER, "")
    return core


def _is_prefix_only_chunk(
    chunk: Text_chunk, start_delimiter: str, end_delimiters: list[str]
) -> bool:
    if chunk is None or not chunk.text:
        return False
    lines = chunk.text.splitlines(keepends=True)
    if len(lines) == 0:
        return False
    for ln in lines:
        # skip purely blank lines
        if ln.strip() == "":
            continue
        core = _line_core_without_nl_and_sentinel(ln)
        kind, _ = classify_delimiter_line(core, start_delimiter, end_delimiters)
        if kind != "end_open":
            return False
    return True


def _merge_prefix_only_chunks(
    chunks: list[Text_chunk], start_delimiter: str, end_delimiters: list[str]
) -> list[Text_chunk]:
    if not chunks:
        return chunks
    merged: list[Text_chunk] = []
    i = 0
    n = len(chunks)
    while i < n:
        curr = chunks[i]
        if _is_prefix_only_chunk(curr, start_delimiter, end_delimiters):
            j = i + 1
            combined_parts: list[str] = [curr.text]
            while j < n and _is_prefix_only_chunk(
                chunks[j], start_delimiter, end_delimiters
            ):
                combined_parts.append(chunks[j].text)
                j += 1
            if j < n:
                combined_parts.append(chunks[j].text)
                merged.append(
                    Text_chunk(text="".join(combined_parts), header=chunks[j].header)
                )
                i = j + 1
                continue
            else:
                for k in range(i, n):
                    merged.append(chunks[k])
                break
        else:
            merged.append(curr)
            i += 1
    return merged


def split_string_by_delimiters(
    text: str, start_delimiter: str, end_delimiters: list[str]
) -> list[Text_chunk]:
    """
    Splits a string into a list of Text_chunk objects based on a start delimiter and a list of possible end delimiters.
    Requirements:
    - It should be general, no hardcoded delimiters here
    - don't remove delimiters themselves from the text
    - It should handle the situation where there is no start delimiter in the text (assume the start of the text as a start delimiter)
    - process the delimiters that start with "</" as closing delimiters (attach them to the previous chunk)
    - consult config.py and mindfile.py for the delimiters we use, to better understand what is expected from this func.
    - the entire text is processed. The output should contain everything from it, but can be a bit bigger.
    - If the first content before any start_delimiter exists, use "EMPTY HEADER" as chunk.header
    - any delimiter encountered - should end the chunk

    Assumptions:
    - the delimiters provided in the inputs are prefixes, placed at the start of the line. The full delimiter (aka header) is the entire line.
    - they are always in the same case (case-sensitive)
    - the dilimiters dont contain newlines (I've updated config.py accordingly)
    - We expect a relatively small text (a few MB).

    """

    # Preprocess DESIGN_LINE wrappers into a sentinel on the delimiter line
    original_text = text or ""
    preprocessed = _preprocess_design_wrapped_delimiters(
        original_text, start_delimiter, end_delimiters
    )

    # Core splitting
    core_chunks = _split_core_by_delimiters(
        preprocessed, start_delimiter, end_delimiters
    )

    # Merge chunks that contain only prefixes (like source open or batch title) and blanks
    core_chunks = _merge_prefix_only_chunks(
        core_chunks, start_delimiter, end_delimiters
    )

    # Postprocess: restore DESIGN_LINE wrappers and sanitize headers
    chunks = _postprocess_restore_design_wrapped(core_chunks)

    total_length = sum(len(c.text) for c in chunks)
    # Useful debug info, keep it
    print(f"Total length of text in chunks: {total_length}")

    return chunks


def split_string_by_delimiters_with_max_len(
    text: str, start_delimiter: str, end_delimiters: list[str], max_len: int
) -> list[Text_chunk]:
    """
    Splits a string by delimiters and then further splits chunks that exceed a maximum length.
    """
    raw_chunks = split_string_by_delimiters(text, start_delimiter, end_delimiters)
    new_chunks = []
    for chunk in raw_chunks:
        if len(chunk.text) > max_len:
            # Pre-subtract the longest possible decoration from max_len
            partial_suffix = " [partial]"
            cont_prefix = f"{chunk.header} [continuation] \n\n"
            longest_decoration = max(len(partial_suffix), len(cont_prefix))
            payload_max_len = max(1, max_len - longest_decoration)

            parts = split_text_into_rougthly_same_size_parts_context_aware(
                chunk.text, payload_max_len
            )
            is_first_part7 = True
            for part_text in parts:
                if is_first_part7:
                    # Add full suffix if it still fits, else omit
                    if (
                        len(part_text) + len(partial_suffix) <= max_len
                        and chunk.header in part_text
                    ):
                        modified_text = part_text.replace(
                            chunk.header, f"{chunk.header}{partial_suffix}", 1
                        )
                    else:
                        modified_text = part_text
                    new_chunks.append(
                        Text_chunk(text=modified_text, header=chunk.header)
                    )
                    is_first_part7 = False
                else:
                    # Prepend full continuation prefix if it fits, else omit
                    if len(cont_prefix) + len(part_text) <= max_len:
                        modified_text = f"{cont_prefix}{part_text}"
                    else:
                        modified_text = part_text
                    new_chunks.append(
                        Text_chunk(text=modified_text, header=chunk.header)
                    )
        else:
            new_chunks.append(chunk)

    # print("#########")
    # print("New sizes:")
    # for chunk in new_chunks:
    #     print(f"{len(chunk.text)} - {chunk.header}")
    # print("#########")

    verify_chunk_lengths(new_chunks, max_len)

    return new_chunks


def remove_section_by_tags(answer, start_tag, end_tag):
    """Remove a section enclosed by the given start and end tags."""
    start_idx = answer.lower().find(start_tag.lower())
    if start_idx == -1:
        return answer

    end_idx = answer.lower().find(end_tag.lower(), start_idx)
    if end_idx == -1:
        return answer

    return (
        answer[:start_idx].rstrip() + "\n" + answer[end_idx + len(end_tag) :].lstrip()
    )


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

    content = answer[start_idx + len(start_tag) : end_idx].strip()
    return content


def remove_tag_section(answer, tag_identifier):
    """Remove a section with standardized tags."""
    # Try standard format
    result = remove_section_by_tags(
        answer, f"<{tag_identifier}>", f"</{tag_identifier}>"
    )

    # If unchanged, try with "my" prefix
    if result == answer:
        result = remove_section_by_tags(
            answer, f"<my {tag_identifier}>", f"</my {tag_identifier}>"
        )

    return result


def clean_whitespace(answer):
    """Remove extra whitespace and empty lines from the answer."""
    return "\n".join(line for line in answer.splitlines() if line.strip())


def optionally_remove_answer_sections(
    answer, remove_cot7=False, remove_internal_dialog7=False
):
    """
    Remove specified sections from the answer (chain of thought and/or internal dialog).
    Returns the modified answer with cleaned whitespace.
    """
    #print("\n--- ENTERING optionally_remove_answer_sections ---")
    #print(f"REMOVE COT: {remove_cot7}, REMOVE DIALOG: {remove_internal_dialog7}")
    #print("--- ORIGINAL ANSWER ---")
    #print(answer)

    if not isinstance(answer, str):
        print(f"## The answer is not a string: {str(answer)}")
        return str(answer)

    original_answer = answer

    try:
        processed_answer = answer
        if remove_cot7:
            processed_answer = remove_tag_section(processed_answer, CHAIN_OF_THOUGHT_TAG)
            #print("--- AFTER COT REMOVAL ---")
            #print(processed_answer)

        if remove_internal_dialog7:
            processed_answer = remove_tag_section(processed_answer, INTERNAL_DIALOG_TAG)
            #print("--- AFTER DIALOG REMOVAL ---")
            #print(processed_answer)

        processed_answer = clean_whitespace(processed_answer)
        #print("--- AFTER WHITESPACE CLEANING ---")
        #print(processed_answer)

        # Only keep content from the "answer to the user" section if both CoT and internal dialog are removed
        if remove_cot7 and remove_internal_dialog7:
            # Try to extract just the answer part if it exists
            extracted = extract_content_from_tag(processed_answer, ANSWER_TO_USER_TAG)
            #print(f"--- EXTRACTED CONTENT ---: {extracted}")

            if extracted:
                processed_answer = extracted
            else:
                # Special case: If the tag exists but has no closing tag, just remove the opening tag
                processed_answer = processed_answer.replace(f"<{ANSWER_TO_USER_TAG}>", "")

        #print("--- FINAL PROCESSED ANSWER ---")
        #print(processed_answer)

        if len(processed_answer) >= len(original_answer):
            if remove_cot7 or remove_internal_dialog7:
                print("## WARNING: optionally_remove_answer_sections did not shorten the answer.")

        #print("--- EXITING optionally_remove_answer_sections ---\n")

        return processed_answer

    except Exception as e:
        msg = f"## Error processing answer: {str(e)}"
        print(msg)
        return msg + "\n" + str(original_answer)
