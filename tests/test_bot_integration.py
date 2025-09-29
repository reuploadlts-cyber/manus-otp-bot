"""Integration tests for Telegram bot commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from bot import IvasmsTelegramBot


class TestBotIntegration:
    """Integration tests for bot functionality."""
    
    @pytest.fixture
    async def bot_instance(self, storage, mock_config):
        """Create a bot instance for testing."""
        with patch('bot.Application') as mock_app_class:
            mock_app = AsyncMock()
            mock_app.bot = AsyncMock()
            mock_app.initialize = AsyncMock()
            mock_app.add_handler = MagicMock()
            mock_app_class.builder.return_value.token.return_value.build.return_value = mock_app
            
            bot = IvasmsTelegramBot()
            bot.storage = storage
            await bot.initialize()
            
            return bot
    
    @pytest.mark.asyncio
    async def test_start_command_authorized(self, bot_instance, mock_update, mock_context):
        """Test /start command with authorized user."""
        # Mock authorized user
        mock_update.effective_user.id = 123456789  # From mock_config
        
        await bot_instance.start_command(mock_update, mock_context)
        
        # Should reply with welcome message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "ivasms Telegram Bot" in call_args[0][0]
        assert call_args[1]["parse_mode"] == "Markdown"
    
    @pytest.mark.asyncio
    async def test_start_command_unauthorized(self, bot_instance, mock_update, mock_context):
        """Test /start command with unauthorized user."""
        # Mock unauthorized user
        mock_update.effective_user.id = 999999999
        
        await bot_instance.start_command(mock_update, mock_context)
        
        # Should reply with unauthorized message
        mock_update.message.reply_text.assert_called_once_with("❌ Unauthorized access.")
    
    @pytest.mark.asyncio
    async def test_status_command(self, bot_instance, mock_update, mock_context, sample_otp_data):
        """Test /status command."""
        # Store some test data
        bot_instance.storage.store_otp(sample_otp_data)
        
        # Mock authorized user
        mock_update.effective_user.id = 123456789
        
        await bot_instance.status_command(mock_update, mock_context)
        
        # Should reply with status information
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        status_message = call_args[0][0]
        
        assert "Bot Status" in status_message
        assert "Runtime:" in status_message
        assert "OTP Statistics:" in status_message
        assert call_args[1]["parse_mode"] == "Markdown"
    
    @pytest.mark.asyncio
    async def test_config_command(self, bot_instance, mock_update, mock_context):
        """Test /config command."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.config_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        config_message = call_args[0][0]
        
        assert "Configuration" in config_message
        assert "test@example.com" not in config_message  # Should be masked
        assert "te****@example.com" in config_message
    
    @pytest.mark.asyncio
    async def test_recent_otps_command_with_data(self, bot_instance, mock_update, mock_context, multiple_otp_data):
        """Test /recent_otps command with data."""
        # Store test OTPs
        for otp_data in multiple_otp_data:
            bot_instance.storage.store_otp(otp_data)
        
        mock_update.effective_user.id = 123456789
        
        await bot_instance.recent_otps_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        assert "Recent 3 OTPs:" in message
        assert "test001" in message or "test002" in message or "test003" in message
    
    @pytest.mark.asyncio
    async def test_recent_otps_command_empty(self, bot_instance, mock_update, mock_context):
        """Test /recent_otps command with no data."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.recent_otps_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with("📭 No OTPs found.")
    
    @pytest.mark.asyncio
    async def test_recent_otps_command_with_limit(self, bot_instance, mock_update, mock_context, multiple_otp_data):
        """Test /recent_otps command with custom limit."""
        # Store test OTPs
        for otp_data in multiple_otp_data:
            bot_instance.storage.store_otp(otp_data)
        
        mock_update.effective_user.id = 123456789
        mock_context.args = ["2"]  # Limit to 2 OTPs
        
        await bot_instance.recent_otps_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        assert "Recent 2 OTPs:" in message
    
    @pytest.mark.asyncio
    async def test_recent_otps_command_invalid_limit(self, bot_instance, mock_update, mock_context):
        """Test /recent_otps command with invalid limit."""
        mock_update.effective_user.id = 123456789
        mock_context.args = ["invalid"]
        
        await bot_instance.recent_otps_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with("❌ Invalid number. Usage: /recent_otps [N]")
    
    @pytest.mark.asyncio
    async def test_last_otp_command_with_data(self, bot_instance, mock_update, mock_context, sample_otp_data):
        """Test /last_otp command with data."""
        bot_instance.storage.store_otp(sample_otp_data)
        
        mock_update.effective_user.id = 123456789
        
        await bot_instance.last_otp_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        message = call_args[0][0]
        
        assert "Last OTP" in message
        assert "New OTP received" in message
        assert sample_otp_data["text"] in message
    
    @pytest.mark.asyncio
    async def test_last_otp_command_empty(self, bot_instance, mock_update, mock_context):
        """Test /last_otp command with no data."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.last_otp_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with("📭 No OTPs found.")
    
    @pytest.mark.asyncio
    async def test_new_otp_command(self, bot_instance, mock_update, mock_context):
        """Test /new_otp command."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.new_otp_command(mock_update, mock_context)
        
        # Should be called at least once (initial message)
        assert mock_update.message.reply_text.call_count >= 1
        
        # Check that force fetch was requested
        force_fetch_request = bot_instance.storage.get_state("force_fetch_requested")
        assert force_fetch_request is not None
        assert force_fetch_request["requested_by"] == 123456789
    
    @pytest.mark.asyncio
    async def test_stop_command(self, bot_instance, mock_update, mock_context):
        """Test /stop command."""
        mock_update.effective_user.id = 123456789
        
        # Initially monitoring should be enabled
        assert bot_instance.monitoring_enabled is True
        
        await bot_instance.stop_command(mock_update, mock_context)
        
        # Should disable monitoring
        assert bot_instance.monitoring_enabled is False
        
        # Should store state
        monitoring_state = bot_instance.storage.get_state("monitoring_enabled")
        assert monitoring_state is False
        
        mock_update.message.reply_text.assert_called_once_with("⏹️ Monitoring stopped.")
    
    @pytest.mark.asyncio
    async def test_start_monitor_command(self, bot_instance, mock_update, mock_context):
        """Test /start_monitor command."""
        mock_update.effective_user.id = 123456789
        
        # Disable monitoring first
        bot_instance.monitoring_enabled = False
        
        await bot_instance.start_monitor_command(mock_update, mock_context)
        
        # Should enable monitoring
        assert bot_instance.monitoring_enabled is True
        
        # Should store state
        monitoring_state = bot_instance.storage.get_state("monitoring_enabled")
        assert monitoring_state is True
        
        mock_update.message.reply_text.assert_called_once_with("▶️ Monitoring resumed.")
    
    @pytest.mark.asyncio
    async def test_restart_command(self, bot_instance, mock_update, mock_context):
        """Test /restart command."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.restart_command(mock_update, mock_context)
        
        # Should set restart flag
        restart_requested = bot_instance.storage.get_state("restart_requested")
        assert restart_requested is True
        
        mock_update.message.reply_text.assert_called_once_with("🔄 Restarting bot...")
    
    @pytest.mark.asyncio
    async def test_logs_command(self, bot_instance, mock_update, mock_context):
        """Test /logs command."""
        mock_update.effective_user.id = 123456789
        
        with patch('bot.get_log_tail') as mock_get_log_tail:
            mock_get_log_tail.return_value = [
                "2024-01-01 12:00:00 - INFO - Test log line 1",
                "2024-01-01 12:00:01 - ERROR - Test log line 2"
            ]
            
            await bot_instance.logs_command(mock_update, mock_context)
            
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            message = call_args[0][0]
            
            assert "Last 2 log lines:" in message
            assert "Test log line 1" in message
            assert "Test log line 2" in message
    
    @pytest.mark.asyncio
    async def test_logs_command_with_limit(self, bot_instance, mock_update, mock_context):
        """Test /logs command with custom limit."""
        mock_update.effective_user.id = 123456789
        mock_context.args = ["5"]
        
        with patch('bot.get_log_tail') as mock_get_log_tail:
            mock_get_log_tail.return_value = ["log line"] * 5
            
            await bot_instance.logs_command(mock_update, mock_context)
            
            # Should call get_log_tail with custom limit
            mock_get_log_tail.assert_called_once_with(5)
    
    @pytest.mark.asyncio
    async def test_help_command(self, bot_instance, mock_update, mock_context):
        """Test /help command."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.help_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        help_message = call_args[0][0]
        
        assert "ivasms Telegram Bot - Commands" in help_message
        assert "/start" in help_message
        assert "/status" in help_message
        assert "/help" in help_message
    
    @pytest.mark.asyncio
    async def test_handle_message_authorized(self, bot_instance, mock_update, mock_context):
        """Test handling non-command messages from authorized user."""
        mock_update.effective_user.id = 123456789
        
        await bot_instance.handle_message(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with("ℹ️ Use /help to see available commands.")
    
    @pytest.mark.asyncio
    async def test_handle_message_unauthorized(self, bot_instance, mock_update, mock_context):
        """Test handling non-command messages from unauthorized user."""
        mock_update.effective_user.id = 999999999
        
        await bot_instance.handle_message(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once_with("❌ Unauthorized access. Use /help for available commands.")
    
    @pytest.mark.asyncio
    async def test_send_notification(self, bot_instance):
        """Test sending notifications to admin chats."""
        with patch.object(bot_instance, '_send_admin_message') as mock_send:
            await bot_instance.send_notification("Test message")
            mock_send.assert_called_once_with("Test message", "Markdown")
    
    @pytest.mark.asyncio
    async def test_send_otp_notification(self, bot_instance, sample_otp_data):
        """Test sending OTP notifications."""
        with patch.object(bot_instance, 'send_notification') as mock_send:
            await bot_instance.send_otp_notification(sample_otp_data)
            
            # Should send formatted OTP message
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "New OTP received" in call_args
            
            # Should mark OTP as sent
            otp = bot_instance.storage.get_last_otp()
            assert otp['sent_to_telegram'] is True
    
    @pytest.mark.asyncio
    async def test_send_error_notification(self, bot_instance):
        """Test sending error notifications."""
        with patch.object(bot_instance, 'send_notification') as mock_send:
            await bot_instance.send_error_notification("Test error", "Test context")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "❌ **Error** (Test context)" in call_args
            assert "Test error" in call_args
    
    @pytest.mark.asyncio
    async def test_send_status_notification(self, bot_instance):
        """Test sending status notifications."""
        with patch.object(bot_instance, 'send_notification') as mock_send:
            await bot_instance.send_status_notification("Test status", "🔔")
            
            mock_send.assert_called_once_with("🔔 Test status", "Markdown")


class TestBotPrivateMethods:
    """Test private methods of the bot."""
    
    @pytest.fixture
    async def bot_instance(self, storage, mock_config):
        """Create a bot instance for testing."""
        with patch('bot.Application'):
            bot = IvasmsTelegramBot()
            bot.storage = storage
            return bot
    
    def test_is_admin(self, bot_instance):
        """Test admin user checking."""
        # Authorized user (from mock_config)
        assert bot_instance._is_admin(123456789) is True
        
        # Unauthorized user
        assert bot_instance._is_admin(999999999) is False
    
    @pytest.mark.asyncio
    async def test_get_status_info(self, bot_instance, sample_otp_data):
        """Test status information gathering."""
        # Store some test data
        bot_instance.storage.store_otp(sample_otp_data)
        bot_instance.storage.set_state("last_login_time", "2024-01-01 12:00:00")
        
        status_info = await bot_instance._get_status_info()
        
        assert "uptime" in status_info
        assert "total_otps" in status_info
        assert status_info["total_otps"] == 1
        assert status_info["last_login_time"] == "2024-01-01 12:00:00"
    
    @pytest.mark.asyncio
    async def test_send_admin_message(self, bot_instance):
        """Test sending messages to admin chats."""
        # Mock the application and bot
        mock_bot = AsyncMock()
        bot_instance.application = MagicMock()
        bot_instance.application.bot = mock_bot
        
        await bot_instance._send_admin_message("Test message")
        
        # Should send to admin chat ID from config
        mock_bot.send_message.assert_called_once_with(
            chat_id=123456789,
            text="Test message",
            parse_mode="Markdown"
        )
