"""Error handling and resilience utilities for the ivasms Telegram bot."""

import asyncio
import functools
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import structlog

from .storage import get_storage

logger = structlog.get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient operations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker half-open, attempting operation", function=func.__name__)
                else:
                    raise Exception(f"Circuit breaker OPEN for {func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True
        return datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == "HALF_OPEN":
            logger.info("Circuit breaker reset to CLOSED")
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("Circuit breaker OPEN", failure_count=self.failure_count)


class RetryManager:
    """Manages retry logic with exponential backoff and jitter."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def __call__(self, func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < self.max_attempts - 1:
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        # Add jitter
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                        
                        logger.warning(
                            "Retry attempt failed, retrying",
                            function=func.__name__,
                            attempt=attempt + 1,
                            delay=delay,
                            error=str(e)
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All retry attempts failed",
                            function=func.__name__,
                            attempts=self.max_attempts,
                            error=str(e)
                        )
            
            raise last_exception
        
        return wrapper


class ErrorTracker:
    """Tracks and analyzes errors for monitoring and alerting."""
    
    def __init__(self):
        self.storage = get_storage()
        self.error_window_hours = 24
        self.max_errors_per_hour = 10
    
    def record_error(self, error_type: str, error_message: str, context: str = "") -> None:
        """Record an error occurrence."""
        try:
            error_data = {
                "type": error_type,
                "message": error_message,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "traceback": traceback.format_exc()
            }
            
            # Store in a list of recent errors
            recent_errors = self.storage.get_state("recent_errors", [])
            recent_errors.append(error_data)
            
            # Keep only errors from the last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=self.error_window_hours)
            recent_errors = [
                err for err in recent_errors
                if datetime.fromisoformat(err["timestamp"]) > cutoff_time
            ]
            
            self.storage.set_state("recent_errors", recent_errors[-100:])  # Keep max 100 errors
            
            logger.error("Error recorded", error_type=error_type, context=context, message=error_message)
            
        except Exception as e:
            logger.error("Failed to record error", error=str(e))
    
    def get_error_rate(self) -> float:
        """Get current error rate (errors per hour)."""
        try:
            recent_errors = self.storage.get_state("recent_errors", [])
            
            # Count errors in the last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_count = sum(
                1 for err in recent_errors
                if datetime.fromisoformat(err["timestamp"]) > one_hour_ago
            )
            
            return recent_count
            
        except Exception as e:
            logger.error("Failed to calculate error rate", error=str(e))
            return 0.0
    
    def is_error_rate_high(self) -> bool:
        """Check if error rate is above threshold."""
        return self.get_error_rate() > self.max_errors_per_hour
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        try:
            recent_errors = self.storage.get_state("recent_errors", [])
            
            if not recent_errors:
                return {"total": 0, "types": {}, "recent_rate": 0.0}
            
            # Count by type
            error_types = {}
            for error in recent_errors:
                error_type = error.get("type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            return {
                "total": len(recent_errors),
                "types": error_types,
                "recent_rate": self.get_error_rate(),
                "last_error": recent_errors[-1] if recent_errors else None
            }
            
        except Exception as e:
            logger.error("Failed to get error summary", error=str(e))
            return {"total": 0, "types": {}, "recent_rate": 0.0}


class HealthChecker:
    """Monitors system health and component status."""
    
    def __init__(self):
        self.storage = get_storage()
        self.error_tracker = ErrorTracker()
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
            "metrics": {}
        }
        
        try:
            # Check database connectivity
            health_status["components"]["database"] = await self._check_database()
            
            # Check error rate
            error_rate = self.error_tracker.get_error_rate()
            health_status["components"]["error_rate"] = {
                "status": "unhealthy" if error_rate > 10 else "healthy",
                "rate": error_rate,
                "threshold": 10
            }
            
            # Check storage usage
            health_status["components"]["storage"] = await self._check_storage()
            
            # Check last successful operations
            health_status["components"]["operations"] = await self._check_operations()
            
            # Determine overall status
            component_statuses = [comp.get("status", "unknown") for comp in health_status["components"].values()]
            if "unhealthy" in component_statuses:
                health_status["overall_status"] = "unhealthy"
            elif "degraded" in component_statuses:
                health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            health_status["overall_status"] = "unhealthy"
            health_status["error"] = str(e)
            return health_status
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            # Test basic database operations
            test_key = f"health_check_{datetime.now().timestamp()}"
            self.storage.set_state(test_key, "test")
            value = self.storage.get_state(test_key)
            self.storage.delete_state(test_key)
            
            if value == "test":
                return {"status": "healthy", "message": "Database operations successful"}
            else:
                return {"status": "unhealthy", "message": "Database read/write test failed"}
                
        except Exception as e:
            return {"status": "unhealthy", "message": f"Database error: {str(e)}"}
    
    async def _check_storage(self) -> Dict[str, Any]:
        """Check storage usage and performance."""
        try:
            stats = self.storage.get_statistics()
            db_size_mb = stats.get("db_size_mb", 0)
            
            status = "healthy"
            if db_size_mb > 100:  # 100MB threshold
                status = "degraded"
            if db_size_mb > 500:  # 500MB threshold
                status = "unhealthy"
            
            return {
                "status": status,
                "size_mb": db_size_mb,
                "total_otps": stats.get("total_otps", 0),
                "message": f"Database size: {db_size_mb}MB"
            }
            
        except Exception as e:
            return {"status": "unhealthy", "message": f"Storage check error: {str(e)}"}
    
    async def _check_operations(self) -> Dict[str, Any]:
        """Check last successful operations."""
        try:
            last_login = self.storage.get_state("last_login_time")
            last_fetch = self.storage.get_state("last_fetch_time")
            
            status = "healthy"
            issues = []
            
            # Check last login (should be within last 24 hours)
            if last_login and last_login != "Never":
                try:
                    login_time = datetime.fromisoformat(last_login.replace("Never", "1970-01-01 00:00:00"))
                    if datetime.now() - login_time > timedelta(hours=24):
                        status = "degraded"
                        issues.append("Login older than 24 hours")
                except Exception:
                    pass
            
            # Check last fetch (should be within last hour)
            if last_fetch and last_fetch != "Never":
                try:
                    fetch_time = datetime.fromisoformat(last_fetch.replace("Never", "1970-01-01 00:00:00"))
                    if datetime.now() - fetch_time > timedelta(hours=1):
                        status = "degraded"
                        issues.append("Fetch older than 1 hour")
                except Exception:
                    pass
            
            return {
                "status": status,
                "last_login": last_login or "Never",
                "last_fetch": last_fetch or "Never",
                "issues": issues
            }
            
        except Exception as e:
            return {"status": "unhealthy", "message": f"Operations check error: {str(e)}"}


# Global instances
error_tracker = ErrorTracker()
health_checker = HealthChecker()


def handle_exception(error_type: str = "Unknown", context: str = ""):
    """Decorator to handle and track exceptions."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_tracker.record_error(
                    error_type=error_type or type(e).__name__,
                    error_message=str(e),
                    context=context or func.__name__
                )
                raise
        return wrapper
    return decorator


async def safe_execute(coro, default_value=None, log_errors: bool = True):
    """Safely execute a coroutine with error handling."""
    try:
        return await coro
    except Exception as e:
        if log_errors:
            logger.error("Safe execution failed", error=str(e), coro=str(coro))
        return default_value


def get_error_context() -> Dict[str, Any]:
    """Get current error context for debugging."""
    return {
        "error_rate": error_tracker.get_error_rate(),
        "error_summary": error_tracker.get_error_summary(),
        "timestamp": datetime.now().isoformat()
    }
