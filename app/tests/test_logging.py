"""Testing the logging system."""
import pytest
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import create_app
from app.services.logging import (
    configure_logging,
    get_logger,
    MetricsCollector,
    log_method,
    log_async_function
)


class TestLoggingSystem:
    """Test cases for logging system."""

    def test_configure_logging(self):
        """Test logging configuration."""
        logger = configure_logging()
        assert logger is not None
        assert logger.level <= logging.INFO

    def test_get_logger(self):
        """Test getting logger instances."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2

    def test_log_levels(self):
        """Test different log levels."""
        logger = get_logger("test")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # All levels should be callable without errors

    def test_metrics_collector_init(self):
        """Test metrics collector initialization."""
        metrics = MetricsCollector()
        assert metrics._request_counts == {}
        assert metrics._response_times == []

    def test_metrics_collector_increment(self):
        """Test metrics collection increment."""
        metrics = MetricsCollector()
        metrics.increment_request_count("/test")
        assert metrics.get_metrics()["request_counts"] == {"/test:200": 1}

    def test_metrics_collector_response_time(self):
        """Test response time recording."""
        metrics = MetricsCollector()
        metrics.record_response_time(100.5)
        assert metrics.get_metrics()["response_times_count"] == 1
        assert metrics.get_metrics()["response_times_avg"] == 100.5

    def test_metrics_collector_error_count(self):
        """Test error count increment."""
        metrics = MetricsCollector()
        metrics.increment_error_count("service", "error")
        assert metrics.get_metrics()["error_counts"] == {"service:error": 1}

    def test_metrics_collector_service_call(self):
        """Test service call count increment."""
        metrics = MetricsCollector()
        metrics.increment_service_call("test_service")
        assert metrics.get_metrics()["service_calls"] == {"test_service": 1}

    def test_metrics_collector_get_metrics(self):
        """Test getting all metrics."""
        metrics = MetricsCollector()

        metrics.increment_request_count("/test")
        metrics.record_response_time(100.0)
        metrics.increment_error_count("service", "error")

        all_metrics = metrics.get_metrics()
        assert "request_counts" in all_metrics
        assert "response_times_avg" in all_metrics
        assert "error_counts" in all_metrics

    def test_metrics_collector_reset(self):
        """Test metrics reset."""
        metrics = MetricsCollector()

        metrics.increment_request_count("/test")
        metrics.record_response_time(100.0)

        assert metrics.get_metrics()["request_counts"] != {}

        metrics.reset()
        assert metrics.get_metrics()["request_counts"] == {}
        assert metrics.get_metrics()["response_times_count"] == 0


class TestLoggingMiddleware:
    """Test cases for logging middleware."""

    def test_request_logging_middleware_class_exists(self):
        """Test request logging middleware class exists and can be imported."""
        from app.services.logging import RequestLoggingMiddleware
        # Middleware should be a class with __call__ method for FastAPI
        assert hasattr(RequestLoggingMiddleware, "__call__")

    def test_error_logging_middleware_class_exists(self):
        """Test error logging middleware class exists and can be imported."""
        from app.services.logging import ErrorLoggingMiddleware
        # Middleware should be a class with __call__ method for FastAPI
        assert hasattr(ErrorLoggingMiddleware, "__call__")


class TestLoggingDecorators:
    """Test cases for logging decorators."""

    async def test_log_method_decorator(self):
        """Test log_method decorator with async method."""
        @log_method("test_service")
        async def test_method(self):
            return "result"

        class TestClass:
            pass

        instance = TestClass()
        result = await test_method(instance)
        assert result == "result"

    async def test_log_async_function_decorator(self):
        """Test log_async_function decorator."""
        @log_async_function("test_function")
        async def test_func():
            return "success"

        result = await test_func()
        assert result == "success"


class TestStructuredLogging:
    """Test cases for structured logging output."""

    def test_json_formatter(self):
        """Test JSON formatter."""
        from app.services.logging import JsonFormatter
        import json

        formatter = JsonFormatter()

        # Create a simple log record
        logger = get_logger("test")
        record = logger.makeRecord(
            "test",
            logging.INFO,
            "test.py",
            1,
            "Test message",
            None,
            None,
            extra={"request_id": "abc123", "extra_data": {"key": "value"}}
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["request_id"] == "abc123"

    def test_log_with_exception(self):
        """Test logging with exception information."""
        logger = get_logger("test")

        try:
            raise ValueError("Test exception")
        except Exception:
            logger.error("An error occurred", exc_info=True)

        # Should not raise an error during logging


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def test_health_endpoint_exists(self):
        """Test that health endpoint is configured in the app."""
        from app.main import app
        # Check that the health route exists
        route_paths = [getattr(route, "path", "") for route in app.routes]
        assert "/health" in route_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])