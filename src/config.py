"""Configuration management for the OTP forwarder bot."""

import os
import yaml
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration manager for the bot."""
    
    def __init__(self):
        self._load_config()
        self._load_env_vars()
    
    def _load_config(self):
        """Load configuration from config.yaml."""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError("config.yaml not found. Please create it from config.yaml.example")
    
    def _load_env_vars(self):
        """Load sensitive configuration from environment variables."""
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        if not self.telegram_token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        
        admin_ids_str = os.getenv('ADMIN_IDS', '')
        self.admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
        if not self.admin_ids:
            raise ValueError("At least one ADMIN_ID is required")
        
        self.ivasms_email = os.getenv('IVASMS_EMAIL')
        self.ivasms_password = os.getenv('IVASMS_PASSWORD')
        if not self.ivasms_email or not self.ivasms_password:
            raise ValueError("IVASMS_EMAIL and IVASMS_PASSWORD are required")
        
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '8'))
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///bot_data.db')
    
    @property
    def site_config(self) -> Dict[str, str]:
        """Get site configuration."""
        return self.config['site']
    
    @property
    def playwright_config(self) -> Dict[str, Any]:
        """Get Playwright configuration."""
        config = self.config['playwright'].copy()
        config['headless'] = self.headless
        return config
    
    @property
    def telegram_config(self) -> Dict[str, Any]:
        """Get Telegram configuration."""
        return self.config['telegram']
    
    @property
    def selectors(self) -> Dict[str, Any]:
        """Get CSS selectors configuration."""
        return self.config['selectors']
    
    @property
    def storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return self.config['storage']
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.admin_ids
    
    def get_sanitized_config(self) -> str:
        """Get configuration without sensitive data for display."""
        return f"""ADMIN_IDS: {self.admin_ids}
POLL_INTERVAL: {self.poll_interval}s
HEADLESS: {self.headless}
LOG_LEVEL: {self.log_level}
SITE_URL: {self.site_config['base_url']}"""


# Global config instance
config = Config()
