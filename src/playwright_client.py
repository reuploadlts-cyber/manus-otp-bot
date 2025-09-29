"""Playwright client for interacting with ivasms.com website."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .config import Config
from .utils import clean_html_tags, generate_message_id, parse_timestamp

logger = structlog.get_logger(__name__)


class IvasmsScraper:
    """Playwright-based scraper for ivasms.com OTP retrieval."""
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.storage_state_path = "./data/browser_state.json"
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self) -> None:
        """Initialize Playwright and browser."""
        try:
            logger.info("Starting Playwright browser")
            self.playwright = await async_playwright().start()
            
            # Launch browser with appropriate settings
            self.browser = await self.playwright.chromium.launch(
                headless=Config.HEADLESS,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps',
                ]
            )
            
            # Create context with persistent state if available
            context_options = {
                'viewport': {'width': 1280, 'height': 720},
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # Load storage state if it exists
            if os.path.exists(self.storage_state_path):
                try:
                    context_options['storage_state'] = self.storage_state_path
                    logger.info("Loaded browser storage state")
                except Exception as e:
                    logger.warning("Failed to load storage state", error=str(e))
            
            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()
            
            # Set timeouts
            self.page.set_default_timeout(Config.BROWSER_TIMEOUT)
            
            logger.info("Playwright browser started successfully")
            
        except Exception as e:
            logger.error("Failed to start Playwright browser", error=str(e))
            await self.close()
            raise
    
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("Playwright browser closed")
            
        except Exception as e:
            logger.error("Error closing browser", error=str(e))
    
    async def save_storage_state(self) -> None:
        """Save browser storage state for session persistence."""
        try:
            if self.context:
                # Ensure directory exists
                Path(self.storage_state_path).parent.mkdir(parents=True, exist_ok=True)
                await self.context.storage_state(path=self.storage_state_path)
                logger.info("Browser storage state saved")
        except Exception as e:
            logger.error("Failed to save storage state", error=str(e))
    
    async def take_screenshot(self, name: str = "debug") -> str:
        """Take a screenshot for debugging purposes."""
        try:
            if not self.page:
                return ""
            
            screenshot_dir = Path("./data/screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = screenshot_dir / f"{name}_{timestamp}.png"
            
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info("Screenshot taken", path=str(screenshot_path))
            return str(screenshot_path)
            
        except Exception as e:
            logger.error("Failed to take screenshot", error=str(e))
            return ""
    
    async def login(self) -> Tuple[bool, str]:
        """
        Login to ivasms.com.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.page:
                return False, "Browser not initialized"
            
            logger.info("Attempting to login to ivasms.com")
            
            # Navigate to login page
            await self.page.goto(Config.IVASMS_LOGIN_URL, wait_until='networkidle')
            
            # Check if already logged in by looking for dashboard elements
            if await self._check_if_logged_in():
                self.is_logged_in = True
                await self.save_storage_state()
                return True, "Already logged in"
            
            # Find and fill login form
            email_selector = 'input[name="email"], input[type="email"], #email'
            password_selector = 'input[name="password"], input[type="password"], #password'
            login_button_selector = 'button[type="submit"], input[type="submit"], button:has-text("Log in"), button:has-text("Login")'
            
            # Wait for login form to be visible
            try:
                await self.page.wait_for_selector(email_selector, timeout=10000)
            except Exception:
                await self.take_screenshot("login_form_not_found")
                return False, "Login form not found"
            
            # Fill credentials
            await self.page.fill(email_selector, Config.IVASMS_EMAIL)
            await self.page.fill(password_selector, Config.IVASMS_PASSWORD)
            
            # Click login button
            await self.page.click(login_button_selector)
            
            # Wait for navigation or error message
            try:
                # Wait for either dashboard or error message
                await self.page.wait_for_load_state('networkidle', timeout=15000)
                await asyncio.sleep(2)  # Give page time to fully load
                
                # Check if login was successful
                if await self._check_if_logged_in():
                    self.is_logged_in = True
                    await self.save_storage_state()
                    logger.info("Login successful")
                    return True, "Login successful"
                else:
                    # Check for error messages
                    error_message = await self._get_error_message()
                    await self.take_screenshot("login_failed")
                    logger.warning("Login failed", error=error_message)
                    return False, f"Login failed: {error_message}"
                    
            except Exception as e:
                await self.take_screenshot("login_timeout")
                logger.error("Login timeout or error", error=str(e))
                return False, f"Login timeout: {str(e)}"
        
        except Exception as e:
            logger.error("Login error", error=str(e))
            await self.take_screenshot("login_error")
            return False, f"Login error: {str(e)}"
    
    async def _check_if_logged_in(self) -> bool:
        """Check if user is currently logged in."""
        try:
            # Look for common dashboard elements
            dashboard_selectors = [
                '.dashboard',
                '.sidebar',
                'nav',
                '[href*="dashboard"]',
                '[href*="portal"]',
                'a:has-text("Dashboard")',
                'a:has-text("Client")',
                'a:has-text("Logout")',
                'a:has-text("Sign out")'
            ]
            
            for selector in dashboard_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            logger.error("Error checking login status", error=str(e))
            return False
    
    async def _get_error_message(self) -> str:
        """Extract error message from the page."""
        try:
            error_selectors = [
                '.error',
                '.alert-danger',
                '.alert-error',
                '.message.error',
                '[class*="error"]',
                '[class*="danger"]'
            ]
            
            for selector in error_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        text = await element.text_content()
                        if text and text.strip():
                            return clean_html_tags(text.strip())
                except Exception:
                    continue
            
            return "Unknown error"
            
        except Exception:
            return "Unknown error"
    
    async def navigate_to_sms_received(self) -> Tuple[bool, str]:
        """
        Navigate to the SMS received page.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.is_logged_in:
                return False, "Not logged in"
            
            logger.info("Navigating to SMS received page")
            
            # Try direct navigation first
            await self.page.goto(Config.IVASMS_SMS_RECEIVED_URL, wait_until='networkidle')
            
            # Check if we're on the right page
            if await self._check_sms_page_loaded():
                logger.info("Successfully navigated to SMS received page")
                return True, "Navigation successful"
            
            # If direct navigation failed, try menu navigation
            logger.info("Direct navigation failed, trying menu navigation")
            
            # Look for Client menu
            client_selectors = [
                'a:has-text("Client")',
                'a:has-text("Client System")',
                '[href*="client"]',
                'nav a:has-text("Client")'
            ]
            
            client_clicked = False
            for selector in client_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        client_clicked = True
                        break
                except Exception:
                    continue
            
            if not client_clicked:
                await self.take_screenshot("client_menu_not_found")
                return False, "Client menu not found"
            
            # Wait for submenu and look for SMS Statistics
            await asyncio.sleep(1)
            
            sms_stats_selectors = [
                'a:has-text("My SMS Statistics")',
                'a:has-text("SMS Statistics")',
                'a:has-text("Received")',
                '[href*="sms/received"]',
                '[href*="received"]'
            ]
            
            for selector in sms_stats_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        await self.page.wait_for_load_state('networkidle')
                        break
                except Exception:
                    continue
            
            # Check if we're now on the SMS page
            if await self._check_sms_page_loaded():
                logger.info("Successfully navigated via menu")
                return True, "Navigation successful via menu"
            else:
                await self.take_screenshot("sms_page_not_loaded")
                return False, "Failed to reach SMS received page"
        
        except Exception as e:
            logger.error("Navigation error", error=str(e))
            await self.take_screenshot("navigation_error")
            return False, f"Navigation error: {str(e)}"
    
    async def _check_sms_page_loaded(self) -> bool:
        """Check if SMS received page is loaded."""
        try:
            # Look for SMS-related elements
            sms_page_selectors = [
                'table',
                '.sms-list',
                '.message-list',
                '[class*="sms"]',
                '[class*="message"]',
                'tbody tr',
                '.received-sms'
            ]
            
            for selector in sms_page_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        return True
                except Exception:
                    continue
            
            # Also check URL
            current_url = self.page.url
            if 'sms' in current_url.lower() or 'received' in current_url.lower():
                return True
            
            return False
            
        except Exception:
            return False
    
    async def fetch_otps(self) -> List[Dict[str, str]]:
        """
        Fetch OTP messages from the SMS received page.
        
        Returns:
            List of OTP dictionaries with keys: id, timestamp, sender, text, service
        """
        try:
            if not self.page:
                return []
            
            logger.info("Fetching OTPs from page")
            
            # Wait for content to load
            await asyncio.sleep(2)
            
            otps = []
            
            # Try different table/list structures
            selectors_to_try = [
                # Table-based structure
                {
                    'container': 'table tbody',
                    'row': 'tr',
                    'timestamp': 'td:nth-child(1), .time, .date',
                    'sender': 'td:nth-child(2), .sender, .from',
                    'text': 'td:nth-child(3), .message, .text',
                    'service': 'td:nth-child(4), .service'
                },
                # Div-based structure
                {
                    'container': '.message-list, .sms-list',
                    'row': '.message, .sms-item, .sms-row',
                    'timestamp': '.time, .date, .timestamp',
                    'sender': '.sender, .from, .number',
                    'text': '.text, .message, .content',
                    'service': '.service, .provider'
                },
                # Generic structure
                {
                    'container': '[class*="sms"], [class*="message"]',
                    'row': 'div, tr',
                    'timestamp': '[class*="time"], [class*="date"]',
                    'sender': '[class*="sender"], [class*="from"]',
                    'text': '[class*="text"], [class*="message"]',
                    'service': '[class*="service"]'
                }
            ]
            
            for structure in selectors_to_try:
                try:
                    # Check if container exists
                    container = await self.page.wait_for_selector(structure['container'], timeout=5000)
                    if not container:
                        continue
                    
                    # Get all rows
                    rows = await self.page.query_selector_all(f"{structure['container']} {structure['row']}")
                    
                    if not rows:
                        continue
                    
                    logger.info(f"Found {len(rows)} potential SMS rows")
                    
                    for row in rows:
                        try:
                            otp_data = await self._extract_otp_from_row(row, structure)
                            if otp_data and otp_data.get('text'):
                                otps.append(otp_data)
                        except Exception as e:
                            logger.debug("Error extracting OTP from row", error=str(e))
                            continue
                    
                    if otps:
                        break  # Found OTPs with this structure
                        
                except Exception as e:
                    logger.debug("Error with selector structure", structure=structure['container'], error=str(e))
                    continue
            
            # If no structured data found, try to extract from page text
            if not otps:
                otps = await self._extract_otps_from_page_text()
            
            logger.info(f"Extracted {len(otps)} OTPs from page")
            return otps
            
        except Exception as e:
            logger.error("Error fetching OTPs", error=str(e))
            await self.take_screenshot("fetch_otps_error")
            return []
    
    async def _extract_otp_from_row(self, row, structure: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Extract OTP data from a single row element."""
        try:
            otp_data = {}
            
            # Extract timestamp
            timestamp_element = await row.query_selector(structure['timestamp'])
            if timestamp_element:
                timestamp_text = await timestamp_element.text_content()
                otp_data['timestamp'] = clean_html_tags(timestamp_text or "").strip()
            else:
                otp_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Extract sender
            sender_element = await row.query_selector(structure['sender'])
            if sender_element:
                sender_text = await sender_element.text_content()
                otp_data['sender'] = clean_html_tags(sender_text or "").strip()
            else:
                otp_data['sender'] = "Unknown"
            
            # Extract message text
            text_element = await row.query_selector(structure['text'])
            if text_element:
                message_text = await text_element.text_content()
                otp_data['text'] = clean_html_tags(message_text or "").strip()
            else:
                # Try to get all text from the row
                row_text = await row.text_content()
                otp_data['text'] = clean_html_tags(row_text or "").strip()
            
            # Extract service (optional)
            service_element = await row.query_selector(structure['service'])
            if service_element:
                service_text = await service_element.text_content()
                otp_data['service'] = clean_html_tags(service_text or "").strip()
            else:
                otp_data['service'] = ""
            
            # Generate unique ID
            otp_data['id'] = generate_message_id(
                otp_data['timestamp'],
                otp_data['sender'],
                otp_data['text']
            )
            
            # Only return if we have meaningful text
            if otp_data['text'] and len(otp_data['text']) > 3:
                return otp_data
            
            return None
            
        except Exception as e:
            logger.debug("Error extracting OTP from row", error=str(e))
            return None
    
    async def _extract_otps_from_page_text(self) -> List[Dict[str, str]]:
        """Fallback method to extract OTPs from page text."""
        try:
            page_text = await self.page.text_content('body')
            if not page_text:
                return []
            
            # This is a basic fallback - in a real implementation,
            # you'd need to analyze the actual page structure
            lines = page_text.split('\n')
            otps = []
            
            for i, line in enumerate(lines):
                line = line.strip()
                if line and any(keyword in line.lower() for keyword in ['code', 'otp', 'verification', 'pin']):
                    otp_data = {
                        'id': generate_message_id(str(i), "unknown", line),
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'sender': "Unknown",
                        'text': line,
                        'service': ""
                    }
                    otps.append(otp_data)
            
            return otps[:10]  # Limit to prevent spam
            
        except Exception as e:
            logger.error("Error extracting OTPs from page text", error=str(e))
            return []
