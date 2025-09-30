"""Telegram bot implementation using aiogram."""

import asyncio
import base64
from datetime import datetime
from typing import List, Optional
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from .config import config
from .storage import Storage, SMSMessage
from .monitor import IVASMSMonitor
from .logger_setup import get_logger

logger = get_logger(__name__)


class BotStates(StatesGroup):
    """Bot state management."""
    waiting_for_admin_id = State()


class OTPForwarderBot:
    """Main bot class."""
    
    def __init__(self):
        self.bot = Bot(token=config.telegram_token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.storage = Storage()
        self.monitor = IVASMSMonitor(self.storage)
        self.is_running = False
        self.start_time = None
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all bot handlers."""
        
        # Start command
        @self.dp.message(CommandStart())
        async def start_handler(message: Message):
            await self._handle_start(message)
        
        # Status command
        @self.dp.message(Command("status"))
        async def status_handler(message: Message):
            await self._handle_status(message)
        
        # Config command
        @self.dp.message(Command("config"))
        async def config_handler(message: Message):
            await self._handle_config(message)
        
        # Set admin command
        @self.dp.message(Command("set_admin"))
        async def set_admin_handler(message: Message, state: FSMContext):
            await self._handle_set_admin(message, state)
        
        # Recent command
        @self.dp.message(Command("recent"))
        async def recent_handler(message: Message):
            await self._handle_recent(message)
        
        # Last command
        @self.dp.message(Command("last"))
        async def last_handler(message: Message):
            await self._handle_last(message)
        
        # History command
        @self.dp.message(Command("history"))
        async def history_handler(message: Message):
            await self._handle_history(message)
        
        # Get OTP command
        @self.dp.message(Command("getotp"))
        async def getotp_handler(message: Message):
            await self._handle_getotp(message)
        
        # Restart command
        @self.dp.message(Command("restart"))
        async def restart_handler(message: Message):
            await self._handle_restart(message)
        
        # Help command
        @self.dp.message(Command("help"))
        async def help_handler(message: Message):
            await self._handle_help(message)
        
        # Admin ID input handler
        @self.dp.message(BotStates.waiting_for_admin_id)
        async def admin_id_input_handler(message: Message, state: FSMContext):
            await self._handle_admin_id_input(message, state)
    
    async def _check_admin(self, message: Message) -> bool:
        """Check if user is admin."""
        if not config.is_admin(message.from_user.id):
            await message.reply("❌ Access denied. This command is for admins only.")
            return False
        return True
    
    async def _check_owner(self, message: Message) -> bool:
        """Check if user is the owner (first admin)."""
        if not config.admin_ids or message.from_user.id != config.admin_ids[0]:
            await message.reply("❌ Access denied. This command is for the owner only.")
            return False
        return True
    
    async def _handle_start(self, message: Message):
        """Handle /start command."""
        status = "🟢 Running" if self.is_running else "🔴 Stopped"
        uptime = ""
        if self.start_time:
            uptime = f"\nUptime: {datetime.now() - self.start_time}"
        
        await message.reply(
            f"🤖 **OTP Forwarder Bot**\n\n"
            f"Status: {status}{uptime}\n"
            f"Version: 1.0.0\n"
            f"Environment: codespace\n"
            f"Admins: {len(config.admin_ids)}\n\n"
            f"Use /help to see available commands."
        )
    
    async def _handle_status(self, message: Message):
        """Handle /status command."""
        if not await self._check_admin(message):
            return
        
        status = "🟢 Running" if self.is_running else "🔴 Stopped"
        login_status = "✅ Logged in" if self.monitor.is_logged_in else "❌ Not logged in"
        monitoring_status = "✅ Monitoring" if self.monitor.is_monitoring else "❌ Not monitoring"
        
        last_otp = await self.storage.get_last_sms()
        last_otp_time = last_otp.timestamp if last_otp else "None"
        
        await message.reply(
            f"📊 **Bot Status**\n\n"
            f"Process: {status}\n"
            f"Login: {login_status}\n"
            f"Monitoring: {monitoring_status}\n"
            f"Last OTP: {last_otp_time}\n"
            f"Current Page: {self.monitor.page.url if self.monitor.page else 'N/A'}"
        )
    
    async def _handle_config(self, message: Message):
        """Handle /config command."""
        if not await self._check_admin(message):
            return
        
        config_text = config.get_sanitized_config()
        await message.reply(f"⚙️ **Configuration**\n\n```\n{config_text}\n```")
    
    async def _handle_set_admin(self, message: Message, state: FSMContext):
        """Handle /set_admin command."""
        if not await self._check_owner(message):
            return
        
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if args:
            try:
                admin_id = int(args[0])
                if admin_id not in config.admin_ids:
                    config.admin_ids.append(admin_id)
                    await message.reply(f"✅ Added admin: {admin_id}")
                else:
                    await message.reply(f"ℹ️ User {admin_id} is already an admin")
            except ValueError:
                await message.reply("❌ Invalid admin ID. Please provide a valid Telegram user ID.")
        else:
            await message.reply("Please provide a Telegram user ID to add as admin.")
    
    async def _handle_recent(self, message: Message):
        """Handle /recent command."""
        if not await self._check_admin(message):
            return
        
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        limit = int(args[0]) if args and args[0].isdigit() else 10
        
        messages = await self.storage.get_recent_sms(limit)
        
        if not messages:
            await message.reply("📭 No SMS messages found.")
            return
        
        for msg in messages:
            await self._send_sms_message(message.chat.id, msg)
    
    async def _handle_last(self, message: Message):
        """Handle /last command."""
        if not await self._check_admin(message):
            return
        
        last_msg = await self.storage.get_last_sms()
        
        if not last_msg:
            await message.reply("📭 No SMS messages found.")
            return
        
        await self._send_sms_message(message.chat.id, last_msg)
    
    async def _handle_history(self, message: Message):
        """Handle /history command."""
        if not await self._check_admin(message):
            return
        
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if len(args) != 2:
            await message.reply("❌ Usage: /history <start_date> <end_date>\nExample: /history 2025-09-01 2025-09-30")
            return
        
        start_date, end_date = args
        
        # Validate date format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            await message.reply("❌ Invalid date format. Use YYYY-MM-DD")
            return
        
        await message.reply("🔄 Fetching history... This may take a moment.")
        
        try:
            messages = await self.monitor.get_history(start_date, end_date)
            
            if not messages:
                await message.reply(f"📭 No messages found for {start_date} to {end_date}")
                return
            
            # If more than 10 messages, send as CSV
            if len(messages) > 10:
                csv_content = await self.storage.export_history_csv(start_date, end_date)
                if csv_content:
                    filename = f"history_{start_date}_{end_date}.csv"
                    await message.reply_document(
                        types.BufferedInputFile(
                            csv_content.encode(),
                            filename=filename
                        ),
                        caption=f"📊 History for {start_date} to {end_date} ({len(messages)} messages)"
                    )
                else:
                    await message.reply("❌ Failed to generate CSV file")
            else:
                for msg in messages:
                    await self._send_sms_message(message.chat.id, msg)
                    
        except Exception as e:
            logger.error(f"History fetch failed: {e}")
            await message.reply(f"❌ Failed to fetch history: {str(e)}")
    
    async def _handle_getotp(self, message: Message):
        """Handle /getotp command."""
        if not await self._check_admin(message):
            return
        
        await message.reply("🔄 Fetching current messages...")
        
        try:
            if not self.monitor.is_logged_in:
                await message.reply("❌ Not logged in. Please restart the bot.")
                return
            
            messages = await self.monitor._scrape_messages()
            
            if not messages:
                await message.reply("📭 No messages found on the page.")
                return
            
            for msg in messages:
                await self._send_sms_message(message.chat.id, msg)
                
        except Exception as e:
            logger.error(f"Get OTP failed: {e}")
            await message.reply(f"❌ Failed to fetch messages: {str(e)}")
    
    async def _handle_restart(self, message: Message):
        """Handle /restart command."""
        if not await self._check_owner(message):
            return
        
        await message.reply("🔄 Restarting bot...")
        
        try:
            await self.stop()
            await asyncio.sleep(2)
            await self.start()
            await message.reply("✅ Bot restarted successfully")
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            await message.reply(f"❌ Restart failed: {str(e)}")
    
    async def _handle_help(self, message: Message):
        """Handle /help command."""
        help_text = """
🤖 **OTP Forwarder Bot Commands**

**General Commands:**
/start - Show bot status and info
/help - Show this help message

**Admin Commands:**
/status - Show detailed bot status
/config - Show bot configuration
/recent [n] - Show last n SMS messages (default: 10)
/last - Show latest SMS message
/history <start> <end> - Get SMS history for date range
/getotp - Fetch current messages from page

**Owner Commands:**
/set_admin <user_id> - Add new admin
/restart - Restart the bot

**Examples:**
/history 2025-09-01 2025-09-30
/recent 5
        """
        await message.reply(help_text)
    
    async def _handle_admin_id_input(self, message: Message, state: FSMContext):
        """Handle admin ID input."""
        try:
            admin_id = int(message.text)
            if admin_id not in config.admin_ids:
                config.admin_ids.append(admin_id)
                await message.reply(f"✅ Added admin: {admin_id}")
            else:
                await message.reply(f"ℹ️ User {admin_id} is already an admin")
        except ValueError:
            await message.reply("❌ Invalid admin ID. Please provide a valid Telegram user ID.")
        finally:
            await state.clear()
    
    async def _send_sms_message(self, chat_id: int, sms: SMSMessage):
        """Send SMS message to Telegram."""
        try:
            message_text = (
                f"🆕 **New SMS received**\n\n"
                f"From: `{sms.sender}`\n"
                f"Message: `{sms.message}`\n"
                f"Time: {sms.timestamp}\n"
                f"URL: {config.site_config['base_url']}{config.site_config['sms_path']}"
            )
            
            await self.bot.send_message(chat_id, message_text)
            
            # Mark as forwarded
            await self.storage.mark_forwarded(sms.id)
            
        except Exception as e:
            logger.error(f"Failed to send SMS message: {e}")
    
    async def start(self):
        """Start the bot."""
        try:
            self.is_running = True
            self.start_time = datetime.now()
            
            # Start monitor
            monitor_started = await self.monitor.start()
            if not monitor_started:
                logger.error("Failed to start monitor")
                return False
            
            # Start monitoring
            await self.monitor.start_monitoring()
            
            # Send startup notification
            if config.telegram_config['notify_on_start']:
                for admin_id in config.admin_ids:
                    try:
                        await self.bot.send_message(
                            admin_id,
                            f"✅ **Bot started**\n\n"
                            f"Version: 1.0.0\n"
                            f"Environment: codespace\n"
                            f"Admins: {len(config.admin_ids)}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send startup notification to {admin_id}: {e}")
            
            logger.info("Bot started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
    
    async def stop(self):
        """Stop the bot."""
        try:
            self.is_running = False
            await self.monitor.cleanup()
            logger.info("Bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    async def run(self):
        """Run the bot."""
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Bot polling error: {e}")
        finally:
            await self.stop()
