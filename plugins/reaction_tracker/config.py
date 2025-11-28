"""
Configuration module for Telegram Reaction Tracker

Manages plugin settings and configuration options.
"""

from dataclasses import dataclass
from typing import Optional, List
import os


@dataclass
class Config:
    """
    Configuration settings for the Reaction Tracker plugin.
    
    Attributes:
        database_path: Path to SQLite database file
        track_anonymous: Whether to track anonymous reactions
        store_message_text: Whether to store associated message text
        allowed_reactions: List of reaction emojis to track (None = all)
        max_history_days: How long to keep reaction history (0 = forever)
        enable_analytics: Whether to enable analytics features
        verbose_logging: Enable detailed logging
    """
    
    database_path: str = "reactions.db"
    track_anonymous: bool = True
    store_message_text: bool = True
    allowed_reactions: Optional[List[str]] = None
    max_history_days: int = 0  # 0 = keep forever
    enable_analytics: bool = True
    verbose_logging: bool = False
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.
        
        Environment variables:
            REACTION_DB_PATH: Database path
            REACTION_TRACK_ANONYMOUS: Track anonymous (true/false)
            REACTION_STORE_TEXT: Store message text (true/false)
            REACTION_MAX_HISTORY_DAYS: Max history days
            REACTION_VERBOSE: Verbose logging (true/false)
        
        Returns:
            Config instance
        """
        return cls(
            database_path=os.getenv("REACTION_DB_PATH", "reactions.db"),
            track_anonymous=os.getenv("REACTION_TRACK_ANONYMOUS", "true").lower() == "true",
            store_message_text=os.getenv("REACTION_STORE_TEXT", "true").lower() == "true",
            max_history_days=int(os.getenv("REACTION_MAX_HISTORY_DAYS", "0")),
            verbose_logging=os.getenv("REACTION_VERBOSE", "false").lower() == "true"
        )
    
    def validate(self) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.database_path:
            raise ValueError("database_path cannot be empty")
        
        if self.max_history_days < 0:
            raise ValueError("max_history_days must be >= 0")
        
        if self.allowed_reactions is not None:
            if not isinstance(self.allowed_reactions, list):
                raise ValueError("allowed_reactions must be a list or None")
            if not all(isinstance(r, str) for r in self.allowed_reactions):
                raise ValueError("All allowed_reactions must be strings")
