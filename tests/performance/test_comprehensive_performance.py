"""
Comprehensive Performance Benchmark Suite
==========================================

Tests the entire system under realistic conditions and measures:
- Latency (P50, P95, P99)
- Cache hit rates
- Cost per query
- Memory usage
- Throughput

Compares performance with/without cache to verify improvements.

Run with:
    pytest tests/performance/test_comprehensive_performance.py -v --tb=short

Or directly:
    python tests/performance/test_comprehensive_performance.py
"""

import time
import statistics
import requests
import json
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal
import psutil
import os


class PerformanceBenchmark:
    """Comprehensive performance benchmark for TRIA AI-BPO"""

    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.process = psutil.Process()

    def measure_query(
        self,
        message: str,
        query_type: str,
        outlet_id: int = 1,
        user_id: str = "benchmark_user",
        session_id: str = "benchmark_session"
    ) -> Dict[str, Any]:
        """Measure a single query performance"""

        # Record start memory
        start_memory_mb = self.process.memory_info().rss / (1024 * 1024)

        # Make request
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/api/chatbot",
                json={
                    "message": message,
                    "outlet_id": outlet_id,
                    "user_id": user_id,
                    "session_id": session_id
                },
                timeout=60
            )

            end_time = time.time()
            latency_seconds = end_time - start_time

            # Record end memory
            end_memory_mb = self.process.memory_info().rss / (1024 * 1024)
            memory_delta_mb = end_memory_mb - start_memory_mb

            # Parse response
            if response.status_code == 200:
                data = response.json()

                # Extract metadata
                metadata = data.get("metadata", {})
                cache_hit = metadata.get("cache_hit", False)

                return {
                    "success": True,
                    "query_type": query_type,
                    "message": message[:50],
                    "latency_seconds": latency_seconds,
                    "latency_ms": latency_seconds * 1000,
                    "cache_hit": cache_hit,
                    "memory_delta_mb": memory_delta_mb,
                    "status_code": response.status_code,
                    "intent": data.get("intent"),
                    "confidence": data.get("confidence"),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "query_type": query_type,
                    "message": message[:50],
                    "latency_seconds": latency_seconds,
                    "latency_ms": latency_seconds * 1000,
                    "cache_hit": False,
                    "memory_delta_mb": memory_delta_mb,
                    "status_code": response.status_code,
                    "error": response.text[:200],
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "query_type": query_type,
                "message": message[:50],
                "latency_seconds": end_time - start_time,
                "latency_ms": (end_time - start_time) * 1000,
                "cache_hit": False,
                "memory_delta_mb": 0,
                "exception": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def run_benchmark(self, queries: List[Dict[str, str]], iterations: int = 3) -> List[Dict[str, Any]]:
        """Run benchmark with multiple iterations"""

        print(f"\n{'='*80}")
        print(f"Performance Benchmark Starting")
        print(f"{'='*80}")
        print(f"Total Queries: {len(queries)}")
        print(f"Iterations per Query: {iterations}")
        print(f"Total Requests: {len(queries) * iterations}")
        print(f"Base URL: {self.base_url}")
        print(f"{'='*80}\n")

        results = []

        for i, query_def in enumerate(queries, 1):
            query_type = query_def["type"]
            message = query_def["message"]

            print(f"\n[{i}/{len(queries)}] Testing: {query_type}")
            print(f"    Message: {message[:70]}...")

            for iteration in range(iterations):
                print(f"    Iteration {iteration + 1}/{iterations}...", end=" ")

                result = self.measure_query(
                    message=message,
                    query_type=query_type
                )

                results.append(result)

                if result["success"]:
                    cache_indicator = "💨 CACHE" if result["cache_hit"] else "🔥 LIVE"
                    print(f"{cache_indicator} - {result['latency_ms']:.0f}ms")
                else:
                    print(f"❌ FAILED - {result.get('error', result.get('exception', 'Unknown'))[:50]}")

                # Small delay between iterations to avoid overwhelming the system
                time.sleep(0.5)

        return results

    def analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze benchmark results"""

        # Filter successful results
        successful = [r for r in results if r["success"]]

        if not successful:
            return {"error": "No successful queries"}

        # Calculate latency metrics
        latencies_ms = [r["latency_ms"] for r in successful]
        memory_deltas = [r["memory_delta_mb"] for r in successful]

        # Group by cache hit/miss
        cache_hits = [r for r in successful if r["cache_hit"]]
        cache_misses = [r for r in successful if not r["cache_hit"]]

        # Group by query type
        by_type = {}
        for result in successful:
            query_type = result["query_type"]
            if query_type not in by_type:
                by_type[query_type] = []
            by_type[query_type].append(result["latency_ms"])

        # Calculate type-specific stats
        type_stats = {}
        for query_type, latencies in by_type.items():
            type_stats[query_type] = {
                "count": len(latencies),
                "mean_ms": statistics.mean(latencies),
                "median_ms": statistics.median(latencies),
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "stdev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0
            }

        # Calculate overall stats
        analysis = {
            "overall": {
                "total_queries": len(results),
                "successful": len(successful),
                "failed": len(results) - len(successful),
                "success_rate": len(successful) / len(results) * 100 if results else 0
            },
            "latency": {
                "mean_ms": statistics.mean(latencies_ms),
                "median_ms": statistics.median(latencies_ms),
                "p95_ms": self._percentile(latencies_ms, 95),
                "p99_ms": self._percentile(latencies_ms, 99),
                "min_ms": min(latencies_ms),
                "max_ms": max(latencies_ms),
                "stdev_ms": statistics.stdev(latencies_ms) if len(latencies_ms) > 1 else 0
            },
            "cache": {
                "total_hits": len(cache_hits),
                "total_misses": len(cache_misses),
                "hit_rate": len(cache_hits) / len(successful) * 100 if successful else 0,
                "avg_latency_hit_ms": statistics.mean([r["latency_ms"] for r in cache_hits]) if cache_hits else 0,
                "avg_latency_miss_ms": statistics.mean([r["latency_ms"] for r in cache_misses]) if cache_misses else 0
            },
            "memory": {
                "avg_delta_mb": statistics.mean(memory_deltas),
                "max_delta_mb": max(memory_deltas),
                "total_delta_mb": sum(memory_deltas)
            },
            "by_query_type": type_stats
        }

        # Calculate cost estimates
        if cache_misses:
            # Assume $0.02 per 1K tokens, ~2K tokens per query
            cost_per_query_usd = 0.02 * 2  # $0.04
            total_cost_without_cache = len(successful) * cost_per_query_usd
            total_cost_with_cache = len(cache_misses) * cost_per_query_usd
            cost_saved = total_cost_without_cache - total_cost_with_cache

            analysis["cost"] = {
                "cost_per_query_usd": cost_per_query_usd,
                "total_cost_without_cache_usd": round(total_cost_without_cache, 2),
                "total_cost_with_cache_usd": round(total_cost_with_cache, 2),
                "cost_saved_usd": round(cost_saved, 2),
                "savings_percent": round(cost_saved / total_cost_without_cache * 100, 1) if total_cost_without_cache > 0 else 0
            }

        return analysis

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def print_report(self, analysis: Dict[str, Any]):
        """Print formatted benchmark report"""

        print(f"\n\n{'='*80}")
        print(f"PERFORMANCE BENCHMARK REPORT")
        print(f"{'='*80}\n")

        # Overall Stats
        print(f"OVERALL RESULTS:")
        print(f"  Total Queries: {analysis['overall']['total_queries']}")
        print(f"  Successful: {analysis['overall']['successful']} ({analysis['overall']['success_rate']:.1f}%)")
        print(f"  Failed: {analysis['overall']['failed']}")

        # Latency Stats
        print(f"\nLATENCY METRICS:")
        lat = analysis['latency']
        print(f"  Mean: {lat['mean_ms']:.0f}ms")
        print(f"  Median (P50): {lat['median_ms']:.0f}ms")
        print(f"  P95: {lat['p95_ms']:.0f}ms")
        print(f"  P99: {lat['p99_ms']:.0f}ms")
        print(f"  Min: {lat['min_ms']:.0f}ms")
        print(f"  Max: {lat['max_ms']:.0f}ms")
        print(f"  Std Dev: {lat['stdev_ms']:.0f}ms")

        # Cache Stats
        print(f"\nCACHE PERFORMANCE:")
        cache = analysis['cache']
        print(f"  Cache Hits: {cache['total_hits']}")
        print(f"  Cache Misses: {cache['total_misses']}")
        print(f"  Hit Rate: {cache['hit_rate']:.1f}%")
        if cache['total_hits'] > 0:
            print(f"  Avg Latency (Cache Hit): {cache['avg_latency_hit_ms']:.0f}ms")
        if cache['total_misses'] > 0:
            print(f"  Avg Latency (Cache Miss): {cache['avg_latency_miss_ms']:.0f}ms")
        if cache['total_hits'] > 0 and cache['total_misses'] > 0:
            speedup = cache['avg_latency_miss_ms'] / cache['avg_latency_hit_ms']
            print(f"  Cache Speedup: {speedup:.1f}x faster")

        # Cost Analysis
        if 'cost' in analysis:
            print(f"\nCOST ANALYSIS:")
            cost = analysis['cost']
            print(f"  Cost per Query: ${cost['cost_per_query_usd']:.4f}")
            print(f"  Total Cost (without cache): ${cost['total_cost_without_cache_usd']:.2f}")
            print(f"  Total Cost (with cache): ${cost['total_cost_with_cache_usd']:.2f}")
            print(f"  💰 Cost Saved: ${cost['cost_saved_usd']:.2f} ({cost['savings_percent']:.1f}%)")

        # Memory Stats
        print(f"\nMEMORY USAGE:")
        mem = analysis['memory']
        print(f"  Avg Delta per Query: {mem['avg_delta_mb']:.2f} MB")
        print(f"  Max Delta per Query: {mem['max_delta_mb']:.2f} MB")
        print(f"  Total Memory Growth: {mem['total_delta_mb']:.2f} MB")

        # Per-Query-Type Breakdown
        print(f"\nBREAKDOWN BY QUERY TYPE:")
        for query_type, stats in analysis['by_query_type'].items():
            print(f"\n  {query_type}:")
            print(f"    Count: {stats['count']}")
            print(f"    Mean: {stats['mean_ms']:.0f}ms")
            print(f"    Median: {stats['median_ms']:.0f}ms")
            print(f"    Min/Max: {stats['min_ms']:.0f}ms / {stats['max_ms']:.0f}ms")

        # Production Readiness Assessment
        print(f"\n\n{'='*80}")
        print(f"PRODUCTION READINESS ASSESSMENT")
        print(f"{'='*80}\n")

        # Check against targets
        target_latency_p95 = 5000  # 5s
        target_latency_mean = 3000  # 3s
        target_cache_hit_rate = 50  # 50%
        target_success_rate = 99  # 99%

        checks = []

        # Latency checks
        if lat['mean_ms'] <= target_latency_mean:
            checks.append(("✅ PASS", f"Mean latency {lat['mean_ms']:.0f}ms ≤ {target_latency_mean}ms target"))
        else:
            checks.append(("❌ FAIL", f"Mean latency {lat['mean_ms']:.0f}ms > {target_latency_mean}ms target"))

        if lat['p95_ms'] <= target_latency_p95:
            checks.append(("✅ PASS", f"P95 latency {lat['p95_ms']:.0f}ms ≤ {target_latency_p95}ms target"))
        else:
            checks.append(("❌ FAIL", f"P95 latency {lat['p95_ms']:.0f}ms > {target_latency_p95}ms target"))

        # Cache check
        if cache['hit_rate'] >= target_cache_hit_rate:
            checks.append(("✅ PASS", f"Cache hit rate {cache['hit_rate']:.1f}% ≥ {target_cache_hit_rate}% target"))
        else:
            checks.append(("⚠️ WARN", f"Cache hit rate {cache['hit_rate']:.1f}% < {target_cache_hit_rate}% target (expected on first run)"))

        # Success rate check
        if analysis['overall']['success_rate'] >= target_success_rate:
            checks.append(("✅ PASS", f"Success rate {analysis['overall']['success_rate']:.1f}% ≥ {target_success_rate}% target"))
        else:
            checks.append(("❌ FAIL", f"Success rate {analysis['overall']['success_rate']:.1f}% < {target_success_rate}% target"))

        for status, message in checks:
            print(f"  {status}: {message}")

        # Overall verdict
        passed = sum(1 for status, _ in checks if "✅ PASS" in status)
        total = len(checks)

        print(f"\n  Overall Score: {passed}/{total} checks passed")

        if passed == total:
            print(f"\n  🎉 VERDICT: PRODUCTION READY!")
        elif passed >= total * 0.75:
            print(f"\n  ⚠️  VERDICT: NEEDS MINOR IMPROVEMENTS")
        else:
            print(f"\n  ❌ VERDICT: NOT PRODUCTION READY - CRITICAL ISSUES")

        print(f"\n{'='*80}\n")


def get_benchmark_queries() -> List[Dict[str, str]]:
    """Get standard benchmark queries covering all scenarios"""

    return [
        # Simple greetings (should be fast, cacheable)
        {"type": "greeting", "message": "Hello"},
        {"type": "greeting", "message": "Hi there!"},
        {"type": "greeting", "message": "Good morning"},

        # Policy questions (should use RAG, cacheable)
        {"type": "policy_question", "message": "What is your return policy?"},
        {"type": "policy_question", "message": "Do you deliver on weekends?"},
        {"type": "policy_question", "message": "What are your business hours?"},
        {"type": "policy_question", "message": "How do I track my order?"},

        # Product inquiries (should use RAG + semantic search, cacheable)
        {"type": "product_inquiry", "message": "Do you have chicken burgers?"},
        {"type": "product_inquiry", "message": "What soft drinks do you have?"},
        {"type": "product_inquiry", "message": "Tell me about your breakfast menu"},
        {"type": "product_inquiry", "message": "Do you have vegetarian options?"},

        # Complaints (should trigger escalation)
        {"type": "complaint", "message": "My order was delivered late and cold"},
        {"type": "complaint", "message": "I received the wrong items"},
        {"type": "complaint", "message": "The food quality was terrible"},

        # Order placement (complex, not cacheable due to uniqueness)
        {"type": "order_placement", "message": "I want to order 10 beef burgers and 5 fries for outlet Jewel"},
        {"type": "order_placement", "message": "Can I get 20 chicken wings and 10 cokes?"},
        {"type": "order_placement", "message": "Order 15 breakfast sets for tomorrow morning"},

        # Mixed complexity
        {"type": "general_query", "message": "What payment methods do you accept?"},
        {"type": "general_query", "message": "Can I cancel my order?"},
        {"type": "general_query", "message": "Do you offer catering services?"}
    ]


def main():
    """Run comprehensive performance benchmark"""

    # Check if server is running
    try:
        response = requests.get("http://localhost:8003/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not healthy. Please start the server first.")
            print(f"   Health check returned: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at http://localhost:8003")
        print("   Please start the server with: python src/enhanced_api.py")
        return
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return

    print("✅ Server is running and healthy\n")

    # Initialize benchmark
    benchmark = PerformanceBenchmark()

    # Get benchmark queries
    queries = get_benchmark_queries()

    # Run benchmark (3 iterations each to test cache)
    results = benchmark.run_benchmark(queries, iterations=3)

    # Analyze results
    analysis = benchmark.analyze_results(results)

    # Print report
    benchmark.print_report(analysis)

    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark_results_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "results": results,
            "analysis": analysis
        }, f, indent=2, default=str)

    print(f"📊 Detailed results saved to: {results_file}\n")


if __name__ == "__main__":
    main()
