"""Tests for monitor functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.monitor import IVASMSMonitor
from src.storage import Storage, SMSMessage


class TestIVASMSMonitor:
    """Test IVASMS monitor functionality."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock storage."""
        return MagicMock(spec=Storage)
    
    @pytest.fixture
    def monitor(self, mock_storage):
        """Create monitor instance with mock storage."""
        return IVASMSMonitor(mock_storage)
    
    @pytest.mark.asyncio
    async def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.storage is not None
        assert monitor.browser is None
        assert monitor.is_logged_in is False
        assert monitor.is_monitoring is False
    
    @pytest.mark.asyncio
    async def test_login_success(self, monitor):
        """Test successful login."""
        with patch('src.monitor.async_playwright') as mock_playwright:
            # Mock playwright objects
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.start.return_value = AsyncMock()
            mock_playwright.return_value.start.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock page interactions
            mock_page.goto = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()
            mock_page.fill = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.url = "https://www.ivasms.com/dashboard"
            
            # Mock popup handling
            with patch.object(monitor, '_handle_popup', return_value=True):
                result = await monitor.start()
                
                assert result is True
                assert monitor.is_logged_in is True
                assert monitor.browser is not None
    
    @pytest.mark.asyncio
    async def test_login_failure(self, monitor):
        """Test login failure."""
        with patch('src.monitor.async_playwright') as mock_playwright:
            # Mock playwright objects
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.start.return_value = AsyncMock()
            mock_playwright.return_value.start.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock page interactions to fail
            mock_page.goto = AsyncMock(side_effect=Exception("Network error"))
            
            result = await monitor.start()
            
            assert result is False
            assert monitor.is_logged_in is False
    
    @pytest.mark.asyncio
    async def test_popup_handling(self, monitor):
        """Test popup handling."""
        mock_page = AsyncMock()
        monitor.page = mock_page
        
        # Mock popup elements
        mock_next_button = AsyncMock()
        mock_done_button = AsyncMock()
        
        mock_page.locator.return_value = mock_next_button
        mock_next_button.count.return_value = 1
        mock_next_button.click = AsyncMock()
        
        # First call returns next button, second call returns done button
        mock_page.locator.side_effect = [
            mock_next_button,  # Next button
            mock_done_button   # Done button
        ]
        mock_done_button.count.return_value = 1
        mock_done_button.click = AsyncMock()
        
        result = await monitor._handle_popup()
        
        assert result is True
        mock_next_button.click.assert_called_once()
        mock_done_button.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_messages(self, monitor):
        """Test message scraping."""
        mock_page = AsyncMock()
        monitor.page = mock_page
        
        # Mock message elements
        mock_row = AsyncMock()
        mock_sender = AsyncMock()
        mock_body = AsyncMock()
        mock_time = AsyncMock()
        
        mock_sender.text_content.return_value = "+1234567890"
        mock_body.text_content.return_value = "Your code is 123456"
        mock_time.text_content.return_value = "2025-01-01 12:00:00"
        
        mock_row.locator.side_effect = [
            mock_sender,  # sender
            mock_body,    # message body
            mock_time     # timestamp
        ]
        
        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator.return_value.all.return_value = [mock_row]
        
        messages = await monitor._scrape_messages()
        
        assert len(messages) == 1
        assert messages[0].sender == "+1234567890"
        assert messages[0].message == "Your code is 123456"
    
    @pytest.mark.asyncio
    async def test_cleanup(self, monitor):
        """Test cleanup functionality."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        
        monitor.browser = mock_browser
        monitor.context = mock_context
        monitor.is_monitoring = True
        
        await monitor.cleanup()
        
        assert monitor.is_monitoring is False
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
