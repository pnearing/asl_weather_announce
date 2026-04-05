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
    jitter: bool = True  # Add random jitter to prevent thundering herd
    retryable_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3
    success_threshold: int = 2  # consecutive successes to close circuit


@dataclass
class APICallMetrics:
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
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state
    
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
                    self._half_open_calls = 0
            else:
                # In CLOSED state, reset failure count on success
                if self._failure_count > 0:
                    self._failure_count = 0
    
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
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "half_open_calls": self._half_open_calls,
                "last_failure_time": self._last_failure_time,
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
        metrics.record("zippopotam", "lookup", duration=0.5, success=True)
        
        # Get statistics
        stats = metrics.get_statistics()
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of call records to keep per service
        """
        self.max_history = max_history
        self._metrics: Dict[str, Deque[APICallMetrics]] = {}
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
        Record an API call metric.
        
        Args:
            service_name: Name of the service
            endpoint: Name of the endpoint
            duration: Duration of the call in seconds
            success: Whether the call succeeded
            error_type: Type of error if failed
            status_code: HTTP status code if applicable
            start_time: Start time of the call (defaults to now - duration)
        """
        if start_time is None:
            start_time = time.time() - duration
        
        metric = APICallMetrics(
            service_name=service_name,
            endpoint=endpoint,
            start_time=start_time,
            end_time=start_time + duration,
            success=success,
            error_type=error_type,
            status_code=status_code,
        )
        
        key = f"{service_name}:{endpoint}"
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = deque(maxlen=self.max_history)
            self._metrics[key].append(metric)
    
    def get_statistics(
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
            Dictionary with statistics
        """
        with self._lock:
            metrics_list: List[APICallMetrics] = []
            
            for key, queue in self._metrics.items():
                key_service, key_endpoint = key.split(":", 1)
                
                if service_name and key_service != service_name:
                    continue
                if endpoint and key_endpoint != endpoint:
                    continue
                
                metrics_list.extend(queue)
            
            if not metrics_list:
                return {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "success_rate": 0.0,
                    "avg_response_time_ms": 0.0,
                    "min_response_time_ms": 0.0,
                    "max_response_time_ms": 0.0,
                    "p95_response_time_ms": 0.0,
                    "p99_response_time_ms": 0.0,
                }
            
            total_calls = len(metrics_list)
            successful_calls = sum(1 for m in metrics_list if m.success)
            failed_calls = total_calls - successful_calls
            durations = [m.duration_ms for m in metrics_list]
            
            return {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": successful_calls / total_calls if total_calls > 0 else 0.0,
                "avg_response_time_ms": statistics.mean(durations),
                "min_response_time_ms": min(durations),
                "max_response_time_ms": max(durations),
                "p95_response_time_ms": self._percentile(durations, 0.95),
                "p99_response_time_ms": self._percentile(durations, 0.99),
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
        with self._lock:
            error_counts: Dict[str, int] = {}
            
            for key, queue in self._metrics.items():
                key_service = key.split(":", 1)[0]
                
                if service_name and key_service != service_name:
                    continue
                
                for metric in queue:
                    if not metric.success and metric.error_type:
                        error_counts[metric.error_type] = error_counts.get(
                            metric.error_type, 0
                        ) + 1
            
            return error_counts


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
        
        self.metrics.record(
            service_name=self.service_name,
            endpoint=self.endpoint,
            duration=duration,
            success=self.success,
            error_type=self.error_type,
            status_code=self.status_code,
            start_time=self.start_time,
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
                        
                        # Add jitter if enabled (±20%)
                        if retry_config.jitter:
                            delay = delay * (0.8 + random.random() * 0.4)
                        
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
