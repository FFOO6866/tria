"""
Response Caching Layer
=======================

Cache responses to dramatically reduce latency for repeated queries.

Cache Levels:
1. Intent classification cache (by message hash)
2. Policy retrieval cache (by query + collection)
3. Full response cache (by message + intent)

Cache Strategy:
- TTL-based expiration (default: 1 hour for responses, 24 hours for policies)
- LRU eviction when size limit reached
- Configurable cache size

NO MOCKING - Production-grade caching
"""

import hashlib
import time
import json
from typing import Dict, Optional, Any, Tuple
from collections import OrderedDict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: float
    hits: int = 0
    ttl_seconds: int = 3600

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() - self.created_at > self.ttl_seconds

    def is_valid(self) -> bool:
        """Check if entry is still valid"""
        return not self.is_expired()


class LRUCache:
    """
    Simple LRU cache with TTL support

    Features:
    - Least Recently Used eviction
    - Time-to-live expiration
    - Hit rate tracking
    - Memory-bounded
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }

    def _make_key(self, *args, **kwargs) -> str:
        """Create cache key from arguments"""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.stats["misses"] += 1
            return None

        entry = self.cache[key]

        # Check if expired
        if entry.is_expired():
            del self.cache[key]
            self.stats["expirations"] += 1
            self.stats["misses"] += 1
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.hits += 1
        self.stats["hits"] += 1

        return entry.value

    def put(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Put value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override (seconds)
        """
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.stats["evictions"] += 1

        # Create entry
        entry = CacheEntry(
            value=value,
            created_at=time.time(),
            ttl_seconds=ttl or self.default_ttl
        )

        # Update cache
        self.cache[key] = entry
        self.cache.move_to_end(key)

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": round(hit_rate, 3),
            "evictions": self.stats["evictions"],
            "expirations": self.stats["expirations"],
            "total_requests": total_requests
        }


class ResponseCache:
    """
    Multi-level cache for chatbot responses

    Cache Levels:
    1. Intent cache - Stores intent classification results
    2. Retrieval cache - Stores RAG retrieval results
    3. Response cache - Stores complete responses
    """

    def __init__(
        self,
        intent_cache_size: int = 1000,
        retrieval_cache_size: int = 500,
        response_cache_size: int = 100,
        intent_ttl: int = 3600,      # 1 hour
        retrieval_ttl: int = 86400,  # 24 hours
        response_ttl: int = 1800     # 30 minutes
    ):
        """
        Initialize multi-level cache

        Args:
            intent_cache_size: Max intent classifications to cache
            retrieval_cache_size: Max retrievals to cache
            response_cache_size: Max complete responses to cache
            intent_ttl: Intent cache TTL (seconds)
            retrieval_ttl: Retrieval cache TTL (seconds)
            response_ttl: Response cache TTL (seconds)
        """
        self.intent_cache = LRUCache(intent_cache_size, intent_ttl)
        self.retrieval_cache = LRUCache(retrieval_cache_size, retrieval_ttl)
        self.response_cache = LRUCache(response_cache_size, response_ttl)

    def get_intent(self, message: str) -> Optional[Dict]:
        """Get cached intent classification"""
        key = self._hash_message(message)
        return self.intent_cache.get(key)

    def put_intent(self, message: str, intent_result: Dict):
        """Cache intent classification"""
        key = self._hash_message(message)
        self.intent_cache.put(key, intent_result)

    def get_retrieval(
        self,
        query: str,
        collection: str,
        top_n: int
    ) -> Optional[list]:
        """Get cached retrieval results"""
        key = self.retrieval_cache._make_key(query, collection, top_n)
        return self.retrieval_cache.get(key)

    def put_retrieval(
        self,
        query: str,
        collection: str,
        top_n: int,
        results: list
    ):
        """Cache retrieval results"""
        key = self.retrieval_cache._make_key(query, collection, top_n)
        self.retrieval_cache.put(key, results)

    def get_response(self, message: str, intent: str) -> Optional[str]:
        """Get cached complete response"""
        key = self._hash_message(f"{message}_{intent}")
        return self.response_cache.get(key)

    def put_response(self, message: str, intent: str, response: str):
        """Cache complete response"""
        key = self._hash_message(f"{message}_{intent}")
        self.response_cache.put(key, response)

    def _hash_message(self, message: str) -> str:
        """Create hash of message for cache key"""
        # Normalize: lowercase, strip whitespace
        normalized = message.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def clear_all(self):
        """Clear all caches"""
        self.intent_cache.clear()
        self.retrieval_cache.clear()
        self.response_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all cache levels"""
        return {
            "intent_cache": self.intent_cache.get_stats(),
            "retrieval_cache": self.retrieval_cache.get_stats(),
            "response_cache": self.response_cache.get_stats(),
            "total_size_mb": self._estimate_size_mb()
        }

    def _estimate_size_mb(self) -> float:
        """Rough estimate of cache memory usage"""
        # Very rough estimate: ~1KB per intent, ~5KB per retrieval, ~2KB per response
        intent_mb = len(self.intent_cache.cache) * 1 / 1024
        retrieval_mb = len(self.retrieval_cache.cache) * 5 / 1024
        response_mb = len(self.response_cache.cache) * 2 / 1024
        return round(intent_mb + retrieval_mb + response_mb, 2)


# Global cache instance
_global_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """Get or create global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache()
    return _global_cache


def reset_cache():
    """Reset global cache (for testing)"""
    global _global_cache
    if _global_cache:
        _global_cache.clear_all()
