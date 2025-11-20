"""
Prometheus Metrics Exporter
============================

Exposes metrics for Prometheus scraping at /metrics endpoint.

Metrics tracked:
- HTTP requests (total, duration, by endpoint)
- Cache performance (hits, misses, hit rate)
- OpenAI API calls (total, cost estimation)
- Xero API requests (total, errors)
- Active sessions
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]  # Buckets for percentile calculation
)

# ============================================================================
# Cache Metrics
# ============================================================================

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits across all cache layers'
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses across all cache layers'
)

cache_requests_total = Counter(
    'cache_requests_total',
    'Total cache requests (hits + misses)'
)

# ============================================================================
# OpenAI API Metrics
# ============================================================================

openai_api_calls_total = Counter(
    'openai_api_calls_total',
    'Total OpenAI API calls',
    ['model', 'operation']
)

openai_api_cost_usd = Counter(
    'openai_api_cost_usd',
    'Estimated OpenAI API cost in USD'
)

openai_api_tokens_total = Counter(
    'openai_api_tokens_total',
    'Total tokens used in OpenAI API calls',
    ['token_type']  # 'prompt' or 'completion'
)

# ============================================================================
# Xero API Metrics
# ============================================================================

xero_api_requests_total = Counter(
    'xero_api_requests_total',
    'Total Xero API requests',
    ['operation']
)

xero_api_errors_total = Counter(
    'xero_api_errors_total',
    'Total Xero API errors',
    ['error_type']
)

xero_invoices_created_total = Counter(
    'xero_invoices_created_total',
    'Total Xero invoices created successfully'
)

# ============================================================================
# Session and Business Metrics
# ============================================================================

active_sessions = Gauge(
    'active_sessions',
    'Number of active chat sessions'
)

orders_created_total = Counter(
    'orders_created_total',
    'Total orders created successfully'
)

order_value_usd = Counter(
    'order_value_usd',
    'Total order value in USD'
)

# ============================================================================
# Metrics Endpoint
# ============================================================================

def get_metrics() -> Response:
    """
    Return Prometheus metrics in text format.

    This endpoint is called by Prometheus scraper every 10-15 seconds.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# Helper Functions for Instrumentation
# ============================================================================

def record_cache_hit():
    """Record a cache hit"""
    cache_hits_total.inc()
    cache_requests_total.inc()


def record_cache_miss():
    """Record a cache miss"""
    cache_misses_total.inc()
    cache_requests_total.inc()


def record_openai_call(model: str, prompt_tokens: int, completion_tokens: int, operation: str = "chat_completion"):
    """
    Record an OpenAI API call with cost estimation.

    Args:
        model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
        prompt_tokens: Number of prompt tokens used
        completion_tokens: Number of completion tokens generated
        operation: Type of operation (e.g., "chat_completion", "embedding")
    """
    openai_api_calls_total.labels(model=model, operation=operation).inc()

    # Track tokens
    openai_api_tokens_total.labels(token_type="prompt").inc(prompt_tokens)
    openai_api_tokens_total.labels(token_type="completion").inc(completion_tokens)

    # Estimate cost (approximate pricing as of 2024)
    cost = 0.0
    if "gpt-4" in model.lower():
        # GPT-4: $0.03 per 1K prompt tokens, $0.06 per 1K completion tokens
        cost = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)
    elif "gpt-3.5-turbo" in model.lower():
        # GPT-3.5-Turbo: $0.0015 per 1K prompt tokens, $0.002 per 1K completion tokens
        cost = (prompt_tokens * 0.0015 / 1000) + (completion_tokens * 0.002 / 1000)

    openai_api_cost_usd.inc(cost)


def record_xero_request(operation: str, success: bool = True, error_type: str = None):
    """
    Record a Xero API request.

    Args:
        operation: Type of operation (e.g., "create_invoice", "get_customer")
        success: Whether the request succeeded
        error_type: Type of error if request failed
    """
    xero_api_requests_total.labels(operation=operation).inc()

    if not success and error_type:
        xero_api_errors_total.labels(error_type=error_type).inc()
    elif success and operation == "create_invoice":
        xero_invoices_created_total.inc()


def record_order_created(order_value: float):
    """
    Record a successfully created order.

    Args:
        order_value: Total order value in USD
    """
    orders_created_total.inc()
    order_value_usd.inc(order_value)


def update_active_sessions(count: int):
    """
    Update the active sessions gauge.

    Args:
        count: Current number of active sessions
    """
    active_sessions.set(count)
