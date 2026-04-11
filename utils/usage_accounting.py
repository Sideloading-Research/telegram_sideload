# Per-round cost tracking and historical cost I/O for OpenRouter.
# The IntegrationWorker starts/ends a round; the OpenRouter provider adds cost per call.

import os
from datetime import datetime
from config import PROJECT_ROOT
from utils.time_utils import get_monday_of_current_week

_total_cost_for_round = 0.0
is_tracking7 = False

# --- Round-scoped flags ---
GENIUS_MODE_ROUND_FLAG7 = False
FIXED_MODEL_ROUND_OVERRIDE: str | None = None
QUALITY_RETRIES_ROUND_OVERRIDE: int | None = None


def set_genius_mode7(value: bool) -> None:
    global GENIUS_MODE_ROUND_FLAG7
    GENIUS_MODE_ROUND_FLAG7 = bool(value)


def is_genius_mode7() -> bool:
    return bool(GENIUS_MODE_ROUND_FLAG7)


def clear_genius_mode7() -> None:
    global GENIUS_MODE_ROUND_FLAG7
    GENIUS_MODE_ROUND_FLAG7 = False


def set_fixed_model_for_round(model_name: str) -> None:
    global FIXED_MODEL_ROUND_OVERRIDE
    FIXED_MODEL_ROUND_OVERRIDE = model_name


def get_fixed_model_for_round() -> str | None:
    return FIXED_MODEL_ROUND_OVERRIDE


def clear_fixed_model_for_round() -> None:
    global FIXED_MODEL_ROUND_OVERRIDE
    FIXED_MODEL_ROUND_OVERRIDE = None


def set_quality_retries_for_round(retries: int) -> None:
    global QUALITY_RETRIES_ROUND_OVERRIDE
    QUALITY_RETRIES_ROUND_OVERRIDE = int(retries)


def get_quality_retries_for_round() -> int | None:
    return QUALITY_RETRIES_ROUND_OVERRIDE


def clear_quality_retries_for_round() -> None:
    global QUALITY_RETRIES_ROUND_OVERRIDE
    QUALITY_RETRIES_ROUND_OVERRIDE = None


# --- Round tracking ---

_COSTS_DIR = os.path.join(PROJECT_ROOT, "TEMP_DATA", "COSTS")


def _ensure_costs_dir():
    try:
        os.makedirs(_COSTS_DIR, exist_ok=True)
    except Exception:
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
        pass


def get_round_cost() -> float:
    """Return the current accumulated round cost (0.0 if not tracking)."""
    return float(_total_cost_for_round)


# --- Historical cost totals ---

def _read_month_file(year: int, month: int) -> list[tuple[datetime, float]]:
    """Read a monthly cost file and return parsed (timestamp, cost) pairs."""
    path = os.path.join(_COSTS_DIR, f"{year}_{month:02d}.txt")
    entries = []
    if not os.path.exists(path):
        return entries
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(" - ")
                if len(parts) == 2:
                    try:
                        ts = datetime.fromisoformat(parts[0])
                        cost = float(parts[1])
                        entries.append((ts, cost))
                    except Exception:
                        continue
    except Exception:
        pass
    return entries


def get_today_total() -> float:
    """Sum all costs recorded today."""
    now = datetime.now()
    entries = _read_month_file(now.year, now.month)
    return sum(cost for ts, cost in entries if ts.date() == now.date())


def get_week_total() -> float:
    """Sum costs since Monday 00:00:00 of the current calendar week."""
    monday = get_monday_of_current_week()
    now = datetime.now()
    entries = _read_month_file(now.year, now.month)
    if monday.month != now.month:
        entries += _read_month_file(monday.year, monday.month)
    return sum(cost for ts, cost in entries if ts >= monday)


def get_current_month_total() -> float:
    """Sum all costs from the current month's file."""
    now = datetime.now()
    entries = _read_month_file(now.year, now.month)
    return sum(cost for _, cost in entries)


def print_current_month_total():
    """Print the current month's total cost."""
    total = get_current_month_total()
    print(f"Total OpenRouter cost this month: {round(total, 3)} credits")
