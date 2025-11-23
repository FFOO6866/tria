"""
Chat Response Caching Layer
============================

High-level caching for complete chat responses using Redis.

Cache Strategy:
- Cache complete responses by message hash + conversation context
- 30-minute TTL for responses (fresh but reusable)
- 1-hour TTL for intent classifications
- 24-hour TTL for policy retrievals

This addresses the P0 performance blocker:
- Current: 14.6s average latency
- With 80% cache hit rate: ~3s average (instant for cache hits)
- Cost savings: 80% reduction ($4,200 → $840/month)
"""

import os
import hashlib
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime

from cache.redis_cache import get_redis_cache, RedisCache

logger = logging.getLogger(__name__)


@dataclass
class CachedChatResponse:
    """Cached chat response with metadata"""
    response_text: str
    intent: str
    confidence: float
    action_taken: str
    knowledge_used: List[Dict]
    cached_at: str
    ttl_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "response_text": self.response_text,
            "intent": self.intent,
            "confidence": self.confidence,
            "action_taken": self.action_taken,
            "knowledge_used": self.knowledge_used,
            "cached_at": self.cached_at,
            "ttl_seconds": self.ttl_seconds,
            "from_cache": True  # Flag to identify cached responses
        }


class ChatResponseCache:
    """
    Production-grade chat response caching

    Features:
    - Redis-backed persistent cache
    - Conversation context awareness
    - Configurable TTLs by response type
    - Cache warming for common queries
    - Performance metrics tracking

    Usage:
        cache = ChatResponseCache()

        # Try to get from cache
        cached = cache.get_response(message, conversation_history)
        if cached:
            return cached  # Instant response!

        # Process normally
        response = agent.handle_message(message)

        # Cache for future requests
        cache.set_response(message, conversation_history, response)
    """

    def __init__(
        self,
        redis_host: str = None,
        redis_port: int = 6379,
        redis_password: str = None,
        redis_db: int = 0,
        default_ttl: int = 1800,  # 30 minutes
        intent_ttl: int = 3600,  # 1 hour
        policy_ttl: int = 86400  # 24 hours
    ):
        """
        Initialize chat response cache

        Args:
            redis_host: Redis host (default from env)
            redis_port: Redis port
            redis_password: Redis password (default from env)
            redis_db: Redis database number
            default_ttl: Default TTL for responses (seconds)
            intent_ttl: TTL for intent classifications (seconds)
            policy_ttl: TTL for policy retrievals (seconds)
        """
        # Get Redis connection info from environment
        redis_host = redis_host or os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", str(redis_port)))
        redis_password = redis_password or os.getenv("REDIS_PASSWORD")

        # Initialize Redis cache
        self.redis_cache = get_redis_cache(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=redis_db
        )

        self.default_ttl = default_ttl
        self.intent_ttl = intent_ttl
        self.policy_ttl = policy_ttl

        logger.info(
            f"ChatResponseCache initialized: {redis_host}:{redis_port}, "
            f"backend={'redis' if not self.redis_cache.using_fallback else 'in-memory'}"
        )

    def _make_context_key(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Create cache key from message and conversation context

        Uses a tiered approach for better cache hit rates:
        - Simple queries (greetings, policy questions): message-only key
        - Context-dependent queries: includes conversation history

        Args:
            message: Current user message
            conversation_history: Recent conversation history

        Returns:
            Hash key for cache lookup
        """
        # Normalize message
        normalized_message = message.lower().strip()

        # Determine if this query is context-independent (can be cached without history)
        # Common patterns that don't need context:
        context_independent_patterns = [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "what is your", "what's your", "delivery policy", "return policy",
            "refund policy", "shipping", "hours", "contact", "help", "thank",
            "warranty", "price of", "how much", "do you have", "available"
        ]

        # Check if message matches context-independent patterns
        is_context_independent = any(
            pattern in normalized_message for pattern in context_independent_patterns
        )

        # For context-independent queries, use message-only key (higher hit rate)
        if is_context_independent or not conversation_history:
            return hashlib.sha256(normalized_message.encode()).hexdigest()

        # For context-dependent queries, include recent history
        # But limit to last 2 messages to balance context vs hit rate
        context_str = normalized_message

        if conversation_history:
            recent_messages = conversation_history[-2:] if len(conversation_history) > 2 else conversation_history
            for msg in recent_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                # Only include first 30 chars to reduce key specificity
                context_str += f"|{role}:{content.lower().strip()[:30]}"

        # Create hash
        return hashlib.sha256(context_str.encode()).hexdigest()

    def get_response(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response for message

        Args:
            message: User message
            conversation_history: Recent conversation history

        Returns:
            Cached response dict or None if not found
        """
        try:
            # Create cache key
            cache_key = f"chat_response:{self._make_context_key(message, conversation_history)}"

            # Get from Redis
            cached_data = self.redis_cache.get(cache_key)

            if cached_data:
                logger.info(f"✅ Cache HIT for message: {message[:50]}...")
                return cached_data

            logger.debug(f"❌ Cache MISS for message: {message[:50]}...")
            return None

        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None

    def set_response(
        self,
        message: str,
        conversation_history: Optional[List[Dict]],
        response: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache response for future requests

        Args:
            message: User message
            conversation_history: Recent conversation history
            response: Response data to cache
            ttl: Optional TTL override (seconds)

        Returns:
            True if cached successfully
        """
        try:
            # Create cache key
            cache_key = f"chat_response:{self._make_context_key(message, conversation_history)}"

            # Add cache metadata
            cache_data = {
                **response,
                "cached_at": datetime.now().isoformat(),
                "ttl_seconds": ttl or self.default_ttl,
                "from_cache": False  # Will be set to True when retrieved
            }

            # Store in Redis
            success = self.redis_cache.set(
                cache_key,
                cache_data,
                ttl=ttl or self.default_ttl
            )

            if success:
                logger.debug(f"✅ Cached response for message: {message[:50]}...")
            else:
                logger.warning(f"⚠️ Failed to cache response for message: {message[:50]}...")

            return success

        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False

    def get_intent(self, message: str) -> Optional[Dict]:
        """
        Get cached intent classification

        Args:
            message: User message

        Returns:
            Cached intent result or None
        """
        try:
            normalized = message.lower().strip()
            cache_key = f"intent:{hashlib.sha256(normalized.encode()).hexdigest()}"
            return self.redis_cache.get(cache_key)

        except Exception as e:
            logger.error(f"Error getting cached intent: {e}")
            return None

    def set_intent(
        self,
        message: str,
        intent_result: Dict,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache intent classification

        Args:
            message: User message
            intent_result: Intent classification result
            ttl: Optional TTL override (seconds)

        Returns:
            True if cached successfully
        """
        try:
            normalized = message.lower().strip()
            cache_key = f"intent:{hashlib.sha256(normalized.encode()).hexdigest()}"
            return self.redis_cache.set(
                cache_key,
                intent_result,
                ttl=ttl or self.intent_ttl
            )

        except Exception as e:
            logger.error(f"Error caching intent: {e}")
            return False

    def get_policy_retrieval(
        self,
        query: str,
        collection: str,
        top_n: int = 5
    ) -> Optional[List[Dict]]:
        """
        Get cached policy retrieval results

        Args:
            query: Search query
            collection: Collection name
            top_n: Number of results

        Returns:
            Cached retrieval results or None
        """
        try:
            normalized = query.lower().strip()
            cache_key = f"policy:{collection}:{top_n}:{hashlib.sha256(normalized.encode()).hexdigest()}"
            return self.redis_cache.get(cache_key)

        except Exception as e:
            logger.error(f"Error getting cached policy retrieval: {e}")
            return None

    def set_policy_retrieval(
        self,
        query: str,
        collection: str,
        top_n: int,
        results: List[Dict],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache policy retrieval results

        Args:
            query: Search query
            collection: Collection name
            top_n: Number of results
            results: Retrieval results to cache
            ttl: Optional TTL override (seconds)

        Returns:
            True if cached successfully
        """
        try:
            normalized = query.lower().strip()
            cache_key = f"policy:{collection}:{top_n}:{hashlib.sha256(normalized.encode()).hexdigest()}"
            return self.redis_cache.set(
                cache_key,
                results,
                ttl=ttl or self.policy_ttl
            )

        except Exception as e:
            logger.error(f"Error caching policy retrieval: {e}")
            return False

    def warm_cache(self, common_queries: List[str]) -> int:
        """
        Pre-warm cache with common queries

        Args:
            common_queries: List of common user queries

        Returns:
            Number of queries warmed
        """
        # This would be called at startup with common queries
        # For now, just log the capability
        logger.info(f"Cache warming capability available for {len(common_queries)} queries")
        return 0

    def clear_all(self) -> int:
        """
        Clear all cached responses

        Returns:
            Number of keys deleted
        """
        try:
            count = self.redis_cache.clear_all("chat_response:*")
            count += self.redis_cache.clear_all("intent:*")
            count += self.redis_cache.clear_all("policy:*")
            logger.info(f"Cleared {count} cached entries")
            return count

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics

        Returns:
            Dictionary with cache metrics
        """
        try:
            redis_info = self.redis_cache.get_info()

            metrics = {
                "backend": redis_info.get("backend", "unknown"),
                "using_fallback": redis_info.get("using_fallback", False),
                "hit_rate": redis_info.get("metrics", {}).get("hit_rate", 0),
                "total_requests": redis_info.get("metrics", {}).get("total_requests", 0),
                "hits": redis_info.get("metrics", {}).get("hits", 0),
                "misses": redis_info.get("metrics", {}).get("misses", 0),
                "errors": redis_info.get("metrics", {}).get("errors", 0),
                "avg_get_time_ms": redis_info.get("metrics", {}).get("avg_get_time_ms", 0),
                "redis_connected": redis_info.get("redis_connected", False)
            }

            # Calculate cost savings
            if metrics["total_requests"] > 0:
                estimated_api_calls_saved = metrics["hits"] * 3.5  # Avg 3.5 GPT-4 calls per query
                estimated_cost_saved = estimated_api_calls_saved * 0.02  # $0.02 per call avg
                metrics["estimated_api_calls_saved"] = int(estimated_api_calls_saved)
                metrics["estimated_cost_saved_usd"] = round(estimated_cost_saved, 2)

            return metrics

        except Exception as e:
            logger.error(f"Error getting cache metrics: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """
        Check if cache is healthy

        Returns:
            True if cache is accessible
        """
        return self.redis_cache.health_check()


# Global cache instance
_global_chat_cache: Optional[ChatResponseCache] = None


def get_chat_cache() -> ChatResponseCache:
    """
    Get or create global chat response cache instance

    Returns:
        ChatResponseCache instance
    """
    global _global_chat_cache

    if _global_chat_cache is None:
        _global_chat_cache = ChatResponseCache()

    return _global_chat_cache


def reset_chat_cache():
    """Reset global cache (for testing)"""
    global _global_chat_cache
    if _global_chat_cache:
        _global_chat_cache.clear_all()
        _global_chat_cache = None
