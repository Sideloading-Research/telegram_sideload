"""
Database layer for Telegram Reaction Tracker

Handles all database operations for storing and querying reaction data.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import threading


logger = logging.getLogger(__name__)


class ReactionDatabase:
    """
    Database abstraction layer for reaction tracking.
    
    Manages SQLite database operations with thread-safe access.
    """
    
    def __init__(self, database_path: str):
        """
        Initialize database connection.
        
        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self._local = threading.local()
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """
        Get thread-local database connection.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.database_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        
        try:
            yield self._local.connection
        except Exception as e:
            self._local.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        else:
            self._local.connection.commit()
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create message_reactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS message_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER,
                    actor_chat_id INTEGER,
                    reaction_emoji TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    message_text TEXT
                )
            """)
            
            # Create reaction_counts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reaction_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    total_count INTEGER NOT NULL,
                    reaction_breakdown TEXT,
                    last_updated INTEGER NOT NULL,
                    UNIQUE(chat_id, message_id)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_lookup 
                ON message_reactions(chat_id, message_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_reactions 
                ON message_reactions(user_id, timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON message_reactions(timestamp)
            """)
            
            logger.info(f"Database initialized at {self.database_path}")
    
    def store_reaction(
        self,
        chat_id: int,
        message_id: int,
        reaction_emoji: str,
        action: str,
        timestamp: int,
        user_id: Optional[int] = None,
        actor_chat_id: Optional[int] = None,
        message_text: Optional[str] = None
    ) -> int:
        """
        Store a single reaction event.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            reaction_emoji: Emoji used for reaction
            action: 'added' or 'removed'
            timestamp: Unix timestamp
            user_id: User ID (None for anonymous)
            actor_chat_id: Actor chat ID (for anonymous)
            message_text: Associated message text
        
        Returns:
            int: Row ID of inserted record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO message_reactions 
                (chat_id, message_id, user_id, actor_chat_id, reaction_emoji, action, timestamp, message_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (chat_id, message_id, user_id, actor_chat_id, reaction_emoji, action, timestamp, message_text))
            
            row_id = cursor.lastrowid
            logger.debug(f"Stored reaction: {action} {reaction_emoji} on message {message_id}")
            return row_id
    
    def update_reaction_count(
        self,
        chat_id: int,
        message_id: int,
        total_count: int,
        reaction_breakdown: Dict[str, int],
        timestamp: int
    ) -> None:
        """
        Update aggregate reaction counts for a message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
            total_count: Total number of reactions
            reaction_breakdown: Dictionary mapping emoji to count
            timestamp: Unix timestamp
        """
        breakdown_json = json.dumps(reaction_breakdown)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reaction_counts (chat_id, message_id, total_count, reaction_breakdown, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, message_id) DO UPDATE SET
                    total_count = excluded.total_count,
                    reaction_breakdown = excluded.reaction_breakdown,
                    last_updated = excluded.last_updated
            """, (chat_id, message_id, total_count, breakdown_json, timestamp))
            
            logger.debug(f"Updated reaction count for message {message_id}: {total_count} total")
    
    def get_message_reactions(self, chat_id: int, message_id: int) -> List[Dict]:
        """
        Get all reactions for a specific message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
        
        Returns:
            List of reaction records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM message_reactions
                WHERE chat_id = ? AND message_id = ?
                ORDER BY timestamp DESC
            """, (chat_id, message_id))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_message_stats(self, chat_id: int, message_id: int) -> Optional[Dict]:
        """
        Get reaction statistics for a message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
        
        Returns:
            Dictionary with stats or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM reaction_counts
                WHERE chat_id = ? AND message_id = ?
            """, (chat_id, message_id))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['reaction_breakdown'] = json.loads(result['reaction_breakdown'])
                return result
            return None
    
    def get_top_reacted_messages(
        self,
        chat_id: Optional[int] = None,
        limit: int = 10,
        min_reactions: int = 1
    ) -> List[Dict]:
        """
        Get most reacted messages.
        
        Args:
            chat_id: Filter by chat ID (None = all chats)
            limit: Maximum number of results
            min_reactions: Minimum reaction count
        
        Returns:
            List of message stats ordered by reaction count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if chat_id is not None:
                cursor.execute("""
                    SELECT * FROM reaction_counts
                    WHERE chat_id = ? AND total_count >= ?
                    ORDER BY total_count DESC
                    LIMIT ?
                """, (chat_id, min_reactions, limit))
            else:
                cursor.execute("""
                    SELECT * FROM reaction_counts
                    WHERE total_count >= ?
                    ORDER BY total_count DESC
                    LIMIT ?
                """, (min_reactions, limit))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['reaction_breakdown'] = json.loads(result['reaction_breakdown'])
                results.append(result)
            
            return results
    
    def get_user_reaction_history(
        self,
        user_id: int,
        limit: int = 50,
        days_back: Optional[int] = None
    ) -> List[Dict]:
        """
        Get reaction history for a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            days_back: Only include reactions from last N days (None = all)
        
        Returns:
            List of user's reactions
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if days_back is not None:
                cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp())
                cursor.execute("""
                    SELECT * FROM message_reactions
                    WHERE user_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, cutoff, limit))
            else:
                cursor.execute("""
                    SELECT * FROM message_reactions
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_reactions(self, days_to_keep: int) -> int:
        """
        Remove reactions older than specified days.
        
        Args:
            days_to_keep: Number of days to keep
        
        Returns:
            Number of deleted records
        """
        cutoff = int((datetime.now() - timedelta(days=days_to_keep)).timestamp())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM message_reactions
                WHERE timestamp < ?
            """, (cutoff,))
            
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old reactions")
            return deleted
    
    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            logger.info("Database connection closed")
