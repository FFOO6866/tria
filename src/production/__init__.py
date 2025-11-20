"""
Production Infrastructure for TRIA AI-BPO
=========================================

This module provides production-grade reliability, resilience, and observability features:

- Transaction management for data integrity
- Idempotency for duplicate prevention
- Retry logic with exponential backoff
- Circuit breakers for fault tolerance
- Input validation and sanitization
- Error tracking and monitoring
- Rate limiting for external APIs
"""

from .transactions import transactional, TransactionManager
from .idempotency import IdempotencyMiddleware, require_idempotency_key
from .retry import retry_with_backoff, retry_on_rate_limit, circuit_breaker, get_circuit_breaker_status
from .validation import (
    OrderValidator,
    sanitize_for_sql,
    validate_decimal_precision,
    validate_phone_number,
    validate_email,
    ValidationError
)
from .error_tracking import init_error_tracking, track_error
from .rate_limiting import XeroRateLimiter, rate_limit_xero, RateLimitExceeded

__all__ = [
    # Transaction management
    'transactional',
    'TransactionManager',
    # Idempotency
    'IdempotencyMiddleware',
    'require_idempotency_key',
    # Retry and circuit breakers
    'retry_with_backoff',
    'retry_on_rate_limit',
    'circuit_breaker',
    'get_circuit_breaker_status',
    # Validation
    'OrderValidator',
    'sanitize_for_sql',
    'validate_decimal_precision',
    'validate_phone_number',
    'validate_email',
    'ValidationError',
    # Error tracking
    'init_error_tracking',
    'track_error',
    # Rate limiting
    'XeroRateLimiter',
    'rate_limit_xero',
    'RateLimitExceeded',
]
