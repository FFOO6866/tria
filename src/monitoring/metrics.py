"""
Metrics Collection Module
=========================

Production-grade metrics collection for monitoring system health and performance.

Features:
1. Response time metrics (min, max, mean, percentiles)
2. Request counting and throughput
3. Error rate tracking
4. Cache performance metrics
5. Rate limit metrics
6. Memory usage monitoring
7. Thread-safe metric aggregation

NO MOCKING - Real production metrics
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


@dataclass
class MetricSnapshot:
    """Single metric measurement"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsSummary:
    """Aggregated metrics summary"""
    name: str
    count: int
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    p95_value: float
    p99_value: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """
    Thread-safe metrics collector

    Collects and aggregates metrics for monitoring dashboards.
    """

    def __init__(self, retention_seconds: int = 3600):
        """
        Initialize metrics collector

        Args:
            retention_seconds: How long to keep metrics in memory (default 1 hour)
        """
        self.retention_seconds = retention_seconds
        self.metrics: Dict[str, List[MetricSnapshot]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a metric value

        Args:
            name: Metric name (e.g., "response_time_ms")
            value: Metric value
            tags: Optional tags for filtering (e.g., {"endpoint": "/chat"})
        """
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            value=value,
            tags=tags or {}
        )

        with self.lock:
            self.metrics[name].append(snapshot)
            self._cleanup_old_metrics()

    def increment_counter(self, name: str, increment: int = 1):
        """
        Increment a counter

        Args:
            name: Counter name (e.g., "requests_total")
            increment: Amount to increment by (default 1)
        """
        with self.lock:
            self.counters[name] += increment

    def get_counter(self, name: str) -> int:
        """Get current counter value"""
        with self.lock:
            return self.counters.get(name, 0)

    def reset_counter(self, name: str):
        """Reset counter to zero"""
        with self.lock:
            self.counters[name] = 0

    def get_summary(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
        since: Optional[datetime] = None
    ) -> Optional[MetricsSummary]:
        """
        Get aggregated metric summary

        Args:
            name: Metric name
            tags: Optional tags to filter by
            since: Optional start time for aggregation

        Returns:
            MetricsSummary or None if no data
        """
        with self.lock:
            snapshots = self.metrics.get(name, [])

            # Filter by tags
            if tags:
                snapshots = [
                    s for s in snapshots
                    if all(s.tags.get(k) == v for k, v in tags.items())
                ]

            # Filter by time
            if since:
                snapshots = [s for s in snapshots if s.timestamp >= since]

            if not snapshots:
                return None

            values = [s.value for s in snapshots]

            return MetricsSummary(
                name=name,
                count=len(values),
                min_value=min(values),
                max_value=max(values),
                mean_value=statistics.mean(values),
                median_value=statistics.median(values),
                p95_value=self._percentile(values, 95),
                p99_value=self._percentile(values, 99),
                tags=tags or {}
            )

    def get_all_summaries(
        self,
        since: Optional[datetime] = None
    ) -> Dict[str, MetricsSummary]:
        """Get summaries for all metrics"""
        summaries = {}
        with self.lock:
            for name in self.metrics.keys():
                summary = self.get_summary(name, since=since)
                if summary:
                    summaries[name] = summary
        return summaries

    def get_rate(
        self,
        counter_name: str,
        time_window_seconds: int = 60
    ) -> float:
        """
        Calculate rate (per second) for a counter over time window

        Args:
            counter_name: Counter name
            time_window_seconds: Time window for rate calculation

        Returns:
            Rate per second
        """
        metric_name = f"{counter_name}_timestamps"
        since = datetime.now() - timedelta(seconds=time_window_seconds)

        with self.lock:
            snapshots = self.metrics.get(metric_name, [])
            recent = [s for s in snapshots if s.timestamp >= since]

            if not recent:
                return 0.0

            return len(recent) / time_window_seconds

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.now() - timedelta(seconds=self.retention_seconds)

        for name in list(self.metrics.keys()):
            self.metrics[name] = [
                s for s in self.metrics[name]
                if s.timestamp > cutoff
            ]

            # Remove empty lists
            if not self.metrics[name]:
                del self.metrics[name]


class ResponseTimeTracker:
    """Track response times for endpoints"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.start_time = None

    def __enter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record response time"""
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.collector.record_metric("response_time_ms", duration_ms)

            # Also track success/failure
            if exc_type:
                self.collector.increment_counter("requests_failed")
            else:
                self.collector.increment_counter("requests_succeeded")


class CacheMetrics:
    """Track cache performance"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def record_hit(self):
        """Record cache hit"""
        self.collector.increment_counter("cache_hits")
        self.collector.increment_counter("cache_requests")

    def record_miss(self):
        """Record cache miss"""
        self.collector.increment_counter("cache_misses")
        self.collector.increment_counter("cache_requests")

    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate

        Returns:
            Hit rate as percentage (0-100)
        """
        hits = self.collector.get_counter("cache_hits")
        requests = self.collector.get_counter("cache_requests")

        if requests == 0:
            return 0.0

        return (hits / requests) * 100


class RateLimitMetrics:
    """Track rate limiting behavior"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def record_allowed(self, user_id: str):
        """Record allowed request"""
        self.collector.increment_counter("rate_limit_allowed")
        self.collector.increment_counter("rate_limit_requests")
        self.collector.record_metric(
            "rate_limit_event",
            1.0,
            tags={"user_id": user_id, "result": "allowed"}
        )

    def record_blocked(self, user_id: str, limit_type: str):
        """Record blocked request"""
        self.collector.increment_counter("rate_limit_blocked")
        self.collector.increment_counter("rate_limit_requests")
        self.collector.record_metric(
            "rate_limit_event",
            0.0,
            tags={"user_id": user_id, "result": "blocked", "type": limit_type}
        )

    def get_block_rate(self) -> float:
        """
        Calculate rate limit block rate

        Returns:
            Block rate as percentage (0-100)
        """
        blocked = self.collector.get_counter("rate_limit_blocked")
        requests = self.collector.get_counter("rate_limit_requests")

        if requests == 0:
            return 0.0

        return (blocked / requests) * 100


class ErrorMetrics:
    """Track error rates and types"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector

    def record_error(
        self,
        error_type: str,
        severity: str = "error",
        **tags
    ):
        """
        Record an error

        Args:
            error_type: Type of error (e.g., "ValidationError")
            severity: Severity level (error, warning, critical)
            **tags: Additional tags for filtering
        """
        self.collector.increment_counter(f"errors_{error_type}")
        self.collector.increment_counter("errors_total")

        self.collector.record_metric(
            "error_event",
            1.0,
            tags={"type": error_type, "severity": severity, **tags}
        )

    def get_error_rate(self, time_window_seconds: int = 60) -> float:
        """
        Calculate error rate over time window

        Args:
            time_window_seconds: Time window for rate calculation

        Returns:
            Errors per second
        """
        return self.collector.get_rate("errors_total", time_window_seconds)

    def get_error_breakdown(self) -> Dict[str, int]:
        """
        Get breakdown of error types

        Returns:
            Dictionary mapping error types to counts
        """
        breakdown = {}
        for name, count in self.collector.counters.items():
            if name.startswith("errors_") and name != "errors_total":
                error_type = name.replace("errors_", "")
                breakdown[error_type] = count
        return breakdown


class MemoryMetrics:
    """Track memory usage"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.process = psutil.Process()

    def record_current(self):
        """Record current memory usage"""
        memory_mb = self.process.memory_info().rss / (1024 * 1024)
        self.collector.record_metric("memory_mb", memory_mb)

    def get_current_mb(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / (1024 * 1024)

    def get_peak_mb(self, since: Optional[datetime] = None) -> float:
        """Get peak memory usage"""
        summary = self.collector.get_summary("memory_mb", since=since)
        return summary.max_value if summary else 0.0


# Global metrics collector
metrics_collector = MetricsCollector(retention_seconds=3600)

# Global metric trackers
response_time_tracker = ResponseTimeTracker(metrics_collector)
cache_metrics = CacheMetrics(metrics_collector)
rate_limit_metrics = RateLimitMetrics(metrics_collector)
error_metrics = ErrorMetrics(metrics_collector)
memory_metrics = MemoryMetrics(metrics_collector)


def get_system_health() -> Dict[str, Any]:
    """
    Get overall system health metrics

    Returns:
        Dictionary with system health information
    """
    # Get recent summaries (last 5 minutes)
    since = datetime.now() - timedelta(minutes=5)

    response_summary = metrics_collector.get_summary("response_time_ms", since=since)

    return {
        "timestamp": datetime.now().isoformat(),
        "requests": {
            "total": metrics_collector.get_counter("requests_succeeded") +
                    metrics_collector.get_counter("requests_failed"),
            "succeeded": metrics_collector.get_counter("requests_succeeded"),
            "failed": metrics_collector.get_counter("requests_failed"),
            "rate_per_sec": metrics_collector.get_rate("requests_succeeded", 60)
        },
        "response_time": {
            "mean_ms": response_summary.mean_value if response_summary else 0,
            "p95_ms": response_summary.p95_value if response_summary else 0,
            "p99_ms": response_summary.p99_value if response_summary else 0
        } if response_summary else None,
        "cache": {
            "hit_rate": cache_metrics.get_hit_rate(),
            "hits": metrics_collector.get_counter("cache_hits"),
            "misses": metrics_collector.get_counter("cache_misses")
        },
        "rate_limiting": {
            "block_rate": rate_limit_metrics.get_block_rate(),
            "blocked": metrics_collector.get_counter("rate_limit_blocked"),
            "allowed": metrics_collector.get_counter("rate_limit_allowed")
        },
        "errors": {
            "total": metrics_collector.get_counter("errors_total"),
            "rate_per_sec": error_metrics.get_error_rate(60),
            "breakdown": error_metrics.get_error_breakdown()
        },
        "memory": {
            "current_mb": memory_metrics.get_current_mb(),
            "peak_mb": memory_metrics.get_peak_mb(since)
        }
    }
