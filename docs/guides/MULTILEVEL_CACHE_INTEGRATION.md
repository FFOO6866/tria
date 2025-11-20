# Multi-Level Cache Integration Guide

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
# Install Redis async client
pip install redis[asyncio]

# Dependencies already installed:
# - chromadb (for L2 semantic cache)
# - sentence-transformers (for embeddings)
```

### 2. Start Redis

```bash
# Option A: Docker (recommended for development)
docker run -d -p 6379:6379 --name tria-redis redis:alpine

# Option B: Use existing Redis Cloud/AWS ElastiCache
# Set REDIS_URL environment variable
export REDIS_URL=rediss://username:password@host:port
```

### 3. Integrate with Your Agent

```python
# src/agents/enhanced_customer_service_agent.py

from services.multilevel_cache import get_cache

class EnhancedCustomerServiceAgent:
    def __init__(self):
        # ... existing initialization ...
        self.cache = None  # Will be initialized on first use

    async def _ensure_cache(self):
        """Lazy cache initialization"""
        if self.cache is None:
            self.cache = await get_cache()

    async def handle_message(
        self,
        message: str,
        user_id: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Handle incoming message with multi-level caching

        Flow:
        1. Check cache (all 4 levels in parallel)
        2. If hit: Return cached response (~1-100ms)
        3. If miss: Full processing + cache result
        """
        await self._ensure_cache()

        # Check cache first
        cached_response = await self.cache.get_multilevel(message, user_id)
        if cached_response:
            # Cache hit! Return immediately
            print(f"Cache hit for user {user_id}")
            return cached_response

        # Cache miss - proceed with full processing
        print(f"Cache miss for user {user_id} - processing...")

        # Existing logic (unchanged)
        intent_result = await self.classify_intent(message, conversation_history)
        intent = intent_result.get('intent', 'unknown')

        retrieved_docs = await self.retrieve_knowledge(message)

        response = await self.generate_response(
            message=message,
            intent=intent,
            retrieved_docs=retrieved_docs,
            conversation_history=conversation_history
        )

        # Cache the result for future requests
        await self.cache.put(
            message=message,
            user_id=user_id,
            response=response,
            intent=intent,
            rag_results=retrieved_docs
        )

        return response
```

### 4. Update API Endpoint

```python
# src/enhanced_api.py

from services.multilevel_cache import get_cache

# In startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("Starting up...")

    # Initialize cache
    cache = await get_cache()
    print(f"Cache initialized")

    # Display cache info
    if cache.redis_client:
        print("✓ Redis connected (L1, L3, L4 enabled)")
    else:
        print("⚠ Redis not available (L1, L3, L4 disabled)")

    if cache.chroma_collection:
        print("✓ ChromaDB connected (L2 enabled)")
    else:
        print("⚠ ChromaDB not available (L2 disabled)")

# In shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    from services.multilevel_cache import close_cache
    await close_cache()
    print("Cache closed")
```

### 5. Add Cache Metrics Endpoint

```python
# src/enhanced_api.py

from services.multilevel_cache import get_cache

@app.get("/cache/metrics")
async def get_cache_metrics():
    """Get cache performance metrics"""
    cache = await get_cache()
    metrics = cache.get_metrics()

    return {
        "status": "ok",
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    }
```

## Advanced Integration

### Cache Warming on Startup

```python
# scripts/warm_cache.py

import asyncio
from services.multilevel_cache import get_cache

COMMON_QUERIES = [
    ("What is your return policy?", "Our return policy allows returns within 30 days."),
    ("How do I track my order?", "Check your email for a tracking link."),
    ("What are your shipping options?", "We offer standard and express shipping."),
    # ... add more common queries
]

async def warm_cache():
    """Pre-populate cache with common queries"""
    cache = await get_cache()

    queries_to_warm = [
        (query, "generic_user", response)
        for query, response in COMMON_QUERIES
    ]

    await cache.warm_cache(queries_to_warm)
    print(f"Cache warmed with {len(queries_to_warm)} queries")

    metrics = cache.get_metrics()
    print(f"Cache metrics: {metrics}")

if __name__ == "__main__":
    asyncio.run(warm_cache())
```

Run on startup:
```bash
python scripts/warm_cache.py
```

### Cache Invalidation on Content Update

```python
# When knowledge base is updated
async def update_knowledge_base(doc_id: str, content: str):
    """Update knowledge base and invalidate related cache"""
    # Update document
    await knowledge_base.update(doc_id, content)

    # Invalidate related cache entries
    cache = await get_cache()

    # Invalidate queries related to this document
    related_queries = await find_related_queries(doc_id)
    for query in related_queries:
        await cache.invalidate(query)

    print(f"Invalidated {len(related_queries)} cache entries")
```

### Monitoring Dashboard Integration

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

cache_hits = Counter('cache_hits_total', 'Total cache hits', ['level'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['level'])
cache_latency = Histogram('cache_latency_seconds', 'Cache latency', ['level'])
cache_cost_saved = Gauge('cache_cost_saved_usd', 'Cost saved by caching')

async def track_cache_metrics():
    """Update Prometheus metrics from cache"""
    cache = await get_cache()
    metrics = cache.metrics

    # Update counters
    cache_hits.labels(level='l1')._value._value = metrics.l1_hits
    cache_hits.labels(level='l2')._value._value = metrics.l2_hits
    cache_hits.labels(level='l3')._value._value = metrics.l3_hits
    cache_hits.labels(level='l4')._value._value = metrics.l4_hits

    cache_misses.labels(level='l1')._value._value = metrics.l1_misses
    cache_misses.labels(level='l2')._value._value = metrics.l2_misses
    cache_misses.labels(level='l3')._value._value = metrics.l3_misses
    cache_misses.labels(level='l4')._value._value = metrics.l4_misses

    cache_cost_saved.set(metrics.cost_saved_usd)
```

## Configuration

### Environment Variables

```bash
# .env file

# Redis connection (required for L1, L3, L4)
REDIS_URL=redis://localhost:6379

# Or for Redis Cloud
REDIS_URL=rediss://default:password@redis-12345.cloud.redislabs.com:12345

# Optional: Semantic similarity threshold (0-1, default: 0.95)
SEMANTIC_THRESHOLD=0.95

# Optional: Embedding model (default: all-MiniLM-L6-v2)
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Custom TTLs

```python
from services.multilevel_cache import MultiLevelCache

# Create cache with custom TTLs
cache = MultiLevelCache()

# Modify TTL constants before initialization
import services.multilevel_cache as cache_module
cache_module.L1_TTL = 7200  # 2 hours instead of 1
cache_module.L2_TTL = 172800  # 48 hours instead of 24

await cache.initialize()
```

## Testing Integration

### Test Cache in Development

```python
# tests/test_agent_with_cache.py

import pytest
from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent

@pytest.mark.asyncio
async def test_agent_cache_hit():
    """Test agent returns cached response on second call"""
    agent = EnhancedCustomerServiceAgent()

    message = "What is your return policy?"
    user_id = "test_user"

    # First call: cache miss (full processing)
    response1 = await agent.handle_message(message, user_id)
    assert "return" in response1.lower()

    # Second call: cache hit (instant)
    response2 = await agent.handle_message(message, user_id)
    assert response2 == response1  # Should be identical

    # Check metrics
    metrics = agent.cache.get_metrics()
    assert metrics['hit_rates']['overall'] > 0
```

## Troubleshooting

### Cache Not Working

**Symptom**: All requests are cache misses

**Check**:
1. Is Redis running? `redis-cli ping` should return `PONG`
2. Is `REDIS_URL` set correctly?
3. Check logs for connection errors

**Fix**:
```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Verify connection
redis-cli ping
```

### Low Cache Hit Rate

**Symptom**: Hit rate < 50% after warmup

**Possible Causes**:
1. TTLs too short (cache expiring too fast)
2. High query variance (users asking unique questions)
3. Semantic threshold too high (L2 not matching similar queries)

**Fix**:
```python
# Increase TTLs
L1_TTL = 7200  # 2 hours
L2_TTL = 172800  # 48 hours

# Lower semantic threshold
cache = MultiLevelCache(semantic_threshold=0.90)  # Default: 0.95
```

### High Memory Usage

**Symptom**: Redis using too much memory

**Fix**:
```bash
# Configure Redis maxmemory and eviction policy
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### L2 Semantic Cache Not Working

**Symptom**: L2 hit rate is 0%

**Check**:
1. Is sentence-transformers installed? `pip list | grep sentence`
2. Are embeddings being generated? Check logs
3. Is ChromaDB collection created?

**Fix**:
```bash
# Reinstall sentence-transformers with compatible numpy
pip install "numpy<2"
pip install --force-reinstall sentence-transformers
```

## Performance Tuning

### Optimize for High Traffic

```python
# Use connection pooling for Redis
from redis.asyncio import ConnectionPool

pool = ConnectionPool.from_url(
    "redis://localhost:6379",
    max_connections=50,  # Increase for high concurrency
    decode_responses=True
)

cache = MultiLevelCache(redis_pool=pool)
```

### Optimize Semantic Search

```python
# Use faster embedding model for L2
cache = MultiLevelCache(
    embedding_model='all-MiniLM-L6-v2'  # Fast (default)
    # embedding_model='all-mpnet-base-v2'  # Slower but more accurate
)
```

### Monitor Performance

```python
# Add timing to agent
import time

async def handle_message(self, message, user_id):
    start = time.time()

    cached = await self.cache.get_multilevel(message, user_id)
    cache_time = time.time() - start

    if cached:
        print(f"Cache hit in {cache_time*1000:.2f}ms")
        return cached

    # Full processing
    response = await self._full_processing(message, user_id)
    total_time = time.time() - start

    print(f"Full processing: {total_time:.2f}s")
    return response
```

## Production Checklist

- [ ] Redis deployed (Cloud/ElastiCache/self-hosted)
- [ ] `REDIS_URL` configured in production environment
- [ ] Cache warming script runs on startup
- [ ] Cache metrics endpoint enabled
- [ ] Monitoring/alerting configured
  - [ ] Alert if hit rate < 60%
  - [ ] Alert if Redis down
  - [ ] Alert if high memory usage
- [ ] TTLs configured for your use case
- [ ] Semantic threshold tuned (default: 0.95)
- [ ] Connection pool sized appropriately
- [ ] Redis eviction policy set (allkeys-lru)
- [ ] Redis maxmemory configured
- [ ] Backup/persistence enabled for Redis

## Success Metrics

Track these after deployment:

```python
# Daily metrics report
metrics = cache.get_metrics()

print(f"Overall hit rate: {metrics['hit_rates']['overall']:.1f}%")
print(f"L1 hit rate: {metrics['hit_rates']['l1']:.1f}%")
print(f"L2 hit rate: {metrics['hit_rates']['l2']:.1f}%")
print(f"L3 hit rate: {metrics['hit_rates']['l3']:.1f}%")
print(f"L4 hit rate: {metrics['hit_rates']['l4']:.1f}%")
print(f"Cost saved today: ${metrics['cost_savings_usd']:.2f}")
```

**Target Metrics**:
- Overall hit rate: **75%+**
- L1 hit rate: **30-35%**
- Average cache latency: **<100ms**
- Cost reduction: **70-90%**

## Support

For issues or questions:
1. Check logs for error messages
2. Verify Redis/ChromaDB connections
3. Review troubleshooting section above
4. Check test suite: `pytest tests/test_multilevel_cache.py -v`
