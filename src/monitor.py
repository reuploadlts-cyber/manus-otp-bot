"""Playwright automation for IVASMS login and SMS monitoring."""

import asyncio
import base64
from datetime import datetime
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .config import config
from .storage import Storage, SMSMessage
from .logger_setup import get_logger

logger = get_logger(__name__)


class IVASMSMonitor:
    """Main monitor class for IVASMS automation."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.is_monitoring = False
        self.last_seen_id: Optional[str] = None
        
    async def start(self) -> bool:
        """Start the browser and login."""
        try:
            playwright = await async_playwright().start()
            
            # Launch browser
            self.browser = await playwright.chromium.launch(
                headless=config.playwright_config['headless'],
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # Create context
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Create page
            self.page = await self.context.new_page()
            
            # Set timeout
            self.page.set_default_timeout(config.playwright_config['timeout_ms'])
            
            # Login
            success = await self._login()
            if success:
                self.is_logged_in = True
                logger.info("Successfully logged in to IVASMS")
                return True
            else:
                logger.error("Failed to login to IVASMS")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start monitor: {e}")
            await self.cleanup()
            return False
    
    async def _login(self) -> bool:
        """Login to IVASMS."""
        try:
            # Navigate to login page
            login_url = f"{config.site_config['base_url']}{config.site_config['login_path']}"
            await self.page.goto(login_url)
            logger.info(f"Navigated to login page: {login_url}")
            
            # Wait for login form
            await self.page.wait_for_selector(config.selectors['login']['email_input'])
            
            # Fill credentials
            await self.page.fill(config.selectors['login']['email_input'], config.ivasms_email)
            await self.page.fill(config.selectors['login']['password_input'], config.ivasms_password)
            
            # Click login button
            await self.page.click(config.selectors['login']['login_button'])
            logger.info("Clicked login button")
            
            # Wait for navigation after login
            await self.page.wait_for_load_state('networkidle')
            
            # Handle popup if it appears
            await self._handle_popup()
            
            # Verify login success by checking if we're on dashboard
            current_url = self.page.url
            if 'login' not in current_url.lower():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed - still on login page")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    async def _handle_popup(self) -> bool:
        """Handle the onboarding popup."""
        try:
            # Wait a bit for popup to appear
            await asyncio.sleep(2)
            
            # Check if popup exists
            popup_selectors = [
                config.selectors['popup']['popup_container'],
                '.popup',
                '.modal',
                '[role="dialog"]'
            ]
            
            popup_exists = False
            for selector in popup_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    popup_exists = True
                    logger.info(f"Found popup with selector: {selector}")
                    break
                except:
                    continue
            
            if not popup_exists:
                logger.info("No popup detected, assuming it's already dismissed")
                return True
            
            # Handle popup flow
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    # Look for Next button
                    next_button = self.page.locator(config.selectors['popup']['next_button'])
                    if await next_button.count() > 0:
                        await next_button.click()
                        logger.info(f"Clicked Next button (attempt {attempt + 1})")
                        await asyncio.sleep(1)
                        continue
                    
                    # Look for Done button
                    done_button = self.page.locator(config.selectors['popup']['done_button'])
                    if await done_button.count() > 0:
                        await done_button.click()
                        logger.info("Clicked Done button")
                        await asyncio.sleep(1)
                        break
                    
                    # If no buttons found, assume popup is dismissed
                    logger.info("No popup buttons found, assuming popup is dismissed")
                    break
                    
                except Exception as e:
                    logger.warning(f"Popup handling attempt {attempt + 1} failed: {e}")
                    if attempt == max_attempts - 1:
                        logger.warning("Max popup handling attempts reached, continuing anyway")
                        break
                    await asyncio.sleep(1)
            
            # Wait for popup to disappear
            await asyncio.sleep(2)
            logger.info("Popup handling completed")
            return True
            
        except Exception as e:
            logger.warning(f"Popup handling failed: {e}")
            return True  # Continue anyway
    
    async def navigate_to_sms_page(self) -> bool:
        """Navigate to SMS statistics page."""
        try:
            # Try direct navigation first
            sms_url = f"{config.site_config['base_url']}{config.site_config['sms_path']}"
            await self.page.goto(sms_url)
            await self.page.wait_for_load_state('networkidle')
            
            # Check if we're on the right page
            if 'sms' in self.page.url.lower() and 'received' in self.page.url.lower():
                logger.info("Successfully navigated to SMS page via direct URL")
                return True
            
            # If direct navigation failed, try sidebar navigation
            logger.info("Direct navigation failed, trying sidebar navigation")
            
            # Look for Client System menu
            client_system = self.page.locator(config.selectors['navigation']['client_system'])
            if await client_system.count() > 0:
                await client_system.click()
                await asyncio.sleep(1)
                
                # Look for My SMS Statistics
                sms_stats = self.page.locator(config.selectors['navigation']['sms_statistics'])
                if await sms_stats.count() > 0:
                    await sms_stats.click()
                    await self.page.wait_for_load_state('networkidle')
                    logger.info("Successfully navigated to SMS page via sidebar")
                    return True
            
            logger.error("Failed to navigate to SMS page")
            return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to SMS page: {e}")
            return False
    
    async def start_monitoring(self) -> bool:
        """Start monitoring for new SMS messages."""
        try:
            if not self.is_logged_in:
                logger.error("Not logged in, cannot start monitoring")
                return False
            
            # Navigate to SMS page
            if not await self.navigate_to_sms_page():
                return False
            
            self.is_monitoring = True
            logger.info("Started SMS monitoring")
            
            # Load existing messages
            await self._load_existing_messages()
            
            # Start monitoring loop
            asyncio.create_task(self._monitoring_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            return False
    
    async def _load_existing_messages(self):
        """Load existing SMS messages from the page."""
        try:
            messages = await self._scrape_messages()
            if messages:
                logger.info(f"Loaded {len(messages)} existing messages")
                # Save messages to storage
                for message in messages:
                    await self.storage.save_sms(message)
                    self.last_seen_id = message.id
        except Exception as e:
            logger.error(f"Failed to load existing messages: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                await self._check_for_new_messages()
                await asyncio.sleep(config.poll_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(config.poll_interval)
    
    async def _check_for_new_messages(self):
        """Check for new SMS messages."""
        try:
            messages = await self._scrape_messages()
            if not messages:
                return
            
            # Find new messages
            new_messages = []
            for message in messages:
                if not self.last_seen_id or message.id != self.last_seen_id:
                    new_messages.append(message)
                else:
                    break  # Stop at first seen message
            
            if new_messages:
                logger.info(f"Found {len(new_messages)} new messages")
                for message in reversed(new_messages):  # Process oldest first
                    await self.storage.save_sms(message)
                    self.last_seen_id = message.id
                    # Notify about new message (this will be handled by the bot)
                    logger.info(f"New SMS: {message.sender} - {message.message}")
            
        except Exception as e:
            logger.error(f"Error checking for new messages: {e}")
    
    async def _scrape_messages(self) -> List[SMSMessage]:
        """Scrape SMS messages from the current page."""
        try:
            # Wait for message list to load
            await self.page.wait_for_selector(config.selectors['sms_page']['message_list'], timeout=10000)
            
            # Get message rows
            rows = await self.page.locator(config.selectors['sms_page']['message_row']).all()
            messages = []
            
            for row in rows:
                try:
                    # Extract message data
                    sender_elem = row.locator(config.selectors['sms_page']['sender']).first
                    body_elem = row.locator(config.selectors['sms_page']['message_body']).first
                    time_elem = row.locator(config.selectors['sms_page']['timestamp']).first
                    
                    sender = await sender_elem.text_content() if await sender_elem.count() > 0 else "Unknown"
                    message = await body_elem.text_content() if await body_elem.count() > 0 else ""
                    timestamp = await time_elem.text_content() if await time_elem.count() > 0 else ""
                    
                    if message:  # Only process if we have a message body
                        # Create unique ID from content
                        message_id = f"{sender}_{timestamp}_{hash(message)}"
                        
                        sms = SMSMessage(
                            id=message_id,
                            sender=sender.strip(),
                            message=message.strip(),
                            timestamp=timestamp.strip(),
                            received_at=datetime.now().isoformat()
                        )
                        messages.append(sms)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse message row: {e}")
                    continue
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to scrape messages: {e}")
            return []
    
    async def get_history(self, start_date: str, end_date: str) -> List[SMSMessage]:
        """Get SMS history for date range."""
        try:
            # Ensure we're on SMS page
            if not await self.navigate_to_sms_page():
                return []
            
            # Fill date fields
            start_date_input = self.page.locator(config.selectors['history']['start_date'])
            end_date_input = self.page.locator(config.selectors['history']['end_date'])
            
            if await start_date_input.count() > 0:
                await start_date_input.fill(start_date)
            if await end_date_input.count() > 0:
                await end_date_input.fill(end_date)
            
            # Click Get SMS button
            get_sms_button = self.page.locator(config.selectors['history']['get_sms_button'])
            if await get_sms_button.count() > 0:
                await get_sms_button.click()
                
                # Wait for results to load
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)  # Additional wait for data to load
            
            # Scrape results
            return await self._scrape_messages()
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    async def take_screenshot(self) -> Optional[bytes]:
        """Take a screenshot for debugging."""
        try:
            if self.page:
                return await self.page.screenshot()
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
        return None
    
    async def cleanup(self):
        """Clean up browser resources."""
        try:
            self.is_monitoring = False
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def restart(self) -> bool:
        """Restart the monitor."""
        try:
            await self.cleanup()
            await asyncio.sleep(2)
            return await self.start()
        except Exception as e:
            logger.error(f"Failed to restart monitor: {e}")
            return False
