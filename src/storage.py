"""Storage management for persisting bot state."""

import json
import sqlite3
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import aiofiles
from .logger_setup import get_logger

logger = get_logger(__name__)


@dataclass
class SMSMessage:
    """SMS message data structure."""
    id: str
    sender: str
    message: str
    timestamp: str
    received_at: str
    forwarded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SMSMessage':
        """Create from dictionary."""
        return cls(**data)


class Storage:
    """Storage manager for bot data."""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sms_messages (
                        id TEXT PRIMARY KEY,
                        sender TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        received_at TEXT NOT NULL,
                        forwarded BOOLEAN DEFAULT 0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def save_sms(self, sms: SMSMessage) -> bool:
        """Save SMS message to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO sms_messages 
                    (id, sender, message, timestamp, received_at, forwarded)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    sms.id, sms.sender, sms.message, 
                    sms.timestamp, sms.received_at, sms.forwarded
                ))
                conn.commit()
                logger.debug(f"Saved SMS: {sms.id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save SMS {sms.id}: {e}")
            return False
    
    async def get_recent_sms(self, limit: int = 10) -> List[SMSMessage]:
        """Get recent SMS messages."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sms_messages 
                    ORDER BY received_at DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [SMSMessage.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get recent SMS: {e}")
            return []
    
    async def get_last_sms(self) -> Optional[SMSMessage]:
        """Get the most recent SMS message."""
        messages = await self.get_recent_sms(1)
        return messages[0] if messages else None
    
    async def get_unforwarded_sms(self) -> List[SMSMessage]:
        """Get SMS messages that haven't been forwarded yet."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sms_messages 
                    WHERE forwarded = 0 
                    ORDER BY received_at ASC
                """)
                
                rows = cursor.fetchall()
                return [SMSMessage.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get unforwarded SMS: {e}")
            return []
    
    async def mark_forwarded(self, sms_id: str) -> bool:
        """Mark SMS as forwarded."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE sms_messages 
                    SET forwarded = 1 
                    WHERE id = ?
                """, (sms_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to mark SMS {sms_id} as forwarded: {e}")
            return False
    
    async def get_state(self, key: str) -> Optional[str]:
        """Get bot state value."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT value FROM bot_state WHERE key = ?
                """, (key,))
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get state {key}: {e}")
            return None
    
    async def set_state(self, key: str, value: str) -> bool:
        """Set bot state value."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO bot_state (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to set state {key}: {e}")
            return False
    
    async def get_last_seen_id(self) -> Optional[str]:
        """Get last seen SMS ID."""
        return await self.get_state("last_seen_id")
    
    async def set_last_seen_id(self, sms_id: str) -> bool:
        """Set last seen SMS ID."""
        return await self.set_state("last_seen_id", sms_id)
    
    async def export_history_csv(self, start_date: str, end_date: str) -> str:
        """Export SMS history as CSV."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sms_messages 
                    WHERE date(received_at) BETWEEN ? AND ?
                    ORDER BY received_at DESC
                """, (start_date, end_date))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return ""
                
                # Create CSV content
                csv_lines = ["id,sender,message,timestamp,received_at,forwarded"]
                for row in rows:
                    csv_lines.append(f'"{row["id"]}","{row["sender"]}","{row["message"]}","{row["timestamp"]}","{row["received_at"]}","{row["forwarded"]}"')
                
                return "\n".join(csv_lines)
        except Exception as e:
            logger.error(f"Failed to export history CSV: {e}")
            return ""
