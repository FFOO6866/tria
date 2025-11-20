"""
Production-Grade Redis Cache
==============================

Redis-backed caching for production deployment with:
- Persistent storage across restarts
- Shared cache across multiple instances
- Atomic operations
- TTL-based expiration
- Connection pooling
- Failover to in-memory cache if Redis unavailable

This addresses P0 performance blocker from production critique.
"""

import json
import logging
import hashlib
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

try:
    import redis
    from redis.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from cache.response_cache import LRUCache  # Fallback to in-memory

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_get_time_ms: float = 0
    total_set_time_ms: float = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0

    @property
    def avg_get_time_ms(self) -> float:
        """Average GET operation time"""
        total_ops = self.hits + self.misses
        return self.total_get_time_ms / total_ops if total_ops > 0 else 0

    @property
    def avg_set_time_ms(self) -> float:
        """Average SET operation time"""
        return self.total_set_time_ms / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 3),
            "avg_get_time_ms": round(self.avg_get_time_ms, 2),
            "avg_set_time_ms": round(self.avg_set_time_ms, 2),
            "total_requests": self.hits + self.misses
        }


class RedisCache:
    """
    Production-grade Redis cache with failover to in-memory

    Features:
    - Connection pooling
    - Automatic failover to in-memory cache
    - TTL-based expiration
    - Atomic operations
    - Performance metrics
    - JSON serialization

    Usage:
        cache = RedisCache(host="localhost", port=6379)
        cache.set("key", {"data": "value"}, ttl=3600)
        value = cache.get("key")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        key_prefix: str = "tria:",
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        fallback_to_memory: bool = True
    ):
        """
        Initialize Redis cache

        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            db: Redis database number
            key_prefix: Prefix for all keys
            max_connections: Max connections in pool
            socket_timeout: Socket timeout (seconds)
            socket_connect_timeout: Connection timeout (seconds)
            fallback_to_memory: Use in-memory cache if Redis unavailable
        """
        self.key_prefix = key_prefix
        self.metrics = CacheMetrics()
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[ConnectionPool] = None
        self.fallback_cache: Optional[LRUCache] = None
        self.using_fallback = False

        if not REDIS_AVAILABLE:
            logger.warning("redis-py not installed. Using in-memory cache fallback.")
            if fallback_to_memory:
                self.fallback_cache = LRUCache(max_size=1000, default_ttl=3600)
                self.using_fallback = True
            return

        try:
            # Create connection pool
            self.connection_pool = ConnectionPool(
                host=host,
                port=port,
                password=password,
                db=db,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=True  # Automatically decode bytes to strings
            )

            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)

            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis cache connected: {host}:{port}")

        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")

            if fallback_to_memory:
                logger.warning("Falling back to in-memory cache")
                self.fallback_cache = LRUCache(max_size=1000, default_ttl=3600)
                self.using_fallback = True
            else:
                raise

    def _make_key(self, key: str) -> str:
        """Create prefixed key"""
        return f"{self.key_prefix}{key}"

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        start_time = time.time()

        try:
            if self.using_fallback and self.fallback_cache:
                value = self.fallback_cache.get(self._make_key(key))
                elapsed_ms = (time.time() - start_time) * 1000

                if value is not None:
                    self.metrics.hits += 1
                    self.metrics.total_get_time_ms += elapsed_ms
                    return value
                else:
                    self.metrics.misses += 1
                    self.metrics.total_get_time_ms += elapsed_ms
                    return default

            if not self.redis_client:
                self.metrics.misses += 1
                return default

            # Get from Redis
            redis_key = self._make_key(key)
            value_str = self.redis_client.get(redis_key)

            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics.total_get_time_ms += elapsed_ms

            if value_str is None:
                self.metrics.misses += 1
                return default

            # Deserialize JSON
            value = json.loads(value_str)
            self.metrics.hits += 1

            return value

        except Exception as e:
            logger.error(f"Cache GET error for key '{key}': {e}")
            self.metrics.errors += 1
            self.metrics.misses += 1
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        start_time = time.time()

        try:
            if self.using_fallback and self.fallback_cache:
                self.fallback_cache.put(self._make_key(key), value, ttl=ttl)
                elapsed_ms = (time.time() - start_time) * 1000
                self.metrics.total_set_time_ms += elapsed_ms
                return True

            if not self.redis_client:
                return False

            # Serialize to JSON
            value_str = json.dumps(value)

            # Set in Redis with TTL
            redis_key = self._make_key(key)
            if ttl:
                self.redis_client.setex(redis_key, ttl, value_str)
            else:
                self.redis_client.set(redis_key, value_str)

            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics.total_set_time_ms += elapsed_ms

            return True

        except Exception as e:
            logger.error(f"Cache SET error for key '{key}': {e}")
            self.metrics.errors += 1
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.using_fallback and self.fallback_cache:
                redis_key = self._make_key(key)
                if redis_key in self.fallback_cache.cache:
                    del self.fallback_cache.cache[redis_key]
                return True

            if not self.redis_client:
                return False

            redis_key = self._make_key(key)
            self.redis_client.delete(redis_key)
            return True

        except Exception as e:
            logger.error(f"Cache DELETE error for key '{key}': {e}")
            self.metrics.errors += 1
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.using_fallback and self.fallback_cache:
                return self._make_key(key) in self.fallback_cache.cache

            if not self.redis_client:
                return False

            redis_key = self._make_key(key)
            return bool(self.redis_client.exists(redis_key))

        except Exception as e:
            logger.error(f"Cache EXISTS error for key '{key}': {e}")
            self.metrics.errors += 1
            return False

    def clear_all(self, pattern: Optional[str] = None) -> int:
        """
        Clear all keys matching pattern

        Args:
            pattern: Pattern to match (e.g., "intent:*"). None = clear all with prefix

        Returns:
            Number of keys deleted
        """
        try:
            if self.using_fallback and self.fallback_cache:
                self.fallback_cache.clear()
                return len(self.fallback_cache.cache)

            if not self.redis_client:
                return 0

            # Use pattern or default to prefix
            search_pattern = f"{self.key_prefix}{pattern or '*'}"
            keys = self.redis_client.keys(search_pattern)

            if keys:
                return self.redis_client.delete(*keys)
            return 0

        except Exception as e:
            logger.error(f"Cache CLEAR error: {e}")
            self.metrics.errors += 1
            return 0

    def get_info(self) -> Dict[str, Any]:
        """
        Get cache information and metrics

        Returns:
            Dictionary with cache info
        """
        info = {
            "backend": "redis" if not self.using_fallback else "in-memory",
            "metrics": self.metrics.to_dict(),
            "using_fallback": self.using_fallback
        }

        try:
            if self.redis_client and not self.using_fallback:
                # Get Redis info
                redis_info = self.redis_client.info("stats")
                info.update({
                    "redis_connected": True,
                    "redis_total_connections": redis_info.get("total_connections_received", 0),
                    "redis_connected_clients": redis_info.get("connected_clients", 0),
                    "redis_keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "redis_keyspace_misses": redis_info.get("keyspace_misses", 0)
                })

                # Calculate Redis hit rate
                redis_hits = redis_info.get("keyspace_hits", 0)
                redis_misses = redis_info.get("keyspace_misses", 0)
                redis_total = redis_hits + redis_misses
                info["redis_hit_rate"] = round(redis_hits / redis_total, 3) if redis_total > 0 else 0

            elif self.using_fallback and self.fallback_cache:
                # Get in-memory cache stats
                fallback_stats = self.fallback_cache.get_stats()
                info["fallback_stats"] = fallback_stats

        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            info["error"] = str(e)

        return info

    def health_check(self) -> bool:
        """
        Check if cache is healthy

        Returns:
            True if cache is accessible, False otherwise
        """
        try:
            if self.using_fallback:
                return self.fallback_cache is not None

            if not self.redis_client:
                return False

            # Test with ping
            self.redis_client.ping()
            return True

        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False

    def __del__(self):
        """Cleanup on deletion"""
        if self.connection_pool:
            try:
                self.connection_pool.disconnect()
            except:
                pass


# Global cache instance
_global_redis_cache: Optional[RedisCache] = None


def get_redis_cache(
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None,
    db: int = 0
) -> RedisCache:
    """
    Get or create global Redis cache instance

    Args:
        host: Redis host
        port: Redis port
        password: Redis password
        db: Redis database number

    Returns:
        RedisCache instance
    """
    global _global_redis_cache

    if _global_redis_cache is None:
        _global_redis_cache = RedisCache(
            host=host,
            port=port,
            password=password,
            db=db,
            fallback_to_memory=True  # Always have fallback for reliability
        )

    return _global_redis_cache


def reset_redis_cache():
    """Reset global cache (for testing)"""
    global _global_redis_cache
    if _global_redis_cache:
        _global_redis_cache.clear_all()
        _global_redis_cache = None
