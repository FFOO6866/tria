"""
Rate Limiting
=============

Production-grade rate limiting for TRIA chatbot.

Features:
1. Per-user rate limiting (prevent spam)
2. Global rate limiting (prevent DoS)
3. IP-based rate limiting
4. Sliding window algorithm (accurate)
5. Token bucket algorithm (burst-friendly)
6. Graceful degradation
7. Rate limit headers (standards-compliant)

Algorithms:
- Sliding Window: Precise, memory-efficient, smooth limiting
- Token Bucket: Allows bursts, good for API usage

NO MOCKING - Real production rate limiting
"""

import time
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limits"""
    PER_USER = "per_user"
    PER_IP = "per_ip"
    GLOBAL = "global"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 10
    requests_per_hour: int = 100
    requests_per_day: int = 1000
    burst_size: int = 20  # Allow bursts up to this size
    enabled: bool = True


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # Unix timestamp
    retry_after: Optional[int] = None  # Seconds until retry allowed
    limit_type: Optional[RateLimitType] = None
    identifier: Optional[str] = None  # User ID or IP

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers (RFC 6585 compliant)"""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter

    Algorithm:
    - Tracks timestamps of requests in a sliding window
    - Removes expired timestamps on each check
    - Precise and memory-efficient

    Example:
        limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
        if limiter.allow_request("user123"):
            process_request()
        else:
            reject_request()
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize sliding window rate limiter

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Window duration in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = Lock()

    def allow_request(self, identifier: str) -> Tuple[bool, RateLimitResult]:
        """
        Check if request is allowed

        Args:
            identifier: User ID, IP address, or other identifier

        Returns:
            Tuple of (allowed, rate_limit_result)
        """
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Get request timestamps for this identifier
            timestamps = self.requests[identifier]

            # Remove expired timestamps
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            # Check if limit exceeded
            current_count = len(timestamps)
            allowed = current_count < self.max_requests

            if allowed:
                # Add current timestamp
                timestamps.append(now)

            # Calculate reset time (when oldest request expires)
            if timestamps:
                reset_at = timestamps[0] + self.window_seconds
                retry_after = int(reset_at - now) if not allowed else None
            else:
                reset_at = now + self.window_seconds
                retry_after = None

            result = RateLimitResult(
                allowed=allowed,
                limit=self.max_requests,
                remaining=max(0, self.max_requests - current_count - (1 if allowed else 0)),
                reset_at=reset_at,
                retry_after=retry_after,
                identifier=identifier
            )

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"{current_count}/{self.max_requests} requests in {self.window_seconds}s window"
                )

            return allowed, result

    def get_current_usage(self, identifier: str) -> int:
        """Get current request count for identifier"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds
            timestamps = self.requests[identifier]

            # Remove expired timestamps
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()

            return len(timestamps)

    def reset(self, identifier: str):
        """Reset rate limit for identifier"""
        with self.lock:
            if identifier in self.requests:
                del self.requests[identifier]
                logger.info(f"Rate limit reset for {identifier}")

    def cleanup_expired(self):
        """Clean up expired entries (call periodically)"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds
            expired = []

            for identifier, timestamps in self.requests.items():
                # Remove expired timestamps
                while timestamps and timestamps[0] < window_start:
                    timestamps.popleft()

                # Mark empty queues for deletion
                if not timestamps:
                    expired.append(identifier)

            # Delete empty queues
            for identifier in expired:
                del self.requests[identifier]

            if expired:
                logger.debug(f"Cleaned up {len(expired)} expired rate limit entries")


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter

    Algorithm:
    - Each user has a bucket with tokens
    - Tokens are added at a fixed rate
    - Each request consumes a token
    - Allows bursts up to bucket capacity

    Example:
        limiter = TokenBucketRateLimiter(capacity=20, refill_rate=10/60)
        if limiter.allow_request("user123"):
            process_request()
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket rate limiter

        Args:
            capacity: Maximum tokens in bucket (burst size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: Dict[str, Dict] = {}
        self.lock = Lock()

    def allow_request(self, identifier: str) -> Tuple[bool, RateLimitResult]:
        """
        Check if request is allowed

        Args:
            identifier: User ID or IP address

        Returns:
            Tuple of (allowed, rate_limit_result)
        """
        with self.lock:
            now = time.time()

            # Get or create bucket
            if identifier not in self.buckets:
                self.buckets[identifier] = {
                    "tokens": self.capacity,
                    "last_update": now
                }

            bucket = self.buckets[identifier]

            # Refill tokens
            time_elapsed = now - bucket["last_update"]
            tokens_to_add = time_elapsed * self.refill_rate
            bucket["tokens"] = min(self.capacity, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now

            # Check if request is allowed
            allowed = bucket["tokens"] >= 1.0

            if allowed:
                bucket["tokens"] -= 1.0

            # Calculate when next token will be available
            if bucket["tokens"] < 1.0:
                tokens_needed = 1.0 - bucket["tokens"]
                retry_after = int(tokens_needed / self.refill_rate) + 1
            else:
                retry_after = None

            result = RateLimitResult(
                allowed=allowed,
                limit=self.capacity,
                remaining=int(bucket["tokens"]),
                reset_at=now + (self.capacity / self.refill_rate),  # Time to full refill
                retry_after=retry_after,
                identifier=identifier
            )

            if not allowed:
                logger.warning(
                    f"Token bucket exhausted for {identifier}: "
                    f"{bucket['tokens']:.2f} tokens remaining"
                )

            return allowed, result

    def reset(self, identifier: str):
        """Reset bucket for identifier"""
        with self.lock:
            if identifier in self.buckets:
                del self.buckets[identifier]
                logger.info(f"Token bucket reset for {identifier}")


class ChatbotRateLimiter:
    """
    Multi-tier rate limiter for chatbot

    Tiers:
    1. Per-user minute limit (prevent rapid-fire spam)
    2. Per-user hour limit (prevent sustained spam)
    3. Per-user day limit (prevent abuse)
    4. Global limit (prevent DoS)

    Example:
        limiter = ChatbotRateLimiter()
        result = limiter.check_rate_limit(user_id="user123", ip_address="1.2.3.4")
        if result.allowed:
            process_request()
        else:
            return_error(result.retry_after)
    """

    def __init__(
        self,
        per_user_config: Optional[RateLimitConfig] = None,
        global_config: Optional[RateLimitConfig] = None,
        enable_ip_limiting: bool = True
    ):
        """
        Initialize multi-tier rate limiter

        Args:
            per_user_config: Per-user rate limit configuration
            global_config: Global rate limit configuration
            enable_ip_limiting: Enable IP-based rate limiting
        """
        # Default configurations
        self.per_user_config = per_user_config or RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            burst_size=20
        )

        self.global_config = global_config or RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=10000,
            requests_per_day=100000,
            burst_size=2000
        )

        self.enable_ip_limiting = enable_ip_limiting

        # Initialize limiters
        # Per-user limiters
        self.user_minute_limiter = SlidingWindowRateLimiter(
            max_requests=self.per_user_config.requests_per_minute,
            window_seconds=60
        )
        self.user_hour_limiter = SlidingWindowRateLimiter(
            max_requests=self.per_user_config.requests_per_hour,
            window_seconds=3600
        )
        self.user_day_limiter = SlidingWindowRateLimiter(
            max_requests=self.per_user_config.requests_per_day,
            window_seconds=86400
        )

        # Token bucket for burst handling
        self.user_burst_limiter = TokenBucketRateLimiter(
            capacity=self.per_user_config.burst_size,
            refill_rate=self.per_user_config.requests_per_minute / 60.0
        )

        # Global limiters
        self.global_minute_limiter = SlidingWindowRateLimiter(
            max_requests=self.global_config.requests_per_minute,
            window_seconds=60
        )

        # IP-based limiter (if enabled)
        if enable_ip_limiting:
            self.ip_limiter = SlidingWindowRateLimiter(
                max_requests=self.per_user_config.requests_per_minute * 2,  # 2x user limit
                window_seconds=60
            )
        else:
            self.ip_limiter = None

        logger.info(
            f"ChatbotRateLimiter initialized: "
            f"per_user={self.per_user_config.requests_per_minute}/min, "
            f"global={self.global_config.requests_per_minute}/min"
        )

    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        check_global: bool = True
    ) -> RateLimitResult:
        """
        Check rate limits across all tiers

        Args:
            user_id: User identifier
            ip_address: IP address
            check_global: Check global rate limit

        Returns:
            RateLimitResult (first limit that fails)
        """
        # Check global limit first (prevents DoS)
        if check_global and self.global_config.enabled:
            allowed, result = self.global_minute_limiter.allow_request("global")
            if not allowed:
                result.limit_type = RateLimitType.GLOBAL
                return result

        # Check IP-based limit
        if self.enable_ip_limiting and ip_address and self.ip_limiter:
            allowed, result = self.ip_limiter.allow_request(f"ip:{ip_address}")
            if not allowed:
                result.limit_type = RateLimitType.PER_IP
                return result

        # Check per-user limits
        if user_id and self.per_user_config.enabled:
            # Check minute limit
            allowed, result = self.user_minute_limiter.allow_request(f"user:{user_id}:minute")
            if not allowed:
                result.limit_type = RateLimitType.PER_USER
                return result

            # Check hour limit
            allowed, result = self.user_hour_limiter.allow_request(f"user:{user_id}:hour")
            if not allowed:
                result.limit_type = RateLimitType.PER_USER
                return result

            # Check day limit
            allowed, result = self.user_day_limiter.allow_request(f"user:{user_id}:day")
            if not allowed:
                result.limit_type = RateLimitType.PER_USER
                return result

            # Check burst limit (token bucket)
            allowed, result = self.user_burst_limiter.allow_request(f"user:{user_id}:burst")
            if not allowed:
                result.limit_type = RateLimitType.PER_USER
                return result

        # All checks passed
        return RateLimitResult(
            allowed=True,
            limit=self.per_user_config.requests_per_minute,
            remaining=self.per_user_config.requests_per_minute,
            reset_at=time.time() + 60,
            limit_type=RateLimitType.PER_USER,
            identifier=user_id
        )

    def get_usage_stats(self, user_id: str) -> Dict[str, int]:
        """Get current usage statistics for user"""
        return {
            "minute": self.user_minute_limiter.get_current_usage(f"user:{user_id}:minute"),
            "hour": self.user_hour_limiter.get_current_usage(f"user:{user_id}:hour"),
            "day": self.user_day_limiter.get_current_usage(f"user:{user_id}:day"),
        }

    def reset_user(self, user_id: str):
        """Reset all rate limits for user"""
        self.user_minute_limiter.reset(f"user:{user_id}:minute")
        self.user_hour_limiter.reset(f"user:{user_id}:hour")
        self.user_day_limiter.reset(f"user:{user_id}:day")
        self.user_burst_limiter.reset(f"user:{user_id}:burst")
        logger.info(f"All rate limits reset for user: {user_id}")

    def cleanup(self):
        """Clean up expired entries (call periodically)"""
        self.user_minute_limiter.cleanup_expired()
        self.user_hour_limiter.cleanup_expired()
        self.user_day_limiter.cleanup_expired()
        self.global_minute_limiter.cleanup_expired()
        if self.ip_limiter:
            self.ip_limiter.cleanup_expired()


# Global rate limiter instance
_global_rate_limiter: Optional[ChatbotRateLimiter] = None


def get_rate_limiter() -> ChatbotRateLimiter:
    """Get or create global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = ChatbotRateLimiter()
    return _global_rate_limiter


def reset_rate_limiter():
    """Reset global rate limiter (for testing)"""
    global _global_rate_limiter
    _global_rate_limiter = None
