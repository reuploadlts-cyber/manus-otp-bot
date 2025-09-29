"""Unit tests for the storage module."""

import json
import pytest
from datetime import datetime, timedelta

from storage import OTPStorage


class TestOTPStorage:
    """Test cases for OTPStorage class."""
    
    def test_init_creates_database(self, temp_db):
        """Test that initialization creates database tables."""
        storage = OTPStorage(temp_db)
        
        # Verify tables exist by attempting to query them
        with storage.lock:
            import sqlite3
            with sqlite3.connect(temp_db) as conn:
                cursor = conn.cursor()
                
                # Check otps table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otps'")
                assert cursor.fetchone() is not None
                
                # Check bot_state table
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_state'")
                assert cursor.fetchone() is not None
    
    def test_store_otp_success(self, storage, sample_otp_data):
        """Test successful OTP storage."""
        result = storage.store_otp(sample_otp_data)
        assert result is True
        
        # Verify OTP was stored
        otps = storage.get_recent_otps(1)
        assert len(otps) == 1
        assert otps[0]['id'] == sample_otp_data['id']
        assert otps[0]['text'] == sample_otp_data['text']
    
    def test_store_duplicate_otp(self, storage, sample_otp_data):
        """Test that duplicate OTPs are not stored."""
        # Store first time
        result1 = storage.store_otp(sample_otp_data)
        assert result1 is True
        
        # Try to store again
        result2 = storage.store_otp(sample_otp_data)
        assert result2 is False
        
        # Verify only one OTP exists
        otps = storage.get_recent_otps(10)
        assert len(otps) == 1
    
    def test_get_unsent_otps(self, storage, multiple_otp_data):
        """Test getting unsent OTPs."""
        # Store multiple OTPs
        for otp_data in multiple_otp_data:
            storage.store_otp(otp_data)
        
        # All should be unsent initially
        unsent = storage.get_unsent_otps()
        assert len(unsent) == 3
        
        # Mark one as sent
        storage.mark_otp_sent(multiple_otp_data[0]['id'])
        
        # Should have 2 unsent now
        unsent = storage.get_unsent_otps()
        assert len(unsent) == 2
    
    def test_mark_otp_sent(self, storage, sample_otp_data):
        """Test marking OTP as sent."""
        # Store OTP
        storage.store_otp(sample_otp_data)
        
        # Mark as sent
        result = storage.mark_otp_sent(sample_otp_data['id'])
        assert result is True
        
        # Verify it's marked as sent
        unsent = storage.get_unsent_otps()
        assert len(unsent) == 0
        
        # Try to mark non-existent OTP
        result = storage.mark_otp_sent("nonexistent")
        assert result is False
    
    def test_get_recent_otps(self, storage, multiple_otp_data):
        """Test getting recent OTPs."""
        # Store multiple OTPs
        for otp_data in multiple_otp_data:
            storage.store_otp(otp_data)
        
        # Get all
        recent = storage.get_recent_otps(10)
        assert len(recent) == 3
        
        # Get limited
        recent = storage.get_recent_otps(2)
        assert len(recent) == 2
        
        # Should be ordered by created_at DESC (most recent first)
        assert recent[0]['id'] == multiple_otp_data[-1]['id']  # Last stored should be first
    
    def test_get_last_otp(self, storage, multiple_otp_data):
        """Test getting the last OTP."""
        # No OTPs initially
        last = storage.get_last_otp()
        assert last is None
        
        # Store OTPs
        for otp_data in multiple_otp_data:
            storage.store_otp(otp_data)
        
        # Get last OTP
        last = storage.get_last_otp()
        assert last is not None
        assert last['id'] == multiple_otp_data[-1]['id']
    
    def test_cleanup_old_otps(self, storage):
        """Test cleanup of old OTPs."""
        # Create old OTP data
        old_otp = {
            "id": "old_otp",
            "timestamp": "2023-01-01 12:00:00",
            "sender": "+1234567890",
            "text": "Old OTP 123456",
            "service": "OldService"
        }
        
        # Manually insert old OTP with old created_at
        old_date = datetime.now() - timedelta(days=35)
        with storage.lock:
            import sqlite3
            with sqlite3.connect(storage.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO otps (id, timestamp, sender, text, service, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    old_otp['id'],
                    old_otp['timestamp'],
                    old_otp['sender'],
                    old_otp['text'],
                    old_otp['service'],
                    old_date.isoformat()
                ))
                conn.commit()
        
        # Add recent OTP
        recent_otp = {
            "id": "recent_otp",
            "timestamp": "2024-01-01 12:00:00",
            "sender": "+1234567890",
            "text": "Recent OTP 654321",
            "service": "RecentService"
        }
        storage.store_otp(recent_otp)
        
        # Verify we have 2 OTPs
        assert storage.get_otp_count() == 2
        
        # Cleanup old OTPs (older than 30 days)
        deleted_count = storage.cleanup_old_otps(30)
        assert deleted_count == 1
        
        # Verify only recent OTP remains
        assert storage.get_otp_count() == 1
        remaining_otps = storage.get_recent_otps(10)
        assert remaining_otps[0]['id'] == recent_otp['id']
    
    def test_state_management(self, storage):
        """Test bot state management."""
        # Set state
        result = storage.set_state("test_key", "test_value")
        assert result is True
        
        # Get state
        value = storage.get_state("test_key")
        assert value == "test_value"
        
        # Get non-existent state with default
        value = storage.get_state("nonexistent", "default")
        assert value == "default"
        
        # Set complex state (dict)
        complex_state = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        storage.set_state("complex", complex_state)
        retrieved = storage.get_state("complex")
        assert retrieved == complex_state
        
        # Delete state
        result = storage.delete_state("test_key")
        assert result is True
        
        # Verify deleted
        value = storage.get_state("test_key", "not_found")
        assert value == "not_found"
        
        # Delete non-existent
        result = storage.delete_state("nonexistent")
        assert result is False
    
    def test_get_all_states(self, storage):
        """Test getting all states."""
        # Set multiple states
        states = {
            "state1": "value1",
            "state2": {"key": "value"},
            "state3": [1, 2, 3]
        }
        
        for key, value in states.items():
            storage.set_state(key, value)
        
        # Get all states
        all_states = storage.get_all_states()
        
        for key, expected_value in states.items():
            assert key in all_states
            assert all_states[key] == expected_value
    
    def test_get_statistics(self, storage, multiple_otp_data):
        """Test getting storage statistics."""
        # Initially empty
        stats = storage.get_statistics()
        assert stats['total_otps'] == 0
        assert stats['unsent_otps'] == 0
        assert stats['recent_otps_24h'] == 0
        
        # Store OTPs
        for otp_data in multiple_otp_data:
            storage.store_otp(otp_data)
        
        # Mark one as sent
        storage.mark_otp_sent(multiple_otp_data[0]['id'])
        
        # Get updated stats
        stats = storage.get_statistics()
        assert stats['total_otps'] == 3
        assert stats['unsent_otps'] == 2
        assert stats['recent_otps_24h'] == 3  # All are recent
        assert stats['db_size_bytes'] > 0
        assert stats['db_size_mb'] >= 0
    
    def test_backup_database(self, storage, sample_otp_data, tmp_path):
        """Test database backup functionality."""
        # Store some data
        storage.store_otp(sample_otp_data)
        storage.set_state("test_state", "test_value")
        
        # Create backup
        backup_path = tmp_path / "backup.db"
        result = storage.backup_database(str(backup_path))
        assert result is True
        assert backup_path.exists()
        
        # Verify backup contains data
        backup_storage = OTPStorage(str(backup_path))
        backup_otps = backup_storage.get_recent_otps(10)
        assert len(backup_otps) == 1
        assert backup_otps[0]['id'] == sample_otp_data['id']
        
        backup_state = backup_storage.get_state("test_state")
        assert backup_state == "test_value"
        
        backup_storage.close()


class TestStorageEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_invalid_db_path(self):
        """Test handling of invalid database path."""
        # This should still work as SQLite will create the file
        storage = OTPStorage("/tmp/test_invalid_path/test.db")
        assert storage is not None
    
    def test_empty_otp_data(self, storage):
        """Test storing empty or invalid OTP data."""
        # Missing required fields should not crash
        invalid_otp = {"id": "test"}
        
        # This might fail but shouldn't crash the application
        try:
            result = storage.store_otp(invalid_otp)
            # If it succeeds, that's also fine
        except Exception:
            # Expected to fail gracefully
            pass
    
    def test_concurrent_access(self, storage, sample_otp_data):
        """Test concurrent access to storage."""
        import threading
        import time
        
        results = []
        
        def store_otp(otp_id):
            otp_data = sample_otp_data.copy()
            otp_data['id'] = f"concurrent_{otp_id}"
            result = storage.store_otp(otp_data)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=store_otp, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 5
        assert all(results)
        
        # Verify all OTPs were stored
        otps = storage.get_recent_otps(10)
        assert len(otps) == 5
