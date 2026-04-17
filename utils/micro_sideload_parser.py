import os

# Maps XML section tag names in micro_sideload.txt to mindfile filenames (without .txt).
# Order matches the sections as they appear in the file.
SECTION_TAG_TO_FILENAME = {
    "self-description": "structured_self_facts",
    "consumed_media_list": "consumed_media_list",
    "dialogs": "dialogs",
    "dreams": "dreams",
    "interviews_etc": "interviews_etc",
    "writings_fiction": "writings_fiction",
    "writings_non_fiction": "writings_non_fiction",
    "structured_memories": "structured_memories",
}

# The first data section tag — everything before it is the system message.
FIRST_SECTION_TAG = "self-description"


def _extract_inner_content(full_text: str, tag_name: str) -> str | None:
    """Returns stripped content between <tag_name> and </tag_name>, or None if absent."""
    open_tag = f"<{tag_name}>"
    close_tag = f"</{tag_name}>"
    start_idx = full_text.find(open_tag)
    if start_idx == -1:
        return None
    content_start = start_idx + len(open_tag)
    end_idx = full_text.find(close_tag, content_start)
    if end_idx == -1:
        return None
    return full_text[content_start:end_idx].strip()


def _extract_system_message(full_text: str) -> str:
    """Returns stripped content before the first data section tag."""
    first_tag = f"<{FIRST_SECTION_TAG}>"
    idx = full_text.find(first_tag)
    if idx == -1:
        return full_text.strip()
    return full_text[:idx].strip()


def _read_file(file_path: str) -> str:
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def parse_micro_sideload(file_path: str) -> dict[str, str]:
    """
    Parses micro_sideload.txt into {mindfile_filename: content}.
    Only sections present in the file are included.
    """
    full_text = _read_file(file_path)
    sections = {"system_message": _extract_system_message(full_text)}
    for tag_name, filename in SECTION_TAG_TO_FILENAME.items():
        content = _extract_inner_content(full_text, tag_name)
        if content is not None:
            sections[filename] = content
    return sections
