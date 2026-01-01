# Group Settings and Limits Guide

## Overview

This bot supports per-group configuration to manage how it interacts in different communities. This allows you to set specific rules, descriptions, and crucially, rate limits to prevent the bot from becoming spammy.

## Configuration File

Settings are stored in the `groups_settings/` directory. Each group has its own `.txt` file (e.g., `sideloading.txt`). The filename doesn't matter, but the `group_id` inside must match the Telegram group ID.

### Example Configuration

```ini
group_id = -1001234567890
group_description = "A friendly group about Python programming."
group_rules = "1. Be nice.\n2. No spam."
max_autotrigger_messages_per_day = 10
max_requested_messages_per_day = 50
```

## Daily Message Limits

To control the volume of bot messages, two specific limits are available. These limits reset daily (at midnight local server time).

### 1. `max_autotrigger_messages_per_day`
Controls messages sent by the bot when it was **not** explicitly asked to speak, but was triggered by a specific keyword (Trigger Word) in the chat.

*   **Usage:** Messages containing words from `TRIGGER_WORDS` (in `bot_config.py`/env vars).
*   **Behavior:** If the limit is reached, the bot will simply ignore further trigger words for the rest of the day.

### 2. `max_requested_messages_per_day`
Controls messages sent by the bot when it is **explicitly** solicited.

*   **Usage:**
    *   Direct replies to the bot's messages.
    *   Mentions of the bot (`@BotName`).
    *   Messages containing the bot's name (Text Mention).
*   **Precedence:** If a message contains both a trigger word AND a mention, it counts as **Requested**.

### Usage Rules

*   **Zero (0) means Forbidden:** If a limit is set to `0`, the bot will **never** respond to that type of trigger in that group.
*   **Default Limits:** If a limit is NOT defined in the group's file (or the file doesn't exist), the bot uses the **generic defaults** defined in `config.py`:
    *   `DEFAULT_MAX_AUTOTRIGGER_MESSAGES_PER_DAY`
    *   `DEFAULT_MAX_REQUESTED_MESSAGES_PER_DAY`
*   **Counting:** Quotas are consumed only when the bot **successfully sends** a reply. Failed attempts (e.g., network errors) generally do not count.

### Global Override

The configuration variable `BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7` (in `config.py`) significantly impacts these limits:

*   **If `True` (Default):** The bot is in "Respectful Mode". It only answers when mentioned or triggered. The group limits described above **apply**.
*   **If `False`:** The bot is in "Chatty Mode" (answers every message). In this mode, **group limits are IGNORED**. The bot assumes if you turned this mode on, you want it to participate in everything.

## Adding a New Group

1.  Get the Group ID (e.g., forward a message to a bot like `@userinfobot` or look at logs).
2.  Create a new `.txt` file in `groups_settings/`.
3.  Add the `group_id` and desired limits.
4.  (Optional) Reload the bot to pick up the new file immediately (though it usually scans on request).

