from utils.usage_accounting import get_round_cost, get_current_month_total

# Helper to remove vowels for compact output

def remove_vowels(s: str) -> str:
    vowels = set("aeiouAEIOU")
    return "".join(ch for ch in s if ch not in vowels)


def build_diag_info(retries_taken: int, scores: dict, models_used: set, request_type: str, style_iterations: int) -> dict:
    """Builds the diagnostic dictionary from its components."""
    return {
        "retries": retries_taken,
        "scores": scores,
        "models_used": models_used,
        "request_type": request_type,
        "style_iterations": style_iterations,
    }


def format_diag_info(diag_info: dict) -> str:
    """Formats the diagnostic dictionary into a user-facing string."""
    
    retries = diag_info.get("retries", "N/A")
    style_iterations = diag_info.get("style_iterations", "N/A")
    request_type = diag_info.get("request_type", "N/A")
    
    scores = diag_info.get("scores", {})
    sys_compl = scores.get("sys_message_compliance", "N/A")
    self_desc = scores.get("self_description_correctness", "N/A")
    
    models_used = diag_info.get("models_used", set())
    if models_used:
        # Ditch the provider part for brevity, e.g., "google/gemini-2.5-flash" -> "gemini-2.5-flash"
        short_model_names = [name.split('/')[-1] for name in models_used]
        models_str = ", ".join(sorted(short_model_names))
    else:
        models_str = "N/A"
            
    # Abbreviated labels (keep them without vowels, as they will be removed for compactness)
    diag_parts = [
        f"t:{request_type}",            # type
        f"qr:{retries}",               # quality_retries
        f"st:{style_iterations}",      # style_iter
        f"smc:{sys_compl}",            # sys_msg_compl
        f"slf:{self_desc}",            # self
        f"m:{models_str}",             # models
    ]
    
    # Usage accounting (always available; non-OpenRouter rounds will just be zeros)
    rc_val = get_round_cost()
    mc_val = get_current_month_total()
    diag_parts.append(f"rc:{round(rc_val, 1)}")
    diag_parts.append(f"mc:{int(round(mc_val, 0))}")
    
    # Remove spaces between entries by joining with ';' and then remove vowels for compactness
    compact = f"[{';'.join(diag_parts)}]"
    compact = remove_vowels(compact)

    # also remove "-" to shorten model names
    compact = compact.replace("-", "")

    return compact