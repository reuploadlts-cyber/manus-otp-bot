"""Test configuration and fixtures for the ivasms Telegram bot."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Add src directory to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config
from storage import OTPStorage


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name
    
    yield temp_db_path
    
    # Cleanup
    if os.path.exists(temp_db_path):
        os.unlink(temp_db_path)


@pytest.fixture
def storage(temp_db):
    """Create a test storage instance."""
    return OTPStorage(temp_db)


@pytest.fixture
def sample_otp_data():
    """Sample OTP data for testing."""
    return {
        "id": "test123",
        "timestamp": "2024-01-01 12:00:00",
        "sender": "+1234567890",
        "text": "Your verification code is 123456",
        "service": "TestService"
    }


@pytest.fixture
def multiple_otp_data():
    """Multiple OTP data samples for testing."""
    return [
        {
            "id": "test001",
            "timestamp": "2024-01-01 10:00:00",
            "sender": "+1111111111",
            "text": "Your code is 111111",
            "service": "Service1"
        },
        {
            "id": "test002",
            "timestamp": "2024-01-01 11:00:00",
            "sender": "+2222222222",
            "text": "Verification: 222222",
            "service": "Service2"
        },
        {
            "id": "test003",
            "timestamp": "2024-01-01 12:00:00",
            "sender": "+3333333333",
            "text": "OTP code 333333",
            "service": "Service3"
        }
    ]


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright page object."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.text_content = AsyncMock(return_value="Sample page content")
    page.screenshot = AsyncMock()
    page.query_selector = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[])
    page.url = "https://www.ivasms.com/portal/sms/received"
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_playwright_context():
    """Mock Playwright browser context."""
    context = AsyncMock()
    context.new_page = AsyncMock()
    context.close = AsyncMock()
    context.storage_state = AsyncMock()
    return context


@pytest.fixture
def mock_playwright_browser():
    """Mock Playwright browser."""
    browser = AsyncMock()
    browser.new_context = AsyncMock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_playwright():
    """Mock Playwright instance."""
    playwright = AsyncMock()
    playwright.chromium.launch = AsyncMock()
    playwright.stop = AsyncMock()
    return playwright


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_telegram_application():
    """Mock Telegram application."""
    app = AsyncMock()
    app.bot = mock_telegram_bot()
    app.initialize = AsyncMock()
    app.start = AsyncMock()
    app.stop = AsyncMock()
    app.shutdown = AsyncMock()
    app.add_handler = MagicMock()
    
    # Mock updater
    app.updater = AsyncMock()
    app.updater.start_polling = AsyncMock()
    app.updater.stop = AsyncMock()
    
    return app


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration for testing."""
    # Set test environment variables
    test_config = {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_ADMIN_CHAT_IDS": "123456789",
        "IVASMS_EMAIL": "test@example.com",
        "IVASMS_PASSWORD": "test_password",
        "POLL_INTERVAL_SECONDS": "5",
        "HEADLESS": "true",
        "DB_PATH": "./test_data/test.db",
        "LOG_LEVEL": "DEBUG",
        "OWNER_PERMISSION_ACKNOWLEDGED": "true"
    }
    
    for key, value in test_config.items():
        monkeypatch.setenv(key, value)
    
    # Reload config
    import importlib
    import config
    importlib.reload(config)
    
    return config.Config


@pytest.fixture
def mock_update():
    """Mock Telegram update object."""
    update = MagicMock()
    update.effective_user.id = 123456789
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram context object."""
    context = MagicMock()
    context.args = []
    return context


@pytest_asyncio.fixture
async def mock_scraper(mock_playwright, mock_playwright_browser, mock_playwright_context, mock_playwright_page):
    """Mock scraper with all dependencies."""
    from playwright_client import IvasmsScraper
    
    scraper = IvasmsScraper()
    scraper.playwright = mock_playwright
    scraper.browser = mock_playwright_browser
    scraper.context = mock_playwright_context
    scraper.page = mock_playwright_page
    scraper.is_logged_in = True
    
    # Mock the context manager methods
    scraper.__aenter__ = AsyncMock(return_value=scraper)
    scraper.__aexit__ = AsyncMock(return_value=None)
    
    return scraper


@pytest.fixture
def clean_storage_state():
    """Clean up storage state after tests."""
    yield
    # Cleanup any global storage state
    from storage import close_storage
    close_storage()
