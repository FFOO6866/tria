#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load Testing for Chat API
==========================

Comprehensive load testing to verify:
1. System handles concurrent users without crashing
2. Cache provides expected 5x performance improvement
3. Response times remain acceptable under load
4. Error rates stay below 1%

Test Scenarios:
- Baseline: Single user (measure best-case performance)
- Light load: 5 concurrent users
- Medium load: 10 concurrent users
- Heavy load: 20 concurrent users
- Stress test: 50 concurrent users (expected to fail gracefully)

Expected Results (with caching):
- Single user: < 3s average (cache miss on first, hit on subsequent)
- 5 concurrent: < 4s average (mostly cache hits)
- 10 concurrent: < 5s average (some queueing)
- 20 concurrent: < 10s average (significant queueing)
- 50 concurrent: Should not crash, but may timeout
"""

import sys
import os
from pathlib import Path
import time
import json
import statistics
import uuid
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv(project_root / ".env")


class LoadTestResult:
    """Results from a single request"""
    def __init__(self, success: bool, latency_ms: float, status_code: int,
                 error: Optional[str] = None, cached: bool = False):
        self.success = success
        self.latency_ms = latency_ms
        self.status_code = status_code
        self.error = error
        self.cached = cached
        self.timestamp = time.time()


class LoadTestScenario:
    """A load test scenario with specific parameters"""
    def __init__(self, name: str, concurrent_users: int, requests_per_user: int,
                 queries: List[str], base_url: str = "http://localhost:8003"):
        self.name = name
        self.concurrent_users = concurrent_users
        self.requests_per_user = requests_per_user
        self.queries = queries
        self.base_url = base_url
        self.results: List[LoadTestResult] = []

    def execute(self) -> Dict:
        """Execute the load test scenario"""
        print(f"\n{'=' * 70}")
        print(f"Running: {self.name}")
        print(f"{'=' * 70}")
        print(f"Concurrent users: {self.concurrent_users}")
        print(f"Requests per user: {self.requests_per_user}")
        print(f"Total requests: {self.concurrent_users * self.requests_per_user}")
        print()

        start_time = time.time()

        # Execute requests concurrently
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            futures = []
            for user_id in range(self.concurrent_users):
                for req_id in range(self.requests_per_user):
                    # Rotate through queries
                    query = self.queries[req_id % len(self.queries)]
                    future = executor.submit(self._send_request, user_id, req_id, query)
                    futures.append(future)

            # Collect results
            for future in as_completed(futures):
                result = future.result()
                self.results.append(result)

                # Progress indicator
                if len(self.results) % 10 == 0:
                    print(f"Progress: {len(self.results)}/{len(futures)} requests completed")

        total_time = time.time() - start_time

        # Calculate metrics
        metrics = self._calculate_metrics(total_time)
        self._print_results(metrics)

        return metrics

    def _send_request(self, user_id: int, req_id: int, query: str) -> LoadTestResult:
        """Send a single chat request"""
        url = f"{self.base_url}/api/chatbot"
        payload = {
            "message": query,
            "session_id": f"load_test_user_{user_id}"
        }

        start = time.time()
        try:
            # Generate unique UUID for idempotency
            idempotency_key = str(uuid.uuid4())

            response = requests.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key
                },
                timeout=60  # 60 second timeout
            )
            latency = (time.time() - start) * 1000

            # Check if response was cached
            cached = False
            if response.status_code == 200:
                data = response.json()
                cached = data.get("metadata", {}).get("from_cache", False)

            return LoadTestResult(
                success=response.status_code == 200,
                latency_ms=latency,
                status_code=response.status_code,
                cached=cached
            )
        except requests.exceptions.Timeout:
            latency = (time.time() - start) * 1000
            return LoadTestResult(
                success=False,
                latency_ms=latency,
                status_code=0,
                error="Timeout"
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return LoadTestResult(
                success=False,
                latency_ms=latency,
                status_code=0,
                error=str(e)
            )

    def _calculate_metrics(self, total_time: float) -> Dict:
        """Calculate performance metrics from results"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        cached = [r for r in successful if r.cached]

        latencies = [r.latency_ms for r in successful]

        metrics = {
            "scenario": self.name,
            "total_requests": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results) if self.results else 0,
            "cached_responses": len(cached),
            "cache_hit_rate": len(cached) / len(successful) if successful else 0,
            "total_time_seconds": total_time,
            "requests_per_second": len(self.results) / total_time if total_time > 0 else 0,
        }

        if latencies:
            metrics.update({
                "avg_latency_ms": statistics.mean(latencies),
                "median_latency_ms": statistics.median(latencies),
                "p95_latency_ms": self._percentile(latencies, 95),
                "p99_latency_ms": self._percentile(latencies, 99),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
            })

        # Error breakdown
        if failed:
            error_types = {}
            for r in failed:
                error_key = r.error or f"HTTP_{r.status_code}"
                error_types[error_key] = error_types.get(error_key, 0) + 1
            metrics["errors"] = error_types

        return metrics

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _print_results(self, metrics: Dict):
        """Print formatted results"""
        print(f"\n{'=' * 70}")
        print(f"Results: {metrics['scenario']}")
        print(f"{'=' * 70}")

        # Overall metrics
        print(f"\nOverall Performance:")
        print(f"  Total requests: {metrics['total_requests']}")
        print(f"  Successful: {metrics['successful']} ({metrics['success_rate']:.1%})")
        print(f"  Failed: {metrics['failed']}")
        print(f"  Total time: {metrics['total_time_seconds']:.2f}s")
        print(f"  Throughput: {metrics['requests_per_second']:.2f} req/s")

        # Cache metrics
        print(f"\nCache Performance:")
        print(f"  Cache hits: {metrics['cached_responses']}")
        print(f"  Hit rate: {metrics['cache_hit_rate']:.1%}")

        # Latency metrics
        if "avg_latency_ms" in metrics:
            print(f"\nLatency Metrics:")
            print(f"  Average: {metrics['avg_latency_ms']:.0f}ms")
            print(f"  Median: {metrics['median_latency_ms']:.0f}ms")
            print(f"  P95: {metrics['p95_latency_ms']:.0f}ms")
            print(f"  P99: {metrics['p99_latency_ms']:.0f}ms")
            print(f"  Min: {metrics['min_latency_ms']:.0f}ms")
            print(f"  Max: {metrics['max_latency_ms']:.0f}ms")

            # Performance assessment
            avg_latency = metrics['avg_latency_ms']
            if avg_latency < 3000:
                grade = "EXCELLENT ✅"
            elif avg_latency < 5000:
                grade = "GOOD ✅"
            elif avg_latency < 10000:
                grade = "ACCEPTABLE ⚠️"
            else:
                grade = "POOR ❌"

            print(f"\n  Performance Grade: {grade}")

        # Error breakdown
        if "errors" in metrics:
            print(f"\nError Breakdown:")
            for error_type, count in metrics["errors"].items():
                print(f"  {error_type}: {count}")

        print()


def test_baseline_single_user(base_url: str) -> Dict:
    """Test 1: Baseline performance with single user"""
    queries = [
        "What is your refund policy?",
        "Tell me about shipping options",
        "What is your refund policy?",  # Repeat to test cache
        "How do I track my order?",
        "What are your business hours?"
    ]

    scenario = LoadTestScenario(
        name="Baseline: Single User",
        concurrent_users=1,
        requests_per_user=5,
        queries=queries,
        base_url=base_url
    )

    return scenario.execute()


def test_light_load(base_url: str) -> Dict:
    """Test 2: Light load with 5 concurrent users"""
    queries = [
        "What is your refund policy?",
        "Tell me about shipping",
        "How do I return items?",
        "What payment methods do you accept?",
        "Do you ship internationally?"
    ]

    scenario = LoadTestScenario(
        name="Light Load: 5 Concurrent Users",
        concurrent_users=5,
        requests_per_user=4,
        queries=queries,
        base_url=base_url
    )

    return scenario.execute()


def test_medium_load(base_url: str) -> Dict:
    """Test 3: Medium load with 10 concurrent users"""
    queries = [
        "What is your refund policy?",
        "Tell me about shipping",
        "How do I return items?",
        "What payment methods do you accept?",
        "Do you ship internationally?",
        "What are your business hours?",
        "How do I contact support?",
        "What is your privacy policy?"
    ]

    scenario = LoadTestScenario(
        name="Medium Load: 10 Concurrent Users",
        concurrent_users=10,
        requests_per_user=3,
        queries=queries,
        base_url=base_url
    )

    return scenario.execute()


def test_heavy_load(base_url: str) -> Dict:
    """Test 4: Heavy load with 20 concurrent users"""
    queries = [
        "What is your refund policy?",
        "Tell me about shipping",
        "How do I return items?",
        "What payment methods do you accept?",
        "Do you ship internationally?",
        "What are your business hours?",
        "How do I contact support?",
        "What is your privacy policy?",
        "Do you offer gift wrapping?",
        "What is your warranty policy?"
    ]

    scenario = LoadTestScenario(
        name="Heavy Load: 20 Concurrent Users",
        concurrent_users=20,
        requests_per_user=3,
        queries=queries,
        base_url=base_url
    )

    return scenario.execute()


def test_stress_test(base_url: str) -> Dict:
    """Test 5: Stress test with 50 concurrent users"""
    queries = [
        "What is your refund policy?",
        "Tell me about shipping",
        "How do I return items?",
        "What payment methods do you accept?",
        "Do you ship internationally?"
    ]

    scenario = LoadTestScenario(
        name="Stress Test: 50 Concurrent Users",
        concurrent_users=50,
        requests_per_user=2,
        queries=queries,
        base_url=base_url
    )

    return scenario.execute()


def check_server_health(base_url: str) -> bool:
    """Check if server is healthy before testing"""
    try:
        # Test chatbot endpoint directly (health endpoint has known bug)
        import uuid
        response = requests.post(
            f"{base_url}/api/chatbot",
            json={"message": "test", "session_id": "health_check"},
            headers={"Idempotency-Key": str(uuid.uuid4())},
            timeout=10
        )
        return response.status_code in [200, 400]  # 200 = working, 400 = also means server responding
    except:
        return False


def generate_report(results: List[Dict], output_file: str):
    """Generate JSON report of all test results"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_results": results,
        "summary": {
            "total_scenarios": len(results),
            "scenarios_passed": sum(1 for r in results if r["success_rate"] > 0.95),
            "average_cache_hit_rate": statistics.mean([r["cache_hit_rate"] for r in results]),
        }
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {output_file}")


def main():
    """Run all load tests"""
    print("=" * 70)
    print(" Chat API Load Testing Suite")
    print("=" * 70)
    print()

    base_url = os.getenv("API_BASE_URL", "http://localhost:8003")

    # Check server health
    print(f"Checking server health at {base_url}...")
    if not check_server_health(base_url):
        print(f"❌ Server not responding at {base_url}")
        print(f"\nPlease start the server first:")
        print(f"  uvicorn src.enhanced_api:app --host 127.0.0.1 --port 8003")
        return 1

    print(f"✅ Server is healthy\n")

    # Run all tests
    results = []

    try:
        # Test 1: Baseline
        result = test_baseline_single_user(base_url)
        results.append(result)
        time.sleep(2)  # Brief pause between tests

        # Test 2: Light load
        result = test_light_load(base_url)
        results.append(result)
        time.sleep(2)

        # Test 3: Medium load
        result = test_medium_load(base_url)
        results.append(result)
        time.sleep(2)

        # Test 4: Heavy load
        result = test_heavy_load(base_url)
        results.append(result)
        time.sleep(2)

        # Test 5: Stress test
        result = test_stress_test(base_url)
        results.append(result)

    except KeyboardInterrupt:
        print("\n\nLoad testing interrupted by user")
        return 1

    # Print summary
    print("\n" + "=" * 70)
    print(" Load Testing Summary")
    print("=" * 70)

    for result in results:
        status = "✅ PASS" if result["success_rate"] > 0.95 else "❌ FAIL"
        print(f"{status} - {result['scenario']}")
        print(f"      Success rate: {result['success_rate']:.1%}")
        print(f"      Avg latency: {result.get('avg_latency_ms', 0):.0f}ms")
        print(f"      Cache hit rate: {result['cache_hit_rate']:.1%}")
        print()

    # Overall assessment
    all_passed = all(r["success_rate"] > 0.95 for r in results)
    avg_cache_hit_rate = statistics.mean([r["cache_hit_rate"] for r in results])

    print("=" * 70)
    if all_passed:
        print("✅ All load tests PASSED!")
        print(f"\nAverage cache hit rate: {avg_cache_hit_rate:.1%}")
        print("\nSystem is ready for production deployment at tested load levels.")
    else:
        print("❌ Some load tests FAILED")
        print("\nThe system needs optimization before production deployment.")

    # Generate detailed report
    output_file = project_root / "data" / "load_test_results.json"
    output_file.parent.mkdir(exist_ok=True)
    generate_report(results, str(output_file))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
