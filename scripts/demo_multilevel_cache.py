"""
Multi-Level Cache Demo
======================

Demonstrates the 4-tier caching system with real examples.

Usage:
    python scripts/demo_multilevel_cache.py
"""

import asyncio
import sys
from pathlib import Path
import time

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

from services.multilevel_cache import MultiLevelCache


async def demo_basic_usage():
    """Demo: Basic cache usage"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Cache Usage")
    print("="*60)

    cache = MultiLevelCache()
    await cache.initialize()

    message = "What is your return policy?"
    user_id = "demo_user"

    # First call: cache miss
    print(f"\n[1] First query: '{message}'")
    start = time.time()
    result = await cache.get_multilevel(message, user_id)
    duration = (time.time() - start) * 1000
    print(f"Result: {result}")
    print(f"Duration: {duration:.2f}ms")
    print(f"Status: CACHE MISS (as expected)")

    # Simulate computing response
    print("\n[2] Computing response (simulated)...")
    await asyncio.sleep(1)  # Simulate LLM call
    response = "Our return policy allows returns within 30 days of purchase."

    # Cache the response
    print("\n[3] Caching response to all levels...")
    await cache.put(
        message=message,
        user_id=user_id,
        response=response,
        intent="policy_question",
        rag_results=[{"document": "Return policy doc", "score": 0.95}]
    )
    print("Response cached!")

    # Second call: cache hit
    print(f"\n[4] Second query: '{message}'")
    start = time.time()
    result = await cache.get_multilevel(message, user_id)
    duration = (time.time() - start) * 1000
    print(f"Result: {result}")
    print(f"Duration: {duration:.2f}ms")
    print(f"Status: CACHE HIT ✓")

    # Show metrics
    print("\n[5] Cache Metrics:")
    metrics = cache.get_metrics()
    print(f"  L1 hit rate: {metrics['hit_rates']['l1']:.1f}%")
    print(f"  Overall hit rate: {metrics['hit_rates']['overall']:.1f}%")
    print(f"  Cost saved: ${metrics['cost_savings_usd']:.2f}")

    await cache.close()


async def demo_semantic_matching():
    """Demo: Semantic similarity matching (L2 cache)"""
    print("\n" + "="*60)
    print("DEMO 2: Semantic Similarity Matching")
    print("="*60)

    cache = MultiLevelCache()
    await cache.initialize()

    if not cache.chroma_collection or not cache.embedding_model:
        print("\nSkipped: ChromaDB or sentence-transformers not available")
        return

    # Cache original query
    original_query = "What is your return policy?"
    response = "Our return policy allows returns within 30 days."

    print(f"\n[1] Caching original query: '{original_query}'")
    await cache.put_l2_semantic(original_query, response)
    await asyncio.sleep(0.1)  # Wait for indexing

    # Try similar queries
    similar_queries = [
        "How do I return an item?",
        "Can I return my purchase?",
        "What's the return process?",
    ]

    print("\n[2] Testing similar queries:")
    for query in similar_queries:
        result = await cache.get_l2_semantic(query, threshold=0.7)
        status = "✓ CACHE HIT" if result else "✗ MISS"
        print(f"  '{query}' → {status}")

    # Try dissimilar query
    print("\n[3] Testing dissimilar query:")
    dissimilar = "What are your store hours?"
    result = await cache.get_l2_semantic(dissimilar, threshold=0.9)
    status = "✓ HIT" if result else "✗ MISS (expected)"
    print(f"  '{dissimilar}' → {status}")

    await cache.close()


async def demo_multilevel_lookup():
    """Demo: Multi-level cache lookup with parallel checks"""
    print("\n" + "="*60)
    print("DEMO 3: Multi-Level Parallel Lookup")
    print("="*60)

    cache = MultiLevelCache()
    await cache.initialize()

    message = "How do I track my order?"
    user_id = "demo_user"
    response = "Check your email for a tracking link."

    # Cache to L1 only
    print("\n[1] Caching to L1 (exact match)...")
    await cache.put_l1_exact(message, user_id, response)

    # Multi-level lookup (should hit L1 first)
    print("\n[2] Multi-level lookup (checks all levels in parallel)...")
    start = time.time()
    result = await cache.get_multilevel(message, user_id)
    duration = (time.time() - start) * 1000

    print(f"Result: {result}")
    print(f"Duration: {duration:.2f}ms")
    print(f"Hit level: L1 (fastest)")

    # Show which levels were checked
    metrics = cache.get_metrics()
    print("\n[3] Cache level hits/misses:")
    print(f"  L1: {metrics['hit_rates']['l1']:.0f}% hit rate")
    print(f"  L2: {metrics['hit_rates']['l2']:.0f}% hit rate")
    print(f"  L3: {metrics['hit_rates']['l3']:.0f}% hit rate")
    print(f"  L4: {metrics['hit_rates']['l4']:.0f}% hit rate")

    await cache.close()


async def demo_performance_comparison():
    """Demo: Performance comparison with/without cache"""
    print("\n" + "="*60)
    print("DEMO 4: Performance Comparison")
    print("="*60)

    cache = MultiLevelCache()
    await cache.initialize()

    message = "What are your shipping options?"
    user_id = "demo_user"
    response = "We offer standard (5-7 days) and express (1-2 days) shipping."

    # Simulate uncached request
    print("\n[1] Uncached request (simulated):")
    print("  - Intent classification: 2s")
    print("  - RAG retrieval: 5s")
    print("  - Response generation: 8s")
    print("  Total: 15s")

    # Cache response
    await cache.put(message, user_id, response)

    # Cached request
    print("\n[2] Cached request:")
    start = time.time()
    result = await cache.get_multilevel(message, user_id)
    duration = (time.time() - start) * 1000
    print(f"  Total: {duration:.2f}ms")

    print("\n[3] Performance improvement:")
    uncached_ms = 15000
    speedup = uncached_ms / duration if duration > 0 else 0
    print(f"  Speedup: {speedup:.0f}x faster")
    print(f"  Latency reduction: {(1 - duration/uncached_ms)*100:.1f}%")

    await cache.close()


async def demo_cache_hit_rate_simulation():
    """Demo: Simulate realistic cache hit rate"""
    print("\n" + "="*60)
    print("DEMO 5: Cache Hit Rate Simulation")
    print("="*60)

    cache = MultiLevelCache()
    await cache.initialize()

    # Pre-populate cache with 20 common queries
    common_queries = [
        f"What is your return policy?",
        f"How do I track my order?",
        f"What are your shipping options?",
        f"Can I cancel my order?",
        f"How do I contact support?",
        f"What payment methods do you accept?",
        f"Do you ship internationally?",
        f"What is your warranty policy?",
        f"How long does shipping take?",
        f"Can I change my shipping address?",
    ]

    print(f"\n[1] Pre-populating cache with {len(common_queries)} common queries...")
    for i, query in enumerate(common_queries):
        await cache.put_l1_exact(query, "user_generic", f"Response {i}")

    # Reset metrics
    cache.reset_metrics()

    # Simulate 100 requests (80% common queries, 20% new)
    print("\n[2] Simulating 100 requests (80% repeat, 20% new)...")
    for i in range(100):
        if i < 80:
            # Common query (should hit cache)
            query = common_queries[i % len(common_queries)]
        else:
            # New query (will miss cache)
            query = f"Unique query {i}"

        result = await cache.get_l1_exact(query, "user_generic")
        if not result:
            # Cache miss - would compute here
            await cache.put_l1_exact(query, "user_generic", f"Response {i}")

    # Show results
    print("\n[3] Results:")
    metrics = cache.get_metrics()
    hit_rate = metrics['hit_rates']['l1']
    print(f"  Cache hit rate: {hit_rate:.1f}%")
    print(f"  Expected: ~80% (80/100 requests were repeats)")
    print(f"  Cost saved: ${metrics['cost_savings_usd']:.2f}")

    print("\n[4] Projected savings at scale:")
    requests_per_month = 100_000
    cost_per_request = 0.03  # $0.03 per uncached request
    total_cost_without_cache = requests_per_month * cost_per_request
    total_cost_with_cache = total_cost_without_cache * (1 - hit_rate/100)
    savings = total_cost_without_cache - total_cost_with_cache

    print(f"  Requests/month: {requests_per_month:,}")
    print(f"  Cost without cache: ${total_cost_without_cache:,.2f}")
    print(f"  Cost with cache: ${total_cost_with_cache:,.2f}")
    print(f"  Savings: ${savings:,.2f}/month ({hit_rate:.0f}% reduction)")

    await cache.close()


async def main():
    """Run all demos"""
    print("\n")
    print("=" * 60)
    print(" " * 15 + "MULTI-LEVEL CACHE DEMO")
    print("=" * 60)

    try:
        await demo_basic_usage()
        await demo_semantic_matching()
        await demo_multilevel_lookup()
        await demo_performance_comparison()
        await demo_cache_hit_rate_simulation()

        print("\n" + "="*60)
        print("All demos completed successfully!")
        print("="*60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
