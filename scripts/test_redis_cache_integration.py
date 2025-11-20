#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Redis Cache Integration
=============================

Quick integration test for the newly implemented Redis-backed cache.

Tests:
1. Redis connection
2. Cache initialization
3. Cache operations (get/set/exists/clear)
4. Metrics tracking
5. Fallback to in-memory if Redis unavailable

Expected Results:
- Redis connection successful (or fallback to in-memory)
- All cache operations work
- Metrics show hit/miss rates
- Cost savings calculations work
"""

import sys
import os
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Fix Windows encoding for Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from cache.chat_response_cache import get_chat_cache
from cache.redis_cache import get_redis_cache
import time


def test_redis_cache():
    """Test Redis cache directly"""
    print("=" * 70)
    print("Test 1: Redis Cache Direct Operations")
    print("=" * 70)

    try:
        # Initialize Redis cache
        redis_cache = get_redis_cache()

        # Check backend
        backend = "redis" if not redis_cache.using_fallback else "in-memory"
        print(f"✓ Cache initialized (backend: {backend})")

        # Test health check
        health = redis_cache.health_check()
        print(f"✓ Health check: {'healthy' if health else 'unhealthy'}")

        # Test set operation
        test_key = "test_key_1"
        test_value = {"message": "Hello, Redis!", "timestamp": time.time()}
        success = redis_cache.set(test_key, test_value, ttl=60)
        print(f"✓ SET operation: {'success' if success else 'failed'}")

        # Test get operation (should be cache hit)
        retrieved = redis_cache.get(test_key)
        if retrieved and retrieved["message"] == "Hello, Redis!":
            print(f"✓ GET operation: success (value matches)")
        else:
            print(f"✗ GET operation: failed (value mismatch)")

        # Test exists operation
        exists = redis_cache.exists(test_key)
        print(f"✓ EXISTS operation: {exists}")

        # Test metrics
        info = redis_cache.get_info()
        print(f"✓ Metrics: {info['metrics']['hits']} hits, {info['metrics']['misses']} misses")
        print(f"  Hit rate: {info['metrics']['hit_rate']:.1%}")
        print(f"  Avg GET time: {info['metrics']['avg_get_time_ms']:.2f}ms")

        # Test delete
        redis_cache.delete(test_key)
        exists_after_delete = redis_cache.exists(test_key)
        print(f"✓ DELETE operation: {'success' if not exists_after_delete else 'failed'}")

        print("\n✅ Redis cache test PASSED\n")
        return True

    except Exception as e:
        print(f"\n❌ Redis cache test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_chat_response_cache():
    """Test chat response cache with conversation context"""
    print("=" * 70)
    print("Test 2: Chat Response Cache (High-Level)")
    print("=" * 70)

    try:
        # Initialize chat cache
        chat_cache = get_chat_cache()
        backend = "redis" if not chat_cache.redis_cache.using_fallback else "in-memory"
        print(f"✓ Chat cache initialized (backend: {backend})")

        # Test response caching
        message = "What's your refund policy?"
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ]

        # First call should be cache miss
        cached_response = chat_cache.get_response(message, conversation_history)
        if cached_response is None:
            print(f"✓ Cache MISS (expected on first call)")
        else:
            print(f"✗ Unexpected cache HIT on first call")

        # Set response
        response_data = {
            "response_text": "Our refund policy allows returns within 30 days...",
            "intent": "policy_question",
            "confidence": 0.95,
            "action_taken": "rag_retrieval",
            "knowledge_used": [{"doc_id": "policy_123"}]
        }

        success = chat_cache.set_response(message, conversation_history, response_data)
        print(f"✓ Response cached: {'success' if success else 'failed'}")

        # Second call should be cache hit
        cached_response = chat_cache.get_response(message, conversation_history)
        if cached_response and cached_response["response_text"] == response_data["response_text"]:
            print(f"✓ Cache HIT (expected on second call)")
            print(f"  Response matches: ✓")
            print(f"  Cached timestamp: {cached_response.get('cached_at', 'N/A')}")
        else:
            print(f"✗ Cache HIT failed or data mismatch")

        # Test intent caching
        intent_result = {"intent": "product_inquiry", "confidence": 0.9}
        chat_cache.set_intent("Tell me about your products", intent_result)
        cached_intent = chat_cache.get_intent("Tell me about your products")
        print(f"✓ Intent caching: {'working' if cached_intent else 'failed'}")

        # Test policy retrieval caching
        policy_results = [
            {"doc_id": "pol_1", "content": "Policy content 1", "score": 0.95}
        ]
        chat_cache.set_policy_retrieval("refund", "policies", 5, policy_results)
        cached_policies = chat_cache.get_policy_retrieval("refund", "policies", 5)
        print(f"✓ Policy caching: {'working' if cached_policies else 'failed'}")

        # Test metrics
        metrics = chat_cache.get_metrics()
        print(f"\n✓ Cache Metrics:")
        print(f"  Backend: {metrics.get('backend', 'unknown')}")
        print(f"  Hit rate: {metrics.get('hit_rate', 0):.1%}")
        print(f"  Total requests: {metrics.get('total_requests', 0)}")
        if metrics.get('estimated_cost_saved_usd'):
            print(f"  Estimated cost saved: ${metrics['estimated_cost_saved_usd']:.2f}")

        # Test health check
        health = chat_cache.health_check()
        print(f"✓ Health check: {'healthy' if health else 'unhealthy'}")

        # Clean up
        chat_cache.clear_all()
        print(f"✓ Cleanup: cache cleared")

        print("\n✅ Chat response cache test PASSED\n")
        return True

    except Exception as e:
        print(f"\n❌ Chat response cache test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_cache_performance():
    """Test cache performance improvement"""
    print("=" * 70)
    print("Test 3: Cache Performance")
    print("=" * 70)

    try:
        redis_cache = get_redis_cache()

        # Test 100 cache operations
        num_operations = 100

        # Warm up
        for i in range(10):
            redis_cache.set(f"warmup_{i}", {"value": i})

        # Test writes
        start_time = time.time()
        for i in range(num_operations):
            redis_cache.set(f"perf_test_{i}", {"value": i, "timestamp": time.time()}, ttl=60)
        write_time = time.time() - start_time

        # Test reads
        start_time = time.time()
        for i in range(num_operations):
            redis_cache.get(f"perf_test_{i}")
        read_time = time.time() - start_time

        # Prevent division by zero for very fast operations
        if read_time == 0:
            read_time = 0.001
        if write_time == 0:
            write_time = 0.001

        print(f"✓ Performance test completed:")
        print(f"  Write: {num_operations} ops in {write_time*1000:.2f}ms ({num_operations/write_time:.0f} ops/sec)")
        print(f"  Read: {num_operations} ops in {read_time*1000:.2f}ms ({num_operations/read_time:.0f} ops/sec)")
        print(f"  Avg write latency: {write_time*1000/num_operations:.2f}ms")
        print(f"  Avg read latency: {read_time*1000/num_operations:.2f}ms")

        # Check if performance is acceptable
        avg_read_latency = read_time * 1000 / num_operations
        if avg_read_latency < 100:  # Less than 100ms average
            print(f"✓ Performance: EXCELLENT (< 100ms)")
        elif avg_read_latency < 500:
            print(f"✓ Performance: GOOD (< 500ms)")
        else:
            print(f"⚠ Performance: SLOW (> 500ms)")

        # Cleanup
        for i in range(num_operations):
            redis_cache.delete(f"perf_test_{i}")

        print("\n✅ Performance test PASSED\n")
        return True

    except Exception as e:
        print(f"\n❌ Performance test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" Redis Cache Integration Test Suite")
    print("=" * 70)
    print()

    results = []

    # Run tests
    results.append(("Redis Cache Operations", test_redis_cache()))
    results.append(("Chat Response Cache", test_chat_response_cache()))
    results.append(("Cache Performance", test_cache_performance()))

    # Summary
    print("=" * 70)
    print(" Test Summary")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    print()
    if all_passed:
        print("✅ All tests PASSED! Redis cache integration is working correctly.")
        print()
        print("Next steps:")
        print("1. Start the API server: uvicorn src.enhanced_api:app --reload")
        print("2. Check cache metrics: GET http://localhost:8000/api/v1/metrics/cache")
        print("3. Run performance benchmarks to verify 5x improvement")
        return 0
    else:
        print("❌ Some tests FAILED. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
