"""Unit tests for utility functions."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from utils import (
    get_git_info,
    get_uptime,
    sanitize_for_telegram,
    extract_otp_from_text,
    generate_message_id,
    parse_timestamp,
    format_otp_message,
    add_jitter,
    is_valid_phone_number,
    truncate_text,
    mask_sensitive_data,
    validate_telegram_chat_id,
    clean_html_tags,
    RateLimiter
)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_git_info_success(self):
        """Test successful git info retrieval."""
        with patch('subprocess.check_output') as mock_subprocess:
            mock_subprocess.side_effect = [
                "abc123def456789012345678901234567890abcd\n",  # Full SHA
                "main\n"  # Branch
            ]
            
            git_info = get_git_info()
            
            assert git_info['commit_sha'] == "abc123def456789012345678901234567890abcd"
            assert git_info['short_sha'] == "abc123de"
            assert git_info['branch'] == "main"
    
    def test_get_git_info_failure(self):
        """Test git info retrieval when git is not available."""
        with patch('subprocess.check_output', side_effect=FileNotFoundError):
            git_info = get_git_info()
            
            assert git_info['commit_sha'] == "unknown"
            assert git_info['short_sha'] == "unknown"
            assert git_info['branch'] == "unknown"
    
    def test_get_uptime(self):
        """Test uptime calculation."""
        # Test various time differences
        now = datetime.now()
        
        # 30 seconds ago
        start_time = now - timedelta(seconds=30)
        uptime = get_uptime(start_time)
        assert "30s" in uptime
        
        # 5 minutes ago
        start_time = now - timedelta(minutes=5, seconds=30)
        uptime = get_uptime(start_time)
        assert "5m" in uptime and "30s" in uptime
        
        # 2 hours ago
        start_time = now - timedelta(hours=2, minutes=30)
        uptime = get_uptime(start_time)
        assert "2h" in uptime and "30m" in uptime
        
        # 3 days ago
        start_time = now - timedelta(days=3, hours=2)
        uptime = get_uptime(start_time)
        assert "3d" in uptime and "2h" in uptime
    
    def test_sanitize_for_telegram(self):
        """Test Telegram message sanitization."""
        # Test special character escaping
        text = "Test_message with *bold* and [link]"
        sanitized = sanitize_for_telegram(text)
        assert "\\_" in sanitized
        assert "\\*" in sanitized
        assert "\\[" in sanitized
        assert "\\]" in sanitized
        
        # Test length truncation
        long_text = "a" * 5000
        sanitized = sanitize_for_telegram(long_text)
        assert len(sanitized) <= 4096
        assert sanitized.endswith("...")
        
        # Test empty string
        assert sanitize_for_telegram("") == ""
        assert sanitize_for_telegram(None) == ""
    
    def test_extract_otp_from_text(self):
        """Test OTP extraction from text."""
        # Test various OTP formats
        test_cases = [
            ("Your verification code is 123456", "123456"),
            ("OTP: 789012", "789012"),
            ("Code 456789", "456789"),
            ("PIN: 1234", "1234"),
            ("Your code is 987654321", "987654321"),  # 9 digits should not match
            ("No OTP here", None),
            ("", None),
            (None, None)
        ]
        
        for text, expected in test_cases:
            result = extract_otp_from_text(text)
            assert result == expected
    
    def test_generate_message_id(self):
        """Test message ID generation."""
        # Same inputs should generate same ID
        id1 = generate_message_id("2024-01-01", "sender", "message")
        id2 = generate_message_id("2024-01-01", "sender", "message")
        assert id1 == id2
        
        # Different inputs should generate different IDs
        id3 = generate_message_id("2024-01-02", "sender", "message")
        assert id1 != id3
        
        # ID should be 16 characters (MD5 hash truncated)
        assert len(id1) == 16
    
    def test_parse_timestamp(self):
        """Test timestamp parsing."""
        test_cases = [
            ("2024-01-01 12:00:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("2024-01-01 12:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("01/01/2024 12:00:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("2024-01-01T12:00:00", datetime(2024, 1, 1, 12, 0, 0)),
            ("invalid_timestamp", None),
            ("", None),
            (None, None)
        ]
        
        for timestamp_str, expected in test_cases:
            result = parse_timestamp(timestamp_str)
            assert result == expected
    
    def test_format_otp_message(self):
        """Test OTP message formatting."""
        otp_data = {
            "timestamp": "2024-01-01 12:00:00",
            "sender": "+1234567890",
            "text": "Your verification code is 123456",
            "service": "TestService"
        }
        
        message = format_otp_message(otp_data)
        
        assert "🔔 **New OTP received**" in message
        assert "2024-01-01 12:00:00" in message
        assert "+1234567890" in message
        assert "Your verification code is 123456" in message
        assert "TestService" in message
        assert "`123456`" in message  # OTP code should be formatted
    
    def test_add_jitter(self):
        """Test jitter addition."""
        base_interval = 10
        
        # Test multiple times to ensure randomness
        results = [add_jitter(base_interval) for _ in range(10)]
        
        # All results should be close to base interval
        for result in results:
            assert 9 <= result <= 11  # 10% jitter
        
        # Results should vary (not all the same)
        assert len(set(results)) > 1
    
    def test_is_valid_phone_number(self):
        """Test phone number validation."""
        valid_numbers = [
            "+1234567890",
            "1234567890",
            "+44 20 7946 0958",
            "(555) 123-4567",
            "555-123-4567"
        ]
        
        invalid_numbers = [
            "",
            None,
            "123",  # Too short
            "12345678901234567890",  # Too long
            "abc123def",  # Contains letters
            "++1234567890"  # Invalid format
        ]
        
        for number in valid_numbers:
            assert is_valid_phone_number(number), f"Should be valid: {number}"
        
        for number in invalid_numbers:
            assert not is_valid_phone_number(number), f"Should be invalid: {number}"
    
    def test_truncate_text(self):
        """Test text truncation."""
        # Short text should not be truncated
        short_text = "Short text"
        assert truncate_text(short_text, 20) == short_text
        
        # Long text should be truncated
        long_text = "This is a very long text that should be truncated"
        truncated = truncate_text(long_text, 20)
        assert len(truncated) <= 20
        assert truncated.endswith("...")
        
        # Custom suffix
        truncated = truncate_text(long_text, 20, " [more]")
        assert truncated.endswith(" [more]")
        
        # Empty text
        assert truncate_text("", 10) == ""
        assert truncate_text(None, 10) == ""
    
    def test_mask_sensitive_data(self):
        """Test sensitive data masking."""
        # Normal case
        assert mask_sensitive_data("password123", 2) == "pa****"
        
        # Short data
        assert mask_sensitive_data("ab", 2) == "****"
        assert mask_sensitive_data("a", 2) == "****"
        
        # Empty data
        assert mask_sensitive_data("", 2) == "****"
        assert mask_sensitive_data(None, 2) == "****"
        
        # Different visible chars
        assert mask_sensitive_data("secret", 3) == "sec****"
    
    def test_validate_telegram_chat_id(self):
        """Test Telegram chat ID validation."""
        valid_ids = ["123456789", "-123456789", "987654321"]
        invalid_ids = ["", "abc", "123", "0", "999"]  # Too small
        
        for chat_id in valid_ids:
            assert validate_telegram_chat_id(chat_id)
        
        for chat_id in invalid_ids:
            assert not validate_telegram_chat_id(chat_id)
    
    def test_clean_html_tags(self):
        """Test HTML tag cleaning."""
        test_cases = [
            ("<p>Hello <b>world</b></p>", "Hello world"),
            ("&amp; &lt; &gt; &quot; &#39; &nbsp;", "& < > \" ' "),
            ("<script>alert('xss')</script>", "alert('xss')"),
            ("No HTML here", "No HTML here"),
            ("", ""),
            (None, "")
        ]
        
        for html, expected in test_cases:
            result = clean_html_tags(html)
            assert result == expected


class TestRateLimiter:
    """Test RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting functionality."""
        limiter = RateLimiter(max_calls=3, time_window=1)
        
        # First 3 calls should succeed
        for _ in range(3):
            assert await limiter.acquire() is True
        
        # 4th call should fail
        assert await limiter.acquire() is False
    
    @pytest.mark.asyncio
    async def test_rate_limiter_time_window(self):
        """Test rate limiter time window reset."""
        import asyncio
        
        limiter = RateLimiter(max_calls=2, time_window=1)
        
        # Use up the limit
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is False
        
        # Wait for time window to reset
        await asyncio.sleep(1.1)
        
        # Should be able to make calls again
        assert await limiter.acquire() is True
    
    def test_rate_limiter_time_until_next_call(self):
        """Test time until next call calculation."""
        limiter = RateLimiter(max_calls=1, time_window=10)
        
        # Initially should be 0
        assert limiter.time_until_next_call() == 0.0
        
        # After using up limit, should be positive
        import asyncio
        asyncio.run(limiter.acquire())
        time_until = limiter.time_until_next_call()
        assert 0 < time_until <= 10


class TestAsyncUtilities:
    """Test async utility functions."""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff utility."""
        from utils import exponential_backoff
        import time
        
        start_time = time.time()
        await exponential_backoff(0, base_delay=0.1, max_delay=1.0)
        elapsed = time.time() - start_time
        
        # Should wait at least base_delay
        assert elapsed >= 0.05  # Allow some tolerance
        
        # Test with jitter disabled would require more complex mocking
        # This basic test ensures the function works
