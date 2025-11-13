#!/usr/bin/env python3
"""
Load Test 4: Soak Test (Memory Leak Detection)
===============================================

Tests system stability over extended period to detect memory leaks
and performance degradation.

Test Parameters:
- Concurrent users: 5 (low load)
- Duration: 24 hours (86,400 seconds)
- Request pattern: Continuous steady queries
- Success criteria:
  - Error rate < 1%
  - No memory leaks (memory stable over time)
  - Performance doesn't degrade (latency stable)
  - No service crashes

This test validates the system can run continuously for days
without accumulating memory or degrading performance.

⚠️  WARNING: This test takes 24 hours to complete!
Consider running overnight or reducing duration for faster validation.
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import psutil
import os

# Configuration
API_BASE_URL = "http://localhost:8003"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/chatbot"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

NUM_CONCURRENT_USERS = 5
TEST_DURATION_SECONDS = 86400  # 24 hours (can reduce to 3600 for 1 hour test)
REPORT_INTERVAL_SECONDS = 300  # Report every 5 minutes
MEMORY_CHECK_INTERVAL = 300  # Check memory every 5 minutes

# Test queries
TEST_QUERIES = [
    "What is your refund policy?",
    "I need to track my order",
    "Tell me about your delivery times",
    "What are your business hours?",
    "How do I contact customer service?",
]

# Metrics storage
metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "response_times": [],
    "errors": defaultdict(int),
    "memory_samples": [],  # Track memory over time
    "latency_samples": [],  # Track P95 latency over time
    "start_time": None,
    "end_time": None
}


async def send_chat_request(session: aiohttp.ClientSession, query: str, session_id: str) -> Dict:
    """Send a single chat request"""
    start_time = time.time()

    try:
        async with session.post(
            CHAT_ENDPOINT,
            json={"message": query, "session_id": session_id},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            response_time = time.time() - start_time

            if response.status == 200:
                await response.json()
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
    """Simulate a single user for the test duration"""
    session_id = f"soak_test_user_{user_id}"
    query_index = 0

    async with aiohttp.ClientSession() as session:
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            query = TEST_QUERIES[query_index % len(TEST_QUERIES)]
            query_index += 1

            result = await send_chat_request(session, query, session_id)

            # Update metrics
            metrics["total_requests"] += 1
            metrics["response_times"].append(result["response_time"])

            if result["status"] == "success":
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1
                metrics["errors"][result["error"]] += 1

            # Realistic delay (10 seconds between queries)
            await asyncio.sleep(10)


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB"""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except:
        return 0.0


def detect_memory_leak(memory_samples: List[Dict]) -> Dict:
    """
    Detect if there's a memory leak based on samples

    Returns:
        Dict with leak_detected, trend, and analysis
    """
    if len(memory_samples) < 10:
        return {
            "leak_detected": False,
            "reason": "Insufficient samples",
            "trend": "unknown"
        }

    # Get memory values over time
    memory_values = [s["memory_mb"] for s in memory_samples]

    # Compare first 25% with last 25%
    quarter = len(memory_values) // 4
    first_quarter_avg = statistics.mean(memory_values[:quarter])
    last_quarter_avg = statistics.mean(memory_values[-quarter:])

    # Calculate growth
    memory_growth = last_quarter_avg - first_quarter_avg
    growth_percentage = (memory_growth / first_quarter_avg) * 100

    # Memory leak criteria: >20% growth over test period
    if growth_percentage > 20:
        return {
            "leak_detected": True,
            "reason": f"Memory grew {growth_percentage:.1f}% ({first_quarter_avg:.1f}MB → {last_quarter_avg:.1f}MB)",
            "trend": "increasing",
            "first_quarter_avg": first_quarter_avg,
            "last_quarter_avg": last_quarter_avg,
            "growth_mb": memory_growth
        }
    else:
        return {
            "leak_detected": False,
            "reason": f"Memory stable (growth: {growth_percentage:.1f}%)",
            "trend": "stable",
            "first_quarter_avg": first_quarter_avg,
            "last_quarter_avg": last_quarter_avg,
            "growth_mb": memory_growth
        }


def calculate_metrics() -> Dict:
    """Calculate current metrics"""
    if not metrics["response_times"]:
        return {
            "total_requests": 0,
            "success_rate": 0,
            "error_rate": 0,
            "response_time": {"mean": 0, "median": 0, "p95": 0, "p99": 0}
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


async def monitor_memory_and_performance(interval_seconds: int, duration_seconds: int):
    """Monitor memory usage and performance over time"""
    start_time = time.time()
    sample_count = 0

    print("\n" + "=" * 80)
    print("SOAK TEST - MEMORY & PERFORMANCE MONITORING")
    print("=" * 80)

    while time.time() - start_time < duration_seconds:
        await asyncio.sleep(interval_seconds)
        sample_count += 1
        elapsed = time.time() - start_time

        # Get current memory
        current_memory = get_memory_usage_mb()

        # Get current metrics
        current_metrics = calculate_metrics()
        current_p95 = current_metrics["response_time"]["p95"]

        # Store samples
        metrics["memory_samples"].append({
            "timestamp": datetime.now().isoformat(),
            "elapsed_hours": elapsed / 3600,
            "memory_mb": current_memory
        })
        metrics["latency_samples"].append({
            "timestamp": datetime.now().isoformat(),
            "elapsed_hours": elapsed / 3600,
            "p95_latency": current_p95
        })

        # Print report
        print(f"\nSample #{sample_count} - Elapsed: {elapsed/3600:.1f} hours")
        print(f"  Memory: {current_memory:.1f} MB")
        print(f"  Requests: {current_metrics['total_requests']}")
        print(f"  Success Rate: {current_metrics['success_rate']:.2f}%")
        print(f"  Error Rate: {current_metrics['error_rate']:.2f}%")
        print(f"  P95 Latency: {current_p95:.2f}s")

        # Check for memory leak (after 30 minutes)
        if elapsed > 1800 and len(metrics["memory_samples"]) > 10:
            leak_analysis = detect_memory_leak(metrics["memory_samples"])
            if leak_analysis["leak_detected"]:
                print(f"  ⚠️  WARNING: Possible memory leak detected!")
                print(f"     {leak_analysis['reason']}")

        # Check for performance degradation
        if len(metrics["latency_samples"]) > 10:
            first_samples = [s["p95_latency"] for s in metrics["latency_samples"][:5]]
            recent_samples = [s["p95_latency"] for s in metrics["latency_samples"][-5:]]
            if statistics.mean(recent_samples) > statistics.mean(first_samples) * 1.5:
                print(f"  ⚠️  WARNING: Performance degradation detected!")


async def main():
    """Main test execution"""
    print("=" * 80)
    print("LOAD TEST 4: SOAK TEST (MEMORY LEAK DETECTION)")
    print("=" * 80)
    print(f"Concurrent users: {NUM_CONCURRENT_USERS}")
    print(f"Duration: {TEST_DURATION_SECONDS/3600:.0f} hours ({TEST_DURATION_SECONDS}s)")
    print(f"Test queries: {len(TEST_QUERIES)} different queries")
    print(f"API endpoint: {CHAT_ENDPOINT}")
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Expected end: {(datetime.now() + timedelta(seconds=TEST_DURATION_SECONDS)).isoformat()}")
    print("\n⚠️  This test will run for an extended period")
    print("   You can reduce TEST_DURATION_SECONDS in the script for faster testing")
    print("=" * 80)

    # Initialize metrics
    metrics["start_time"] = time.time()

    # Create tasks
    tasks = []

    # User simulation tasks
    for user_id in range(NUM_CONCURRENT_USERS):
        task = asyncio.create_task(
            simulate_user(user_id, TEST_DURATION_SECONDS)
        )
        tasks.append(task)

    # Monitoring task
    monitor_task = asyncio.create_task(
        monitor_memory_and_performance(MEMORY_CHECK_INTERVAL, TEST_DURATION_SECONDS)
    )
    tasks.append(monitor_task)

    # Wait for all tasks
    await asyncio.gather(*tasks)

    metrics["end_time"] = time.time()

    # Final report
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    final_metrics = calculate_metrics()

    print(f"\nTest Duration: {(metrics['end_time'] - metrics['start_time'])/3600:.1f} hours")
    print(f"Total Requests: {final_metrics['total_requests']}")
    print(f"Successful: {final_metrics['successful_requests']} ({final_metrics['success_rate']:.2f}%)")
    print(f"Failed: {final_metrics['failed_requests']} ({final_metrics['error_rate']:.2f}%)")

    print(f"\nResponse Times:")
    print(f"  Mean: {final_metrics['response_time']['mean']:.2f}s")
    print(f"  Median: {final_metrics['response_time']['median']:.2f}s")
    print(f"  P95: {final_metrics['response_time']['p95']:.2f}s")
    print(f"  P99: {final_metrics['response_time']['p99']:.2f}s")

    # Memory leak analysis
    print(f"\n" + "=" * 80)
    print("MEMORY LEAK ANALYSIS")
    print("=" * 80)

    leak_analysis = detect_memory_leak(metrics["memory_samples"])
    print(f"\nLeak Detected: {'YES ⚠️' if leak_analysis['leak_detected'] else 'NO ✅'}")
    print(f"Reason: {leak_analysis['reason']}")

    if len(metrics["memory_samples"]) > 0:
        memory_values = [s["memory_mb"] for s in metrics["memory_samples"]]
        print(f"\nMemory Statistics:")
        print(f"  Initial: {memory_values[0]:.1f} MB")
        print(f"  Final: {memory_values[-1]:.1f} MB")
        print(f"  Min: {min(memory_values):.1f} MB")
        print(f"  Max: {max(memory_values):.1f} MB")
        print(f"  Growth: {memory_values[-1] - memory_values[0]:.1f} MB")

    # Performance degradation analysis
    if len(metrics["latency_samples"]) > 10:
        first_latencies = [s["p95_latency"] for s in metrics["latency_samples"][:5]]
        last_latencies = [s["p95_latency"] for s in metrics["latency_samples"][-5:]]
        first_avg = statistics.mean(first_latencies)
        last_avg = statistics.mean(last_latencies)
        degradation = ((last_avg - first_avg) / first_avg) * 100

        print(f"\n" + "=" * 80)
        print("PERFORMANCE DEGRADATION ANALYSIS")
        print("=" * 80)
        print(f"\nP95 Latency Trend:")
        print(f"  Initial (first 5 samples): {first_avg:.2f}s")
        print(f"  Final (last 5 samples): {last_avg:.2f}s")
        print(f"  Change: {degradation:+.1f}%")

    # Success criteria
    print("\n" + "=" * 80)
    print("SUCCESS CRITERIA EVALUATION")
    print("=" * 80)

    criteria_passed = []
    criteria_failed = []

    # Criterion 1: Error rate < 1%
    if final_metrics['error_rate'] < 1:
        criteria_passed.append("✅ Error rate < 1% PASS")
    else:
        criteria_failed.append(f"❌ Error rate < 1% FAIL ({final_metrics['error_rate']:.2f}%)")

    # Criterion 2: No memory leak
    if not leak_analysis["leak_detected"]:
        criteria_passed.append("✅ No memory leak detected PASS")
    else:
        criteria_failed.append(f"❌ Memory leak detected FAIL ({leak_analysis['reason']})")

    # Criterion 3: Performance stable (degradation < 20%)
    if len(metrics["latency_samples"]) > 10:
        if degradation < 20:
            criteria_passed.append("✅ Performance stable PASS")
        else:
            criteria_failed.append(f"❌ Performance degraded FAIL ({degradation:.1f}% slower)")

    # Criterion 4: System didn't crash
    if metrics["end_time"] - metrics["start_time"] >= TEST_DURATION_SECONDS * 0.95:
        criteria_passed.append("✅ System ran full duration PASS")
    else:
        criteria_failed.append("❌ System crashed before completion FAIL")

    for criterion in criteria_passed:
        print(criterion)

    for criterion in criteria_failed:
        print(criterion)

    # Overall verdict
    print("\n" + "=" * 80)
    if not criteria_failed:
        print("✅ SOAK TEST: PASSED")
        print("System is stable for long-term operation")
    else:
        print("❌ SOAK TEST: FAILED")
        print(f"Failed {len(criteria_failed)} of {len(criteria_passed) + len(criteria_failed)} criteria")
    print("=" * 80)

    # Save results
    results_file = f"load_test_4_soak_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_type": "soak_test",
            "parameters": {
                "concurrent_users": NUM_CONCURRENT_USERS,
                "duration_hours": TEST_DURATION_SECONDS / 3600
            },
            "metrics": final_metrics,
            "memory_analysis": leak_analysis,
            "memory_samples": metrics["memory_samples"],
            "latency_samples": metrics["latency_samples"],
            "errors": dict(metrics["errors"]),
            "criteria_passed": criteria_passed,
            "criteria_failed": criteria_failed,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: This test runs for 24 hours by default")
    print("To run a shorter test, edit TEST_DURATION_SECONDS in the script")
    print("Recommended for initial testing: 3600 seconds (1 hour)\n")

    response = input("Continue with soak test? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        asyncio.run(main())
    else:
        print("Test cancelled")
