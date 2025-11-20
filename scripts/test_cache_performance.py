"""
Test Cache Performance
======================

Verify that response caching dramatically improves latency for repeated queries.

Test Strategy:
1. Run test queries twice (cold then warm cache)
2. Measure latency difference
3. Verify cache hit rate
4. Print cache statistics

Expected Result:
- First run: 10-20s (full processing)
- Second run: <1s (cached response)
- 90%+ latency reduction for cache hits
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent
from cache.response_cache import get_cache, reset_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceResult:
    """Performance test result"""
    query: str
    intent: str
    first_run_seconds: float
    second_run_seconds: float
    latency_reduction_pct: float
    cache_hit: bool


def test_cache_performance():
    """
    Test cache performance improvement

    Returns:
        List of performance results
    """
    print("\n" + "=" * 80)
    print("CACHE PERFORMANCE TEST")
    print("=" * 80)

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set")
        sys.exit(1)

    # Reset cache to start fresh
    print("\n[1/4] Resetting cache...")
    reset_cache()

    # Initialize agent with cache enabled
    print("[2/4] Initializing agent with cache enabled...")
    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=True,
        enable_rag=True,
        enable_escalation=True,
        enable_response_validation=True
    )

    # Test queries covering different intents
    test_queries = [
        {"query": "What's your refund policy?", "expected_intent": "policy_question"},
        {"query": "How much does a pizza box cost?", "expected_intent": "product_inquiry"},
        {"query": "My order arrived damaged!", "expected_intent": "complaint"},
        {"query": "Hello, I need help", "expected_intent": "greeting"},
    ]

    results: List[PerformanceResult] = []

    print(f"\n[3/4] Running {len(test_queries)} queries twice (cold then warm cache)...\n")

    for idx, test_case in enumerate(test_queries, 1):
        query = test_case["query"]
        expected_intent = test_case["expected_intent"]

        print(f"Test {idx}/{len(test_queries)}: \"{query}\"")
        print(f"Expected intent: {expected_intent}")

        # First run (cache miss)
        print("  [RUN 1] Cold cache (expecting cache miss)...", end=" ", flush=True)
        start_time = time.time()
        response1 = agent.handle_message(query)
        first_run_time = time.time() - start_time
        print(f"{first_run_time:.2f}s")

        # Second run (cache hit)
        print("  [RUN 2] Warm cache (expecting cache hit)...", end=" ", flush=True)
        start_time = time.time()
        response2 = agent.handle_message(query)
        second_run_time = time.time() - start_time
        print(f"{second_run_time:.2f}s")

        # Calculate improvement
        latency_reduction_pct = ((first_run_time - second_run_time) / first_run_time) * 100
        cache_hit = response2.action_taken == "cached_response"

        # Store result
        result = PerformanceResult(
            query=query,
            intent=response1.intent,
            first_run_seconds=first_run_time,
            second_run_seconds=second_run_time,
            latency_reduction_pct=latency_reduction_pct,
            cache_hit=cache_hit
        )
        results.append(result)

        # Print summary
        print(f"  Intent: {response1.intent} (expected: {expected_intent})")
        print(f"  Cache hit: {'YES' if cache_hit else 'NO'}")
        print(f"  Latency reduction: {latency_reduction_pct:.1f}%")

        # Verify intent matches
        if response1.intent != expected_intent:
            print(f"  [WARN] Intent mismatch!")

        print()

    # Get cache statistics
    print("[4/4] Cache statistics:")
    cache = get_cache()
    cache_stats = cache.get_stats()

    print(f"\nINTENT CACHE:")
    print(f"  Size: {cache_stats['intent_cache']['size']}/{cache_stats['intent_cache']['max_size']}")
    print(f"  Hits: {cache_stats['intent_cache']['hits']}")
    print(f"  Misses: {cache_stats['intent_cache']['misses']}")
    print(f"  Hit rate: {cache_stats['intent_cache']['hit_rate']:.1%}")

    print(f"\nRETRIEVAL CACHE:")
    print(f"  Size: {cache_stats['retrieval_cache']['size']}/{cache_stats['retrieval_cache']['max_size']}")
    print(f"  Hits: {cache_stats['retrieval_cache']['hits']}")
    print(f"  Misses: {cache_stats['retrieval_cache']['misses']}")
    print(f"  Hit rate: {cache_stats['retrieval_cache']['hit_rate']:.1%}")

    print(f"\nRESPONSE CACHE:")
    print(f"  Size: {cache_stats['response_cache']['size']}/{cache_stats['response_cache']['max_size']}")
    print(f"  Hits: {cache_stats['response_cache']['hits']}")
    print(f"  Misses: {cache_stats['response_cache']['misses']}")
    print(f"  Hit rate: {cache_stats['response_cache']['hit_rate']:.1%}")

    print(f"\nTOTAL MEMORY: ~{cache_stats['total_size_mb']:.2f} MB")

    return results


def print_summary(results: List[PerformanceResult]):
    """Print test summary"""
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)

    # Calculate averages
    avg_first_run = sum(r.first_run_seconds for r in results) / len(results)
    avg_second_run = sum(r.second_run_seconds for r in results) / len(results)
    avg_reduction = sum(r.latency_reduction_pct for r in results) / len(results)
    cache_hit_rate = sum(1 for r in results if r.cache_hit) / len(results)

    print(f"\nQUERIES TESTED: {len(results)}")
    print(f"\nAVERAGE LATENCY:")
    print(f"  First run (cache miss): {avg_first_run:.2f}s")
    print(f"  Second run (cache hit):  {avg_second_run:.2f}s")
    print(f"  Improvement:            {avg_reduction:.1f}%")
    print(f"\nCACHE HIT RATE: {cache_hit_rate:.0%}")

    # Detailed results
    print(f"\nDETAILED RESULTS:")
    print(f"{'Query':<40} {'Intent':<15} {'1st Run':<10} {'2nd Run':<10} {'Reduction':<12} {'Cache Hit'}")
    print("-" * 110)

    for result in results:
        query_short = result.query[:37] + "..." if len(result.query) > 40 else result.query
        cache_hit_str = "YES" if result.cache_hit else "NO"
        print(
            f"{query_short:<40} "
            f"{result.intent:<15} "
            f"{result.first_run_seconds:>8.2f}s  "
            f"{result.second_run_seconds:>8.2f}s  "
            f"{result.latency_reduction_pct:>10.1f}%  "
            f"{cache_hit_str}"
        )

    # Assessment
    print(f"\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)

    if avg_reduction >= 80:
        print("[OK] Cache performance EXCELLENT - 80%+ latency reduction")
    elif avg_reduction >= 50:
        print("[OK] Cache performance GOOD - 50%+ latency reduction")
    else:
        print("[WARN] Cache performance POOR - <50% latency reduction")

    if cache_hit_rate >= 0.9:
        print("[OK] Cache hit rate EXCELLENT - 90%+ hits")
    elif cache_hit_rate >= 0.7:
        print("[OK] Cache hit rate GOOD - 70%+ hits")
    else:
        print("[WARN] Cache hit rate POOR - <70% hits")

    # Compare to previous performance
    print(f"\nCOMPARISON TO PREVIOUS BENCHMARK:")
    print(f"  Previous avg (no cache): 14.6s")
    print(f"  Current avg (with cache): {avg_second_run:.2f}s")
    if avg_second_run < 5:
        improvement_vs_previous = ((14.6 - avg_second_run) / 14.6) * 100
        print(f"  Overall improvement: {improvement_vs_previous:.1f}%")
        print(f"  [OK] Target of <5s ACHIEVED!")
    else:
        print(f"  [WARN] Target of <5s NOT achieved yet")


if __name__ == "__main__":
    try:
        results = test_cache_performance()
        print_summary(results)

        print("\n" + "=" * 80)
        print("CACHE PERFORMANCE TEST COMPLETE")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        print(f"\n[ERROR] Test failed: {str(e)}")
        sys.exit(1)
