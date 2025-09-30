"""Main entry point for the OTP Forwarder Bot."""

import asyncio
import signal
import sys
from .bot import OTPForwarderBot
from .logger_setup import setup_logging, get_logger
from .config import config

# Setup logging
logger = setup_logging(config.log_level)


class BotManager:
    """Manages the bot lifecycle."""
    
    def __init__(self):
        self.bot = OTPForwarderBot()
        self.shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the bot."""
        try:
            logger.info("Starting OTP Forwarder Bot...")
            
            # Start the bot
            success = await self.bot.start()
            if not success:
                logger.error("Failed to start bot")
                return False
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Start bot polling
            await self.bot.run()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Shutdown the bot gracefully."""
        try:
            logger.info("Shutting down bot...")
            await self.bot.stop()
            logger.info("Bot shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main function."""
    manager = BotManager()
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
