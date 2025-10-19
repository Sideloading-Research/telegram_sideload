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
            
    diag_parts = [
        f"type:{request_type}",
        f"quality_retries:{retries}",
        f"style_iter:{style_iterations}",
        f"sys_msg_compl:{sys_compl}",
        f"self:{self_desc}",
        f"models:{models_str}"
    ]
    
    return f"[{'; '.join(diag_parts)}]"
