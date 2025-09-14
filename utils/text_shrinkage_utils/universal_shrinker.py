from utils.text_utils import (
    find_sentence_end_before,
    find_sentence_start_after,
    find_word_break_left,
    find_word_break_right,
)


def shrink_universal_text(text: str, target_len_chars: int) -> str:
    """Shrink any text to roughly *target_len_chars* characters.

    The strategy is deliberately simple and **domain-agnostic** so it can be
    applied to any body of text (articles, code, e-mails, etc.).  It keeps the
    *beginning* and the *end* of the input verbatim and replaces the removed
    middle section with a placeholder ("<...>").

    1.  If the original text is already shorter than *target_len_chars*, it is
        returned unchanged.
    2.  Otherwise, we reserve space for the placeholder and split the remaining
        budget approximately in half between the head and the tail.
    3.  We try to cut at the closest **word boundary** (space/new-line) so that
        we do not break words in half.  This keeps the output more readable
        while still deterministic and lightweight (no heavy NLP dependencies).

    Prefer cutting on **sentence boundaries**; fall back to word boundaries.

    The algorithm is *O(n)* in the length of the input and requires no external
    libraries beyond the Python standard library.
    """

    # Fast path – already within the allowed length.
    if len(text) <= target_len_chars:
        return text

    placeholder = "<...>"

    # If the target length is extremely small, we may not even be able to fit
    # the placeholder plus some context. In that degenerate case, just truncate
    # hard and append an ellipsis-like marker.
    if target_len_chars <= len(placeholder) + 2:
        return text[: max(0, target_len_chars - len(placeholder))] + placeholder

    # Budget for real content once placeholder is inserted.
    remaining_len = target_len_chars - len(placeholder)
    head_len = remaining_len // 2
    tail_len = remaining_len - head_len  # ensures total matches exactly

    # ----------------------------------------------------------------------

    head_part = text[:head_len]
    tail_part = text[-tail_len:]

    # Try sentence boundary first
    cut_left = find_sentence_end_before(head_part)
    if cut_left == -1:
        cut_left = find_word_break_left(head_part)

    if cut_left != -1 and cut_left < len(head_part) - 8:  # keep reasonable size
        head_part = head_part[: cut_left + 1].rstrip()

    cut_right = find_sentence_start_after(tail_part)
    if cut_right == -1:
        cut_right = find_word_break_right(tail_part)

    if 0 < cut_right < len(tail_part) - 8:
        tail_part = tail_part[cut_right:].lstrip()

    # Finally, assemble the shrunk text. We use newline if the adjacent
    # characters already contain newlines; otherwise keep as single string.
    # This prevents accidental word concatenation.
    joiner = "\n" if (head_part.endswith("\n") or tail_part.startswith("\n")) else ""
    shrunk_text = f"{head_part}{joiner}{placeholder}{joiner}{tail_part}"

    # Edge-case guard: Ensure we didn't overshoot due to adjustments. If we did,
    # simply hard truncate from the end.
    if len(shrunk_text) > target_len_chars:
        shrunk_text = shrunk_text[:target_len_chars]

    return shrunk_text
