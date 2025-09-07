from utils.text_shrinkage_utils.shrink_dialogs import shrink_dialogs_text
from utils.text_shrinkage_utils.universal_shrinker import shrink_universal_text


def shrink_any_text(text, target_len_chars, source_type):
    print(f"## Shrinking text for {source_type}")
    if source_type == "dialogs":
        # print(f"Using dialogs shrinker for {source_type}")
        return shrink_dialogs_text(text, target_len_chars)
    else:
        # print(f"Using universal shrinker for {source_type}")
        return shrink_universal_text(text, target_len_chars)