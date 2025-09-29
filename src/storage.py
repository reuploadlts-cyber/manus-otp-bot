"""Storage module for persisting OTP data and bot state."""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import structlog

from .config import Config

logger = structlog.get_logger(__name__)


class OTPStorage:
    """SQLite-based storage for OTP data and bot state."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DB_PATH
        self.lock = threading.Lock()
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create OTPs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS otps (
                        id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        text TEXT NOT NULL,
                        service TEXT,
                        created_at TEXT NOT NULL,
                        sent_to_telegram BOOLEAN DEFAULT FALSE
                    )
                ''')
                
                # Create bot state table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_otps_timestamp ON otps(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_otps_created_at ON otps(created_at)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_otps_sent ON otps(sent_to_telegram)')
                
                conn.commit()
                logger.info("Database initialized successfully", db_path=self.db_path)
                
        except Exception as e:
            logger.error("Failed to initialize database", error=str(e), db_path=self.db_path)
            raise
    
    def store_otp(self, otp_data: Dict[str, str]) -> bool:
        """
        Store an OTP in the database.
        
        Args:
            otp_data: Dictionary containing OTP data
            
        Returns:
            True if stored successfully, False if already exists
        """
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Check if OTP already exists
                    cursor.execute('SELECT id FROM otps WHERE id = ?', (otp_data['id'],))
                    if cursor.fetchone():
                        logger.debug("OTP already exists", otp_id=otp_data['id'])
                        return False
                    
                    # Insert new OTP
                    cursor.execute('''
                        INSERT INTO otps (id, timestamp, sender, text, service, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        otp_data['id'],
                        otp_data['timestamp'],
                        otp_data['sender'],
                        otp_data['text'],
                        otp_data.get('service', ''),
                        datetime.now().isoformat()
                    ))
                    
                    conn.commit()
                    logger.info("OTP stored successfully", otp_id=otp_data['id'])
                    return True
                    
        except Exception as e:
            logger.error("Failed to store OTP", error=str(e), otp_data=otp_data)
            return False
    
    def get_unsent_otps(self) -> List[Dict[str, Any]]:
        """Get all OTPs that haven't been sent to Telegram."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM otps 
                        WHERE sent_to_telegram = FALSE 
                        ORDER BY created_at ASC
                    ''')
                    
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error("Failed to get unsent OTPs", error=str(e))
            return []
    
    def mark_otp_sent(self, otp_id: str) -> bool:
        """Mark an OTP as sent to Telegram."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        UPDATE otps 
                        SET sent_to_telegram = TRUE 
                        WHERE id = ?
                    ''', (otp_id,))
                    
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        logger.debug("OTP marked as sent", otp_id=otp_id)
                        return True
                    else:
                        logger.warning("OTP not found for marking as sent", otp_id=otp_id)
                        return False
                        
        except Exception as e:
            logger.error("Failed to mark OTP as sent", error=str(e), otp_id=otp_id)
            return False
    
    def get_recent_otps(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent OTPs."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM otps 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error("Failed to get recent OTPs", error=str(e))
            return []
    
    def get_last_otp(self) -> Optional[Dict[str, Any]]:
        """Get the most recent OTP."""
        recent_otps = self.get_recent_otps(limit=1)
        return recent_otps[0] if recent_otps else None
    
    def cleanup_old_otps(self, days: int = 30) -> int:
        """Remove OTPs older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        DELETE FROM otps 
                        WHERE created_at < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
                        logger.info("Cleaned up old OTPs", deleted_count=deleted_count, days=days)
                    
                    return deleted_count
                    
        except Exception as e:
            logger.error("Failed to cleanup old OTPs", error=str(e))
            return 0
    
    def get_otp_count(self) -> int:
        """Get total number of stored OTPs."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM otps')
                    return cursor.fetchone()[0]
                    
        except Exception as e:
            logger.error("Failed to get OTP count", error=str(e))
            return 0
    
    def set_state(self, key: str, value: Any) -> bool:
        """Set a bot state value."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Convert value to JSON string
                    value_json = json.dumps(value)
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO bot_state (key, value, updated_at)
                        VALUES (?, ?, ?)
                    ''', (key, value_json, datetime.now().isoformat()))
                    
                    conn.commit()
                    logger.debug("State set", key=key)
                    return True
                    
        except Exception as e:
            logger.error("Failed to set state", error=str(e), key=key)
            return False
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a bot state value."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT value FROM bot_state WHERE key = ?', (key,))
                    row = cursor.fetchone()
                    
                    if row:
                        return json.loads(row[0])
                    else:
                        return default
                        
        except Exception as e:
            logger.error("Failed to get state", error=str(e), key=key)
            return default
    
    def delete_state(self, key: str) -> bool:
        """Delete a bot state value."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('DELETE FROM bot_state WHERE key = ?', (key,))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        logger.debug("State deleted", key=key)
                        return True
                    else:
                        return False
                        
        except Exception as e:
            logger.error("Failed to delete state", error=str(e), key=key)
            return False
    
    def get_all_states(self) -> Dict[str, Any]:
        """Get all bot state values."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT key, value FROM bot_state')
                    rows = cursor.fetchall()
                    
                    states = {}
                    for row in rows:
                        try:
                            states[row['key']] = json.loads(row['value'])
                        except json.JSONDecodeError:
                            logger.warning("Failed to decode state value", key=row['key'])
                            states[row['key']] = row['value']
                    
                    return states
                    
        except Exception as e:
            logger.error("Failed to get all states", error=str(e))
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Total OTPs
                    cursor.execute('SELECT COUNT(*) FROM otps')
                    total_otps = cursor.fetchone()[0]
                    
                    # Unsent OTPs
                    cursor.execute('SELECT COUNT(*) FROM otps WHERE sent_to_telegram = FALSE')
                    unsent_otps = cursor.fetchone()[0]
                    
                    # OTPs from last 24 hours
                    yesterday = (datetime.now() - timedelta(days=1)).isoformat()
                    cursor.execute('SELECT COUNT(*) FROM otps WHERE created_at > ?', (yesterday,))
                    recent_otps = cursor.fetchone()[0]
                    
                    # Database size
                    db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                    
                    return {
                        'total_otps': total_otps,
                        'unsent_otps': unsent_otps,
                        'recent_otps_24h': recent_otps,
                        'db_size_bytes': db_size,
                        'db_size_mb': round(db_size / (1024 * 1024), 2)
                    }
                    
        except Exception as e:
            logger.error("Failed to get statistics", error=str(e))
            return {}
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of the database."""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.db_path}.backup_{timestamp}"
            
            # Ensure backup directory exists
            Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
            
            with self.lock:
                # Use SQLite backup API for safe backup
                source = sqlite3.connect(self.db_path)
                backup = sqlite3.connect(backup_path)
                
                source.backup(backup)
                
                source.close()
                backup.close()
            
            logger.info("Database backup created", backup_path=backup_path)
            return True
            
        except Exception as e:
            logger.error("Failed to backup database", error=str(e))
            return False
    
    def close(self) -> None:
        """Close database connections and cleanup."""
        # SQLite connections are closed automatically in context managers
        logger.info("Storage closed")


# Convenience functions for global storage instance
_storage_instance: Optional[OTPStorage] = None


def get_storage() -> OTPStorage:
    """Get global storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = OTPStorage()
    return _storage_instance


def close_storage() -> None:
    """Close global storage instance."""
    global _storage_instance
    if _storage_instance:
        _storage_instance.close()
        _storage_instance = None
