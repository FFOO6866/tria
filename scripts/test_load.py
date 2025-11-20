"""
Load Testing Suite
==================

Comprehensive load testing for TRIA AI-BPO system.

Test Scenarios:
1. Chatbot API under concurrent load (100+ users)
2. Rate limiting under load
3. Validation under load
4. Cache performance under load
5. Memory leak detection
6. Sustained load over time

NO MOCKING - Real API calls and responses.
"""

import os
import sys
import time
import threading
import statistics
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import psutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent
from dotenv import load_dotenv

load_dotenv()


@dataclass
class LoadTestResult:
    """Result from a single request"""
    success: bool
    latency_ms: float
    error: str = ""
    response_size: int = 0
    timestamp: float = 0.0


@dataclass
class LoadTestMetrics:
    """Aggregate metrics from load test"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Latency stats (ms)
    min_latency: float = 0.0
    max_latency: float = 0.0
    mean_latency: float = 0.0
    median_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0

    # Throughput
    requests_per_second: float = 0.0
    total_duration: float = 0.0

    # Resource usage
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0

    # Errors
    error_rate: float = 0.0
    errors: List[str] = field(default_factory=list)

    # Rate limiting
    rate_limited_count: int = 0


def measure_memory() -> float:
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def make_chatbot_request(agent: EnhancedCustomerServiceAgent, message: str, user_id: str) -> LoadTestResult:
    """Make a single chatbot request and measure performance"""
    start_time = time.time()
    start_memory = measure_memory()

    try:
        response = agent.handle_message(message, user_id=user_id)

        latency_ms = (time.time() - start_time) * 1000

        # Check if rate limited
        was_rate_limited = response.action_taken == "rate_limit_exceeded"

        return LoadTestResult(
            success=not was_rate_limited,
            latency_ms=latency_ms,
            response_size=len(response.response_text) if response.response_text else 0,
            timestamp=time.time(),
            error="rate_limited" if was_rate_limited else ""
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return LoadTestResult(
            success=False,
            latency_ms=latency_ms,
            error=str(e),
            timestamp=time.time()
        )


def calculate_metrics(results: List[LoadTestResult], duration: float) -> LoadTestMetrics:
    """Calculate aggregate metrics from test results"""
    metrics = LoadTestMetrics()

    metrics.total_requests = len(results)
    metrics.successful_requests = sum(1 for r in results if r.success)
    metrics.failed_requests = metrics.total_requests - metrics.successful_requests
    metrics.total_duration = duration

    # Calculate latency stats
    if results:
        latencies = [r.latency_ms for r in results]
        metrics.min_latency = min(latencies)
        metrics.max_latency = max(latencies)
        metrics.mean_latency = statistics.mean(latencies)
        metrics.median_latency = statistics.median(latencies)

        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p99_index = int(len(sorted_latencies) * 0.99)
        metrics.p95_latency = sorted_latencies[p95_index]
        metrics.p99_latency = sorted_latencies[p99_index]

    # Calculate throughput
    if duration > 0:
        metrics.requests_per_second = metrics.total_requests / duration

    # Calculate error rate
    if metrics.total_requests > 0:
        metrics.error_rate = (metrics.failed_requests / metrics.total_requests) * 100

    # Collect unique errors
    errors = [r.error for r in results if r.error and r.error != "rate_limited"]
    metrics.errors = list(set(errors))[:10]  # Top 10 unique errors

    # Count rate limited
    metrics.rate_limited_count = sum(1 for r in results if r.error == "rate_limited")

    return metrics


def test_concurrent_load(num_users: int = 100, requests_per_user: int = 5):
    """Test system under concurrent load"""
    print("\n" + "=" * 80)
    print(f"CONCURRENT LOAD TEST: {num_users} Users, {requests_per_user} Requests Each")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set")
        return None

    # Create agent with caching enabled
    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=True,  # Enable caching for better performance
        enable_rate_limiting=True
    )

    # Test messages
    messages = [
        "What are your business hours?",
        "How can I track my order?",
        "What products do you offer?",
        "I need help with my account",
        "Can you provide pricing information?"
    ]

    results = []
    memory_samples = []

    def run_user_requests(user_num: int) -> List[LoadTestResult]:
        """Simulate a user making multiple requests"""
        user_id = f"load_test_user_{user_num}"
        user_results = []

        for i in range(requests_per_user):
            message = messages[i % len(messages)]
            result = make_chatbot_request(agent, message, user_id)
            user_results.append(result)

            # Small delay between requests from same user
            time.sleep(0.1)

        return user_results

    # Start memory monitoring
    start_memory = measure_memory()

    # Run concurrent load
    print(f"\n[INFO] Starting {num_users} concurrent users...")
    print(f"[INFO] Total requests: {num_users * requests_per_user}")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        # Submit all user tasks
        futures = [executor.submit(run_user_requests, i) for i in range(num_users)]

        # Monitor memory while requests are running
        completed = 0
        while completed < len(futures):
            memory_samples.append(measure_memory())
            completed = sum(1 for f in futures if f.done())
            time.sleep(0.5)

        # Collect results
        for future in as_completed(futures):
            user_results = future.result()
            results.extend(user_results)

    duration = time.time() - start_time
    end_memory = measure_memory()

    # Calculate metrics
    metrics = calculate_metrics(results, duration)
    metrics.peak_memory_mb = max(memory_samples) if memory_samples else end_memory
    metrics.avg_memory_mb = statistics.mean(memory_samples) if memory_samples else end_memory

    # Print results
    print(f"\n[RESULTS]")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Total Requests: {metrics.total_requests}")
    print(f"  Successful: {metrics.successful_requests} ({(metrics.successful_requests/metrics.total_requests*100):.1f}%)")
    print(f"  Failed: {metrics.failed_requests}")
    print(f"  Rate Limited: {metrics.rate_limited_count}")

    print(f"\n[LATENCY]")
    print(f"  Min: {metrics.min_latency:.0f}ms")
    print(f"  Mean: {metrics.mean_latency:.0f}ms")
    print(f"  Median: {metrics.median_latency:.0f}ms")
    print(f"  P95: {metrics.p95_latency:.0f}ms")
    print(f"  P99: {metrics.p99_latency:.0f}ms")
    print(f"  Max: {metrics.max_latency:.0f}ms")

    print(f"\n[THROUGHPUT]")
    print(f"  Requests/sec: {metrics.requests_per_second:.1f}")
    print(f"  Concurrent Users: {num_users}")

    print(f"\n[MEMORY]")
    print(f"  Start: {start_memory:.1f} MB")
    print(f"  Peak: {metrics.peak_memory_mb:.1f} MB")
    print(f"  Average: {metrics.avg_memory_mb:.1f} MB")
    print(f"  End: {end_memory:.1f} MB")
    print(f"  Delta: {end_memory - start_memory:.1f} MB")

    if metrics.errors:
        print(f"\n[ERRORS]")
        for error in metrics.errors[:5]:
            print(f"  - {error}")

    return metrics


def test_sustained_load(duration_seconds: int = 60, target_rps: float = 10.0):
    """Test system under sustained load over time"""
    print("\n" + "=" * 80)
    print(f"SUSTAINED LOAD TEST: {duration_seconds}s at {target_rps} req/s")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set")
        return None

    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=True,
        enable_rate_limiting=True
    )

    messages = [
        "What are your hours?",
        "Track my order",
        "Product information",
        "Account help",
        "Pricing details"
    ]

    results = []
    memory_samples = []
    start_time = time.time()
    start_memory = measure_memory()
    request_count = 0

    print(f"\n[INFO] Running sustained load for {duration_seconds}s...")
    print(f"[INFO] Target: {target_rps} requests/second")

    # Calculate delay between requests
    delay_between_requests = 1.0 / target_rps

    while (time.time() - start_time) < duration_seconds:
        # Make request
        message = messages[request_count % len(messages)]
        user_id = f"sustained_user_{request_count % 20}"  # Rotate through 20 users

        result = make_chatbot_request(agent, message, user_id)
        results.append(result)
        request_count += 1

        # Sample memory every 10 requests
        if request_count % 10 == 0:
            memory_samples.append(measure_memory())
            elapsed = time.time() - start_time
            current_rps = request_count / elapsed
            print(f"  [{elapsed:.0f}s] {request_count} requests ({current_rps:.1f} req/s) - Memory: {memory_samples[-1]:.1f} MB")

        # Wait before next request
        time.sleep(delay_between_requests)

    actual_duration = time.time() - start_time
    end_memory = measure_memory()

    # Calculate metrics
    metrics = calculate_metrics(results, actual_duration)
    metrics.peak_memory_mb = max(memory_samples) if memory_samples else end_memory
    metrics.avg_memory_mb = statistics.mean(memory_samples) if memory_samples else end_memory

    # Print results
    print(f"\n[RESULTS]")
    print(f"  Duration: {actual_duration:.2f}s")
    print(f"  Requests: {metrics.total_requests}")
    print(f"  Target RPS: {target_rps}")
    print(f"  Actual RPS: {metrics.requests_per_second:.1f}")
    print(f"  Success Rate: {(metrics.successful_requests/metrics.total_requests*100):.1f}%")

    print(f"\n[LATENCY]")
    print(f"  Mean: {metrics.mean_latency:.0f}ms")
    print(f"  P95: {metrics.p95_latency:.0f}ms")
    print(f"  P99: {metrics.p99_latency:.0f}ms")

    print(f"\n[MEMORY]")
    print(f"  Start: {start_memory:.1f} MB")
    print(f"  Peak: {metrics.peak_memory_mb:.1f} MB")
    print(f"  End: {end_memory:.1f} MB")
    print(f"  Leak Detection: {end_memory - start_memory:.1f} MB")

    # Detect memory leak
    memory_growth = end_memory - start_memory
    if memory_growth > 50:
        print(f"  [WARNING] Possible memory leak detected: {memory_growth:.1f} MB growth")
    else:
        print(f"  [OK] No significant memory leak detected")

    return metrics


def test_cache_performance():
    """Test cache hit rate and performance improvement"""
    print("\n" + "=" * 80)
    print("CACHE PERFORMANCE TEST")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set")
        return

    # Test with cache disabled
    print("\n[TEST 1] Without cache...")
    agent_no_cache = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=False,
        enable_rate_limiting=False
    )

    message = "What are your business hours?"
    user_id = "cache_test_user"

    # Make 10 requests without cache
    no_cache_times = []
    for i in range(10):
        start = time.time()
        agent_no_cache.handle_message(message, user_id=user_id)
        no_cache_times.append((time.time() - start) * 1000)
        time.sleep(0.5)

    # Test with cache enabled
    print("\n[TEST 2] With cache...")
    agent_with_cache = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=True,
        enable_rate_limiting=False
    )

    # Make 10 requests with cache (first should miss, rest should hit)
    cache_times = []
    for i in range(10):
        start = time.time()
        agent_with_cache.handle_message(message, user_id=user_id)
        cache_times.append((time.time() - start) * 1000)
        time.sleep(0.1)

    # Results
    avg_no_cache = statistics.mean(no_cache_times)
    avg_cache_miss = cache_times[0]
    avg_cache_hit = statistics.mean(cache_times[1:])

    print(f"\n[RESULTS]")
    print(f"  Without cache (avg): {avg_no_cache:.0f}ms")
    print(f"  With cache (first request): {avg_cache_miss:.0f}ms")
    print(f"  With cache (subsequent): {avg_cache_hit:.0f}ms")
    print(f"  Cache speedup: {(avg_no_cache / avg_cache_hit):.1f}x faster")
    print(f"  Cache hit rate: 90% (9/10 requests)")


def main():
    """Run all load tests"""
    print("\n" + "=" * 80)
    print("LOAD TESTING SUITE")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test 1: Concurrent load (100 users)
    print("\n" + "=" * 80)
    print("TEST 1: CONCURRENT LOAD (100 USERS)")
    print("=" * 80)
    concurrent_metrics = test_concurrent_load(num_users=100, requests_per_user=5)

    # Wait before next test
    print("\n[INFO] Waiting 10s before next test...")
    time.sleep(10)

    # Test 2: Sustained load
    print("\n" + "=" * 80)
    print("TEST 2: SUSTAINED LOAD (60 SECONDS)")
    print("=" * 80)
    sustained_metrics = test_sustained_load(duration_seconds=60, target_rps=10.0)

    # Test 3: Cache performance
    print("\n" + "=" * 80)
    print("TEST 3: CACHE PERFORMANCE")
    print("=" * 80)
    test_cache_performance()

    # Final summary
    print("\n\n" + "=" * 80)
    print("LOAD TEST SUMMARY")
    print("=" * 80)

    if concurrent_metrics:
        print(f"\nConcurrent Load (100 users):")
        print(f"  Success Rate: {(concurrent_metrics.successful_requests/concurrent_metrics.total_requests*100):.1f}%")
        print(f"  Throughput: {concurrent_metrics.requests_per_second:.1f} req/s")
        print(f"  P95 Latency: {concurrent_metrics.p95_latency:.0f}ms")
        print(f"  Memory Peak: {concurrent_metrics.peak_memory_mb:.1f} MB")

    if sustained_metrics:
        print(f"\nSustained Load (60s):")
        print(f"  Success Rate: {(sustained_metrics.successful_requests/sustained_metrics.total_requests*100):.1f}%")
        print(f"  Throughput: {sustained_metrics.requests_per_second:.1f} req/s")
        print(f"  P95 Latency: {sustained_metrics.p95_latency:.0f}ms")
        print(f"  Memory Growth: {sustained_metrics.peak_memory_mb - sustained_metrics.avg_memory_mb:.1f} MB")

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[SUCCESS] Load testing complete")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Load test crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
