"""Utility functions for the ivasms Telegram bot."""

import asyncio
import hashlib
import random
import re
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


def get_git_info() -> Dict[str, str]:
    """Get git commit information for deployment info."""
    try:
        # Get current commit SHA
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        # Get current branch
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        # Get short SHA
        short_sha = commit_sha[:8]
        
        return {
            "commit_sha": commit_sha,
            "short_sha": short_sha,
            "branch": branch
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "commit_sha": "unknown",
            "short_sha": "unknown",
            "branch": "unknown"
        }


def get_uptime(start_time: datetime) -> str:
    """Calculate uptime from start time."""
    uptime_delta = datetime.now() - start_time
    
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def sanitize_for_telegram(text: str, max_length: int = 4096) -> str:
    """Sanitize text for Telegram message sending."""
    if not text:
        return ""
    
    # Remove or replace problematic characters
    sanitized = text.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length - 3] + "..."
    
    return sanitized


def extract_otp_from_text(text: str) -> Optional[str]:
    """Extract OTP code from message text using common patterns."""
    if not text:
        return None
    
    # Common OTP patterns
    patterns = [
        r'\b(\d{4,8})\b',  # 4-8 digit codes
        r'code[:\s]+(\d{4,8})',  # "code: 123456"
        r'verification[:\s]+(\d{4,8})',  # "verification: 123456"
        r'otp[:\s]+(\d{4,8})',  # "otp: 123456"
        r'pin[:\s]+(\d{4,8})',  # "pin: 123456"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)
    
    return None


def generate_message_id(timestamp: str, sender: str, text: str) -> str:
    """Generate a unique message ID for deduplication."""
    content = f"{timestamp}:{sender}:{text}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse various timestamp formats to datetime object."""
    if not timestamp_str:
        return None
    
    # Common timestamp formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str.strip(), fmt)
        except ValueError:
            continue
    
    logger.warning("Failed to parse timestamp", timestamp=timestamp_str)
    return None


def format_otp_message(otp_data: Dict[str, Any]) -> str:
    """Format OTP data into a readable Telegram message."""
    message_parts = ["🔔 **New OTP received**"]
    
    if otp_data.get("timestamp"):
        message_parts.append(f"**Time:** {otp_data['timestamp']}")
    
    if otp_data.get("sender"):
        message_parts.append(f"**From:** {otp_data['sender']}")
    
    if otp_data.get("text"):
        # Extract OTP code if possible
        otp_code = extract_otp_from_text(otp_data["text"])
        if otp_code:
            message_parts.append(f"**OTP Code:** `{otp_code}`")
        message_parts.append(f"**Message:** {otp_data['text']}")
    
    if otp_data.get("service"):
        message_parts.append(f"**Service:** {otp_data['service']}")
    
    return "\n".join(message_parts)


def add_jitter(base_interval: int, jitter_percent: float = 0.1) -> float:
    """Add random jitter to an interval to avoid fixed patterns."""
    jitter = base_interval * jitter_percent
    return base_interval + random.uniform(-jitter, jitter)


async def exponential_backoff(
    attempt: int, 
    base_delay: float = 1.0, 
    max_delay: float = 60.0,
    jitter: bool = True
) -> None:
    """Implement exponential backoff with optional jitter."""
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)  # 50-100% of calculated delay
    
    await asyncio.sleep(delay)


def is_valid_phone_number(phone: str) -> bool:
    """Check if a string looks like a valid phone number."""
    if not phone:
        return False
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it's all digits and reasonable length
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length with suffix."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def mask_sensitive_data(data: str, visible_chars: int = 2) -> str:
    """Mask sensitive data showing only first few characters."""
    if not data:
        return "****"
    
    if len(data) <= visible_chars:
        return "****"
    
    return data[:visible_chars] + "****"


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self) -> bool:
        """Check if we can make a call within rate limits."""
        now = time.time()
        
        # Remove old calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        # Check if we can make a new call
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        
        return False
    
    def time_until_next_call(self) -> float:
        """Get time in seconds until next call is allowed."""
        if len(self.calls) < self.max_calls:
            return 0.0
        
        oldest_call = min(self.calls)
        return max(0.0, self.time_window - (time.time() - oldest_call))


def validate_telegram_chat_id(chat_id: str) -> bool:
    """Validate Telegram chat ID format."""
    try:
        chat_id_int = int(chat_id)
        # Telegram chat IDs are typically large integers
        return abs(chat_id_int) > 1000
    except ValueError:
        return False


def clean_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    
    # Simple HTML tag removal
    clean_text = re.sub(r'<[^>]+>', '', text)
    
    # Decode common HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    }
    
    for entity, char in html_entities.items():
        clean_text = clean_text.replace(entity, char)
    
    return clean_text.strip()
