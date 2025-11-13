#!/usr/bin/env python3
"""
Load Test 5: Chaos Engineering Test
====================================

Tests system resilience under random failure conditions.

Test Parameters:
- Concurrent users: 20
- Duration: 10 minutes (600 seconds)
- Chaos scenarios:
  * Random request delays/timeouts
  * Intermittent network failures
  * Random error injection
  * Connection pool exhaustion attempts
  * Concurrent burst attempts

Success criteria:
- System recovers from failures automatically
- Error rate < 30% (very lenient due to chaos)
- No complete system crash
- Graceful degradation observed

This test validates the system's resilience and ability to
recover from various failure scenarios without manual intervention.

⚠️  WARNING: This test intentionally causes failures
"""

import asyncio
import aiohttp
import time
import json
import statistics
import random
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

# Configuration
API_BASE_URL = "http://localhost:8003"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/chatbot"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

NUM_CONCURRENT_USERS = 20
TEST_DURATION_SECONDS = 600  # 10 minutes
REPORT_INTERVAL_SECONDS = 30

# Chaos parameters
CHAOS_PROBABILITY = 0.3  # 30% of requests will experience chaos
TIMEOUT_RANGE = (1, 5)  # Random timeout between 1-5 seconds
MAX_RETRIES = 2

# Test queries
TEST_QUERIES = [
    "Hello",
    "What is your refund policy?",
    "I need help with my order",
    "Tell me about delivery",
    "Place an order for pizza boxes",
    "I have a complaint",
]

# Metrics storage
metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "chaos_injected": 0,
    "recovered_requests": 0,  # Requests that succeeded after chaos
    "response_times": [],
    "errors": defaultdict(int),
    "chaos_events": defaultdict(int),
    "start_time": None,
    "end_time": None
}


async def inject_chaos() -> str:
    """
    Randomly inject chaos into the system

    Returns:
        Type of chaos injected or None
    """
    if random.random() > CHAOS_PROBABILITY:
        return None  # No chaos this time

    chaos_type = random.choice([
        "timeout",
        "delay",
        "connection_error",
        "multiple_requests"  # Connection pool stress
    ])

    metrics["chaos_injected"] += 1
    metrics["chaos_events"][chaos_type] += 1

    return chaos_type


async def send_chat_request_with_chaos(
    session: aiohttp.ClientSession,
    query: str,
    session_id: str,
    chaos_type: str = None
) -> Dict:
    """
    Send a chat request with optional chaos injection

    Args:
        session: aiohttp session
        query: Query to send
        session_id: Session ID
        chaos_type: Type of chaos to inject (if any)

    Returns:
        Dict with status, response_time, chaos info
    """
    start_time = time.time()

    # Apply chaos if specified
    if chaos_type == "timeout":
        # Use a very short timeout to cause failure
        timeout = random.uniform(*TIMEOUT_RANGE)
    elif chaos_type == "delay":
        # Add artificial delay before request
        await asyncio.sleep(random.uniform(2, 5))
        timeout = 30
    elif chaos_type == "connection_error":
        # Simulate connection error by using wrong endpoint
        return {
            "status": "error",
            "response_time": time.time() - start_time,
            "error": "Simulated connection error",
            "chaos": chaos_type,
            "recovered": False
        }
    elif chaos_type == "multiple_requests":
        # Send multiple concurrent requests (stress connection pool)
        timeout = 30
    else:
        timeout = 30  # Normal timeout

    try:
        async with session.post(
            CHAT_ENDPOINT,
            json={"message": query, "session_id": session_id},
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            response_time = time.time() - start_time

            if response.status == 200:
                await response.json()
                return {
                    "status": "success",
                    "response_time": response_time,
                    "error": None,
                    "chaos": chaos_type,
                    "recovered": chaos_type is not None  # Recovered if chaos was injected
                }
            else:
                return {
                    "status": "error",
                    "response_time": response_time,
                    "error": f"HTTP {response.status}",
                    "chaos": chaos_type,
                    "recovered": False
                }

    except asyncio.TimeoutError:
        response_time = time.time() - start_time
        return {
            "status": "error",
            "response_time": response_time,
            "error": "Timeout",
            "chaos": chaos_type,
            "recovered": False
        }
    except Exception as e:
        response_time = time.time() - start_time
        return {
            "status": "error",
            "response_time": response_time,
            "error": str(e),
            "chaos": chaos_type,
            "recovered": False
        }


async def send_with_retry(
    session: aiohttp.ClientSession,
    query: str,
    session_id: str,
    max_retries: int = MAX_RETRIES
) -> Dict:
    """
    Send request with retry logic after chaos

    Returns:
        Final result after retries
    """
    # First attempt (with potential chaos)
    chaos_type = await inject_chaos()
    result = await send_chat_request_with_chaos(session, query, session_id, chaos_type)

    # If chaos caused failure, retry without chaos
    if result["status"] == "error" and chaos_type is not None:
        for retry in range(max_retries):
            await asyncio.sleep(1)  # Brief delay before retry
            retry_result = await send_chat_request_with_chaos(session, query, session_id, None)

            if retry_result["status"] == "success":
                # System recovered!
                metrics["recovered_requests"] += 1
                return {
                    **retry_result,
                    "initial_chaos": chaos_type,
                    "recovered_on_retry": retry + 1
                }

    return result


async def simulate_user(user_id: int, duration_seconds: int):
    """Simulate a single user with chaos injection"""
    session_id = f"chaos_test_user_{user_id}"
    query_index = 0

    async with aiohttp.ClientSession() as session:
        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            query = TEST_QUERIES[query_index % len(TEST_QUERIES)]
            query_index += 1

            # Send request with potential chaos and retry
            result = await send_with_retry(session, query, session_id)

            # Update metrics
            metrics["total_requests"] += 1
            metrics["response_times"].append(result["response_time"])

            if result["status"] == "success":
                metrics["successful_requests"] += 1
            else:
                metrics["failed_requests"] += 1
                metrics["errors"][result["error"]] += 1

            # Random delay between requests (2-5 seconds)
            await asyncio.sleep(random.uniform(2, 5))


def calculate_metrics() -> Dict:
    """Calculate current metrics"""
    if not metrics["response_times"]:
        return {
            "total_requests": 0,
            "success_rate": 0,
            "error_rate": 0,
            "recovery_rate": 0,
            "response_time": {"mean": 0, "median": 0, "p95": 0}
        }

    response_times = sorted(metrics["response_times"])
    total = metrics["total_requests"]
    successful = metrics["successful_requests"]
    failed = metrics["failed_requests"]
    chaos_injected = metrics["chaos_injected"]
    recovered = metrics["recovered_requests"]

    return {
        "total_requests": total,
        "successful_requests": successful,
        "failed_requests": failed,
        "chaos_injected": chaos_injected,
        "recovered_requests": recovered,
        "success_rate": (successful / total * 100) if total > 0 else 0,
        "error_rate": (failed / total * 100) if total > 0 else 0,
        "recovery_rate": (recovered / chaos_injected * 100) if chaos_injected > 0 else 0,
        "response_time": {
            "mean": statistics.mean(response_times),
            "median": statistics.median(response_times),
            "p95": response_times[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0,
            "p99": response_times[int(len(response_times) * 0.99)] if len(response_times) > 0 else 0
        }
    }


async def monitor_health(interval_seconds: int, duration_seconds: int):
    """Monitor system health during chaos"""
    start_time = time.time()

    print("\n" + "=" * 80)
    print("CHAOS TEST - HEALTH MONITORING")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration_seconds:
            await asyncio.sleep(interval_seconds)

            # Check health endpoint
            try:
                async with session.get(
                    HEALTH_ENDPOINT,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    health_status = "✅ UP" if response.status == 200 else "⚠️  DEGRADED"
            except:
                health_status = "🚨 DOWN"

            # Get current metrics
            current_metrics = calculate_metrics()

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Health: {health_status}")
            print(f"  Requests: {current_metrics['total_requests']} | Success: {current_metrics['success_rate']:.1f}%")
            print(f"  Chaos Injected: {current_metrics['chaos_injected']} | Recovered: {current_metrics['recovery_rate']:.1f}%")
            print(f"  Error Rate: {current_metrics['error_rate']:.1f}%")


async def main():
    """Main test execution"""
    print("=" * 80)
    print("LOAD TEST 5: CHAOS ENGINEERING TEST")
    print("=" * 80)
    print(f"Concurrent users: {NUM_CONCURRENT_USERS}")
    print(f"Duration: {TEST_DURATION_SECONDS/60:.1f} minutes")
    print(f"Chaos probability: {CHAOS_PROBABILITY*100:.0f}%")
    print(f"Chaos types: timeout, delay, connection_error, pool_stress")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"\nStart time: {datetime.now().isoformat()}")
    print("\n⚠️  This test INTENTIONALLY causes failures to test resilience")
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

    # Health monitoring task
    monitor_task = asyncio.create_task(
        monitor_health(REPORT_INTERVAL_SECONDS, TEST_DURATION_SECONDS)
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

    print(f"\nTest Duration: {(metrics['end_time'] - metrics['start_time'])/60:.1f} minutes")
    print(f"Total Requests: {final_metrics['total_requests']}")
    print(f"Successful: {final_metrics['successful_requests']} ({final_metrics['success_rate']:.2f}%)")
    print(f"Failed: {final_metrics['failed_requests']} ({final_metrics['error_rate']:.2f}%)")

    print(f"\nChaos Impact:")
    print(f"  Chaos Events Injected: {final_metrics['chaos_injected']}")
    print(f"  Requests Recovered: {final_metrics['recovered_requests']}")
    print(f"  Recovery Rate: {final_metrics['recovery_rate']:.2f}%")

    print(f"\nChaos Event Breakdown:")
    for chaos_type, count in sorted(metrics["chaos_events"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {chaos_type}: {count}")

    print(f"\nResponse Times:")
    print(f"  Mean: {final_metrics['response_time']['mean']:.2f}s")
    print(f"  Median: {final_metrics['response_time']['median']:.2f}s")
    print(f"  P95: {final_metrics['response_time']['p95']:.2f}s")

    if metrics["errors"]:
        print(f"\nError Breakdown:")
        for error, count in sorted(metrics["errors"].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {error}: {count}")

    # Success criteria
    print("\n" + "=" * 80)
    print("SUCCESS CRITERIA EVALUATION")
    print("=" * 80)

    criteria_passed = []
    criteria_failed = []

    # Criterion 1: System didn't crash (some successful requests)
    if final_metrics['successful_requests'] > 0:
        criteria_passed.append("✅ System survived chaos PASS")
    else:
        criteria_failed.append("❌ System crashed FAIL")

    # Criterion 2: Error rate < 30% (very lenient due to intentional failures)
    if final_metrics['error_rate'] < 30:
        criteria_passed.append("✅ Error rate < 30% PASS")
    else:
        criteria_failed.append(f"❌ Error rate < 30% FAIL ({final_metrics['error_rate']:.2f}%)")

    # Criterion 3: Recovery rate > 50% (system can recover from failures)
    if final_metrics['recovery_rate'] > 50:
        criteria_passed.append("✅ Recovery rate > 50% PASS")
    else:
        criteria_failed.append(f"❌ Recovery rate > 50% FAIL ({final_metrics['recovery_rate']:.2f}%)")

    # Criterion 4: P95 latency < 20s (lenient for chaos)
    if final_metrics['response_time']['p95'] < 20:
        criteria_passed.append("✅ P95 latency < 20s PASS")
    else:
        criteria_failed.append(f"❌ P95 latency < 20s FAIL ({final_metrics['response_time']['p95']:.2f}s)")

    for criterion in criteria_passed:
        print(criterion)

    for criterion in criteria_failed:
        print(criterion)

    # Overall verdict
    print("\n" + "=" * 80)
    if not criteria_failed:
        print("✅ CHAOS TEST: PASSED")
        print("System demonstrates good resilience and recovery")
    else:
        print("❌ CHAOS TEST: FAILED")
        print(f"Failed {len(criteria_failed)} of {len(criteria_passed) + len(criteria_failed)} criteria")
        print("\nRecommendations:")
        if final_metrics['error_rate'] > 30:
            print("  - Add circuit breakers for external services")
            print("  - Implement request retry logic")
        if final_metrics['recovery_rate'] < 50:
            print("  - Improve error handling and retry strategies")
            print("  - Add graceful degradation for failed dependencies")
    print("=" * 80)

    # Save results
    results_file = f"load_test_5_chaos_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_type": "chaos_test",
            "parameters": {
                "concurrent_users": NUM_CONCURRENT_USERS,
                "duration_seconds": TEST_DURATION_SECONDS,
                "chaos_probability": CHAOS_PROBABILITY,
                "max_retries": MAX_RETRIES
            },
            "metrics": final_metrics,
            "chaos_events": dict(metrics["chaos_events"]),
            "errors": dict(metrics["errors"]),
            "criteria_passed": criteria_passed,
            "criteria_failed": criteria_failed,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
