"""
Multi-Level Cache System
=========================

4-tier caching system optimized for maximum cache hit rate.

Cache Levels:
1. L1: Exact match cache (Redis, ~1ms) - Hash-based key for identical queries
2. L2: Semantic similarity cache (ChromaDB, ~50ms) - Vector similarity for similar queries
3. L3: Intent cache (Redis, ~10ms) - Cache intent classification results
4. L4: RAG results cache (Redis, ~100ms) - Cache RAG retrieval results

Architecture:
- Async-first: All operations are async for maximum performance
- Parallel checks: Check all cache levels simultaneously using asyncio.as_completed()
- Intelligent TTLs: Different TTLs per cache level (L1: 1h, L2: 24h, L3: 6h, L4: 12h)
- Metrics tracking: Track hit rates, latency, and cost savings per level
- Cache warming: Support for pre-warming common queries

Target Performance:
- 75%+ combined cache hit rate
- <8s perceived latency with streaming
- 90% cost reduction through caching

NO MOCKING - Production-grade caching with real infrastructure
"""

import asyncio
import hashlib
import json
import logging
import time
import os
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Redis for L1, L3, L4 caches
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis[asyncio] not installed. Install with: pip install redis[asyncio]")

# Sentence transformers for L2 embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")

# ChromaDB for L2 vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("chromadb not installed. Install with: pip install chromadb")


# Constants
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHROMA_CACHE_DIR = PROJECT_ROOT / "data" / "chromadb_cache"

# TTL values (seconds)
L1_TTL = 3600      # 1 hour - exact matches
L2_TTL = 86400     # 24 hours - semantic matches are stable
L3_TTL = 21600     # 6 hours - intent classifications
L4_TTL = 43200     # 12 hours - RAG results

# Semantic similarity threshold for L2 cache hits
SEMANTIC_THRESHOLD = 0.95


@dataclass
class CacheMetrics:
    """
    Metrics for cache performance tracking

    Tracks hit rates, latency, and cost savings per cache level
    """
    # Hit/miss counters per level
    l1_hits: int = 0
    l1_misses: int = 0
    l2_hits: int = 0
    l2_misses: int = 0
    l3_hits: int = 0
    l3_misses: int = 0
    l4_hits: int = 0
    l4_misses: int = 0

    # Latency tracking (milliseconds)
    l1_latency_sum: float = 0.0
    l2_latency_sum: float = 0.0
    l3_latency_sum: float = 0.0
    l4_latency_sum: float = 0.0

    # Cache operations
    total_puts: int = 0
    total_invalidations: int = 0

    # Cost savings (estimated based on avoided LLM calls)
    cost_saved_usd: float = 0.0

    def get_hit_rate(self, level: Optional[str] = None) -> float:
        """
        Get hit rate for a specific level or overall

        Args:
            level: 'l1', 'l2', 'l3', 'l4', or None for overall

        Returns:
            Hit rate as a percentage (0-100)
        """
        if level == 'l1':
            total = self.l1_hits + self.l1_misses
            return (self.l1_hits / total * 100) if total > 0 else 0.0
        elif level == 'l2':
            total = self.l2_hits + self.l2_misses
            return (self.l2_hits / total * 100) if total > 0 else 0.0
        elif level == 'l3':
            total = self.l3_hits + self.l3_misses
            return (self.l3_hits / total * 100) if total > 0 else 0.0
        elif level == 'l4':
            total = self.l4_hits + self.l4_misses
            return (self.l4_hits / total * 100) if total > 0 else 0.0
        else:
            # Overall hit rate
            total_hits = self.l1_hits + self.l2_hits + self.l3_hits + self.l4_hits
            total_requests = (
                self.l1_hits + self.l1_misses +
                self.l2_hits + self.l2_misses +
                self.l3_hits + self.l3_misses +
                self.l4_hits + self.l4_misses
            )
            # Each request checks all levels, so divide by 4
            total_requests = total_requests // 4 if total_requests > 0 else 1
            return (total_hits / total_requests * 100) if total_requests > 0 else 0.0

    def get_avg_latency(self, level: str) -> float:
        """
        Get average latency for a cache level in milliseconds

        Args:
            level: 'l1', 'l2', 'l3', or 'l4'

        Returns:
            Average latency in milliseconds
        """
        if level == 'l1':
            total = self.l1_hits + self.l1_misses
            return (self.l1_latency_sum / total) if total > 0 else 0.0
        elif level == 'l2':
            total = self.l2_hits + self.l2_misses
            return (self.l2_latency_sum / total) if total > 0 else 0.0
        elif level == 'l3':
            total = self.l3_hits + self.l3_misses
            return (self.l3_latency_sum / total) if total > 0 else 0.0
        elif level == 'l4':
            total = self.l4_hits + self.l4_misses
            return (self.l4_latency_sum / total) if total > 0 else 0.0
        else:
            return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for reporting"""
        return {
            'hit_rates': {
                'l1': round(self.get_hit_rate('l1'), 2),
                'l2': round(self.get_hit_rate('l2'), 2),
                'l3': round(self.get_hit_rate('l3'), 2),
                'l4': round(self.get_hit_rate('l4'), 2),
                'overall': round(self.get_hit_rate(), 2),
            },
            'average_latency_ms': {
                'l1': round(self.get_avg_latency('l1'), 2),
                'l2': round(self.get_avg_latency('l2'), 2),
                'l3': round(self.get_avg_latency('l3'), 2),
                'l4': round(self.get_avg_latency('l4'), 2),
            },
            'operations': {
                'total_puts': self.total_puts,
                'total_invalidations': self.total_invalidations,
            },
            'cost_savings_usd': round(self.cost_saved_usd, 2),
        }


class MultiLevelCache:
    """
    4-tier caching system for maximum cache hit rate

    Features:
    - Parallel cache checks (asyncio.as_completed)
    - Intelligent TTL management per level
    - Semantic similarity matching (L2)
    - Comprehensive metrics tracking
    - Cache warming for common queries

    Usage:
        cache = MultiLevelCache()
        await cache.initialize()

        # Check cache (checks all levels in parallel)
        cached_response = await cache.get_multilevel(message, user_id)

        if cached_response:
            return cached_response

        # Compute response
        response = await compute_response(message)

        # Cache result
        await cache.put(message, user_id, response, intent="question", rag_results=[...])
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        embedding_model: str = 'all-MiniLM-L6-v2',
        semantic_threshold: float = SEMANTIC_THRESHOLD,
    ):
        """
        Initialize multi-level cache

        Args:
            redis_url: Redis connection URL (default: builds from REDIS_HOST/PORT/PASSWORD)
            embedding_model: Sentence transformer model for L2 embeddings
            semantic_threshold: Similarity threshold for L2 cache hits (0-1)
        """
        # Build Redis URL from environment variables (compatible with docker-compose)
        if redis_url:
            self.redis_url = redis_url
        elif os.getenv('REDIS_URL'):
            self.redis_url = os.getenv('REDIS_URL')
        else:
            # Build URL from separate env vars (docker-compose pattern)
            host = os.getenv('REDIS_HOST', 'localhost')
            port = os.getenv('REDIS_PORT', '6379')
            password = os.getenv('REDIS_PASSWORD', '')
            if password:
                self.redis_url = f"redis://:{password}@{host}:{port}"
            else:
                self.redis_url = f"redis://{host}:{port}"
        self.embedding_model_name = embedding_model
        self.semantic_threshold = semantic_threshold

        # Redis client (L1, L3, L4)
        self.redis_client: Optional[aioredis.Redis] = None

        # ChromaDB client (L2)
        self.chroma_client: Optional[chromadb.ClientAPI] = None
        self.chroma_collection: Optional[chromadb.Collection] = None

        # Embedding model (L2)
        self.embedding_model: Optional[SentenceTransformer] = None

        # Metrics
        self.metrics = CacheMetrics()

        # Initialization flag
        self._initialized = False

    async def initialize(self):
        """
        Initialize cache clients (Redis, ChromaDB, embeddings)

        Call this once at application startup
        """
        if self._initialized:
            return

        # Initialize Redis for L1, L3, L4
        if REDIS_AVAILABLE:
            try:
                self.redis_client = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self.redis_client.ping()
                logger.info(f"Redis connected: {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                logger.warning("L1, L3, L4 caches will be disabled")
                self.redis_client = None
        else:
            logger.warning("Redis not available. L1, L3, L4 caches disabled.")

        # Initialize ChromaDB for L2
        if CHROMADB_AVAILABLE:
            try:
                # Ensure directory exists
                CHROMA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

                self.chroma_client = chromadb.PersistentClient(
                    path=str(CHROMA_CACHE_DIR),
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=False
                    )
                )

                # Get or create cache collection
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="response_cache_l2",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"ChromaDB L2 cache initialized: {CHROMA_CACHE_DIR}")
            except Exception as e:
                logger.warning(f"ChromaDB initialization failed: {e}")
                logger.warning("L2 semantic cache will be disabled")
                self.chroma_client = None
                self.chroma_collection = None
        else:
            logger.warning("ChromaDB not available. L2 semantic cache disabled.")

        # Initialize sentence transformer for L2
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info(f"Embedding model loaded: {self.embedding_model_name}")
            except Exception as e:
                logger.warning(f"Embedding model failed to load: {e}")
                logger.warning("L2 semantic cache will be disabled")
                self.embedding_model = None
        else:
            logger.warning("Sentence transformers not available. L2 semantic cache disabled.")

        self._initialized = True

    async def close(self):
        """Close cache connections"""
        if self.redis_client:
            await self.redis_client.close()

    # ===== Multi-level cache operations =====

    async def get_multilevel(
        self,
        message: str,
        user_id: str
    ) -> Optional[str]:
        """
        Check all cache levels in parallel, return first hit

        Strategy:
        1. Launch all cache checks simultaneously (asyncio.as_completed)
        2. Return as soon as ANY level returns a hit
        3. Cancel remaining checks to save resources

        Args:
            message: User message/query
            user_id: User identifier for cache key

        Returns:
            Cached response or None if all levels miss
        """
        if not self._initialized:
            await self.initialize()

        # Create tasks for all cache levels
        tasks = [
            asyncio.create_task(self.get_l1_exact(message, user_id)),
            asyncio.create_task(self.get_l2_semantic(message)),
            asyncio.create_task(self.get_l3_intent(message)),
            asyncio.create_task(self.get_l4_rag(message)),
        ]

        # Wait for first completion
        try:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    # Cache hit! Cancel remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    return result
        except Exception as e:
            logger.error(f"Error in multilevel cache check: {e}")

        # All levels missed
        return None

    async def put(
        self,
        message: str,
        user_id: str,
        response: str,
        intent: Optional[str] = None,
        rag_results: Optional[List[Dict]] = None
    ):
        """
        Cache response to all appropriate levels

        Caching strategy:
        - L1: Always cache full response (exact match)
        - L2: Always cache with embeddings (semantic match)
        - L3: Cache if intent provided
        - L4: Cache if RAG results provided

        Args:
            message: User message/query
            user_id: User identifier
            response: Full response to cache
            intent: Optional intent classification result
            rag_results: Optional RAG retrieval results
        """
        if not self._initialized:
            await self.initialize()

        # Cache to all levels in parallel
        tasks = []

        # L1: Full response with exact match
        tasks.append(asyncio.create_task(
            self.put_l1_exact(message, user_id, response)
        ))

        # L2: Semantic similarity
        tasks.append(asyncio.create_task(
            self.put_l2_semantic(message, response)
        ))

        # L3: Intent classification
        if intent:
            tasks.append(asyncio.create_task(
                self.put_l3_intent(message, intent)
            ))

        # L4: RAG results
        if rag_results:
            tasks.append(asyncio.create_task(
                self.put_l4_rag(message, rag_results)
            ))

        # Wait for all caches to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        self.metrics.total_puts += 1

    # ===== L1: Exact match cache (Redis) =====

    async def get_l1_exact(
        self,
        message: str,
        user_id: str
    ) -> Optional[str]:
        """
        L1 cache: Exact match with user context

        Key: l1:{user_id}:{hash(message)}
        TTL: 1 hour
        Latency: ~1ms
        """
        start_time = time.time()

        try:
            if not self.redis_client:
                self.metrics.l1_misses += 1
                return None

            key = self._make_l1_key(message, user_id)
            cached = await self.redis_client.get(key)

            latency_ms = (time.time() - start_time) * 1000
            self.metrics.l1_latency_sum += latency_ms

            if cached:
                self.metrics.l1_hits += 1
                # Estimate cost savings (GPT-4 response ~$0.03 per request)
                self.metrics.cost_saved_usd += 0.03
                return cached
            else:
                self.metrics.l1_misses += 1
                return None
        except Exception as e:
            logger.debug(f"L1 cache error: {e}")
            self.metrics.l1_misses += 1
            return None

    async def put_l1_exact(
        self,
        message: str,
        user_id: str,
        response: str
    ):
        """Cache full response with exact match"""
        try:
            if not self.redis_client:
                return

            key = self._make_l1_key(message, user_id)
            await self.redis_client.setex(key, L1_TTL, response)
        except Exception as e:
            logger.debug(f"L1 cache put error: {e}")

    def _make_l1_key(self, message: str, user_id: str) -> str:
        """Create L1 cache key"""
        normalized = message.lower().strip()
        msg_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"l1:{user_id}:{msg_hash}"

    # ===== L2: Semantic similarity cache (ChromaDB) =====

    async def get_l2_semantic(
        self,
        message: str,
        threshold: Optional[float] = None
    ) -> Optional[str]:
        """
        L2 cache: Semantic similarity matching

        Uses sentence transformers + ChromaDB to find similar queries
        Returns cached response if similarity >= threshold

        TTL: 24 hours
        Latency: ~50ms
        """
        start_time = time.time()

        try:
            if not self.chroma_collection or not self.embedding_model:
                self.metrics.l2_misses += 1
                return None

            threshold = threshold or self.semantic_threshold

            # Generate embedding for query
            embedding = self.embedding_model.encode(message).tolist()

            # Search in ChromaDB
            results = self.chroma_collection.query(
                query_embeddings=[embedding],
                n_results=1
            )

            latency_ms = (time.time() - start_time) * 1000
            self.metrics.l2_latency_sum += latency_ms

            # Check if we have results and similarity is above threshold
            if (results['ids'] and len(results['ids'][0]) > 0 and
                results['distances'][0][0] is not None):

                # ChromaDB returns distance, convert to similarity
                # For cosine: similarity = 1 - distance
                similarity = 1 - results['distances'][0][0]

                if similarity >= threshold:
                    # Check TTL (stored in metadata)
                    metadata = results['metadatas'][0][0]
                    created_at = metadata.get('created_at', 0)

                    if time.time() - created_at < L2_TTL:
                        response = results['documents'][0][0]
                        self.metrics.l2_hits += 1
                        self.metrics.cost_saved_usd += 0.03
                        return response

            self.metrics.l2_misses += 1
            return None
        except Exception as e:
            logger.debug(f"L2 cache error: {e}")
            self.metrics.l2_misses += 1
            return None

    async def put_l2_semantic(
        self,
        message: str,
        response: str
    ):
        """Cache response with semantic embeddings"""
        try:
            if not self.chroma_collection or not self.embedding_model:
                return

            # Generate embedding
            embedding = self.embedding_model.encode(message).tolist()

            # Create unique ID
            doc_id = hashlib.sha256(message.encode()).hexdigest()[:16]

            # Store in ChromaDB
            self.chroma_collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[response],
                metadatas=[{
                    'message': message[:200],  # Store truncated message for debugging
                    'created_at': time.time()
                }]
            )
        except Exception as e:
            logger.debug(f"L2 cache put error: {e}")

    # ===== L3: Intent cache (Redis) =====

    async def get_l3_intent(self, message: str) -> Optional[str]:
        """
        L3 cache: Intent classification results

        Caches the classified intent for a message
        TTL: 6 hours
        Latency: ~10ms
        """
        start_time = time.time()

        try:
            if not self.redis_client:
                self.metrics.l3_misses += 1
                return None

            key = self._make_l3_key(message)
            cached = await self.redis_client.get(key)

            latency_ms = (time.time() - start_time) * 1000
            self.metrics.l3_latency_sum += latency_ms

            if cached:
                self.metrics.l3_hits += 1
                # Intent classification saves ~$0.001 (GPT-3.5 call)
                self.metrics.cost_saved_usd += 0.001
                return cached
            else:
                self.metrics.l3_misses += 1
                return None
        except Exception as e:
            logger.debug(f"L3 cache error: {e}")
            self.metrics.l3_misses += 1
            return None

    async def put_l3_intent(self, message: str, intent: str):
        """Cache intent classification result"""
        try:
            if not self.redis_client:
                return

            key = self._make_l3_key(message)
            await self.redis_client.setex(key, L3_TTL, intent)
        except Exception as e:
            logger.debug(f"L3 cache put error: {e}")

    def _make_l3_key(self, message: str) -> str:
        """Create L3 cache key"""
        normalized = message.lower().strip()
        msg_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"l3:intent:{msg_hash}"

    # ===== L4: RAG results cache (Redis) =====

    async def get_l4_rag(self, message: str) -> Optional[List[Dict]]:
        """
        L4 cache: RAG retrieval results

        Caches the retrieved documents for a query
        TTL: 12 hours
        Latency: ~100ms (due to JSON deserialization)
        """
        start_time = time.time()

        try:
            if not self.redis_client:
                self.metrics.l4_misses += 1
                return None

            key = self._make_l4_key(message)
            cached = await self.redis_client.get(key)

            latency_ms = (time.time() - start_time) * 1000
            self.metrics.l4_latency_sum += latency_ms

            if cached:
                self.metrics.l4_hits += 1
                # RAG retrieval saves ~$0.005 (embeddings + search)
                self.metrics.cost_saved_usd += 0.005
                return json.loads(cached)
            else:
                self.metrics.l4_misses += 1
                return None
        except Exception as e:
            logger.debug(f"L4 cache error: {e}")
            self.metrics.l4_misses += 1
            return None

    async def put_l4_rag(self, message: str, rag_results: List[Dict]):
        """Cache RAG retrieval results"""
        try:
            if not self.redis_client:
                return

            key = self._make_l4_key(message)
            # Serialize to JSON
            serialized = json.dumps(rag_results)
            await self.redis_client.setex(key, L4_TTL, serialized)
        except Exception as e:
            logger.debug(f"L4 cache put error: {e}")

    def _make_l4_key(self, message: str) -> str:
        """Create L4 cache key"""
        normalized = message.lower().strip()
        msg_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"l4:rag:{msg_hash}"

    # ===== Cache management =====

    async def invalidate(self, message: str, user_id: Optional[str] = None):
        """
        Invalidate cache entries for a message

        Args:
            message: Message to invalidate
            user_id: Optional user ID (if None, invalidates for all users)
        """
        tasks = []

        if self.redis_client:
            # Invalidate L1 (if user_id provided)
            if user_id:
                key_l1 = self._make_l1_key(message, user_id)
                tasks.append(self.redis_client.delete(key_l1))

            # Invalidate L3
            key_l3 = self._make_l3_key(message)
            tasks.append(self.redis_client.delete(key_l3))

            # Invalidate L4
            key_l4 = self._make_l4_key(message)
            tasks.append(self.redis_client.delete(key_l4))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self.metrics.total_invalidations += 1

    async def warm_cache(self, queries: List[Tuple[str, str, str]]):
        """
        Warm cache with common queries

        Args:
            queries: List of (message, user_id, response) tuples
        """
        for message, user_id, response in queries:
            await self.put(message, user_id, response)

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        return self.metrics.to_dict()

    def reset_metrics(self):
        """Reset metrics (useful for testing)"""
        self.metrics = CacheMetrics()


# Global cache instance
_global_cache: Optional[MultiLevelCache] = None


async def get_cache() -> MultiLevelCache:
    """
    Get or create global cache instance

    Returns:
        Initialized MultiLevelCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MultiLevelCache()
        await _global_cache.initialize()
    return _global_cache


async def close_cache():
    """Close global cache instance"""
    global _global_cache
    if _global_cache:
        await _global_cache.close()
        _global_cache = None
