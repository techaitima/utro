"""
API Safety Service for Utro Bot v3.0
Provides rate limiting, timeouts, retries, and circuit breaker protection.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_per_user_per_hour: int = 50
    max_global_per_minute: int = 20
    timeout_seconds: float = 30.0
    max_retries: int = 3
    base_retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 300.0  # 5 minutes


class RequestCounter:
    """Tracks request counts with time-based expiration."""
    
    def __init__(self):
        self._user_requests: Dict[int, list] = defaultdict(list)
        self._global_requests: list = []
        self._lock = asyncio.Lock()
    
    async def add_request(self, user_id: Optional[int] = None) -> None:
        """Record a new request."""
        async with self._lock:
            now = time.time()
            self._global_requests.append(now)
            if user_id:
                self._user_requests[user_id].append(now)
    
    async def get_user_count_last_hour(self, user_id: int) -> int:
        """Get user's request count in the last hour."""
        async with self._lock:
            now = time.time()
            hour_ago = now - 3600
            # Clean old entries
            self._user_requests[user_id] = [
                t for t in self._user_requests[user_id] if t > hour_ago
            ]
            return len(self._user_requests[user_id])
    
    async def get_global_count_last_minute(self) -> int:
        """Get global request count in the last minute."""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60
            # Clean old entries
            self._global_requests = [
                t for t in self._global_requests if t > minute_ago
            ]
            return len(self._global_requests)


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, threshold: int = 5, timeout: float = 300.0):
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.is_open = False
        self._lock = asyncio.Lock()
    
    async def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.threshold:
                self.is_open = True
                logger.warning(
                    f"Circuit breaker OPENED after {self.failure_count} failures. "
                    f"Will retry in {self.timeout}s"
                )
    
    async def record_success(self) -> None:
        """Record a success and reset the counter."""
        async with self._lock:
            self.failure_count = 0
            self.is_open = False
    
    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            if not self.is_open:
                return True
            
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.timeout:
                    logger.info("Circuit breaker timeout passed, allowing retry")
                    self.is_open = False
                    self.failure_count = 0
                    return True
            
            return False
    
    async def get_retry_after(self) -> float:
        """Get seconds until circuit closes."""
        async with self._lock:
            if not self.is_open or not self.last_failure_time:
                return 0
            elapsed = time.time() - self.last_failure_time
            return max(0, self.timeout - elapsed)


class APIRateLimiter:
    """
    Rate limiter for API calls.
    Combines request counting, circuit breaker, and provides decorators.
    """
    
    def __init__(self, name: str, config: Optional[RateLimitConfig] = None):
        self.name = name
        self.config = config or RateLimitConfig()
        self.counter = RequestCounter()
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout
        )
    
    async def check_limits(self, user_id: Optional[int] = None) -> tuple[bool, str]:
        """
        Check if request is allowed.
        
        Returns:
            Tuple of (allowed: bool, error_message: str)
        """
        # Check circuit breaker first
        if not await self.circuit_breaker.can_execute():
            retry_after = await self.circuit_breaker.get_retry_after()
            return False, f"Сервис временно недоступен. Повторите через {int(retry_after)}с"
        
        # Check global rate limit
        global_count = await self.counter.get_global_count_last_minute()
        if global_count >= self.config.max_global_per_minute:
            return False, "Слишком много запросов. Подождите минуту."
        
        # Check user rate limit
        if user_id:
            user_count = await self.counter.get_user_count_last_hour(user_id)
            if user_count >= self.config.max_per_user_per_hour:
                return False, "Превышен лимит запросов (50/час). Попробуйте позже."
        
        return True, ""
    
    async def record_request(self, user_id: Optional[int] = None) -> None:
        """Record a successful request."""
        await self.counter.add_request(user_id)
        await self.circuit_breaker.record_success()
    
    async def record_failure(self) -> None:
        """Record a failed request."""
        await self.circuit_breaker.record_failure()


# Global rate limiters for each API
_rate_limiters: Dict[str, APIRateLimiter] = {}


def get_rate_limiter(name: str) -> APIRateLimiter:
    """Get or create a rate limiter for the specified API."""
    if name not in _rate_limiters:
        _rate_limiters[name] = APIRateLimiter(name)
    return _rate_limiters[name]


# Global rate limiter instance for easy access
api_rate_limiter = get_rate_limiter("global")


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


class APITimeoutError(Exception):
    """Raised when API call times out."""
    pass


def with_timeout(timeout_seconds: float = 30.0):
    """
    Decorator that adds timeout to async functions.
    
    Args:
        timeout_seconds: Maximum time to wait for the function
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout after {timeout_seconds}s in {func.__name__}")
                raise APITimeoutError(f"Превышено время ожидания ({timeout_seconds}с)")
        return wrapper
    return decorator


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential: bool = True
):
    """
    Decorator that adds retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        exponential: Whether to use exponential backoff
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (APITimeoutError, CircuitBreakerOpen, RateLimitExceeded):
                    # Don't retry these
                    raise
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1)) if exponential else base_delay
                        logger.warning(
                            f"Attempt {attempt}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        return wrapper
    return decorator


def with_rate_limit(limiter_name: str, user_id_param: Optional[str] = None):
    """
    Decorator that adds rate limiting to async functions.
    
    Args:
        limiter_name: Name of the rate limiter to use
        user_id_param: Name of the parameter containing user_id (if any)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            limiter = get_rate_limiter(limiter_name)
            
            # Extract user_id if specified
            user_id = None
            if user_id_param and user_id_param in kwargs:
                user_id = kwargs[user_id_param]
            
            # Check limits
            allowed, error_msg = await limiter.check_limits(user_id)
            if not allowed:
                raise RateLimitExceeded(error_msg)
            
            try:
                result = await func(*args, **kwargs)
                await limiter.record_request(user_id)
                return result
            except Exception as e:
                await limiter.record_failure()
                raise
        return wrapper
    return decorator


def safe_api_call(
    limiter_name: str,
    timeout: float = 30.0,
    max_retries: int = 3,
    user_id_param: Optional[str] = None
):
    """
    Combined decorator for safe API calls.
    Applies rate limiting, timeout, and retry with backoff.
    
    Args:
        limiter_name: Name of the rate limiter
        timeout: Timeout in seconds
        max_retries: Maximum retry attempts
        user_id_param: Parameter name for user_id
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Apply decorators in order: rate_limit -> timeout -> retry
        decorated = with_rate_limit(limiter_name, user_id_param)(func)
        decorated = with_timeout(timeout)(decorated)
        decorated = with_retry(max_retries)(decorated)
        return decorated
    return decorator


# Utility function for getting limiter stats
async def get_api_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all API rate limiters."""
    stats = {}
    for name, limiter in _rate_limiters.items():
        global_count = await limiter.counter.get_global_count_last_minute()
        stats[name] = {
            "global_requests_last_minute": global_count,
            "circuit_breaker_open": limiter.circuit_breaker.is_open,
            "failure_count": limiter.circuit_breaker.failure_count
        }
    return stats
