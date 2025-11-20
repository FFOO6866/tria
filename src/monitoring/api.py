"""
Monitoring API Endpoints
========================

REST API endpoints for accessing system health and metrics.

Endpoints:
- GET /health - Basic health check
- GET /metrics - Current metrics summary
- GET /metrics/detailed - Detailed metrics with breakdown
- GET /metrics/errors - Error metrics and breakdown
- GET /metrics/cache - Cache performance metrics
- GET /metrics/rate-limit - Rate limiting metrics

Usage with Flask:
    from monitoring.api import monitoring_bp
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')

Usage standalone:
    from monitoring.api import get_health_status, get_metrics_summary
    health = get_health_status()
    metrics = get_metrics_summary()
"""

from flask import Blueprint, jsonify, request
from typing import Dict, Any
from datetime import datetime, timedelta
import psutil

from .metrics import (
    metrics_collector,
    cache_metrics,
    rate_limit_metrics,
    error_metrics,
    memory_metrics,
    get_system_health
)


# Create Flask blueprint
monitoring_bp = Blueprint('monitoring', __name__)


def get_health_status() -> Dict[str, Any]:
    """
    Get basic system health status

    Returns:
        Dictionary with health status
    """
    try:
        # Get process info
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        cpu_percent = process.cpu_percent(interval=0.1)

        # Check if services are responsive
        health_checks = {
            "metrics_collector": True,  # If we got here, it's working
            "memory_usage_mb": memory_mb,
            "cpu_percent": cpu_percent
        }

        # Determine overall health
        is_healthy = (
            memory_mb < 2000 and  # Less than 2GB
            cpu_percent < 90  # Less than 90% CPU
        )

        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "checks": health_checks,
            "uptime_seconds": int(datetime.now().timestamp() - process.create_time())
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


def get_metrics_summary(time_window_minutes: int = 5) -> Dict[str, Any]:
    """
    Get summary of current metrics

    Args:
        time_window_minutes: Time window for metrics (default 5 minutes)

    Returns:
        Dictionary with metrics summary
    """
    since = datetime.now() - timedelta(minutes=time_window_minutes)

    # Get response time summary
    response_summary = metrics_collector.get_summary("response_time_ms", since=since)

    return {
        "timestamp": datetime.now().isoformat(),
        "time_window_minutes": time_window_minutes,
        "requests": {
            "total": metrics_collector.get_counter("requests_total"),
            "succeeded": metrics_collector.get_counter("requests_succeeded"),
            "failed": metrics_collector.get_counter("requests_failed"),
            "success_rate": _calculate_success_rate(),
            "requests_per_minute": metrics_collector.get_rate("requests_succeeded", time_window_minutes * 60)
        },
        "response_time": {
            "count": response_summary.count if response_summary else 0,
            "mean_ms": response_summary.mean_value if response_summary else 0,
            "median_ms": response_summary.median_value if response_summary else 0,
            "p95_ms": response_summary.p95_value if response_summary else 0,
            "p99_ms": response_summary.p99_value if response_summary else 0,
            "min_ms": response_summary.min_value if response_summary else 0,
            "max_ms": response_summary.max_value if response_summary else 0
        } if response_summary else None,
        "cache": {
            "hit_rate": cache_metrics.get_hit_rate(),
            "hits": metrics_collector.get_counter("cache_hits"),
            "misses": metrics_collector.get_counter("cache_misses"),
            "total_requests": metrics_collector.get_counter("cache_requests")
        },
        "rate_limiting": {
            "block_rate": rate_limit_metrics.get_block_rate(),
            "blocked": metrics_collector.get_counter("rate_limit_blocked"),
            "allowed": metrics_collector.get_counter("rate_limit_allowed"),
            "total_requests": metrics_collector.get_counter("rate_limit_requests")
        },
        "errors": {
            "total": metrics_collector.get_counter("errors_total"),
            "rate_per_minute": error_metrics.get_error_rate(time_window_minutes * 60),
            "breakdown": error_metrics.get_error_breakdown()
        },
        "memory": {
            "current_mb": memory_metrics.get_current_mb(),
            "peak_mb": memory_metrics.get_peak_mb(since)
        },
        "validation": {
            "failures": metrics_collector.get_counter("validation_failures")
        }
    }


def _calculate_success_rate() -> float:
    """Calculate success rate percentage"""
    succeeded = metrics_collector.get_counter("requests_succeeded")
    total = metrics_collector.get_counter("requests_total")
    if total == 0:
        return 0.0
    return (succeeded / total) * 100


# ============================================================================
# FLASK API ENDPOINTS
# ============================================================================

@monitoring_bp.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint

    Returns:
        JSON response with health status
    """
    health_status = get_health_status()
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


@monitoring_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    Metrics summary endpoint

    Query parameters:
        time_window: Time window in minutes (default: 5)

    Returns:
        JSON response with metrics summary
    """
    time_window = request.args.get('time_window', default=5, type=int)
    metrics_data = get_metrics_summary(time_window)
    return jsonify(metrics_data)


@monitoring_bp.route('/metrics/detailed', methods=['GET'])
def detailed_metrics():
    """
    Detailed metrics with system health

    Returns:
        JSON response with detailed system health and metrics
    """
    time_window = request.args.get('time_window', default=5, type=int)

    detailed_data = {
        "health": get_health_status(),
        "metrics": get_metrics_summary(time_window),
        "system_health": get_system_health()
    }

    return jsonify(detailed_data)


@monitoring_bp.route('/metrics/errors', methods=['GET'])
def error_metrics_endpoint():
    """
    Error metrics endpoint

    Returns:
        JSON response with error metrics and breakdown
    """
    time_window = request.args.get('time_window', default=60, type=int)

    error_data = {
        "timestamp": datetime.now().isoformat(),
        "time_window_minutes": time_window,
        "total_errors": metrics_collector.get_counter("errors_total"),
        "error_rate_per_minute": error_metrics.get_error_rate(time_window * 60),
        "error_breakdown": error_metrics.get_error_breakdown(),
        "validation_failures": metrics_collector.get_counter("validation_failures")
    }

    return jsonify(error_data)


@monitoring_bp.route('/metrics/cache', methods=['GET'])
def cache_metrics_endpoint():
    """
    Cache performance metrics endpoint

    Returns:
        JSON response with cache metrics
    """
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "hit_rate": cache_metrics.get_hit_rate(),
        "hits": metrics_collector.get_counter("cache_hits"),
        "misses": metrics_collector.get_counter("cache_misses"),
        "total_requests": metrics_collector.get_counter("cache_requests"),
        "effectiveness": "good" if cache_metrics.get_hit_rate() > 50 else "needs_improvement"
    }

    return jsonify(cache_data)


@monitoring_bp.route('/metrics/rate-limit', methods=['GET'])
def rate_limit_metrics_endpoint():
    """
    Rate limiting metrics endpoint

    Returns:
        JSON response with rate limit metrics
    """
    rate_limit_data = {
        "timestamp": datetime.now().isoformat(),
        "block_rate": rate_limit_metrics.get_block_rate(),
        "blocked": metrics_collector.get_counter("rate_limit_blocked"),
        "allowed": metrics_collector.get_counter("rate_limit_allowed"),
        "total_requests": metrics_collector.get_counter("rate_limit_requests"),
        "effectiveness": "active" if metrics_collector.get_counter("rate_limit_blocked") > 0 else "no_blocks"
    }

    return jsonify(rate_limit_data)


@monitoring_bp.route('/metrics/reset', methods=['POST'])
def reset_metrics():
    """
    Reset metrics counters (use with caution!)

    Returns:
        JSON response confirming reset
    """
    # Reset all counters
    for counter_name in list(metrics_collector.counters.keys()):
        metrics_collector.reset_counter(counter_name)

    return jsonify({
        "status": "success",
        "message": "All metrics counters have been reset",
        "timestamp": datetime.now().isoformat()
    })


# ============================================================================
# STANDALONE FUNCTIONS (for non-Flask usage)
# ============================================================================

def print_metrics_summary(time_window_minutes: int = 5):
    """
    Print metrics summary to console

    Args:
        time_window_minutes: Time window for metrics
    """
    metrics = get_metrics_summary(time_window_minutes)

    print("\n" + "=" * 80)
    print(f"METRICS SUMMARY (Last {time_window_minutes} minutes)")
    print("=" * 80)
    print(f"Timestamp: {metrics['timestamp']}")
    print()

    print("REQUESTS:")
    req = metrics['requests']
    print(f"  Total: {req['total']}")
    print(f"  Succeeded: {req['succeeded']}")
    print(f"  Failed: {req['failed']}")
    print(f"  Success Rate: {req['success_rate']:.2f}%")
    print(f"  Rate: {req['requests_per_minute']:.2f} req/min")
    print()

    if metrics['response_time']:
        rt = metrics['response_time']
        print("RESPONSE TIME:")
        print(f"  Count: {rt['count']}")
        print(f"  Mean: {rt['mean_ms']:.0f} ms")
        print(f"  Median: {rt['median_ms']:.0f} ms")
        print(f"  P95: {rt['p95_ms']:.0f} ms")
        print(f"  P99: {rt['p99_ms']:.0f} ms")
        print()

    cache = metrics['cache']
    print("CACHE:")
    print(f"  Hit Rate: {cache['hit_rate']:.2f}%")
    print(f"  Hits: {cache['hits']}")
    print(f"  Misses: {cache['misses']}")
    print()

    rl = metrics['rate_limiting']
    print("RATE LIMITING:")
    print(f"  Block Rate: {rl['block_rate']:.2f}%")
    print(f"  Blocked: {rl['blocked']}")
    print(f"  Allowed: {rl['allowed']}")
    print()

    err = metrics['errors']
    print("ERRORS:")
    print(f"  Total: {err['total']}")
    print(f"  Rate: {err['rate_per_minute']:.2f} errors/min")
    if err['breakdown']:
        print("  Breakdown:")
        for error_type, count in err['breakdown'].items():
            print(f"    {error_type}: {count}")
    print()

    mem = metrics['memory']
    print("MEMORY:")
    print(f"  Current: {mem['current_mb']:.1f} MB")
    print(f"  Peak: {mem['peak_mb']:.1f} MB")
    print()

    print("=" * 80)


if __name__ == "__main__":
    # Standalone usage example
    print("Monitoring API - Standalone Usage")
    print()

    # Print health status
    health_status = get_health_status()
    print(f"Health Status: {health_status['status']}")
    print()

    # Print metrics summary
    print_metrics_summary()
