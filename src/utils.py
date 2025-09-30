"""Utility functions for the OTP Forwarder Bot."""

import re
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any


def validate_date_format(date_string: str) -> bool:
    """Validate date string format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def extract_otp_from_message(message: str) -> Optional[str]:
    """Extract OTP code from SMS message."""
    # Common OTP patterns
    patterns = [
        r'code is (\d{4,8})',
        r'verification code: (\d{4,8})',
        r'OTP: (\d{4,8})',
        r'(\d{4,8}) is your code',
        r'your code: (\d{4,8})',
        r'(\d{6})',  # Generic 6-digit code
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def sanitize_phone_number(phone: str) -> str:
    """Sanitize phone number for display."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format based on length
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 11:
        return f"+{digits}"
    else:
        return phone  # Return original if can't format


def generate_message_id(sender: str, timestamp: str, message: str) -> str:
    """Generate unique message ID."""
    content = f"{sender}_{timestamp}_{message}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def format_timestamp(timestamp: str) -> str:
    """Format timestamp for display."""
    try:
        # Try to parse various timestamp formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        # If no format matches, return original
        return timestamp
        
    except Exception:
        return timestamp


def truncate_message(message: str, max_length: int = 100) -> str:
    """Truncate message if too long."""
    if len(message) <= max_length:
        return message
    
    return message[:max_length-3] + "..."


def is_valid_telegram_id(user_id: str) -> bool:
    """Validate Telegram user ID format."""
    try:
        uid = int(user_id)
        return 1 <= uid <= 2**63 - 1  # Valid Telegram user ID range
    except ValueError:
        return False


def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def format_sms_for_telegram(sms: Dict[str, Any]) -> str:
    """Format SMS message for Telegram display."""
    sender = sanitize_phone_number(sms.get('sender', 'Unknown'))
    message = escape_markdown(sms.get('message', ''))
    timestamp = format_timestamp(sms.get('timestamp', ''))
    
    # Extract OTP if present
    otp = extract_otp_from_message(sms.get('message', ''))
    otp_text = f"\n🔑 OTP: `{otp}`" if otp else ""
    
    return (
        f"🆕 **New SMS received**{otp_text}\n\n"
        f"From: `{sender}`\n"
        f"Message: `{message}`\n"
        f"Time: {timestamp}"
    )


def parse_command_args(text: str) -> List[str]:
    """Parse command arguments from message text."""
    parts = text.split()
    return parts[1:] if len(parts) > 1 else []


def get_error_summary(error: Exception) -> str:
    """Get a user-friendly error summary."""
    error_type = type(error).__name__
    error_message = str(error)
    
    # Common error patterns
    if "timeout" in error_message.lower():
        return "⏱️ Operation timed out. Please try again."
    elif "network" in error_message.lower() or "connection" in error_message.lower():
        return "🌐 Network error. Check your connection."
    elif "login" in error_message.lower() or "authentication" in error_message.lower():
        return "🔐 Login failed. Check your credentials."
    elif "not found" in error_message.lower():
        return "❌ Resource not found."
    elif "permission" in error_message.lower() or "access" in error_message.lower():
        return "🚫 Access denied."
    else:
        return f"❌ {error_type}: {error_message[:100]}"


def create_csv_content(data: List[Dict[str, Any]], headers: List[str]) -> str:
    """Create CSV content from data."""
    if not data:
        return ""
    
    # Escape CSV values
    def escape_csv_value(value: Any) -> str:
        if value is None:
            return ""
        str_value = str(value)
        if ',' in str_value or '"' in str_value or '\n' in str_value:
            return f'"{str_value.replace('"', '""')}"'
        return str_value
    
    # Create CSV lines
    lines = [','.join(escape_csv_value(header) for header in headers)]
    
    for row in data:
        line = ','.join(escape_csv_value(row.get(header, '')) for header in headers)
        lines.append(line)
    
    return '\n'.join(lines)


def validate_config_values(config_dict: Dict[str, Any]) -> List[str]:
    """Validate configuration values and return errors."""
    errors = []
    
    # Check required fields
    required_fields = ['telegram_token', 'admin_ids', 'ivasms_email', 'ivasms_password']
    for field in required_fields:
        if not config_dict.get(field):
            errors.append(f"Missing required field: {field}")
    
    # Validate admin IDs
    admin_ids = config_dict.get('admin_ids', [])
    if not isinstance(admin_ids, list) or not admin_ids:
        errors.append("At least one admin ID is required")
    else:
        for admin_id in admin_ids:
            if not isinstance(admin_id, int) or admin_id <= 0:
                errors.append(f"Invalid admin ID: {admin_id}")
    
    # Validate poll interval
    poll_interval = config_dict.get('poll_interval', 8)
    if not isinstance(poll_interval, int) or poll_interval < 1 or poll_interval > 300:
        errors.append("Poll interval must be between 1 and 300 seconds")
    
    # Validate email format
    email = config_dict.get('ivasms_email', '')
    if email and '@' not in email:
        errors.append("Invalid email format")
    
    return errors
