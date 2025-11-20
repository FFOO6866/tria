"""
Retry Logic and Circuit Breakers for External API Reliability
=============================================================

Implements:
- Exponential backoff retries for transient failures
- Circuit breakers to prevent cascade failures
- Rate limit aware retries
- Timeout enforcement

Usage:
    from production.retry import retry_with_backoff, circuit_breaker

    @circuit_breaker("xero")
    @retry_with_backoff(max_attempts=3)
    def call_xero_api():
        ...
"""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception,
    before_sleep_log,
    after_log
)
from pybreaker import CircuitBreaker, CircuitBreakerError
import requests
import logging
import functools

logger = logging.getLogger(__name__)

# ============================================================================
# RETRY DECORATORS
# ============================================================================

def retry_with_backoff(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 10
):
    """
    Retry decorator with exponential backoff for transient failures.

    Args:
        max_attempts: Maximum retry attempts (default 3)
        min_wait: Minimum wait seconds between retries (default 2)
        max_wait: Maximum wait seconds between retries (default 10)

    Returns:
        Decorator function

    Example:
        @retry_with_backoff(max_attempts=5)
        def call_external_api():
            response = requests.get("https://api.example.com")
            response.raise_for_status()
            return response.json()
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError  # Will check status in reraise_if
        )),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


def retry_on_rate_limit(max_attempts: int = 5):
    """
    Retry with longer backoff specifically for rate limit errors (429).

    Args:
        max_attempts: Maximum retry attempts (default 5)

    Returns:
        Decorator function
    """
    def should_retry(exception):
        """Check if exception is retryable rate limit error"""
        if isinstance(exception, requests.exceptions.HTTPError):
            return exception.response.status_code == 429
        return False

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=5, max=60),  # Longer waits for rate limits
        retry=retry_if_exception(should_retry),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )


# ============================================================================
# CIRCUIT BREAKERS
# ============================================================================

# Circuit breaker for Xero API
xero_circuit_breaker = CircuitBreaker(
    fail_max=5,  # Open circuit after 5 consecutive failures
    reset_timeout=60,  # Stay open for 60 seconds
    name="xero_api"
)

# Circuit breaker for OpenAI API
openai_circuit_breaker = CircuitBreaker(
    fail_max=3,  # More sensitive - opens after 3 failures
    reset_timeout=30,  # Shorter timeout
    name="openai_api"
)

# Circuit breaker for database
database_circuit_breaker = CircuitBreaker(
    fail_max=10,  # Less sensitive - database should be stable
    reset_timeout=120,  # Longer timeout (2 min)
    name="database"
)


def circuit_breaker(breaker_name: str = "default"):
    """
    Decorator to apply circuit breaker to function.

    Args:
        breaker_name: Name of circuit breaker to use
                     Options: "xero", "openai", "database"

    Returns:
        Decorator function

    Example:
        @circuit_breaker("xero")
        def call_xero_api():
            ...
    """
    breakers = {
        "xero": xero_circuit_breaker,
        "openai": openai_circuit_breaker,
        "database": database_circuit_breaker
    }

    breaker = breakers.get(breaker_name)
    if not breaker:
        logger.warning(f"Unknown circuit breaker '{breaker_name}', using default")
        breaker = xero_circuit_breaker

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error(
                    f"Circuit breaker '{breaker_name}' is OPEN - "
                    f"blocking request to prevent cascade failure"
                )
                raise Exception(
                    f"{breaker_name} service is temporarily unavailable. "
                    f"Please try again in a few minutes."
                )
        return wrapper
    return decorator


def get_circuit_breaker_status():
    """
    Get current status of all circuit breakers.

    Returns:
        dict: Circuit breaker states

    Example:
        status = get_circuit_breaker_status()
        # {'xero': 'closed', 'openai': 'open', 'database': 'half-open'}
    """
    return {
        'xero': xero_circuit_breaker.current_state,
        'openai': openai_circuit_breaker.current_state,
        'database': database_circuit_breaker.current_state
    }
