"""
Reaction Tracker Plugin

This plugin tracks message reactions (likes, emojis) on bot messages to learn
from user feedback. It stores reactions in a database and provides analytics
to identify which bot responses users prefer.

This is a passive plugin that doesn't modify messages - it only tracks reactions
via handlers that need to be registered separately in the main bot.

Author: Marco
License: Public Domain (Unlicense)
"""

import os
import sys
import logging
from typing import Optional, Dict, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram import Update
    from telegram.ext import ContextTypes, MessageReactionHandler
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not installed. Reaction tracking will be disabled.")

from database import ReactionDatabase
from config import Config


logger = logging.getLogger(__name__)


class ReactionTracker:
    """
    Tracks message reactions for learning from user feedback.
    
    This plugin is passive - it doesn't modify messages in the plugin pipeline.
    Instead, it provides handlers that must be registered in main.py.
    """
    
    def __init__(self, database_path: Optional[str] = None):
        """Initialize reaction tracker."""
        if database_path is None:
            # Store in plugin directory
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            database_path = os.path.join(plugin_dir, "reactions.db")
        
        self.config = Config(
            database_path=database_path,
            track_anonymous=True,
            store_message_text=False,  # Bot handles message storage separately
            verbose_logging=False
        )
        
        self.db = ReactionDatabase(database_path)
        logger.info(f"ReactionTracker initialized with database: {database_path}")
    
    async def handle_reaction_update(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle MessageReactionUpdated events."""
        if not TELEGRAM_AVAILABLE:
            return
        
        reaction = update.message_reaction
        if reaction is None:
            return
        
        chat_id = reaction.chat.id
        message_id = reaction.message_id
        timestamp = int(reaction.date.timestamp() if hasattr(reaction.date, 'timestamp') else reaction.date)
        
        user_id = reaction.user.id if reaction.user else None
        actor_chat_id = reaction.actor_chat.id if reaction.actor_chat else None
        
        # Process old and new reactions
        old_emojis = set()
        new_emojis = set()
        
        for reaction_type in reaction.old_reaction:
            if hasattr(reaction_type, 'emoji'):
                old_emojis.add(reaction_type.emoji)
        
        for reaction_type in reaction.new_reaction:
            if hasattr(reaction_type, 'emoji'):
                new_emojis.add(reaction_type.emoji)
        
        # Determine what was added and removed
        added = new_emojis - old_emojis
        removed = old_emojis - new_emojis
        
        # Store added reactions
        for emoji in added:
            self.db.store_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction_emoji=emoji,
                action='added',
                timestamp=timestamp,
                user_id=user_id,
                actor_chat_id=actor_chat_id
            )
            logger.info(f"Reaction added: {emoji} on message {message_id}")
        
        # Store removed reactions
        for emoji in removed:
            self.db.store_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction_emoji=emoji,
                action='removed',
                timestamp=timestamp,
                user_id=user_id,
                actor_chat_id=actor_chat_id
            )
    
    async def handle_reaction_count_update(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle MessageReactionCountUpdated events."""
        if not TELEGRAM_AVAILABLE:
            return
        
        reaction_count = update.message_reaction_count
        if reaction_count is None:
            return
        
        chat_id = reaction_count.chat.id
        message_id = reaction_count.message_id
        timestamp = int(reaction_count.date.timestamp() if hasattr(reaction_count.date, 'timestamp') else reaction_count.date)
        
        # Build reaction breakdown
        reaction_breakdown = {}
        total_count = 0
        
        for reaction in reaction_count.reactions:
            if hasattr(reaction.type, 'emoji'):
                emoji = reaction.type.emoji
                count = reaction.total_count
                reaction_breakdown[emoji] = count
                total_count += count
        
        # Update database
        self.db.update_reaction_count(
            chat_id=chat_id,
            message_id=message_id,
            total_count=total_count,
            reaction_breakdown=reaction_breakdown,
            timestamp=timestamp
        )
    
    def get_reaction_handler(self):
        """Get MessageReactionHandler for individual reactions."""
        if not TELEGRAM_AVAILABLE:
            return None
        return MessageReactionHandler(self.handle_reaction_update)
    
    def get_reaction_count_handler(self):
        """Get MessageReactionHandler for reaction counts."""
        if not TELEGRAM_AVAILABLE:
            return None
        return MessageReactionHandler(
            self.handle_reaction_count_update,
            message_reaction_count=True
        )
    
    def get_message_stats(self, chat_id: int, message_id: int) -> Optional[Dict]:
        """Get reaction statistics for a specific message."""
        return self.db.get_message_stats(chat_id, message_id)
    
    def get_top_messages(
        self,
        chat_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get most reacted messages."""
        return self.db.get_top_reacted_messages(chat_id, limit, min_reactions=1)
    
    def close(self):
        """Close database connection."""
        self.db.close()


# Global tracker instance
_tracker_instance = None


def get_tracker() -> ReactionTracker:
    """Get or create global tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ReactionTracker()
    return _tracker_instance


# Plugin interface functions (required by plugin system)
def is_plugin_applicable(messages, provider):
    """
    This plugin doesn't modify messages in the pipeline.
    It only tracks reactions via handlers.
    
    Returns False so it doesn't interfere with message processing.
    """
    return False


def process_messages(messages, provider):
    """
    This plugin doesn't modify messages.
    Reaction tracking happens via handlers registered in main.py.
    """
    return messages


# Helper function to get handlers for registration in main.py
def get_handlers():
    """
    Get reaction handlers for registration in main bot.
    
    Usage in main.py:
        from plugins.reaction_tracker.main import get_handlers
        for handler in get_handlers():
            if handler:
                app.add_handler(handler)
    """
    if not TELEGRAM_AVAILABLE:
        return []
    
    tracker = get_tracker()
    return [
        tracker.get_reaction_handler(),
        tracker.get_reaction_count_handler()
    ]
