"""Configuration module for the ivasms Telegram bot."""

import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Configuration class that reads from environment variables."""
    
    # Telegram configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_CHAT_IDS: List[int] = [
        int(chat_id.strip()) 
        for chat_id in os.getenv("TELEGRAM_ADMIN_CHAT_IDS", "").split(",") 
        if chat_id.strip().isdigit()
    ]
    
    # ivasms.com credentials
    IVASMS_EMAIL: str = os.getenv("IVASMS_EMAIL", "")
    IVASMS_PASSWORD: str = os.getenv("IVASMS_PASSWORD", "")
    
    # Bot behavior configuration
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"
    
    # Storage configuration
    DB_PATH: str = os.getenv("DB_PATH", "./data/state.db")
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./data/bot.log")
    
    # Browser configuration
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # milliseconds
    LOGIN_RETRY_ATTEMPTS: int = int(os.getenv("LOGIN_RETRY_ATTEMPTS", "3"))
    LOGIN_RETRY_DELAY: int = int(os.getenv("LOGIN_RETRY_DELAY", "5"))  # seconds
    
    # Health check configuration
    HEARTBEAT_INTERVAL_HOURS: int = int(os.getenv("HEARTBEAT_INTERVAL_HOURS", "24"))
    
    # Site URLs
    IVASMS_BASE_URL: str = "https://www.ivasms.com"
    IVASMS_LOGIN_URL: str = f"{IVASMS_BASE_URL}/portal/login"
    IVASMS_SMS_RECEIVED_URL: str = f"{IVASMS_BASE_URL}/portal/sms/received"
    
    # Permission acknowledgment
    OWNER_PERMISSION_ACKNOWLEDGED: bool = os.getenv("OWNER_PERMISSION_ACKNOWLEDGED", "false").lower() == "true"
    PERMISSION_REFERENCE: str = os.getenv("PERMISSION_REFERENCE", "Website owner permission granted for OTP scraping")
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not cls.TELEGRAM_BOT_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN is required")
            
        if not cls.TELEGRAM_ADMIN_CHAT_IDS:
            errors.append("TELEGRAM_ADMIN_CHAT_IDS is required")
            
        if not cls.IVASMS_EMAIL:
            errors.append("IVASMS_EMAIL is required")
            
        if not cls.IVASMS_PASSWORD:
            errors.append("IVASMS_PASSWORD is required")
            
        if cls.POLL_INTERVAL_SECONDS < 5:
            errors.append("POLL_INTERVAL_SECONDS must be at least 5 seconds")
            
        if not cls.OWNER_PERMISSION_ACKNOWLEDGED:
            errors.append("OWNER_PERMISSION_ACKNOWLEDGED must be set to 'true' to confirm website owner permission")
            
        return errors
    
    @classmethod
    def get_masked_email(cls) -> str:
        """Return masked email for display purposes."""
        if not cls.IVASMS_EMAIL:
            return "****"
        
        parts = cls.IVASMS_EMAIL.split("@")
        if len(parts) != 2:
            return "****"
            
        username, domain = parts
        if len(username) <= 2:
            masked_username = "****"
        else:
            masked_username = username[:2] + "****"
            
        return f"{masked_username}@{domain}"
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Return configuration summary for display."""
        return {
            "email": cls.get_masked_email(),
            "poll_interval": f"{cls.POLL_INTERVAL_SECONDS}s",
            "headless": cls.HEADLESS,
            "log_level": cls.LOG_LEVEL,
            "admin_chat_count": len(cls.TELEGRAM_ADMIN_CHAT_IDS),
            "permission_acknowledged": cls.OWNER_PERMISSION_ACKNOWLEDGED,
            "permission_reference": cls.PERMISSION_REFERENCE
        }
