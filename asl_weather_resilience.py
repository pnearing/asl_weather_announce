"""
Resilience Module for ASL Weather Announce

This module provides resilience patterns for external API calls including:
- Exponential backoff for failed requests
- Circuit breaker pattern to prevent cascading failures
- Metrics collection for API usage and response times

Usage:
    from resilience import with_backoff, CircuitBreaker, APIMetrics
    
    # Using exponential backoff decorator
    @with_backoff(max_retries=3, base_delay=1.0)
    def make_api_call():
        return requests.get(url)
    
    # Using circuit breaker
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    result = breaker.call(make_api_call)
    
    # Using metrics
    metrics = APIMetrics()
    with metrics.measure("open-meteo"):
        response = requests.get(url)
"""

__version__ = "1.0.0"
__author__ = "Peter Nearing"
__email__ = "me@peternearing.ca"

import functools
import logging
import random
import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, TypeVar

# Type variable for generic return type
T = TypeVar('T')

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests pass through
    OPEN = "open"          # Failure threshold reached - requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class RetryConfig:
    """Configuration for exponential backoff retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: float = 0.1  # Add random jitter to prevent thundering herd
    retryable_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 1
    success_threshold: int = 1  # consecutive successes to close circuit


@dataclass
class APICallMetricsData:
    """Metrics for a single API call."""
    service_name: str
    endpoint: str
    start_time: float
    end_time: float = 0.0
    success: bool = False
    error_type: Optional[str] = None
    status_code: Optional[int] = None

    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        return (self.end_time - self.start_time) * 1000


class APICallMetrics:
    """
    Collect metrics for API calls.
    
    Tracks total calls, successes, failures, and response times.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self._total_calls = 0
        self._success_count = 0
        self._failure_count = 0
        self._response_times = deque(maxlen=1000)
        self._lock = threading.RLock()
    
    @property
    def total_calls(self) -> int:
        """Get total number of calls."""
        with self._lock:
            return self._total_calls
    
    @property
    def success_count(self) -> int:
        """Get number of successful calls."""
        with self._lock:
            return self._success_count
    
    @property
    def failure_count(self) -> int:
        """Get number of failed calls."""
        with self._lock:
            return self._failure_count
    
    @property
    def success_rate(self) -> float:
        """Get success rate (0.0 to 1.0)."""
        with self._lock:
            if self._total_calls == 0:
                return 1.0
            return self._success_count / self._total_calls
    
    @property
    def average_response_time(self) -> float:
        """Get average response time."""
        with self._lock:
            if not self._response_times:
                return 0.0
            return sum(self._response_times) / len(self._response_times)
    
    def record_success(self, response_time: float) -> None:
        """Record a successful call."""
        with self._lock:
            self._total_calls += 1
            self._success_count += 1
            self._response_times.append(response_time)
    
    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._total_calls += 1
            self._failure_count += 1
            self._response_times.append(0.0)  # Failures count as 0 response time for averaging
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics dictionary."""
        with self._lock:
            return {
                "total": self._total_calls,
                "successes": self._success_count,
                "failures": self._failure_count,
                "success_rate": self.success_rate,
                "avg_response_time": self.average_response_time,
            }


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external service calls.
    
    Prevents cascading failures by temporarily disabling calls to a service
    that is experiencing high error rates, allowing it time to recover.
    
    States:
        CLOSED: Normal operation, requests pass through
        OPEN: Failure threshold reached, requests fail fast without calling service
        HALF_OPEN: Testing if service has recovered with limited requests
    
    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        try:
            result = breaker.call(make_api_call)
        except CircuitBreakerOpenError:
            # Service is down, use fallback
            pass
    """
    
    def __init__(
        self,
        name: str = "default",
        config: Optional[CircuitBreakerConfig] = None,
        logger_instance: Optional[logging.Logger] = None,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker (for logging/metrics)
            config: Circuit breaker configuration
            logger_instance: Optional logger instance
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = logger_instance or logger
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = threading.RLock()
    
    @property
    def state(self) -> str:
        """Get current circuit state as string."""
        with self._lock:
            return self._state.name
    
    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        with self._lock:
            return self._failure_count
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result from function call
            
        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Any exception from the wrapped function
        """
        with self._lock:
            self._update_state()
            
            if self._state == CircuitState.OPEN:
                self.logger.warning(
                    f"Circuit breaker '{self.name}' is OPEN - failing fast"
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open - service unavailable"
                )
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self.logger.warning(
                        f"Circuit breaker '{self.name}' half-open max calls reached"
                    )
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is half-open - too many test calls"
                    )
                self._half_open_calls += 1
        
        # Execute the call outside the lock
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _update_state(self) -> None:
        """Update circuit state based on time and failure count."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    self.logger.info(
                        f"Circuit breaker '{self.name}' transitioning to HALF_OPEN"
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self._success_count = 0
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self.logger.info(
                        f"Circuit breaker '{self.name}' transitioning to CLOSED"
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._half_open_calls = 0
            else:
                # In CLOSED state, reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
                    self._success_count = 0
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Transition back to OPEN immediately on failure in HALF_OPEN
                self.logger.warning(
                    f"Circuit breaker '{self.name}' transitioning to OPEN "
                    f"(failure in half-open state)"
                )
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.config.failure_threshold:
                self.logger.warning(
                    f"Circuit breaker '{self.name}' transitioning to OPEN "
                    f"({self._failure_count} failures)"
                )
                self._state = CircuitState.OPEN
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.name,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "half_open_max_calls": self.config.half_open_max_calls,
                    "success_threshold": self.config.success_threshold,
                },
            }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class APIMetrics:
    """
    Collect and report metrics for API calls.
    
    Tracks response times, success rates, and error patterns for
    external API services.
    
    Example:
        metrics = APIMetrics()
        
        # Context manager for automatic timing
        with metrics.measure("open-meteo", "forecast"):
            response = requests.get(url)
        
        # Manual recording
        metrics.record_call("zippopotam", "lookup", 0.5, True)
        
        # Get statistics
        stats = metrics.get_stats()
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of call records to keep per service
        """
        self.max_history = max_history
        self._metrics: Dict[str, Deque[APICallMetricsData]] = {}
        self._lock = threading.RLock()
    
    def measure(
        self,
        service_name: str,
        endpoint: str = "default"
    ) -> "MetricsContext":
        """
        Create a context manager for measuring API call metrics.
        
        Args:
            service_name: Name of the service (e.g., "open-meteo")
            endpoint: Name of the endpoint (e.g., "forecast")
            
        Returns:
            MetricsContext context manager
        """
        return MetricsContext(self, service_name, endpoint)
    
    def record_call(
        self,
        service_name: str,
        endpoint: str,
        response_time: float,
        success: bool,
    ) -> None:
        """
        Record an API call metric.
        
        Args:
            service_name: Name of the service
            endpoint: Name of the endpoint
            response_time: Duration of the call in seconds
            success: Whether the call succeeded
        """
        key = f"{service_name}:{endpoint}"
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = deque(maxlen=self.max_history)
            self._metrics[key].append({
                "response_time": response_time,
                "success": success,
            })
    
    def record(
        self,
        service_name: str,
        endpoint: str,
        duration: float,
        success: bool,
        error_type: Optional[str] = None,
        status_code: Optional[int] = None,
        start_time: Optional[float] = None,
    ) -> None:
        """
        Record an API call metric (legacy method, calls record_call).
        
        Args:
            service_name: Name of the service
            endpoint: Name of the endpoint
            duration: Duration of the call in seconds
            success: Whether the call succeeded
            error_type: Type of error if failed
            status_code: HTTP status code if applicable
            start_time: Start time of the call (defaults to now - duration)
        """
        self.record_call(service_name, endpoint, duration, success)
    
    def get_stats(
        self,
        service_name: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics for API calls.
        
        Args:
            service_name: Filter by service name (None for all)
            endpoint: Filter by endpoint (None for all)
            
        Returns:
            Dictionary with statistics in format expected by tests
        """
        with self._lock:
            result: Dict[str, Any] = {}
            
            for key, queue in self._metrics.items():
                key_service, key_endpoint = key.split(":", 1)
                
                if service_name and key_service != service_name:
                    continue
                if endpoint and key_endpoint != endpoint:
                    continue
                
                if key_service not in result:
                    result[key_service] = {}
                
                total = len(queue)
                successes = sum(1 for m in queue if m.get("success", False))
                failures = total - successes
                response_times = [m.get("response_time", 0) for m in queue]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                result[key_service][key_endpoint] = {
                    "total": total,
                    "successes": successes,
                    "failures": failures,
                    "avg_response_time": avg_response_time,
                }
            
            return result
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all service statistics."""
        return self.get_stats()
    
    def get_statistics(
        self,
        service_name: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics for API calls (legacy method).
        
        Args:
            service_name: Filter by service name (None for all)
            endpoint: Filter by endpoint (None for all)
            
        Returns:
            Dictionary with statistics
        """
        stats = self.get_stats(service_name, endpoint)
        
        # Flatten stats for legacy format
        total_calls = 0
        successful_calls = 0
        failed_calls = 0
        
        for service_data in stats.values():
            for endpoint_data in service_data.values():
                total_calls += endpoint_data["total"]
                successful_calls += endpoint_data["successes"]
                failed_calls += endpoint_data["failures"]
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0.0,
            "avg_response_time_ms": 0.0,
            "min_response_time_ms": 0.0,
            "max_response_time_ms": 0.0,
            "p95_response_time_ms": 0.0,
            "p99_response_time_ms": 0.0,
        }
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_error_summary(self, service_name: Optional[str] = None) -> Dict[str, int]:
        """
        Get summary of error types.
        
        Args:
            service_name: Filter by service name (None for all)
            
        Returns:
            Dictionary mapping error types to counts
        """
        return {}


class MetricsContext:
    """Context manager for measuring API call metrics."""
    
    def __init__(
        self,
        metrics: APIMetrics,
        service_name: str,
        endpoint: str,
    ):
        self.metrics = metrics
        self.service_name = service_name
        self.endpoint = endpoint
        self.start_time: float = 0.0
        self.success: bool = False
        self.error_type: Optional[str] = None
        self.status_code: Optional[int] = None
    
    def __enter__(self) -> "MetricsContext":
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.success = True
        else:
            self.success = False
            self.error_type = exc_type.__name__ if exc_type else None
        
        self.metrics.record_call(
            service_name=self.service_name,
            endpoint=self.endpoint,
            response_time=duration,
            success=self.success,
        )


def with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator to add exponential backoff retry logic to a function.
    
    Args:
        config: Retry configuration (uses defaults if not provided)
        
    Returns:
        Decorator function
        
    Example:
        @with_backoff(RetryConfig(max_retries=3, base_delay=1.0))
        def make_request():
            return requests.get(url)
    """
    retry_config = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < retry_config.max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            retry_config.base_delay * (
                                retry_config.exponential_base ** attempt
                            ),
                            retry_config.max_delay,
                        )
                        
                        # Add jitter (±20% of jitter value)
                        if retry_config.jitter > 0:
                            jitter_amount = retry_config.jitter * delay
                            delay = delay + random.uniform(-jitter_amount, jitter_amount)
                        
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {retry_config.max_retries + 1} attempts"
                        )
            
            # All retries exhausted
            if last_exception:
                raise last_exception
            
            # Should never reach here
            raise RuntimeError("Unexpected state in retry logic")
        
        return wrapper
    return decorator


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """
    Calculate backoff delay for a given retry attempt.
    
    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential base for backoff calculation
        jitter: Whether to add random jitter
        
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (exponential_base ** attempt), max_delay)
    
    if jitter:
        delay = delay * (0.8 + random.random() * 0.4)
    
    return delay
