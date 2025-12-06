# Reaction Tracker Integration Instructions

## For telegram-llm-bot/main.py

Add this code after the plugin loading section (around line 200-300):

```python
# ============================================================================
# REACTION TRACKER INTEGRATION
# ============================================================================
# Register reaction tracker handlers (must be done separately from plugin pipeline)
try:
    from plugins.reaction_tracker.main import get_handlers
    reaction_handlers = get_handlers()
    for handler in reaction_handlers:
        if handler:
            app.add_handler(handler)
    print("✅ Reaction tracker handlers registered")
except Exception as e:
    print(f"⚠️ Could not register reaction tracker: {e}")
```

## Update allowed_updates

Find the `run_polling()` call at the end of main.py and update it:

```python
# OLD:
app.run_polling()

# NEW:
app.run_polling(
    allowed_updates=[
        "message",
        "edited_message",
        "channel_post",
        "edited_channel_post",
        "message_reaction",           # ADD THIS
        "message_reaction_count",     # AND THIS
        "inline_query",
        "chosen_inline_result",
        "callback_query",
    ]
)
```

## Optional: Add Statistics Commands

Add these command handlers:

```python
async def reaction_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show reaction statistics."""
    from plugins.reaction_tracker.main import get_tracker
    from plugins.reaction_tracker.analytics import ReactionAnalytics
    
    tracker = get_tracker()
    analytics = ReactionAnalytics(tracker.db)
    
    chat_id = update.effective_chat.id
    stats = analytics.get_engagement_stats(chat_id=chat_id, days_back=7)
    
    await update.message.reply_text(
        f"📊 **Reaction Statistics (Last 7 Days)**\n\n"
        f"Total Reactions: {stats['total_reactions']}\n"
        f"Unique Users: {stats['unique_users']}\n"
        f"Unique Messages: {stats['unique_messages']}\n"
        f"Avg Reactions/Message: {stats['avg_reactions_per_message']:.2f}\n"
        f"Avg Reactions/User: {stats['avg_reactions_per_user']:.2f}"
    )

async def top_reactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show most reacted messages."""
    from plugins.reaction_tracker.main import get_tracker
    
    tracker = get_tracker()
    chat_id = update.effective_chat.id
    top_messages = tracker.get_top_messages(chat_id=chat_id, limit=5)
    
    if not top_messages:
        await update.message.reply_text("No reactions yet!")
        return
    
    response = "🏆 **Top Reacted Messages**\n\n"
    for i, msg in enumerate(top_messages, 1):
        breakdown = msg['reaction_breakdown']
        emoji_str = " ".join([f"{emoji}×{count}" for emoji, count in breakdown.items()])
        response += f"{i}. Message #{msg['message_id']}\n"
        response += f"   Total: {msg['total_count']} | {emoji_str}\n\n"
    
    await update.message.reply_text(response)

# Register commands
app.add_handler(CommandHandler("reactionstats", reaction_stats_command))
app.add_handler(CommandHandler("topreactions", top_reactions_command))
```

## Verification

After integration, test with:

1. Send a message from the bot
2. React to it with an emoji
3. Run `/reactionstats` to see if it's tracked
4. Check `plugins/reaction_tracker/reactions.db` exists

## Troubleshooting

If reactions aren't being tracked:

1. Check bot is admin in the chat
2. Verify `allowed_updates` includes reaction types
3. Check console for "✅ Reaction tracker handlers registered"
4. Ensure `python-telegram-bot>=20.8` is installed
