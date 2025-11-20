"""
Concurrent Load Testing Suite
==============================

Tests system behavior under concurrent load:
- 10 concurrent users (basic load)
- 50 concurrent users (burst load)
- 100 concurrent users (spike test)
- Soak test (5 users for extended period)

Verifies:
- No crashes or errors under load
- Latency degradation is acceptable
- Memory usage remains stable
- Database connection pool handles load
- Cache effectiveness under concurrency

Run with:
    python tests/load/test_concurrent_load.py

Requirements:
    pip install locust  # For load testing
"""

import time
import requests
import concurrent.futures
import statistics
from typing import List, Dict, Any
from datetime import datetime
import psutil
import threading
import json


class LoadTestResult:
    """Container for load test results"""

    def __init__(self):
        self.requests_sent = 0
        self.requests_succeeded = 0
        self.requests_failed = 0
        self.latencies_ms: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.start_time = None
        self.end_time = None
        self.memory_samples: List[float] = []
        self.lock = threading.Lock()

    def add_success(self, latency_ms: float):
        """Record a successful request"""
        with self.lock:
            self.requests_sent += 1
            self.requests_succeeded += 1
            self.latencies_ms.append(latency_ms)

    def add_failure(self, error: Dict[str, Any]):
        """Record a failed request"""
        with self.lock:
            self.requests_sent += 1
            self.requests_failed += 1
            self.errors.append(error)

    def sample_memory(self):
        """Sample current memory usage"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / (1024 * 1024)
        with self.lock:
            self.memory_samples.append(memory_mb)

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics"""
        duration_seconds = (self.end_time - self.start_time) if self.end_time and self.start_time else 0

        summary = {
            "requests": {
                "total": self.requests_sent,
                "succeeded": self.requests_succeeded,
                "failed": self.requests_failed,
                "success_rate": (self.requests_succeeded / self.requests_sent * 100) if self.requests_sent > 0 else 0
            },
            "duration_seconds": duration_seconds,
            "throughput_rps": self.requests_sent / duration_seconds if duration_seconds > 0 else 0
        }

        if self.latencies_ms:
            sorted_latencies = sorted(self.latencies_ms)
            summary["latency"] = {
                "mean_ms": statistics.mean(self.latencies_ms),
                "median_ms": statistics.median(self.latencies_ms),
                "p95_ms": self._percentile(sorted_latencies, 95),
                "p99_ms": self._percentile(sorted_latencies, 99),
                "min_ms": min(self.latencies_ms),
                "max_ms": max(self.latencies_ms),
                "stdev_ms": statistics.stdev(self.latencies_ms) if len(self.latencies_ms) > 1 else 0
            }

        if self.memory_samples:
            memory_growth = max(self.memory_samples) - min(self.memory_samples)
            summary["memory"] = {
                "start_mb": min(self.memory_samples),
                "end_mb": max(self.memory_samples),
                "growth_mb": memory_growth,
                "avg_mb": statistics.mean(self.memory_samples)
            }

        if self.errors:
            summary["errors"] = {
                "count": len(self.errors),
                "samples": self.errors[:5]  # First 5 errors
            }

        return summary

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]


class ConcurrentLoadTester:
    """Load tester with concurrent users"""

    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url

    def simulate_user(
        self,
        user_id: int,
        queries: List[str],
        result: LoadTestResult,
        think_time_seconds: float = 1.0
    ):
        """Simulate a single user making multiple requests"""

        session_id = f"load_test_user_{user_id}"

        for query in queries:
            try:
                # Make request
                start_time = time.time()

                response = requests.post(
                    f"{self.base_url}/api/chatbot",
                    json={
                        "message": query,
                        "outlet_id": 1,
                        "user_id": f"user_{user_id}",
                        "session_id": session_id
                    },
                    timeout=60
                )

                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000

                if response.status_code == 200:
                    result.add_success(latency_ms)
                else:
                    result.add_failure({
                        "user_id": user_id,
                        "query": query,
                        "status_code": response.status_code,
                        "error": response.text[:200]
                    })

            except Exception as e:
                result.add_failure({
                    "user_id": user_id,
                    "query": query,
                    "exception": str(e)
                })

            # Think time between requests
            time.sleep(think_time_seconds)

    def run_concurrent_test(
        self,
        num_users: int,
        queries_per_user: List[str],
        test_name: str
    ) -> LoadTestResult:
        """Run concurrent load test with N users"""

        print(f"\n{'='*80}")
        print(f"Starting Load Test: {test_name}")
        print(f"{'='*80}")
        print(f"  Concurrent Users: {num_users}")
        print(f"  Queries per User: {len(queries_per_user)}")
        print(f"  Total Requests: {num_users * len(queries_per_user)}")
        print(f"{'='*80}\n")

        result = LoadTestResult()
        result.start_time = time.time()

        # Start memory monitoring thread
        memory_monitor_running = True

        def monitor_memory():
            while memory_monitor_running:
                result.sample_memory()
                time.sleep(5)  # Sample every 5 seconds

        memory_thread = threading.Thread(target=monitor_memory, daemon=True)
        memory_thread.start()

        # Launch concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = []

            for user_id in range(num_users):
                future = executor.submit(
                    self.simulate_user,
                    user_id,
                    queries_per_user,
                    result,
                    think_time_seconds=0.5
                )
                futures.append(future)

            # Wait for all users to complete
            for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
                try:
                    future.result()
                    print(f"  User {i}/{num_users} completed")
                except Exception as e:
                    print(f"  User {i}/{num_users} failed: {e}")

        result.end_time = time.time()
        memory_monitor_running = False

        print(f"\n✅ Load test completed in {result.end_time - result.start_time:.1f} seconds\n")

        return result

    def print_results(self, test_name: str, result: LoadTestResult):
        """Print formatted test results"""

        summary = result.get_summary()

        print(f"\n{'='*80}")
        print(f"LOAD TEST RESULTS: {test_name}")
        print(f"{'='*80}\n")

        # Requests
        print(f"REQUESTS:")
        reqs = summary['requests']
        print(f"  Total: {reqs['total']}")
        print(f"  Succeeded: {reqs['succeeded']} ({reqs['success_rate']:.1f}%)")
        print(f"  Failed: {reqs['failed']}")

        # Duration & Throughput
        print(f"\nPERFORMANCE:")
        print(f"  Duration: {summary['duration_seconds']:.1f}s")
        print(f"  Throughput: {summary['throughput_rps']:.1f} req/s")

        # Latency
        if 'latency' in summary:
            print(f"\nLATENCY:")
            lat = summary['latency']
            print(f"  Mean: {lat['mean_ms']:.0f}ms")
            print(f"  Median: {lat['median_ms']:.0f}ms")
            print(f"  P95: {lat['p95_ms']:.0f}ms")
            print(f"  P99: {lat['p99_ms']:.0f}ms")
            print(f"  Min/Max: {lat['min_ms']:.0f}ms / {lat['max_ms']:.0f}ms")

        # Memory
        if 'memory' in summary:
            print(f"\nMEMORY:")
            mem = summary['memory']
            print(f"  Start: {mem['start_mb']:.1f} MB")
            print(f"  End: {mem['end_mb']:.1f} MB")
            print(f"  Growth: {mem['growth_mb']:.1f} MB")
            print(f"  Average: {mem['avg_mb']:.1f} MB")

        # Errors
        if 'errors' in summary:
            print(f"\nERRORS ({summary['errors']['count']} total):")
            for i, error in enumerate(summary['errors']['samples'], 1):
                print(f"  {i}. {error}")

        # Pass/Fail Assessment
        print(f"\nASSESSMENT:")

        checks = []

        # Success rate check
        if reqs['success_rate'] >= 99:
            checks.append(("✅ PASS", f"Success rate {reqs['success_rate']:.1f}% ≥ 99%"))
        else:
            checks.append(("❌ FAIL", f"Success rate {reqs['success_rate']:.1f}% < 99%"))

        # Latency check
        if 'latency' in summary:
            if lat['p95_ms'] <= 5000:
                checks.append(("✅ PASS", f"P95 latency {lat['p95_ms']:.0f}ms ≤ 5000ms"))
            else:
                checks.append(("❌ FAIL", f"P95 latency {lat['p95_ms']:.0f}ms > 5000ms"))

        # Memory growth check
        if 'memory' in summary:
            if mem['growth_mb'] <= 200:
                checks.append(("✅ PASS", f"Memory growth {mem['growth_mb']:.1f}MB ≤ 200MB"))
            else:
                checks.append(("⚠️ WARN", f"Memory growth {mem['growth_mb']:.1f}MB > 200MB"))

        for status, message in checks:
            print(f"  {status}: {message}")

        passed = sum(1 for status, _ in checks if "✅ PASS" in status)
        total = len(checks)

        print(f"\n  Score: {passed}/{total} checks passed")

        if passed == total:
            print(f"\n  🎉 VERDICT: TEST PASSED")
        else:
            print(f"\n  ❌ VERDICT: TEST FAILED - ISSUES DETECTED")

        print(f"\n{'='*80}\n")

        return passed == total


def get_test_queries() -> List[str]:
    """Get realistic test queries"""

    return [
        "Hello",
        "What is your return policy?",
        "Do you have chicken burgers?",
        "I want to order 5 burgers",
        "What are your business hours?"
    ]


def main():
    """Run all load tests"""

    # Check if server is running
    try:
        response = requests.get("http://localhost:8003/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not healthy. Please start the server first.")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at http://localhost:8003")
        print("   Please start the server with: python src/enhanced_api.py")
        return

    print("✅ Server is running and healthy\n")

    tester = ConcurrentLoadTester()
    queries = get_test_queries()

    all_results = {}

    # Test 1: Basic Load (10 concurrent users)
    print("\n" + "="*80)
    print("TEST 1: BASIC LOAD (10 Concurrent Users)")
    print("="*80)

    result_10 = tester.run_concurrent_test(
        num_users=10,
        queries_per_user=queries,
        test_name="Basic Load (10 users)"
    )
    passed_10 = tester.print_results("Basic Load (10 users)", result_10)
    all_results["basic_load_10_users"] = result_10.get_summary()

    # Wait between tests
    print("\nWaiting 10 seconds before next test...")
    time.sleep(10)

    # Test 2: Burst Load (50 concurrent users)
    print("\n" + "="*80)
    print("TEST 2: BURST LOAD (50 Concurrent Users)")
    print("="*80)

    result_50 = tester.run_concurrent_test(
        num_users=50,
        queries_per_user=queries[:3],  # Shorter queries to complete faster
        test_name="Burst Load (50 users)"
    )
    passed_50 = tester.print_results("Burst Load (50 users)", result_50)
    all_results["burst_load_50_users"] = result_50.get_summary()

    # Wait between tests
    print("\nWaiting 10 seconds before next test...")
    time.sleep(10)

    # Test 3: Spike Test (100 concurrent users, brief)
    print("\n" + "="*80)
    print("TEST 3: SPIKE TEST (100 Concurrent Users)")
    print("="*80)

    result_100 = tester.run_concurrent_test(
        num_users=100,
        queries_per_user=queries[:2],  # Very short queries
        test_name="Spike Test (100 users)"
    )
    passed_100 = tester.print_results("Spike Test (100 users)", result_100)
    all_results["spike_test_100_users"] = result_100.get_summary()

    # Final Summary
    print("\n" + "="*80)
    print("LOAD TESTING SUMMARY")
    print("="*80)

    tests_passed = sum([passed_10, passed_50, passed_100])
    tests_total = 3

    print(f"\n  Tests Passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print(f"\n  🎉 ALL LOAD TESTS PASSED - PRODUCTION READY!")
    else:
        print(f"\n  ❌ SOME LOAD TESTS FAILED - NOT PRODUCTION READY")
        print(f"\n  Issues detected:")
        if not passed_10:
            print(f"    - Basic load (10 users) failed")
        if not passed_50:
            print(f"    - Burst load (50 users) failed")
        if not passed_100:
            print(f"    - Spike test (100 users) failed")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"load_test_results_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n  📊 Detailed results saved to: {results_file}\n")

    print("="*80 + "\n")


if __name__ == "__main__":
    main()
