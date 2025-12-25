# Flood Protection & Security Features

This document describes the security measures implemented in the bot to protect against abuse, floods, and unauthorized usage.

## 1. Rate Limiting (Flood Protection)

The bot implements a global rate limiter to prevent LLM cost spikes and API abuse.

### Mechanism
- **Algorithm**: Sliding window counter.
- **Storage**: Request timestamps are stored in `TEMP_DATA/global_request_timestamps.txt`.
- **Limit**: Defined by `GLOBAL_RATE_LIMIT_REQUESTS_PER_MINUTE` in `config.py` (default: 10 requests/minute).

### Behavior
1. **Normal Operation**: As long as the global request count is below the limit, requests are processed normally.
2. **Limit Exceeded**:
   - The bot stops processing the "heavy" logic (LLM generation).
   - **Silent Blocking**: Most requests are dropped silently to avoid spamming the chat.
   - **Warning Message**: Once per minute, if the limit is exceeded, the bot replies with a configured warning (e.g., "Dude, slow down...").
   - This prevents the bot from sending 100 replies to 100 spammed messages.

### Self-Cleaning
The timestamp file is automatically pruned on every request. Timestamps older than 60 seconds are discarded, ensuring the file size remains negligible regardless of uptime.

---

## 2. Jailbreak Detection

The bot uses the `DoormanWorker` to classify each incoming request.

### Mechanism
- **Classification**: The `DoormanWorker` analyzes the user's prompt + recent context and classifies it into one of: `SHALLOW`, `DEEP`, `GENIUS`, `JAILBREAK`, or `EXPLOITATION`.
- **Trigger**: An LLM-based classifier (prompted to detect malicious intent) makes this decision.
- **Action**:
  - If classified as `JAILBREAK` or `EXPLOITATION`:
    - The bot **overrides** the user's message with a sanitized, pre-configured alarm text (e.g., "Seems the user attempted to jailbreak...").
    - This sanitized message is what the downstream workers (Style, Quality, etc.) see and respond to.
    - The `IntegrationWorker` forces "Shallow Mode" (skipping deep DB lookups) for these requests to minimize resource usage.
  - The bot then generates a refusal response based on this sanitized input.

### Config
- `JAILBREAK_ALARM_TEXT` in `config.py` defines the replacement text.
- `JAILBREAK_TRUNCATE_LEN` defines how much of the original message is kept for context (safely truncated).

---

## 3. Authorization

Access to the bot is strictly controlled via allowlists.

- **User Allowlist**: Only Telegram User IDs listed in `ALLOWED_USER_IDS` can interact with the bot in private chats.
- **Group Allowlist**: The bot will only process messages in groups listed in `ALLOWED_GROUP_IDS`.
- **Unauthorized Access**: Users or groups not on the list receive a "Not authorized" message, and their requests are not sent to the LLM.

