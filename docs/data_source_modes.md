# Data Source Modes

The bot supports four data source modes that control how much of the mindfile is loaded into each AI request. Smaller modes are cheaper and faster but provide the AI with less context.

## The Four Modes

| Mode | What it loads | When to use |
|---|---|---|
| `NORMAL` | Full mindfile from the remote GitHub repo (or `LOCAL_MINDFILE_DIR_PATH` if set) | Production — richest context |
| `MICRO` | `micro_sideload.txt` from the repo's `smaller_versions_of_dataset/fallback_versions/` path | Cost-saving fallback |
| `NANO` | `nano_sideload.txt` from the same fallback path | Extreme cost savings |
| `QUICK_TEST` | Local directory defined by `QUICK_TEST_SIDELOAD` in `config.py` | Development and testing only |

### Static configuration

The initial mode is set via `DATA_SOURCE_MODE` in `config.py`. Change this value and restart the bot to make it permanent.

```python
DATA_SOURCE_MODE = "NORMAL"   # recommended for production
```

---

## Manual Admin Commands

Any authorised user can switch modes at runtime by sending a plain text message to the bot:

| Command | Effect |
|---|---|
| `admin:norm` | Switch to NORMAL mode |
| `admin:micro` | Switch to MICRO mode |
| `admin:nano` | Switch to NANO mode |
| `admin:test` | Switch to QUICK_TEST mode |

The bot confirms each switch with a short acknowledgement message. The mindfile is refreshed immediately.

> **Override expiry**: when `DATA_SOURCE_MODE = "NORMAL"` is set in `config.py`, manual commands create a *temporary* override that expires at the end of the current calendar day (see [Cost-Based Auto-Switching](#cost-based-auto-switching) below).

---

## Cost-Based Auto-Switching

When `DATA_SOURCE_MODE = "NORMAL"` is set in `config.py`, the bot monitors monthly API spend and automatically downgrades to a cheaper mode to stay within budget.

### Thresholds

| Monthly spend | Mode |
|---|---|
| < 50 % of `MAX_COST_PER_MONTH_USD` | NORMAL |
| 50 – 75 % | MICRO |
| ≥ 75 % | NANO |

The thresholds are configurable in `config.py`:

```python
COST_MODE_MICRO_THRESHOLD_PCT = 0.50
COST_MODE_NANO_THRESHOLD_PCT  = 0.75
```

### When the check runs

- **On startup** — before the bot begins polling.
- **After every AI request** — immediately after costs are recorded to disk.

The mode is only changed (and the mindfile refreshed) when the target mode differs from the current one, so most requests incur no overhead.

### User override

A manual admin command (e.g. `admin:micro`) sets a *user override* that prevents the auto-switcher from changing the mode for the rest of the current calendar day. At the start of the next day (detected on the first incoming request), the override expires and cost-based selection resumes automatically.

### When auto-switching is disabled

Auto-switching is active **only** when the static `DATA_SOURCE_MODE` in `config.py` equals `"NORMAL"`. If the admin hard-coded `"NANO"` or `"MICRO"` there, the auto-switcher does nothing — that static value is treated as an intentional permanent choice.

### Relevant source files

| File | Role |
|---|---|
| `utils/cost_mode_switcher.py` | All auto-switching logic and override state |
| `utils/usage_accounting.py` | Monthly cost totals read from disk |
| `config.py` | `MAX_COST_PER_MONTH_USD`, threshold percentages, `ORIGINAL_DATA_SOURCE_MODE` |
| `main.py` | Calls `apply_cost_based_mode()` on startup and after each AI reply |
