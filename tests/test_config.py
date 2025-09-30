"""Tests for configuration management."""

import pytest
import os
import tempfile
from unittest.mock import patch
from src.config import Config


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test config initialization with valid data."""
        with patch.dict(os.environ, {
            'TELEGRAM_TOKEN': 'test_token',
            'ADMIN_IDS': '123456789,987654321',
            'IVASMS_EMAIL': 'test@example.com',
            'IVASMS_PASSWORD': 'test_password'
        }):
            with patch('builtins.open', create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = """
site:
  base_url: "https://www.ivasms.com"
  login_path: "/login"
  sms_path: "/portal/sms/received"

playwright:
  timeout_ms: 30000
  retries: 3

telegram:
  notify_on_start: true
  notify_on_errors: true

selectors:
  login:
    email_input: 'input[name="email"]'
    password_input: 'input[name="password"]'
    login_button: 'button[type="submit"]'
"""
                config = Config()
                
                assert config.telegram_token == 'test_token'
                assert config.admin_ids == [123456789, 987654321]
                assert config.ivasms_email == 'test@example.com'
                assert config.ivasms_password == 'test_password'
    
    def test_missing_telegram_token(self):
        """Test error when TELEGRAM_TOKEN is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('builtins.open', create=True):
                with pytest.raises(ValueError, match="TELEGRAM_TOKEN environment variable is required"):
                    Config()
    
    def test_missing_admin_ids(self):
        """Test error when ADMIN_IDS is missing."""
        with patch.dict(os.environ, {
            'TELEGRAM_TOKEN': 'test_token',
            'IVASMS_EMAIL': 'test@example.com',
            'IVASMS_PASSWORD': 'test_password'
        }):
            with patch('builtins.open', create=True):
                with pytest.raises(ValueError, match="At least one ADMIN_ID is required"):
                    Config()
    
    def test_is_admin(self):
        """Test admin check functionality."""
        with patch.dict(os.environ, {
            'TELEGRAM_TOKEN': 'test_token',
            'ADMIN_IDS': '123456789,987654321',
            'IVASMS_EMAIL': 'test@example.com',
            'IVASMS_PASSWORD': 'test_password'
        }):
            with patch('builtins.open', create=True):
                config = Config()
                
                assert config.is_admin(123456789) is True
                assert config.is_admin(987654321) is True
                assert config.is_admin(999999999) is False
    
    def test_get_sanitized_config(self):
        """Test sanitized config output."""
        with patch.dict(os.environ, {
            'TELEGRAM_TOKEN': 'test_token',
            'ADMIN_IDS': '123456789',
            'IVASMS_EMAIL': 'test@example.com',
            'IVASMS_PASSWORD': 'test_password',
            'POLL_INTERVAL': '10',
            'HEADLESS': 'false'
        }):
            with patch('builtins.open', create=True):
                config = Config()
                sanitized = config.get_sanitized_config()
                
                assert 'test_token' not in sanitized
                assert 'test_password' not in sanitized
                assert 'ADMIN_IDS: [123456789]' in sanitized
                assert 'POLL_INTERVAL: 10s' in sanitized
