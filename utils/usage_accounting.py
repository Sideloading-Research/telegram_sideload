# Simple per-round usage accounting aggregator for OpenRouter
# The IntegrationWorker starts/ends a round, and OpenRouter provider adds cost per call.

import os
from datetime import datetime

_total_cost_for_round = 0.0
is_tracking7 = False  # boolean naming convention per user preference

# --- Round-scoped GENIUS mode flag ---
GENIUS_MODE_ROUND_FLAG7 = False


def set_genius_mode7(value: bool) -> None:
    """Enable/disable GENIUS mode for the current round."""
    global GENIUS_MODE_ROUND_FLAG7
    GENIUS_MODE_ROUND_FLAG7 = bool(value)


def is_genius_mode7() -> bool:
    """Return True if GENIUS mode is active for the current round."""
    return bool(GENIUS_MODE_ROUND_FLAG7)


def clear_genius_mode7() -> None:
    """Clear GENIUS mode flag at the end of the round."""
    global GENIUS_MODE_ROUND_FLAG7
    GENIUS_MODE_ROUND_FLAG7 = False


_COSTS_DIR = os.path.join("TEMP_DATA", "COSTS")


def _ensure_costs_dir():
    try:
        os.makedirs(_COSTS_DIR, exist_ok=True)
    except Exception:
        # Avoid crashing the app on FS errors
        pass


def _month_filename(dt: datetime) -> str:
    return f"{dt.year}_{dt.month:02d}.txt"


def _month_file_path(dt: datetime) -> str:
    return os.path.join(_COSTS_DIR, _month_filename(dt))


def start_round():
    """Begin tracking a new round."""
    global _total_cost_for_round, is_tracking7
    _total_cost_for_round = 0.0
    is_tracking7 = True


def add_cost(cost):
    """Add cost to the current round (no-op if tracking is not active)."""
    global _total_cost_for_round
    if not is_tracking7:
        return
    try:
        if cost is None:
            return
        _total_cost_for_round += float(cost)
    except Exception:
        # Be resilient to unexpected types
        pass


def end_round_print():
    """Finish tracking and print the total cost for the round."""
    global is_tracking7
    if is_tracking7:
        print(f"Total OpenRouter cost this round: {_total_cost_for_round} credits")
        is_tracking7 = False


def record_round_cost_to_disk():
    """Append the current round cost with timestamp to the monthly cost file."""
    try:
        now = datetime.now()
        _ensure_costs_dir()
        path = _month_file_path(now)
        line = f"{now.isoformat()} - {_total_cost_for_round}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Avoid crashing on FS errors
        pass


def get_round_cost() -> float:
    """Return the current accumulated round cost (0.0 if not tracking)."""
    return float(_total_cost_for_round)


def get_current_month_total() -> float:
    """Sum all costs from the current month's file. Returns 0.0 if not available."""
    try:
        now = datetime.now()
        path = _month_file_path(now)
        if not os.path.exists(path):
            return 0.0
        total = 0.0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                # Expected format: timestamp - cost
                parts = line.strip().split(" - ")
                if len(parts) == 2:
                    try:
                        total += float(parts[1])
                    except Exception:
                        # Skip malformed lines
                        continue
        return total
    except Exception:
        return 0.0


def print_current_month_total():
    """Print the current month's total cost."""
    total = get_current_month_total()
    print(f"Total OpenRouter cost this month: {round(total, 3)} credits")
