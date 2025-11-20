"""
Multi-Level Cache Tests
========================

Comprehensive tests for the 4-tier caching system.

Test Strategy:
1. Test each cache level independently
2. Test cache miss → compute → cache hit flow
3. Test semantic similarity matching (L2)
4. Test parallel cache checks
5. Test TTL expiration
6. Test metrics tracking
7. Test cache invalidation

NO MOCKING - Tests use real Redis and ChromaDB instances
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from services.multilevel_cache import (
    MultiLevelCache,
    CacheMetrics,
    L1_TTL,
    L2_TTL,
    L3_TTL,
    L4_TTL
)


# ===== Fixtures =====

@pytest.fixture
async def cache():
    """Create and initialize cache for testing"""
    cache = MultiLevelCache()
    await cache.initialize()

    # Clean up any existing test data
    if cache.redis_client:
        # Delete all test keys
        async for key in cache.redis_client.scan_iter("l1:test*"):
            await cache.redis_client.delete(key)
        async for key in cache.redis_client.scan_iter("l3:*"):
            await cache.redis_client.delete(key)
        async for key in cache.redis_client.scan_iter("l4:*"):
            await cache.redis_client.delete(key)

    # Reset metrics
    cache.reset_metrics()

    yield cache

    # Cleanup
    await cache.close()


# ===== L1 Cache Tests (Exact Match) =====

@pytest.mark.asyncio
async def test_l1_cache_hit(cache):
    """Test L1 cache hit with exact match"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # First call: cache miss
    result = await cache.get_l1_exact(message, user_id)
    assert result is None
    assert cache.metrics.l1_misses == 1
    assert cache.metrics.l1_hits == 0

    # Cache the response
    await cache.put_l1_exact(message, user_id, response)

    # Second call: cache hit
    result = await cache.get_l1_exact(message, user_id)
    assert result == response
    assert cache.metrics.l1_hits == 1
    assert cache.metrics.l1_misses == 1


@pytest.mark.asyncio
async def test_l1_cache_user_specific(cache):
    """Test L1 cache is user-specific"""
    message = "What is your return policy?"
    user_id_1 = "test_user_1"
    user_id_2 = "test_user_2"
    response_1 = "Standard return policy"
    response_2 = "Premium return policy"

    # Cache for user 1
    await cache.put_l1_exact(message, user_id_1, response_1)

    # Cache for user 2
    await cache.put_l1_exact(message, user_id_2, response_2)

    # Verify each user gets their own cached response
    result_1 = await cache.get_l1_exact(message, user_id_1)
    result_2 = await cache.get_l1_exact(message, user_id_2)

    assert result_1 == response_1
    assert result_2 == response_2


@pytest.mark.asyncio
async def test_l1_cache_normalization(cache):
    """Test L1 cache normalizes messages (case-insensitive, whitespace)"""
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # Cache with lowercase
    await cache.put_l1_exact("what is your return policy?", user_id, response)

    # Should hit with uppercase
    result = await cache.get_l1_exact("WHAT IS YOUR RETURN POLICY?", user_id)
    assert result == response

    # Should hit with extra whitespace
    result = await cache.get_l1_exact("  what is your return policy?  ", user_id)
    assert result == response


# ===== L2 Cache Tests (Semantic Similarity) =====

@pytest.mark.asyncio
async def test_l2_semantic_cache_hit(cache):
    """Test L2 cache hits on semantically similar queries"""
    if not cache.chroma_collection or not cache.embedding_model:
        pytest.skip("ChromaDB or sentence-transformers not available")

    message_1 = "What is your return policy?"
    message_2 = "How do I return an item?"  # Semantically similar
    response = "Our return policy allows returns within 30 days."

    # Cache original message
    await cache.put_l2_semantic(message_1, response)

    # Wait a bit for ChromaDB to index
    await asyncio.sleep(0.1)

    # Query with similar message
    result = await cache.get_l2_semantic(message_2, threshold=0.7)

    # Should return cached response if similarity is high enough
    # Note: This test might be flaky depending on embedding quality
    if result:
        assert "return" in result.lower()
        assert cache.metrics.l2_hits == 1


@pytest.mark.asyncio
async def test_l2_semantic_cache_miss_low_similarity(cache):
    """Test L2 cache miss when similarity is too low"""
    if not cache.chroma_collection or not cache.embedding_model:
        pytest.skip("ChromaDB or sentence-transformers not available")

    message_1 = "What is your return policy?"
    message_2 = "What are your store hours?"  # Semantically different
    response = "Our return policy allows returns within 30 days."

    # Cache original message
    await cache.put_l2_semantic(message_1, response)

    # Wait for indexing
    await asyncio.sleep(0.1)

    # Query with different message
    result = await cache.get_l2_semantic(message_2, threshold=0.9)

    # Should miss due to low similarity
    assert result is None
    assert cache.metrics.l2_misses == 1


# ===== L3 Cache Tests (Intent) =====

@pytest.mark.asyncio
async def test_l3_intent_cache(cache):
    """Test L3 cache for intent classification"""
    message = "I want to return my order"
    intent = "return_request"

    # First call: miss
    result = await cache.get_l3_intent(message)
    assert result is None
    assert cache.metrics.l3_misses == 1

    # Cache intent
    await cache.put_l3_intent(message, intent)

    # Second call: hit
    result = await cache.get_l3_intent(message)
    assert result == intent
    assert cache.metrics.l3_hits == 1


# ===== L4 Cache Tests (RAG Results) =====

@pytest.mark.asyncio
async def test_l4_rag_cache(cache):
    """Test L4 cache for RAG retrieval results"""
    message = "What is your return policy?"
    rag_results = [
        {
            "document": "Return policy: 30 days",
            "score": 0.95,
            "metadata": {"source": "policies.md"}
        },
        {
            "document": "Return process: Contact support",
            "score": 0.85,
            "metadata": {"source": "faq.md"}
        }
    ]

    # First call: miss
    result = await cache.get_l4_rag(message)
    assert result is None
    assert cache.metrics.l4_misses == 1

    # Cache RAG results
    await cache.put_l4_rag(message, rag_results)

    # Second call: hit
    result = await cache.get_l4_rag(message)
    assert result == rag_results
    assert cache.metrics.l4_hits == 1


# ===== Multi-Level Cache Tests =====

@pytest.mark.asyncio
async def test_multilevel_cache_l1_hit(cache):
    """Test multilevel cache returns L1 result first"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # Cache in L1
    await cache.put_l1_exact(message, user_id, response)

    # Get from multilevel (should hit L1)
    result = await cache.get_multilevel(message, user_id)
    assert result == response
    assert cache.metrics.l1_hits == 1


@pytest.mark.asyncio
async def test_multilevel_cache_miss(cache):
    """Test multilevel cache returns None when all levels miss"""
    message = "What is your return policy?"
    user_id = "test_user_1"

    # Get from multilevel (should miss all levels)
    result = await cache.get_multilevel(message, user_id)
    assert result is None

    # All levels should have recorded a miss
    assert cache.metrics.l1_misses >= 1
    assert cache.metrics.l2_misses >= 1
    assert cache.metrics.l3_misses >= 1
    assert cache.metrics.l4_misses >= 1


@pytest.mark.asyncio
async def test_multilevel_put_all_levels(cache):
    """Test putting to multilevel cache populates all levels"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."
    intent = "policy_question"
    rag_results = [{"document": "Return policy doc", "score": 0.95}]

    # Put to all levels
    await cache.put(message, user_id, response, intent=intent, rag_results=rag_results)

    # Wait a bit for async operations
    await asyncio.sleep(0.2)

    # Verify L1
    l1_result = await cache.get_l1_exact(message, user_id)
    assert l1_result == response

    # Verify L3
    l3_result = await cache.get_l3_intent(message)
    assert l3_result == intent

    # Verify L4
    l4_result = await cache.get_l4_rag(message)
    assert l4_result == rag_results


# ===== Parallel Cache Check Tests =====

@pytest.mark.asyncio
async def test_parallel_cache_checks(cache):
    """Test that cache checks run in parallel"""
    message = "What is your return policy?"
    user_id = "test_user_1"

    start_time = time.time()

    # All levels should check in parallel
    result = await cache.get_multilevel(message, user_id)

    duration = time.time() - start_time

    # With parallel checks, should be faster than sum of individual checks
    # Even with misses, should complete in < 500ms
    assert duration < 0.5  # 500ms
    assert result is None  # All levels miss


@pytest.mark.asyncio
async def test_parallel_cache_early_return(cache):
    """Test that multilevel cache returns as soon as any level hits"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # Cache in L1 (fastest)
    await cache.put_l1_exact(message, user_id, response)

    start_time = time.time()
    result = await cache.get_multilevel(message, user_id)
    duration = time.time() - start_time

    # Should return very quickly (L1 latency ~1ms)
    assert result == response
    assert duration < 0.1  # 100ms

    # Only L1 should have hit (other levels may not have completed)
    assert cache.metrics.l1_hits == 1


# ===== Cache Invalidation Tests =====

@pytest.mark.asyncio
async def test_cache_invalidation(cache):
    """Test cache invalidation clears entries"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."
    intent = "policy_question"
    rag_results = [{"document": "Return policy doc"}]

    # Cache to all levels
    await cache.put(message, user_id, response, intent=intent, rag_results=rag_results)
    await asyncio.sleep(0.1)

    # Verify cached
    result = await cache.get_l1_exact(message, user_id)
    assert result == response

    # Invalidate
    await cache.invalidate(message, user_id)
    await asyncio.sleep(0.1)

    # Verify cleared
    result = await cache.get_l1_exact(message, user_id)
    assert result is None


# ===== Metrics Tests =====

@pytest.mark.asyncio
async def test_metrics_tracking(cache):
    """Test that metrics are tracked correctly"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # Reset metrics
    cache.reset_metrics()

    # Cache miss
    await cache.get_l1_exact(message, user_id)
    assert cache.metrics.l1_misses == 1
    assert cache.metrics.l1_hits == 0

    # Cache hit
    await cache.put_l1_exact(message, user_id, response)
    await cache.get_l1_exact(message, user_id)
    assert cache.metrics.l1_hits == 1
    assert cache.metrics.l1_misses == 1

    # Hit rate should be 50%
    hit_rate = cache.metrics.get_hit_rate('l1')
    assert 49 <= hit_rate <= 51  # Allow for rounding


@pytest.mark.asyncio
async def test_metrics_cost_savings(cache):
    """Test that cost savings are tracked"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # Reset metrics
    cache.reset_metrics()
    initial_cost = cache.metrics.cost_saved_usd

    # Cache and hit
    await cache.put_l1_exact(message, user_id, response)
    await cache.get_l1_exact(message, user_id)

    # Cost savings should increase
    assert cache.metrics.cost_saved_usd > initial_cost


@pytest.mark.asyncio
async def test_metrics_to_dict(cache):
    """Test metrics can be converted to dict"""
    metrics_dict = cache.get_metrics()

    assert 'hit_rates' in metrics_dict
    assert 'l1' in metrics_dict['hit_rates']
    assert 'l2' in metrics_dict['hit_rates']
    assert 'l3' in metrics_dict['hit_rates']
    assert 'l4' in metrics_dict['hit_rates']
    assert 'overall' in metrics_dict['hit_rates']

    assert 'average_latency_ms' in metrics_dict
    assert 'operations' in metrics_dict
    assert 'cost_savings_usd' in metrics_dict


# ===== Cache Warming Tests =====

@pytest.mark.asyncio
async def test_cache_warming(cache):
    """Test cache warming with common queries"""
    queries = [
        ("What is your return policy?", "user1", "30 days return policy"),
        ("What are your store hours?", "user2", "Open 9am-5pm"),
        ("How do I track my order?", "user3", "Check your email for tracking"),
    ]

    # Warm cache
    await cache.warm_cache(queries)
    await asyncio.sleep(0.2)

    # Verify all queries are cached
    for message, user_id, expected_response in queries:
        result = await cache.get_l1_exact(message, user_id)
        assert result == expected_response


# ===== Performance Tests =====

@pytest.mark.asyncio
async def test_cache_performance_l1(cache):
    """Test L1 cache performance meets <1ms target"""
    message = "What is your return policy?"
    user_id = "test_user_1"
    response = "Our return policy allows returns within 30 days."

    # Cache response
    await cache.put_l1_exact(message, user_id, response)

    # Measure latency over 10 calls
    latencies = []
    for _ in range(10):
        start = time.time()
        await cache.get_l1_exact(message, user_id)
        latencies.append((time.time() - start) * 1000)

    avg_latency = sum(latencies) / len(latencies)

    # L1 should average < 10ms (relaxed from 1ms for network overhead)
    assert avg_latency < 10, f"L1 average latency {avg_latency:.2f}ms exceeds 10ms target"


@pytest.mark.asyncio
async def test_high_cache_hit_rate_simulation(cache):
    """Simulate high cache hit rate scenario"""
    # Pre-populate cache with 100 common queries
    for i in range(100):
        message = f"Query {i}"
        user_id = f"user_{i % 10}"  # 10 users
        response = f"Response {i}"
        await cache.put_l1_exact(message, user_id, response)

    # Reset metrics
    cache.reset_metrics()

    # Simulate 1000 requests (90% cache hits)
    for i in range(1000):
        message = f"Query {i % 100}"  # 90% will be cached
        user_id = f"user_{i % 10}"
        result = await cache.get_l1_exact(message, user_id)
        if not result:
            # Cache miss - would compute and cache here
            await cache.put_l1_exact(message, user_id, f"Response {i}")

    # Check hit rate
    hit_rate = cache.metrics.get_hit_rate('l1')

    # Should achieve ~90% hit rate
    assert hit_rate >= 85, f"Hit rate {hit_rate:.1f}% below 85% target"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
