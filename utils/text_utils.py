import math

SENTENCE_TOKENS = [". ", "? ", "! ", ".\n", "?\n", "!\n"]


def get_splitting_params(text, max_len):
    total_len = len(text)
    if max_len <= 0:
        raise ValueError("max_len must be positive")
    n = max(1, math.ceil(total_len / max_len))
    part_size = math.ceil(total_len / n)
    return n, part_size


def find_sentence_end_before(segment: str) -> int:
    """Return index *after* the last sentence-ending punctuation in segment.

    If no sentence boundary exists, returns -1.
    """
    best = -1
    for token in SENTENCE_TOKENS:
        idx = segment.rfind(token)
        if idx != -1:
            # Cut after the full token (e.g., after space/newline following the punctuation)
            best = max(best, idx + len(token))
    # Also treat punctuation at end-of-text as a valid boundary
    if best == -1 and segment:
        last_char = segment[-1]
        if last_char in ".?!":
            best = len(segment)
        elif (
            len(segment) >= 2
            and segment[-2] in ".?!"
            and segment[-1] in ['"', "'", ")", "]", "}", "”", "’", "»"]
        ):
            best = len(segment)
    return best


def find_sentence_start_after(segment: str) -> int:
    """Return index *at* start of first sentence inside segment.

    That is, the position just **after** the first punctuation token if
    present, otherwise -1.
    """
    best = -1
    for token in SENTENCE_TOKENS:
        idx = segment.find(token)
        if idx != -1:
            candidate = idx + len(token)
            if best == -1 or candidate < best:
                best = candidate
    # If the very first char is a closing quote/bracket after punctuation, skip it
    if best == -1 and segment:
        if segment[0] in ['"', "'", ")", "]", "}", "”", "’", "»"]:
            best = 1
    return best


def find_word_break_left(segment: str) -> int:
    cut = segment.rfind(" ")
    if cut == -1:
        cut = segment.rfind("\n")
    return cut


def find_word_break_right(segment: str) -> int:
    cut = segment.find(" ")
    if cut == -1:
        cut = segment.find("\n")
    return cut


def find_paragraph_break_left(segment: str) -> int:
    """Return index after the last paragraph break (\n\n) in segment, else -1."""
    idx = segment.rfind("\n\n")
    if idx != -1:
        return idx + 2
    return -1


def find_paragraph_break_right(segment: str) -> int:
    """Return index after the first paragraph break (\n\n) in segment, else -1."""
    idx = segment.find("\n\n")
    if idx != -1:
        return idx + 2
    return -1


def choose_context_aware_cut_index(
    source: str, start_idx: int, min_end: int, target_end: int, hard_end: int
) -> int:
    """Choose a cut index within [min_end, hard_end], aiming near target_end.

    Preference order: paragraph break > sentence end > word/newline break.
    Always cuts after the boundary token to avoid leading whitespace in next part.
    Returns an absolute index in source.
    """
    text_len = len(source)
    if min_end < start_idx + 1:
        min_end = start_idx + 1
    if hard_end > text_len:
        hard_end = text_len
    if target_end > hard_end:
        target_end = hard_end
    if target_end < min_end:
        target_end = min_end

    cut_index = -1

    # Search before/at target within allowed range
    left_start = min_end
    left_end = target_end
    before_segment = source[left_start:left_end]

    if before_segment:
        cut_rel = find_paragraph_break_left(before_segment)
        if cut_rel > 0:
            cut_index = left_start + cut_rel

    if cut_index == -1 and before_segment:
        cut_rel = find_sentence_end_before(before_segment)
        if cut_rel > 0:
            cut_index = left_start + cut_rel

    if cut_index == -1 and before_segment:
        cut_rel = find_word_break_left(before_segment)
        if cut_rel != -1:
            # Cut after the whitespace
            cut_index = left_start + cut_rel + 1

    # If not found, search after target up to hard_end
    right_start = target_end
    right_end = hard_end
    after_segment = source[right_start:right_end]

    if cut_index == -1 and after_segment:
        cut_rel = find_paragraph_break_right(after_segment)
        if cut_rel != -1 and (right_start + cut_rel) <= hard_end:
            cut_index = right_start + cut_rel

    if cut_index == -1 and after_segment:
        cut_rel = find_sentence_start_after(after_segment)
        if cut_rel != -1 and (right_start + cut_rel) <= hard_end:
            cut_index = right_start + cut_rel

    if cut_index == -1 and after_segment:
        cut_rel = find_word_break_right(after_segment)
        if cut_rel != -1 and (right_start + cut_rel + 1) <= hard_end:
            cut_index = right_start + cut_rel + 1

    if cut_index == -1:
        # Fallback to hard_end within allowed range
        cut_index = hard_end

    return cut_index


def tokenize_paragraphs(text: str):
    tokens = []
    last = 0
    i = 0
    n = len(text)
    while i + 1 < n:
        if text[i] == "\n" and text[i + 1] == "\n":
            tokens.append(text[last : i + 2])
            last = i + 2
            i += 2
        else:
            i += 1
    if last < n:
        tokens.append(text[last:])
    return tokens


def tokenize_sentences(text: str):
    tokens = []
    start = 0
    i = 0
    n = len(text)
    closing = ['"', "'", ")", "]", "}", "”", "’", "»"]
    while i < n:
        ch = text[i]
        if ch == "." or ch == "!" or ch == "?":
            end = i + 1
            while end < n and text[end] in closing:
                end += 1
            if end < n and (text[end] == " " or text[end] == "\n"):
                end += 1
            tokens.append(text[start:end])
            start = end
            i = end
        else:
            i += 1
    if start < n:
        tokens.append(text[start:])
    return tokens


def tokenize_words(text: str):
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        start = i
        while i < n and text[i] != " " and text[i] != "\n" and text[i] != "\t":
            i += 1
        while i < n and (text[i] == " " or text[i] == "\n" or text[i] == "\t"):
            i += 1
        tokens.append(text[start:i])
    return tokens


def pack_tokens_greedy_balanced(tokens, max_len: int):
    lengths = [len(t) for t in tokens]
    for l in lengths:
        if l > max_len:
            return None
    total_len = sum(lengths)
    if total_len == 0:
        return []
    n = max(1, math.ceil(total_len / max_len))
    if n == 1:
        return ["".join(tokens)]

    parts = []
    token_idx = 0
    consumed = 0
    for part_i in range(n - 1):
        remaining_len = total_len - consumed
        remaining_parts = n - part_i - 1
        lower_bound = remaining_len - remaining_parts * max_len
        if lower_bound < 1:
            lower_bound = 1
        upper_bound = remaining_len - remaining_parts
        if upper_bound > max_len:
            upper_bound = max_len
        if upper_bound < lower_bound:
            return None
        target = math.ceil(remaining_len / (remaining_parts + 1))
        if target < lower_bound:
            target = lower_bound
        if target > upper_bound:
            target = upper_bound

        cur_len = 0
        start_idx = token_idx
        # First, ensure we reach at least lower_bound
        while token_idx < len(tokens) and cur_len < lower_bound:
            next_len = lengths[token_idx]
            if cur_len + next_len > upper_bound:
                return None
            cur_len += next_len
            token_idx += 1
        # Then, try to approach target without exceeding upper_bound
        while token_idx < len(tokens) and cur_len < target:
            next_len = lengths[token_idx]
            if cur_len + next_len > upper_bound:
                break
            cur_len += next_len
            token_idx += 1
        part_text = "".join(tokens[start_idx:token_idx])
        parts.append(part_text)
        consumed += cur_len

    # Last part
    parts.append("".join(tokens[token_idx:]))
    if len(parts[-1]) > max_len:
        return None
    return parts


def split_text_into_rougthly_same_size_parts_context_aware(text, max_len):
    """
    Splits text into roughly same size parts while trying to avoid breaking paragraphs, sentences, and words.

    Each part is guaranteed to be no more than max_len characters long.
    """
    parts = []
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if max_len <= 0:
        raise ValueError("max_len must be positive")
    if len(text) == 0:
        # keep parts empty
        pass
    elif len(text) <= max_len:
        parts.append(text)
    else:
        # Level 1: paragraphs
        para_tokens = tokenize_paragraphs(text)
        parts_try = pack_tokens_greedy_balanced(para_tokens, max_len)
        if parts_try is not None:
            parts = parts_try
        else:
            # Level 2: sentences
            sent_tokens = tokenize_sentences(text)
            parts_try = pack_tokens_greedy_balanced(sent_tokens, max_len)
            if parts_try is not None:
                parts = parts_try
            else:
                # Level 3: words
                word_tokens = tokenize_words(text)
                parts_try = pack_tokens_greedy_balanced(word_tokens, max_len)
                if parts_try is not None:
                    parts = parts_try
                else:
                    # Level 4: letters
                    letter_tokens = list(text)
                    parts = pack_tokens_greedy_balanced(letter_tokens, max_len) or []
    return parts


def verify_chunk_lengths(chunks, max_len):
    ind = 0
    for chunk in chunks:
        if len(chunk.text) > max_len:
            msg = f"Chunk too large! Ind: {ind}, Len: {len(chunk.text)}, Max: {max_len}"
            print(msg)
            raise ValueError(msg)
        ind += 1
