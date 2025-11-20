#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Cache Integration in Chatbot API
======================================

Tests the newly integrated cache by sending identical queries
and verifying cache hit rate > 0%.

Expected Results:
- First request: Cache MISS (from_cache: false)
- Second identical request: Cache HIT (from_cache: true)
- Cache hit should be 5-20x faster than cache miss
"""

import requests
import time
import uuid
import json
from typing import Dict, List


def test_cache_integration(base_url: str = "http://localhost:8003") -> bool:
    """
    Test cache integration with repeated identical queries.

    Returns:
        True if cache is working, False otherwise
    """
    print("="*70)
    print(" CACHE INTEGRATION TEST")
    print("="*70)
    print()

    # Test query (simple policy question that should be cacheable)
    test_query = "What is your refund policy?"
    session_id = f"cache_test_{uuid.uuid4().hex[:8]}"

    # Request 1: Should be a cache MISS
    print(f"Request 1: Sending query (expecting cache MISS)...")
    print(f"Query: '{test_query}'")
    print()

    start1 = time.time()
    response1 = requests.post(
        f"{base_url}/api/chatbot",
        json={
            "message": test_query,
            "session_id": session_id
        },
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4())
        },
        timeout=60
    )
    latency1 = (time.time() - start1) * 1000

    if response1.status_code != 200:
        print(f"❌ Request 1 failed: HTTP {response1.status_code}")
        return False

    data1 = response1.json()
    from_cache1 = data1.get("metadata", {}).get("from_cache", False)

    print(f"✅ Request 1 completed:")
    print(f"   Latency: {latency1:.0f}ms")
    print(f"   From cache: {from_cache1}")
    print(f"   Intent: {data1.get('intent')}")
    print(f"   Response preview: {data1.get('message', '')[:100]}...")
    print()

    if from_cache1:
        print("⚠️  WARNING: First request returned from_cache=true")
        print("   This might indicate cache was already populated")
        print()

    # Wait a moment to ensure cache write completes
    time.sleep(1)

    # Request 2: Should be a cache HIT (same query, same session)
    print(f"Request 2: Sending identical query (expecting cache HIT)...")
    print(f"Query: '{test_query}'")
    print()

    start2 = time.time()
    response2 = requests.post(
        f"{base_url}/api/chatbot",
        json={
            "message": test_query,
            "session_id": session_id
        },
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": str(uuid.uuid4())  # Different idempotency key
        },
        timeout=60
    )
    latency2 = (time.time() - start2) * 1000

    if response2.status_code != 200:
        print(f"❌ Request 2 failed: HTTP {response2.status_code}")
        return False

    data2 = response2.json()
    from_cache2 = data2.get("metadata", {}).get("from_cache", False)

    print(f"✅ Request 2 completed:")
    print(f"   Latency: {latency2:.0f}ms")
    print(f"   From cache: {from_cache2}")
    print(f"   Intent: {data2.get('intent')}")
    print(f"   Response preview: {data2.get('message', '')[:100]}...")
    print()

    # Calculate performance improvement
    if latency1 > 0 and latency2 > 0:
        speedup = latency1 / latency2
        print(f"Performance Comparison:")
        print(f"   Request 1 (cache miss): {latency1:.0f}ms")
        print(f"   Request 2 (cache hit?): {latency2:.0f}ms")
        print(f"   Speedup: {speedup:.1f}x faster")
        print()

    # Verify cache is working
    print("="*70)
    print(" VERIFICATION")
    print("="*70)

    if from_cache2:
        print("✅ CACHE INTEGRATION WORKING!")
        print(f"   Second request was served from cache")
        print(f"   Performance improvement: {speedup:.1f}x")
        print()
        return True
    else:
        print("❌ CACHE NOT WORKING")
        print(f"   Second identical request was NOT served from cache")
        print(f"   from_cache flag: {from_cache2}")
        print()

        # Debug information
        print("Debug Information:")
        print(f"   Response 1 metadata: {json.dumps(data1.get('metadata', {}), indent=2)}")
        print(f"   Response 2 metadata: {json.dumps(data2.get('metadata', {}), indent=2)}")
        print()

        return False


def test_cache_with_multiple_queries() -> Dict:
    """
    Test cache with multiple different queries to measure hit rate.

    Returns:
        dict: Test statistics
    """
    print("\n")
    print("="*70)
    print(" MULTI-QUERY CACHE TEST")
    print("="*70)
    print()

    queries = [
        "What is your refund policy?",
        "Tell me about shipping options",
        "What is your refund policy?",  # Repeat
        "How do I track my order?",
        "Tell me about shipping options",  # Repeat
        "What is your refund policy?",  # Repeat again
    ]

    base_url = "http://localhost:8003"
    session_id = f"multi_test_{uuid.uuid4().hex[:8]}"

    results = []
    cache_hits = 0
    cache_misses = 0

    for i, query in enumerate(queries, 1):
        print(f"Request {i}/{len(queries)}: '{query[:40]}...'")

        start = time.time()
        response = requests.post(
            f"{base_url}/api/chatbot",
            json={
                "message": query,
                "session_id": session_id
            },
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": str(uuid.uuid4())
            },
            timeout=60
        )
        latency = (time.time() - start) * 1000

        if response.status_code == 200:
            data = response.json()
            from_cache = data.get("metadata", {}).get("from_cache", False)

            if from_cache:
                cache_hits += 1
                print(f"   ✅ Cache HIT - {latency:.0f}ms")
            else:
                cache_misses += 1
                print(f"   ❌ Cache MISS - {latency:.0f}ms")

            results.append({
                "query": query,
                "from_cache": from_cache,
                "latency_ms": latency
            })
        else:
            print(f"   ❌ Request failed: HTTP {response.status_code}")
            results.append({
                "query": query,
                "error": response.status_code
            })

        # Small delay between requests
        time.sleep(0.5)

    # Calculate statistics
    total_requests = len(queries)
    cache_hit_rate = (cache_hits / total_requests) * 100

    print()
    print("="*70)
    print(" RESULTS")
    print("="*70)
    print(f"Total requests: {total_requests}")
    print(f"Cache hits: {cache_hits}")
    print(f"Cache misses: {cache_misses}")
    print(f"Cache hit rate: {cache_hit_rate:.1f}%")
    print()

    if cache_hit_rate > 0:
        print("✅ CACHE IS WORKING!")
        print(f"   Hit rate: {cache_hit_rate:.1f}%")
        print(f"   Expected: 50% (3 out of 6 are repeats)")
    else:
        print("❌ CACHE NOT WORKING")
        print(f"   Hit rate: 0%")

    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_rate": cache_hit_rate,
        "results": results
    }


def main():
    """Run cache integration tests"""

    # Check server health
    base_url = "http://localhost:8003"
    print(f"Checking server health at {base_url}...")

    try:
        response = requests.post(
            f"{base_url}/api/chatbot",
            json={"message": "test", "session_id": "health_check"},
            headers={"Idempotency-Key": str(uuid.uuid4())},
            timeout=10
        )
        if response.status_code not in [200, 400]:
            print(f"❌ Server not healthy: HTTP {response.status_code}")
            return 1
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        print(f"\nPlease start the server first:")
        print(f"  uvicorn src.enhanced_api:app --host 127.0.0.1 --port 8003")
        return 1

    print(f"✅ Server is running\n")

    # Test 1: Simple cache test with identical queries
    success = test_cache_integration(base_url)

    # Test 2: Multiple queries with repeats
    stats = test_cache_with_multiple_queries()

    # Overall assessment
    print("\n")
    print("="*70)
    print(" FINAL ASSESSMENT")
    print("="*70)

    if success and stats["cache_hit_rate"] > 0:
        print("✅ CACHE INTEGRATION SUCCESSFUL!")
        print()
        print("Next steps:")
        print("  1. Run full load tests to measure performance improvement")
        print("  2. Verify cache hit rates under concurrent load")
        print("  3. Monitor Redis memory usage")
        print()
        return 0
    else:
        print("❌ CACHE INTEGRATION FAILED")
        print()
        print("Troubleshooting:")
        print("  1. Check Redis connection in server logs")
        print("  2. Verify chat_cache is initialized (not None)")
        print("  3. Check for cache errors in server logs")
        print()
        return 1


if __name__ == "__main__":
    exit(main())
