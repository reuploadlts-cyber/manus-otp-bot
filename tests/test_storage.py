"""Tests for storage management."""

import pytest
import tempfile
import os
from datetime import datetime
from src.storage import Storage, SMSMessage


class TestSMSMessage:
    """Test SMS message data structure."""
    
    def test_sms_message_creation(self):
        """Test SMS message creation."""
        sms = SMSMessage(
            id="test_id",
            sender="+1234567890",
            message="Your code is 123456",
            timestamp="2025-01-01 12:00:00",
            received_at="2025-01-01T12:00:00"
        )
        
        assert sms.id == "test_id"
        assert sms.sender == "+1234567890"
        assert sms.message == "Your code is 123456"
        assert sms.forwarded is False
    
    def test_sms_message_to_dict(self):
        """Test SMS message to dictionary conversion."""
        sms = SMSMessage(
            id="test_id",
            sender="+1234567890",
            message="Your code is 123456",
            timestamp="2025-01-01 12:00:00",
            received_at="2025-01-01T12:00:00"
        )
        
        data = sms.to_dict()
        assert data['id'] == "test_id"
        assert data['sender'] == "+1234567890"
        assert data['forwarded'] is False
    
    def test_sms_message_from_dict(self):
        """Test SMS message creation from dictionary."""
        data = {
            'id': 'test_id',
            'sender': '+1234567890',
            'message': 'Your code is 123456',
            'timestamp': '2025-01-01 12:00:00',
            'received_at': '2025-01-01T12:00:00',
            'forwarded': True
        }
        
        sms = SMSMessage.from_dict(data)
        assert sms.id == "test_id"
        assert sms.forwarded is True


class TestStorage:
    """Test storage functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        storage = Storage(db_path)
        yield storage
        
        # Cleanup
        os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_save_sms(self, temp_db):
        """Test saving SMS message."""
        sms = SMSMessage(
            id="test_id",
            sender="+1234567890",
            message="Your code is 123456",
            timestamp="2025-01-01 12:00:00",
            received_at="2025-01-01T12:00:00"
        )
        
        result = await temp_db.save_sms(sms)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_recent_sms(self, temp_db):
        """Test getting recent SMS messages."""
        # Save test messages
        for i in range(5):
            sms = SMSMessage(
                id=f"test_id_{i}",
                sender=f"+123456789{i}",
                message=f"Test message {i}",
                timestamp=f"2025-01-01 12:0{i}:00",
                received_at=f"2025-01-01T12:0{i}:00"
            )
            await temp_db.save_sms(sms)
        
        # Get recent messages
        messages = await temp_db.get_recent_sms(3)
        assert len(messages) == 3
        assert messages[0].id == "test_id_4"  # Most recent first
    
    @pytest.mark.asyncio
    async def test_get_last_sms(self, temp_db):
        """Test getting last SMS message."""
        # Save test message
        sms = SMSMessage(
            id="test_id",
            sender="+1234567890",
            message="Test message",
            timestamp="2025-01-01 12:00:00",
            received_at="2025-01-01T12:00:00"
        )
        await temp_db.save_sms(sms)
        
        # Get last message
        last_sms = await temp_db.get_last_sms()
        assert last_sms is not None
        assert last_sms.id == "test_id"
    
    @pytest.mark.asyncio
    async def test_mark_forwarded(self, temp_db):
        """Test marking SMS as forwarded."""
        # Save test message
        sms = SMSMessage(
            id="test_id",
            sender="+1234567890",
            message="Test message",
            timestamp="2025-01-01 12:00:00",
            received_at="2025-01-01T12:00:00"
        )
        await temp_db.save_sms(sms)
        
        # Mark as forwarded
        result = await temp_db.mark_forwarded("test_id")
        assert result is True
        
        # Check if marked
        messages = await temp_db.get_recent_sms(1)
        assert messages[0].forwarded is True
    
    @pytest.mark.asyncio
    async def test_state_management(self, temp_db):
        """Test bot state management."""
        # Set state
        result = await temp_db.set_state("test_key", "test_value")
        assert result is True
        
        # Get state
        value = await temp_db.get_state("test_key")
        assert value == "test_value"
        
        # Get non-existent state
        value = await temp_db.get_state("non_existent")
        assert value is None
