"""
Rate Limiting for External API Calls
=====================================

Implements rate limiting to comply with external API quotas and prevent throttling.
Specifically designed for Xero API's 60 requests/minute limit.

Usage:
    from production.rate_limiting import XeroRateLimiter

    rate_limiter = XeroRateLimiter()

    @rate_limiter.limit
    def call_xero_api():
        response = requests.get("https://api.xero.com/...")
        return response
"""

import time
import threading
from functools import wraps
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class XeroRateLimiter:
    """
    Rate limiter for Xero API calls.

    Xero limits: 60 requests per minute, 5000 requests per day.
    This implementation enforces the per-minute limit with a sliding window.
    """

    def __init__(self, max_calls_per_minute: int = 55, max_calls_per_day: int = 4500):
        """
        Initialize rate limiter.

        Args:
            max_calls_per_minute: Maximum API calls per minute (default 55, below Xero's 60 limit for safety)
            max_calls_per_day: Maximum API calls per day (default 4500, below Xero's 5000 limit for safety)
        """
        self.max_calls_per_minute = max_calls_per_minute
        self.max_calls_per_day = max_calls_per_day

        # Sliding window for minute-level tracking
        self.call_times_minute = deque()
        # Sliding window for day-level tracking
        self.call_times_day = deque()

        # Thread lock for concurrent access
        self.lock = threading.Lock()

    def _clean_old_calls(self):
        """Remove calls outside the tracking windows"""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        one_day_ago = now - timedelta(days=1)

        # Clean minute window
        while self.call_times_minute and self.call_times_minute[0] < one_minute_ago:
            self.call_times_minute.popleft()

        # Clean day window
        while self.call_times_day and self.call_times_day[0] < one_day_ago:
            self.call_times_day.popleft()

    def _wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        with self.lock:
            self._clean_old_calls()

            # Check minute limit
            if len(self.call_times_minute) >= self.max_calls_per_minute:
                oldest_call = self.call_times_minute[0]
                wait_time = 60 - (datetime.now() - oldest_call).total_seconds()

                if wait_time > 0:
                    logger.warning(
                        f"Rate limit approaching: {len(self.call_times_minute)}/{self.max_calls_per_minute} "
                        f"calls in last minute. Waiting {wait_time:.1f}s"
                    )
                    time.sleep(wait_time + 0.1)  # Add small buffer
                    self._clean_old_calls()

            # Check day limit
            if len(self.call_times_day) >= self.max_calls_per_day:
                oldest_call = self.call_times_day[0]
                wait_time = 86400 - (datetime.now() - oldest_call).total_seconds()

                if wait_time > 0:
                    logger.error(
                        f"Daily rate limit reached: {len(self.call_times_day)}/{self.max_calls_per_day} "
                        f"calls today. Next call available in {wait_time/3600:.1f} hours"
                    )
                    raise RateLimitExceeded(
                        f"Daily Xero API limit reached. Retry after {wait_time/3600:.1f} hours"
                    )

            # Record this call
            now = datetime.now()
            self.call_times_minute.append(now)
            self.call_times_day.append(now)

    def limit(self, func):
        """
        Decorator to apply rate limiting to a function.

        Usage:
            rate_limiter = XeroRateLimiter()

            @rate_limiter.limit
            def call_xero_api():
                return requests.get("https://api.xero.com/...")
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            self._wait_if_needed()
            return func(*args, **kwargs)
        return wrapper

    def get_stats(self):
        """
        Get current rate limiting statistics.

        Returns:
            dict: Current usage statistics
        """
        with self.lock:
            self._clean_old_calls()
            return {
                'calls_last_minute': len(self.call_times_minute),
                'calls_today': len(self.call_times_day),
                'minute_limit': self.max_calls_per_minute,
                'day_limit': self.max_calls_per_day,
                'minute_remaining': self.max_calls_per_minute - len(self.call_times_minute),
                'day_remaining': self.max_calls_per_day - len(self.call_times_day)
            }


class RateLimitExceeded(Exception):
    """Raised when daily rate limit is exceeded"""
    pass


# Global instance for Xero API
xero_rate_limiter = XeroRateLimiter()


def rate_limit_xero(func):
    """
    Convenience decorator for Xero API rate limiting.

    Usage:
        from production.rate_limiting import rate_limit_xero

        @rate_limit_xero
        def create_invoice(data):
            response = requests.post("https://api.xero.com/invoices", json=data)
            return response
    """
    return xero_rate_limiter.limit(func)
