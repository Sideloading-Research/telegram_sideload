"""
Analytics utilities for Telegram Reaction Tracker

Provides analytics and reporting features for reaction data.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
import json

from .database import ReactionDatabase


logger = logging.getLogger(__name__)


class ReactionAnalytics:
    """
    Analytics engine for reaction data.
    
    Provides methods to analyze and report on reaction patterns.
    """
    
    def __init__(self, database: ReactionDatabase):
        """
        Initialize analytics engine.
        
        Args:
            database: ReactionDatabase instance
        """
        self.db = database
    
    def get_most_popular_emoji(
        self,
        chat_id: Optional[int] = None,
        days_back: Optional[int] = None
    ) -> List[Tuple[str, int]]:
        """
        Get most popular reaction emojis.
        
        Args:
            chat_id: Filter by chat ID (None = all chats)
            days_back: Only include reactions from last N days
        
        Returns:
            List of (emoji, count) tuples ordered by popularity
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT reaction_emoji, COUNT(*) as count
                FROM message_reactions
                WHERE action = 'added'
            """
            params = []
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            if days_back is not None:
                cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp())
                query += " AND timestamp >= ?"
                params.append(cutoff)
            
            query += " GROUP BY reaction_emoji ORDER BY count DESC"
            
            cursor.execute(query, params)
            return [(row[0], row[1]) for row in cursor.fetchall()]
    
    def get_most_active_users(
        self,
        chat_id: Optional[int] = None,
        days_back: Optional[int] = None,
        limit: int = 10
    ) -> List[Tuple[int, int]]:
        """
        Get most active users (by reaction count).
        
        Args:
            chat_id: Filter by chat ID (None = all chats)
            days_back: Only include reactions from last N days
            limit: Maximum number of results
        
        Returns:
            List of (user_id, reaction_count) tuples
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT user_id, COUNT(*) as count
                FROM message_reactions
                WHERE user_id IS NOT NULL AND action = 'added'
            """
            params = []
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            if days_back is not None:
                cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp())
                query += " AND timestamp >= ?"
                params.append(cutoff)
            
            query += " GROUP BY user_id ORDER BY count DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [(row[0], row[1]) for row in cursor.fetchall()]
    
    def get_reaction_timeline(
        self,
        chat_id: int,
        message_id: int
    ) -> List[Dict]:
        """
        Get timeline of reactions for a specific message.
        
        Args:
            chat_id: Chat ID
            message_id: Message ID
        
        Returns:
            List of reaction events ordered by time
        """
        reactions = self.db.get_message_reactions(chat_id, message_id)
        
        # Sort by timestamp
        reactions.sort(key=lambda x: x['timestamp'])
        
        return reactions
    
    def get_user_favorite_emoji(self, user_id: int) -> Optional[str]:
        """
        Get user's most frequently used reaction emoji.
        
        Args:
            user_id: User ID
        
        Returns:
            Most used emoji or None
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT reaction_emoji, COUNT(*) as count
                FROM message_reactions
                WHERE user_id = ? AND action = 'added'
                GROUP BY reaction_emoji
                ORDER BY count DESC
                LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            return row[0] if row else None
    
    def get_engagement_stats(
        self,
        chat_id: Optional[int] = None,
        days_back: int = 7
    ) -> Dict:
        """
        Get overall engagement statistics.
        
        Args:
            chat_id: Filter by chat ID (None = all chats)
            days_back: Number of days to analyze
        
        Returns:
            Dictionary with engagement metrics
        """
        cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp())
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total reactions
            query = "SELECT COUNT(*) FROM message_reactions WHERE action = 'added' AND timestamp >= ?"
            params = [cutoff]
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            cursor.execute(query, params)
            total_reactions = cursor.fetchone()[0]
            
            # Unique users
            query = "SELECT COUNT(DISTINCT user_id) FROM message_reactions WHERE action = 'added' AND timestamp >= ? AND user_id IS NOT NULL"
            params = [cutoff]
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            cursor.execute(query, params)
            unique_users = cursor.fetchone()[0]
            
            # Unique messages
            query = "SELECT COUNT(DISTINCT message_id) FROM message_reactions WHERE action = 'added' AND timestamp >= ?"
            params = [cutoff]
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            cursor.execute(query, params)
            unique_messages = cursor.fetchone()[0]
            
            return {
                'total_reactions': total_reactions,
                'unique_users': unique_users,
                'unique_messages': unique_messages,
                'avg_reactions_per_message': total_reactions / unique_messages if unique_messages > 0 else 0,
                'avg_reactions_per_user': total_reactions / unique_users if unique_users > 0 else 0,
                'period_days': days_back
            }
    
    def export_to_json(
        self,
        chat_id: Optional[int] = None,
        days_back: Optional[int] = None
    ) -> str:
        """
        Export reaction data to JSON format.
        
        Args:
            chat_id: Filter by chat ID (None = all chats)
            days_back: Only include reactions from last N days
        
        Returns:
            JSON string with reaction data
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM message_reactions WHERE 1=1"
            params = []
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            if days_back is not None:
                cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp())
                query += " AND timestamp >= ?"
                params.append(cutoff)
            
            query += " ORDER BY timestamp DESC"
            
            cursor.execute(query, params)
            
            reactions = [dict(row) for row in cursor.fetchall()]
            
            return json.dumps({
                'export_date': datetime.now().isoformat(),
                'total_records': len(reactions),
                'reactions': reactions
            }, indent=2)
    
    def get_trending_messages(
        self,
        chat_id: Optional[int] = None,
        hours_back: int = 24,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get trending messages (high reaction velocity).
        
        Args:
            chat_id: Filter by chat ID (None = all chats)
            hours_back: Time window to analyze
            limit: Maximum number of results
        
        Returns:
            List of trending message stats
        """
        cutoff = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
        
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT chat_id, message_id, COUNT(*) as reaction_count
                FROM message_reactions
                WHERE action = 'added' AND timestamp >= ?
            """
            params = [cutoff]
            
            if chat_id is not None:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            query += " GROUP BY chat_id, message_id ORDER BY reaction_count DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            
            trending = []
            for row in cursor.fetchall():
                trending.append({
                    'chat_id': row[0],
                    'message_id': row[1],
                    'reaction_count': row[2],
                    'reactions_per_hour': row[2] / hours_back
                })
            
            return trending
