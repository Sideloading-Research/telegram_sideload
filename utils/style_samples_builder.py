QUOTE_PREFIX = "QUOTE: "


def _find_quote_start_positions(text: str) -> list[int]:
    """Returns positions where QUOTE: appears at the start of a line."""
    positions = []
    idx = 0
    prefix_len = len(QUOTE_PREFIX)
    while True:
        pos = text.find(QUOTE_PREFIX, idx)
        if pos == -1:
            break
        if pos == 0 or text[pos - 1] == '\n':
            positions.append(pos)
        idx = pos + prefix_len
    return positions


def _extract_raw_quotes(text: str) -> list[str]:
    """Extracts the raw text following each QUOTE: marker (up to the next one)."""
    positions = _find_quote_start_positions(text)
    prefix_len = len(QUOTE_PREFIX)
    raw_quotes = []
    for i, pos in enumerate(positions):
        start = pos + prefix_len
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        raw_quotes.append(text[start:end])
    return raw_quotes


def _clean_raw_quote(raw: str) -> str:
    """Strips surrounding whitespace and wrapping double-quotes from a raw quote block."""
    text = raw.strip()
    if text.startswith('"'):
        text = text[1:]
    close_pos = text.rfind('"')
    if close_pos != -1:
        text = text[:close_pos]
    return text.strip()


def extract_quotes(dialogs_content: str) -> list[str]:
    """Returns cleaned quote strings extracted from dialogs content."""
    raw_quotes = _extract_raw_quotes(dialogs_content)
    cleaned = [_clean_raw_quote(r) for r in raw_quotes]
    return [q for q in cleaned if q]


def build_style_samples_content(dialogs_content: str) -> str | None:
    """
    Builds style_samples text from QUOTE: parts in dialogs content.
    Returns None if no quotes are found.
    """
    quotes = extract_quotes(dialogs_content)
    if not quotes:
        return None
    return "\n\n".join(quotes)
