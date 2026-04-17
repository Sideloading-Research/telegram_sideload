"""
Automatic DATA_SOURCE_MODE selection based on monthly cost.
Only active when ORIGINAL_DATA_SOURCE_MODE == "NORMAL" in config —
a non-NORMAL static config means the admin intentionally fixed the mode.

User admin commands set a temporary override that expires at the end of
the current calendar day; the next incoming request of a new day
reverts to cost-based selection.
"""

from datetime import date
import config
import utils.usage_accounting as ua

_override_mode: str | None = None
_override_date: date | None = None


def is_cost_switching_enabled() -> bool:
    return config.ORIGINAL_DATA_SOURCE_MODE == "NORMAL"


def get_cost_based_mode() -> str:
    monthly_total = ua.get_current_month_total()
    nano_threshold = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_NANO_THRESHOLD_PCT
    micro_threshold = config.MAX_COST_PER_MONTH_USD * config.COST_MODE_MICRO_THRESHOLD_PCT
    if monthly_total >= nano_threshold:
        return "NANO"
    if monthly_total >= micro_threshold:
        return "MICRO"
    return "NORMAL"


def set_user_override(mode: str) -> None:
    global _override_mode, _override_date
    _override_mode = mode
    _override_date = date.today()


def is_override_active() -> bool:
    if _override_mode is None or _override_date is None:
        return False
    return _override_date >= date.today()


def _clear_override() -> None:
    global _override_mode, _override_date
    _override_mode = None
    _override_date = None


def _expire_override_if_stale() -> None:
    if _override_date is not None and _override_date < date.today():
        _clear_override()


def apply_cost_based_mode(mind_manager) -> None:
    if not is_cost_switching_enabled():
        return
    _expire_override_if_stale()
    if is_override_active():
        return
    target_mode = get_cost_based_mode()
    if config.DATA_SOURCE_MODE == target_mode:
        return
    config.set_data_source_mode(target_mode)
    mind_manager.force_refresh()
    print(f"Cost-based mode switch: → {target_mode} (monthly: ${ua.get_current_month_total():.2f})")
