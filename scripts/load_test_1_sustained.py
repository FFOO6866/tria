#!/usr/bin/env python3
"""
Load Test 1: Sustained Load
============================

Tests system stability under sustained concurrent load.

Test Parameters:
- Concurrent users: 10
- Duration: 1 hour (3600 seconds)
- Request pattern: Continuous queries
- Success criteria:
  - Error rate < 5%
  - P95 latency < 10s
  - No memory leaks
  - No service crashes

This test validates the system can handle normal production load
for extended periods without degradation.
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

# Configuration
API_BASE_URL = "http://localhost:8003"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/chatbot"
NUM_CONCURRENT_USERS = 10
TEST_DURATION_SECONDS = 3600  # 1 hour
REPORT_INTERVAL_SECONDS = 60  # Report every minute

# Test queries (mix of common and varied queries)
TEST_QUERIES = [
    "What is your refund policy?",
    "I need to track my order",
    "Tell me about your delivery times",
    "I want to place an order for pizza boxes",
    "What are your business hours?",
    "How do I contact customer service?",
    "I have a complaint about my last order",
    "What products do you offer?",
    "Can I change my delivery address?",
    "I need help with an urgent issue",
]

# Metrics storage
metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "response_times": [],
    "errors": defaultdict(int),
    "start_time": None,
    "end_time": None
}


async def send_chat_request(session: aiohttp.ClientSession, query: str, session_id: str) -> Dict:
    """
    Send a single chat request

    Returns:
        Dict with status, response_time, and error (if any)
    """
    start_time = time.time()

    try:
        async with session.post(
            CHAT_ENDPOINT,
            json={"message": query, "session_id": session_id},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            response_time = time.time() - start_time

            if response.status == 200:
                await response.json()  # Consume response
                return {
                    "status": "success",
                    "response_time": response_time,
                    "error": None
                }
            else:
                return {
                    "status": "error",
                    "response_time": response_time,
                    "error": f"HTTP {response.status}"
                }

    except asyncio.TimeoutError:
        response_time = time.time() - start_time
        return {
            "status": "error",
            "response_time": response_time,
            "error": "Timeout"
        }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            "status": "error",
            "response_time": response_time,
            "error": str(e)
        }


async def simulate_user(user_id: int, duration_seconds: int):
    """
    Simulate a single user sending requests continuously

    Args:
        user_id: Unique user identifier
        duration_seconds: How long to run
    """
    session_id = f"load_test_user_{user_id}"
    query_index = 0

    async with aiohttp.ClientSession() as session:
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            # Select query (cycle through)
            query = TEST_QUERIES[query_index % len(TEST_QUERIES)]
            query_index += 1

            # Send request
            result = await send_chat_request(session, query, session_id)

            # Update metrics
            metrics["total_requests"] += 1
            metrics["response_times"].append(result["response_time"])

            if result["status"] == "success":
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1
                metrics["errors"][result["error"]] += 1

            # Small delay between requests (5 seconds)
            # Realistic user behavior: read response, think, type next query
            await asyncio.sleep(5)


def calculate_metrics() -> Dict:
    """Calculate and return current metrics"""
    if not metrics["response_times"]:
        return {
            "total_requests": 0,
            "success_rate": 0,
            "error_rate": 0,
            "response_time": {"mean": 0, "median": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}
        }

    response_times = sorted(metrics["response_times"])
    total = metrics["total_requests"]
    successful = metrics["successful_requests"]
    failed = metrics["failed_requests"]

    return {
        "total_requests": total,
        "successful_requests": successful,
        "failed_requests": failed,
        "success_rate": (successful / total * 100) if total > 0 else 0,
        "error_rate": (failed / total * 100) if total > 0 else 0,
        "response_time": {
            "mean": statistics.mean(response_times),
            "median": statistics.median(response_times),
            "p95": response_times[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0,
            "p99": response_times[int(len(response_times) * 0.99)] if len(response_times) > 0 else 0,
            "min": min(response_times),
            "max": max(response_times)
        }
    }


async def report_metrics_periodically(interval_seconds: int, duration_seconds: int):
    """Report metrics at regular intervals"""
    start_time = time.time()
    report_count = 0

    print("\n" + "=" * 80)
    print("SUSTAINED LOAD TEST - PROGRESS REPORTS")
    print("=" * 80)

    while time.time() - start_time < duration_seconds:
        await asyncio.sleep(interval_seconds)
        report_count += 1
        elapsed = time.time() - start_time

        current_metrics = calculate_metrics()

        print(f"\nReport #{report_count} - Elapsed: {elapsed/60:.1f} minutes")
        print(f"  Total requests: {current_metrics['total_requests']}")
        print(f"  Success rate: {current_metrics['success_rate']:.2f}%")
        print(f"  Error rate: {current_metrics['error_rate']:.2f}%")
        print(f"  Response time (P95): {current_metrics['response_time']['p95']:.2f}s")
        print(f"  Response time (mean): {current_metrics['response_time']['mean']:.2f}s")

        # Check for issues
        if current_metrics['error_rate'] > 10:
            print(f"  ⚠️  WARNING: High error rate ({current_metrics['error_rate']:.2f}%)")

        if current_metrics['response_time']['p95'] > 10:
            print(f"  ⚠️  WARNING: High P95 latency ({current_metrics['response_time']['p95']:.2f}s)")


async def main():
    """Main test execution"""
    print("=" * 80)
    print("LOAD TEST 1: SUSTAINED LOAD")
    print("=" * 80)
    print(f"Concurrent users: {NUM_CONCURRENT_USERS}")
    print(f"Duration: {TEST_DURATION_SECONDS/60:.0f} minutes ({TEST_DURATION_SECONDS}s)")
    print(f"Test queries: {len(TEST_QUERIES)} different queries")
    print(f"API endpoint: {CHAT_ENDPOINT}")
    print(f"Start time: {datetime.now().isoformat()}")
    print("=" * 80)

    # Initialize metrics
    metrics["start_time"] = time.time()

    # Create tasks for concurrent users + reporter
    tasks = []

    # User simulation tasks
    for user_id in range(NUM_CONCURRENT_USERS):
        task = asyncio.create_task(
            simulate_user(user_id, TEST_DURATION_SECONDS)
        )
        tasks.append(task)

    # Metrics reporting task
    reporter_task = asyncio.create_task(
        report_metrics_periodically(REPORT_INTERVAL_SECONDS, TEST_DURATION_SECONDS)
    )
    tasks.append(reporter_task)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)

    metrics["end_time"] = time.time()

    # Final report
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    final_metrics = calculate_metrics()

    print(f"\nTest Duration: {(metrics['end_time'] - metrics['start_time'])/60:.1f} minutes")
    print(f"Total Requests: {final_metrics['total_requests']}")
    print(f"Successful: {final_metrics['successful_requests']} ({final_metrics['success_rate']:.2f}%)")
    print(f"Failed: {final_metrics['failed_requests']} ({final_metrics['error_rate']:.2f}%)")

    print(f"\nResponse Times:")
    print(f"  Mean: {final_metrics['response_time']['mean']:.2f}s")
    print(f"  Median: {final_metrics['response_time']['median']:.2f}s")
    print(f"  P95: {final_metrics['response_time']['p95']:.2f}s")
    print(f"  P99: {final_metrics['response_time']['p99']:.2f}s")
    print(f"  Min: {final_metrics['response_time']['min']:.2f}s")
    print(f"  Max: {final_metrics['response_time']['max']:.2f}s")

    if metrics["errors"]:
        print(f"\nError Breakdown:")
        for error, count in sorted(metrics["errors"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count} ({count/final_metrics['total_requests']*100:.2f}%)")

    # Success criteria check
    print("\n" + "=" * 80)
    print("SUCCESS CRITERIA EVALUATION")
    print("=" * 80)

    criteria_passed = []
    criteria_failed = []

    # Criterion 1: Error rate < 5%
    if final_metrics['error_rate'] < 5:
        criteria_passed.append("✅ Error rate < 5% PASS")
    else:
        criteria_failed.append(f"❌ Error rate < 5% FAIL ({final_metrics['error_rate']:.2f}%)")

    # Criterion 2: P95 latency < 10s
    if final_metrics['response_time']['p95'] < 10:
        criteria_passed.append("✅ P95 latency < 10s PASS")
    else:
        criteria_failed.append(f"❌ P95 latency < 10s FAIL ({final_metrics['response_time']['p95']:.2f}s)")

    # Criterion 3: At least 90% of expected requests completed
    expected_requests_min = (TEST_DURATION_SECONDS / 5) * NUM_CONCURRENT_USERS * 0.9  # 90% of expected
    if final_metrics['total_requests'] >= expected_requests_min:
        criteria_passed.append("✅ Request throughput adequate PASS")
    else:
        criteria_failed.append(f"❌ Request throughput too low FAIL ({final_metrics['total_requests']} vs {expected_requests_min:.0f} expected)")

    # Print results
    for criterion in criteria_passed:
        print(criterion)

    for criterion in criteria_failed:
        print(criterion)

    # Overall verdict
    print("\n" + "=" * 80)
    if not criteria_failed:
        print("✅ SUSTAINED LOAD TEST: PASSED")
        print("System is stable under sustained load for 1 hour")
    else:
        print("❌ SUSTAINED LOAD TEST: FAILED")
        print(f"Failed {len(criteria_failed)} of {len(criteria_passed) + len(criteria_failed)} criteria")
    print("=" * 80)

    # Save detailed results to file
    results_file = f"load_test_1_sustained_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_type": "sustained_load",
            "parameters": {
                "concurrent_users": NUM_CONCURRENT_USERS,
                "duration_seconds": TEST_DURATION_SECONDS,
                "queries": TEST_QUERIES
            },
            "metrics": final_metrics,
            "errors": dict(metrics["errors"]),
            "criteria_passed": criteria_passed,
            "criteria_failed": criteria_failed,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
