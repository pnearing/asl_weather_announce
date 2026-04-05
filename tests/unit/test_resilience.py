"""
Tests for the resilience module (circuit breaker, metrics, exponential backoff).
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from resilience import (
    APICallMetrics,
    APIMetrics,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    RetryConfig,
    with_backoff,
)


class TestAPICallMetrics(unittest.TestCase):
    """Test cases for APICallMetrics class."""
    
    def test_initial_state(self):
        """Test initial state of metrics."""
        metrics = APICallMetrics()
        
        self.assertEqual(metrics.total_calls, 0)
        self.assertEqual(metrics.success_count, 0)
        self.assertEqual(metrics.failure_count, 0)
        self.assertEqual(metrics.average_response_time, 0.0)
    
    def test_record_success(self):
        """Test recording successful calls."""
        metrics = APICallMetrics()
        
        metrics.record_success(0.5)
        metrics.record_success(1.0)
        
        self.assertEqual(metrics.total_calls, 2)
        self.assertEqual(metrics.success_count, 2)
        self.assertEqual(metrics.failure_count, 0)
        self.assertEqual(metrics.average_response_time, 0.75)
    
    def test_record_failure(self):
        """Test recording failed calls."""
        metrics = APICallMetrics()
        
        metrics.record_failure()
        metrics.record_failure()
        
        self.assertEqual(metrics.total_calls, 2)
        self.assertEqual(metrics.success_count, 0)
        self.assertEqual(metrics.failure_count, 2)
    
    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = APICallMetrics()
        
        # No calls yet
        self.assertEqual(metrics.success_rate, 1.0)
        
        # All failures
        metrics.record_failure()
        metrics.record_failure()
        self.assertEqual(metrics.success_rate, 0.0)
        
        # Mixed
        metrics.record_success(0.5)
        metrics.record_success(0.5)
        self.assertEqual(metrics.success_rate, 0.5)
    
    def test_get_stats(self):
        """Test getting statistics dictionary."""
        metrics = APICallMetrics()
        
        metrics.record_success(0.5)
        metrics.record_failure()
        
        stats = metrics.get_stats()
        
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["successes"], 1)
        self.assertEqual(stats["failures"], 1)
        self.assertEqual(stats["success_rate"], 0.5)
        self.assertEqual(stats["avg_response_time"], 0.25)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for CircuitBreaker class."""
    
    def test_initial_state(self):
        """Test initial state is CLOSED."""
        cb = CircuitBreaker(name="test")
        
        self.assertEqual(cb.state, "CLOSED")
        self.assertEqual(cb.name, "test")
    
    def test_successful_call(self):
        """Test successful function call."""
        cb = CircuitBreaker(name="test")
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, "CLOSED")
    
    def test_failure_counting(self):
        """Test that failures are counted."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)
        
        def fail_func():
            raise ValueError("error")
        
        # First 2 failures - should not open circuit
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(fail_func)
        
        self.assertEqual(cb.state, "CLOSED")
        self.assertEqual(cb.failure_count, 2)
        
        # 3rd failure - should open circuit
        with self.assertRaises(ValueError):
            cb.call(fail_func)
        
        self.assertEqual(cb.state, "OPEN")
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(name="test", config=config)
        
        def fail_func():
            raise ValueError("error")
        
        # Trigger failures to open circuit
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(fail_func)
        
        self.assertEqual(cb.state, "OPEN")
        
        # Next call should raise CircuitBreakerOpenError immediately
        with self.assertRaises(CircuitBreakerOpenError):
            cb.call(lambda: "should not execute")
    
    def test_circuit_recovery(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        cb = CircuitBreaker(name="test", config=config)
        
        def fail_func():
            raise ValueError("error")
        
        # Open the circuit
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(fail_func)
        
        self.assertEqual(cb.state, "OPEN")
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Circuit should be in HALF_OPEN state
        # A successful call should close it
        result = cb.call(lambda: "success")
        
        self.assertEqual(result, "success")
        self.assertEqual(cb.state, "CLOSED")
    
    def test_half_open_failure_reopens(self):
        """Test that failure in HALF_OPEN reopens circuit."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        cb = CircuitBreaker(name="test", config=config)
        
        def fail_func():
            raise ValueError("error")
        
        # Open the circuit
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(fail_func)
        
        # Wait for recovery
        time.sleep(0.15)
        
        # Failure in HALF_OPEN should reopen circuit
        with self.assertRaises(ValueError):
            cb.call(fail_func)
        
        self.assertEqual(cb.state, "OPEN")
    
    def test_success_resets_failure_count(self):
        """Test that successful call resets failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)
        
        call_count = [0]
        
        def sometimes_fail():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("error")
            return "success"
        
        # 2 failures
        for _ in range(2):
            with self.assertRaises(ValueError):
                cb.call(sometimes_fail)
        
        self.assertEqual(cb.failure_count, 2)
        
        # Success should reset
        result = cb.call(sometimes_fail)
        
        self.assertEqual(result, "success")
        self.assertEqual(cb.failure_count, 0)
    
    def test_custom_config(self):
        """Test circuit breaker with custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=30,
            half_open_max_calls=3
        )
        cb = CircuitBreaker(name="test", config=config)
        
        self.assertEqual(cb.config.failure_threshold, 5)
        self.assertEqual(cb.config.recovery_timeout, 30)
        self.assertEqual(cb.config.half_open_max_calls, 3)
    
    def test_get_stats(self):
        """Test getting circuit breaker statistics."""
        cb = CircuitBreaker(name="test")
        
        cb.call(lambda: "success")
        
        stats = cb.get_stats()
        
        self.assertEqual(stats["name"], "test")
        self.assertEqual(stats["state"], "CLOSED")
        self.assertIn("config", stats)


class TestAPIMetrics(unittest.TestCase):
    """Test cases for APIMetrics class."""
    
    def test_record_call(self):
        """Test recording API calls."""
        metrics = APIMetrics()
        
        metrics.record_call("service1", "endpoint1", 0.5, True)
        metrics.record_call("service1", "endpoint1", 0.6, True)
        metrics.record_call("service1", "endpoint1", 0.4, False)
        
        stats = metrics.get_stats()
        
        self.assertIn("service1", stats)
        self.assertIn("endpoint1", stats["service1"])
        
        endpoint_stats = stats["service1"]["endpoint1"]
        self.assertEqual(endpoint_stats["total"], 3)
        self.assertEqual(endpoint_stats["successes"], 2)
        self.assertEqual(endpoint_stats["failures"], 1)
    
    def test_measure_context_manager(self):
        """Test the measure context manager."""
        metrics = APIMetrics()
        
        with metrics.measure("service1", "endpoint1"):
            time.sleep(0.01)  # Small delay
        
        stats = metrics.get_stats()
        endpoint_stats = stats["service1"]["endpoint1"]
        
        self.assertEqual(endpoint_stats["total"], 1)
        self.assertEqual(endpoint_stats["successes"], 1)
        self.assertGreater(endpoint_stats["avg_response_time"], 0)
    
    def test_measure_with_exception(self):
        """Test that exceptions are recorded as failures."""
        metrics = APIMetrics()
        
        with self.assertRaises(ValueError):
            with metrics.measure("service1", "endpoint1"):
                raise ValueError("error")
        
        stats = metrics.get_stats()
        endpoint_stats = stats["service1"]["endpoint1"]
        
        self.assertEqual(endpoint_stats["total"], 1)
        self.assertEqual(endpoint_stats["failures"], 1)
        self.assertEqual(endpoint_stats["successes"], 0)
    
    def test_get_all_stats(self):
        """Test getting all service statistics."""
        metrics = APIMetrics()
        
        metrics.record_call("service1", "endpoint1", 0.5, True)
        metrics.record_call("service2", "endpoint1", 0.3, True)
        
        all_stats = metrics.get_all_stats()
        
        self.assertIn("service1", all_stats)
        self.assertIn("service2", all_stats)


class TestExponentialBackoff(unittest.TestCase):
    """Test cases for exponential backoff functionality."""
    
    def test_with_backoff_success(self):
        """Test that successful function is called once."""
        config = RetryConfig(max_retries=3, base_delay=0.01)
        
        call_count = [0]
        
        @with_backoff(config)
        def success_func():
            call_count[0] += 1
            return "success"
        
        result = success_func()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 1)
    
    def test_with_backoff_retry_then_success(self):
        """Test retry on failure then success."""
        config = RetryConfig(max_retries=3, base_delay=0.01)
        
        call_count = [0]
        
        @with_backoff(config)
        def fail_then_succeed():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("error")
            return "success"
        
        result = fail_then_succeed()
        
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)
    
    def test_with_backoff_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        
        @with_backoff(config)
        def always_fail():
            raise ValueError("error")
        
        with self.assertRaises(ValueError):
            always_fail()
    
    def test_with_backoff_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately."""
        config = RetryConfig(
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(ValueError,)
        )
        
        call_count = [0]
        
        @with_backoff(config)
        def raise_type_error():
            call_count[0] += 1
            raise TypeError("not retryable")
        
        with self.assertRaises(TypeError):
            raise_type_error()
        
        # Should only be called once
        self.assertEqual(call_count[0], 1)


class TestRetryConfig(unittest.TestCase):
    """Test cases for RetryConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.base_delay, 1.0)
        self.assertEqual(config.max_delay, 60.0)
        self.assertEqual(config.exponential_base, 2.0)
        self.assertEqual(config.jitter, 0.1)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0
        )
        
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.base_delay, 2.0)
        self.assertEqual(config.max_delay, 30.0)


class TestCircuitBreakerConfig(unittest.TestCase):
    """Test cases for CircuitBreakerConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        
        self.assertEqual(config.failure_threshold, 5)
        self.assertEqual(config.recovery_timeout, 60)
        self.assertEqual(config.half_open_max_calls, 1)
        self.assertEqual(config.success_threshold, 3)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30
        )
        
        self.assertEqual(config.failure_threshold, 3)
        self.assertEqual(config.recovery_timeout, 30)


if __name__ == "__main__":
    unittest.main()
