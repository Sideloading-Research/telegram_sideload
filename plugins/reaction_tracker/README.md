# Reaction Tracker Plugin

**Author:** Marco  
**License:** Public Domain (Unlicense)

## Overview

This plugin tracks message reactions (👍, ❤️, 🔥, etc.) on bot messages to learn from user feedback. It stores reactions in a SQLite database and provides analytics to identify which bot responses users prefer.

## Purpose

Enable the bot to learn from user reactions:
- Track which responses get positive reactions (👍, ❤️, 🔥)
- Identify poorly received responses (👎, 💔)
- Analyze engagement patterns over time
- Use reaction data to improve bot responses

## How It Works

This is a **passive plugin** that doesn't modify messages in the processing pipeline. Instead, it:

1. Registers handlers for `MessageReactionUpdated` and `MessageReactionCountUpdated` events
2. Stores reaction data in a SQLite database (`reactions.db`)
3. Provides analytics methods to query reaction statistics

## Features

- ✅ Track individual user reactions
- ✅ Track aggregate reaction counts
- ✅ Support for anonymous reactions (from channels)
- ✅ SQLite database with thread-safe operations
- ✅ Analytics for identifying top-rated messages
- ✅ Query interface for statistics

## Database Schema

### message_reactions
Stores individual reaction events:
- `chat_id`, `message_id`, `user_id`, `actor_chat_id`
- `reaction_emoji`, `action` (added/removed), `timestamp`

### reaction_counts
Stores aggregate statistics:
- `chat_id`, `message_id`, `total_count`
- `reaction_breakdown` (JSON: emoji → count)

## Integration

### 1. Enable in config_plugins.py

```python
PLUGIN_STATUS = {
    # ... other plugins ...
    "reaction_tracker": True,
}
```

### 2. Register Handlers in main.py

Add this code in `main.py` after loading plugins:

```python
# Register reaction tracker handlers
try:
    from plugins.reaction_tracker.main import get_handlers
    for handler in get_handlers():
        if handler:
            app.add_handler(handler)
    print("✅ Reaction tracker handlers registered")
except Exception as e:
    print(f"⚠️ Could not register reaction tracker: {e}")
```

### 3. Update allowed_updates

In `main.py`, when calling `run_polling()`, add reaction updates:

```python
app.run_polling(
    allowed_updates=[
        "message",
        "message_reaction",           # ADD THIS
        "message_reaction_count"      # AND THIS
    ]
)
```

## Usage

### Query Statistics

```python
from plugins.reaction_tracker.main import get_tracker
from plugins.reaction_tracker.analytics import ReactionAnalytics

tracker = get_tracker()
analytics = ReactionAnalytics(tracker.db)

# Get most reacted messages
top_messages = tracker.get_top_messages(chat_id=123, limit=10)

# Get engagement stats
stats = analytics.get_engagement_stats(chat_id=123, days_back=7)
print(f"Total reactions: {stats['total_reactions']}")

# Get most popular emojis
popular = analytics.get_most_popular_emoji(chat_id=123, days_back=7)
```

### Add Commands (Optional)

You can add commands to query statistics:

```python
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show reaction statistics."""
    from plugins.reaction_tracker.main import get_tracker
    from plugins.reaction_tracker.analytics import ReactionAnalytics
    
    tracker = get_tracker()
    analytics = ReactionAnalytics(tracker.db)
    
    chat_id = update.effective_chat.id
    stats = analytics.get_engagement_stats(chat_id=chat_id, days_back=7)
    
    await update.message.reply_text(
        f"📊 Reactions (7 days):\n"
        f"Total: {stats['total_reactions']}\n"
        f"Users: {stats['unique_users']}\n"
        f"Messages: {stats['unique_messages']}"
    )

# Register command
app.add_handler(CommandHandler("reactionstats", stats_command))
```

## Learning from Reactions

### Identify Best Responses

```python
# Get top-rated bot messages
top_messages = tracker.get_top_messages(chat_id=123, limit=10)

# Analyze sentiment
positive_emojis = {"👍", "❤️", "🔥", "💯", "⭐"}
negative_emojis = {"👎", "💔", "😢"}

for msg in top_messages:
    breakdown = msg['reaction_breakdown']
    positive = sum(count for emoji, count in breakdown.items() if emoji in positive_emojis)
    negative = sum(count for emoji, count in breakdown.items() if emoji in negative_emojis)
    
    if positive > negative:
        print(f"✅ Message {msg['message_id']}: Well received")
    else:
        print(f"❌ Message {msg['message_id']}: Poorly received")
```

## Requirements

- `python-telegram-bot>=20.8`
- Telegram Bot API 6.0+
- Bot must be admin in groups/channels to receive reaction updates

## Important Notes

1. **Bot Permissions**: Bot must be an administrator in groups/channels
2. **allowed_updates**: Must include `"message_reaction"` and `"message_reaction_count"`
3. **Passive Plugin**: Doesn't modify messages, only tracks reactions
4. **Database**: Stored in plugin directory as `reactions.db`

## Troubleshooting

### Reactions Not Being Tracked

1. Check bot is admin in the chat
2. Verify `allowed_updates` includes reaction types
3. Check `python-telegram-bot` version is >= 20.8
4. Ensure handlers are registered in `main.py`

### Database Issues

Database is stored in the plugin directory. To reset:
```bash
rm plugins/reaction_tracker/reactions.db
```

## Analytics Methods

Available in `analytics.py`:

- `get_most_popular_emoji()` - Most used reactions
- `get_most_active_users()` - Top reactors
- `get_engagement_stats()` - Overall metrics
- `get_trending_messages()` - High-velocity reactions
- `export_to_json()` - Export data

## Example: Sentiment Analysis

```python
def analyze_bot_sentiment(chat_id):
    """Analyze user sentiment towards bot responses."""
    analytics = ReactionAnalytics(tracker.db)
    
    popular = analytics.get_most_popular_emoji(chat_id=chat_id, days_back=7)
    
    positive = {"👍", "❤️", "🔥", "💯", "⭐"}
    negative = {"👎", "💔", "😢"}
    
    pos_count = sum(c for e, c in popular if e in positive)
    neg_count = sum(c for e, c in popular if e in negative)
    
    sentiment = (pos_count - neg_count) / (pos_count + neg_count)
    return sentiment  # -1 (negative) to +1 (positive)
```

## Future Enhancements

- Automatic response quality scoring
- Integration with AI training data
- Reaction-based response ranking
- User preference learning
- A/B testing support

---

**Note**: This plugin requires manual handler registration in `main.py`. See integration instructions above.
