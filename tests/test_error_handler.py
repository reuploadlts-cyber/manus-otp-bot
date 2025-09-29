"""Tests for error handling and resilience features."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from error_handler import (
    CircuitBreaker,
    RetryManager,
    ErrorTracker,
    HealthChecker,
    handle_exception,
    safe_execute,
    get_error_context
)


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in CLOSED state."""
        @CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        async def test_function():
            return "success"
        
        # Should work normally in CLOSED state
        result = await test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        call_count = 0
        
        @CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")
        
        # First failure
        with pytest.raises(ValueError):
            await failing_function()
        
        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await failing_function()
        
        # Third call should fail due to open circuit
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await failing_function()
        
        # Should not have called the function the third time
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through HALF_OPEN state."""
        call_count = 0
        should_fail = True
        
        @CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        async def conditional_function():
            nonlocal call_count, should_fail
            call_count += 1
            if should_fail:
                raise ValueError("Test error")
            return "success"
        
        # Cause failure to open circuit
        with pytest.raises(ValueError):
            await conditional_function()
        
        # Should be open now
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await conditional_function()
        
        # Wait for recovery timeout
        await asyncio.sleep(0.2)
        
        # Fix the function and try again
        should_fail = False
        result = await conditional_function()
        
        # Should succeed and reset circuit
        assert result == "success"
        assert call_count == 2  # One failure + one success


class TestRetryManager:
    """Test RetryManager functionality."""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt."""
        call_count = 0
        
        @RetryManager(max_attempts=3, base_delay=0.01)
        async def success_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_function()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        call_count = 0
        
        @RetryManager(max_attempts=3, base_delay=0.01)
        async def eventually_success_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await eventually_success_function()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        """Test retry exhaustion."""
        call_count = 0
        
        @RetryManager(max_attempts=2, base_delay=0.01)
        async def always_fail_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")
        
        with pytest.raises(ValueError, match="Persistent error"):
            await always_fail_function()
        
        assert call_count == 2


class TestErrorTracker:
    """Test ErrorTracker functionality."""
    
    @pytest.fixture
    def error_tracker(self, storage):
        """Create error tracker with test storage."""
        tracker = ErrorTracker()
        tracker.storage = storage
        return tracker
    
    def test_record_error(self, error_tracker):
        """Test error recording."""
        error_tracker.record_error("TestError", "Test message", "test_context")
        
        recent_errors = error_tracker.storage.get_state("recent_errors", [])
        assert len(recent_errors) == 1
        
        error = recent_errors[0]
        assert error["type"] == "TestError"
        assert error["message"] == "Test message"
        assert error["context"] == "test_context"
        assert "timestamp" in error
        assert "traceback" in error
    
    def test_get_error_rate(self, error_tracker):
        """Test error rate calculation."""
        # Initially should be 0
        assert error_tracker.get_error_rate() == 0.0
        
        # Record some errors
        for i in range(3):
            error_tracker.record_error("TestError", f"Error {i}")
        
        # Should return 3 (3 errors in last hour)
        assert error_tracker.get_error_rate() == 3.0
    
    def test_is_error_rate_high(self, error_tracker):
        """Test error rate threshold checking."""
        # Initially should be low
        assert error_tracker.is_error_rate_high() is False
        
        # Record many errors
        for i in range(15):
            error_tracker.record_error("TestError", f"Error {i}")
        
        # Should be high now
        assert error_tracker.is_error_rate_high() is True
    
    def test_get_error_summary(self, error_tracker):
        """Test error summary generation."""
        # Record different types of errors
        error_tracker.record_error("TypeError", "Type error message")
        error_tracker.record_error("ValueError", "Value error message")
        error_tracker.record_error("TypeError", "Another type error")
        
        summary = error_tracker.get_error_summary()
        
        assert summary["total"] == 3
        assert summary["types"]["TypeError"] == 2
        assert summary["types"]["ValueError"] == 1
        assert summary["recent_rate"] == 3.0
        assert summary["last_error"]["type"] == "TypeError"


class TestHealthChecker:
    """Test HealthChecker functionality."""
    
    @pytest.fixture
    def health_checker(self, storage):
        """Create health checker with test storage."""
        checker = HealthChecker()
        checker.storage = storage
        return checker
    
    @pytest.mark.asyncio
    async def test_check_system_health_healthy(self, health_checker):
        """Test system health check when everything is healthy."""
        health_status = await health_checker.check_system_health()
        
        assert "timestamp" in health_status
        assert health_status["overall_status"] in ["healthy", "degraded"]  # Might be degraded due to no operations
        assert "components" in health_status
        assert "database" in health_status["components"]
        assert health_status["components"]["database"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_check_database_health(self, health_checker):
        """Test database health check."""
        db_health = await health_checker._check_database()
        
        assert db_health["status"] == "healthy"
        assert "Database operations successful" in db_health["message"]
    
    @pytest.mark.asyncio
    async def test_check_storage_health(self, health_checker, multiple_otp_data):
        """Test storage health check."""
        # Add some data
        for otp_data in multiple_otp_data:
            health_checker.storage.store_otp(otp_data)
        
        storage_health = await health_checker._check_storage()
        
        assert storage_health["status"] == "healthy"  # Should be healthy with small DB
        assert storage_health["total_otps"] == 3
        assert storage_health["size_mb"] >= 0
    
    @pytest.mark.asyncio
    async def test_check_operations_health(self, health_checker):
        """Test operations health check."""
        # Set some operation times
        health_checker.storage.set_state("last_login_time", datetime.now().isoformat())
        health_checker.storage.set_state("last_fetch_time", datetime.now().isoformat())
        
        ops_health = await health_checker._check_operations()
        
        assert ops_health["status"] == "healthy"
        assert ops_health["last_login"] != "Never"
        assert ops_health["last_fetch"] != "Never"


class TestDecoratorsAndUtilities:
    """Test decorators and utility functions."""
    
    @pytest.mark.asyncio
    async def test_handle_exception_decorator(self, storage):
        """Test handle_exception decorator."""
        with patch('error_handler.error_tracker') as mock_tracker:
            @handle_exception("TestError", "test_context")
            async def failing_function():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError):
                await failing_function()
            
            # Should have recorded the error
            mock_tracker.record_error.assert_called_once_with(
                error_type="TestError",
                error_message="Test error",
                context="test_context"
            )
    
    @pytest.mark.asyncio
    async def test_safe_execute_success(self):
        """Test safe_execute with successful coroutine."""
        async def success_coro():
            return "success"
        
        result = await safe_execute(success_coro())
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_safe_execute_failure(self):
        """Test safe_execute with failing coroutine."""
        async def failing_coro():
            raise ValueError("Test error")
        
        result = await safe_execute(failing_coro(), default_value="default")
        assert result == "default"
    
    @pytest.mark.asyncio
    async def test_safe_execute_no_logging(self):
        """Test safe_execute with logging disabled."""
        async def failing_coro():
            raise ValueError("Test error")
        
        with patch('error_handler.logger') as mock_logger:
            result = await safe_execute(failing_coro(), log_errors=False)
            assert result is None
            mock_logger.error.assert_not_called()
    
    def test_get_error_context(self):
        """Test get_error_context function."""
        with patch('error_handler.error_tracker') as mock_tracker:
            mock_tracker.get_error_rate.return_value = 5.0
            mock_tracker.get_error_summary.return_value = {"total": 10}
            
            context = get_error_context()
            
            assert context["error_rate"] == 5.0
            assert context["error_summary"]["total"] == 10
            assert "timestamp" in context


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self):
        """Test circuit breaker combined with retry manager."""
        call_count = 0
        
        @CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        @RetryManager(max_attempts=2, base_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 4:  # Fail first 4 attempts
                raise ValueError("Flaky error")
            return "success"
        
        # First call: retry 2 times, both fail
        with pytest.raises(ValueError):
            await flaky_function()
        assert call_count == 2
        
        # Second call: retry 2 times, both fail (total 4 failures)
        with pytest.raises(ValueError):
            await flaky_function()
        assert call_count == 4
        
        # Third call: should be blocked by circuit breaker
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await flaky_function()
        assert call_count == 4  # No additional calls
    
    @pytest.mark.asyncio
    async def test_error_tracking_with_decorators(self, storage):
        """Test error tracking integration with decorators."""
        error_tracker = ErrorTracker()
        error_tracker.storage = storage
        
        with patch('error_handler.error_tracker', error_tracker):
            @handle_exception("IntegrationError", "integration_test")
            @RetryManager(max_attempts=2, base_delay=0.01)
            async def tracked_function():
                raise ValueError("Tracked error")
            
            with pytest.raises(ValueError):
                await tracked_function()
            
            # Should have recorded errors from both retry attempts
            recent_errors = error_tracker.storage.get_state("recent_errors", [])
            assert len(recent_errors) == 2  # One for each retry attempt
            
            for error in recent_errors:
                assert error["type"] == "IntegrationError"
                assert error["context"] == "integration_test"
