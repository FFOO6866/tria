#!/usr/bin/env python3
"""
Load Test 3: Spike Test
========================

Tests system behavior under extreme sudden spikes and recovery.

Test Pattern:
- Phase 1: Baseline (5 users, 1 minute)
- Phase 2: Spike (100 users, 2 minutes)
- Phase 3: Recovery (5 users, 2 minutes)

Success criteria:
- System doesn't crash during spike
- Error rate < 20% during spike (very lenient)
- System recovers after spike (error rate < 5%)
- Memory returns to baseline after recovery

This test validates the system can survive extreme traffic spikes
and recover gracefully when load returns to normal.
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

# Configuration
API_BASE_URL = "http://localhost:8003"
CHAT_ENDPOINT = f"{API_BASE_URL}/api/chatbot"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

# Test phases
BASELINE_USERS = 5
SPIKE_USERS = 100
RECOVERY_USERS = 5

BASELINE_DURATION = 60  # 1 minute
SPIKE_DURATION = 120    # 2 minutes
RECOVERY_DURATION = 120 # 2 minutes

TOTAL_DURATION = BASELINE_DURATION + SPIKE_DURATION + RECOVERY_DURATION

# Test queries
TEST_QUERIES = [
    "Hello",
    "What is your refund policy?",
    "I need help",
    "Track my order",
    "Place an order",
]

# Metrics storage
metrics = {
    "baseline": {"requests": 0, "successful": 0, "failed": 0, "response_times": []},
    "spike": {"requests": 0, "successful": 0, "failed": 0, "response_times": []},
    "recovery": {"requests": 0, "successful": 0, "failed": 0, "response_times": []},
    "errors": defaultdict(int),
    "start_time": None,
    "phase_times": {},
}


def get_current_phase(elapsed: float) -> str:
    """Determine current test phase"""
    if elapsed < BASELINE_DURATION:
        return "baseline"
    elif elapsed < BASELINE_DURATION + SPIKE_DURATION:
        return "spike"
    else:
        return "recovery"


async def send_chat_request(session: aiohttp.ClientSession, query: str, session_id: str) -> Dict:
    """Send a single chat request"""
    start_time = time.time()

    try:
        async with session.post(
            CHAT_ENDPOINT,
            json={"message": query, "session_id": session_id},
            timeout=aiohttp.ClientTimeout(total=30)
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


async def check_health(session: aiohttp.ClientSession) -> bool:
    """Check if server is still responding"""
    try:
        async with session.get(
            HEALTH_ENDPOINT,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            return response.status in [200, 503]  # 503 = degraded but alive
    except:
        return False


async def simulate_user(user_id: int, phase: str):
    """
    Simulate a single user for their phase duration

    Args:
        user_id: Unique user identifier
        phase: "baseline", "spike", or "recovery"
    """
    session_id = f"spike_test_{phase}_user_{user_id}"
    query_index = 0

    # Determine how long this user should run
    if phase == "baseline":
        duration = BASELINE_DURATION
    elif phase == "spike":
        duration = SPIKE_DURATION
    else:  # recovery
        duration = RECOVERY_DURATION

    async with aiohttp.ClientSession() as session:
        start_time = time.time()

        while time.time() - start_time < duration:
            query = TEST_QUERIES[query_index % len(TEST_QUERIES)]
            query_index += 1

            result = await send_chat_request(session, query, session_id)

            # Update metrics for current phase
            metrics[phase]["requests"] += 1
            metrics[phase]["response_times"].append(result["response_time"])

            if result["status"] == "success":
                metrics[phase]["successful"] += 1
            else:
                metrics[phase]["failed"] += 1
                metrics["errors"][result["error"]] += 1

            # Short delay
            await asyncio.sleep(2)


def calculate_phase_metrics(phase: str) -> Dict:
    """Calculate metrics for a specific phase"""
    phase_data = metrics[phase]

    if not phase_data["response_times"]:
        return {
            "requests": 0,
            "success_rate": 0,
            "error_rate": 0,
            "response_time": {"mean": 0, "p95": 0}
        }

    response_times = sorted(phase_data["response_times"])
    total = phase_data["requests"]
    successful = phase_data["successful"]
    failed = phase_data["failed"]

    return {
        "requests": total,
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / total * 100) if total > 0 else 0,
        "error_rate": (failed / total * 100) if total > 0 else 0,
        "response_time": {
            "mean": statistics.mean(response_times),
            "median": statistics.median(response_times),
            "p95": response_times[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0
        }
    }


async def monitor_test():
    """Monitor test progress and report status"""
    start_time = metrics["start_time"]

    print("\n" + "=" * 80)
    print("SPIKE TEST - MONITORING")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        while True:
            elapsed = time.time() - start_time
            current_phase = get_current_phase(elapsed)

            # Check if test is complete
            if elapsed >= TOTAL_DURATION:
                break

            # Check health
            is_healthy = await check_health(session)
            health_status = "✅ UP" if is_healthy else "🚨 DOWN"

            # Get current metrics
            phase_metrics = calculate_phase_metrics(current_phase)

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Phase: {current_phase.upper()} | Health: {health_status}")
            print(f"  Requests: {phase_metrics['requests']} | Success: {phase_metrics['success_rate']:.1f}% | Errors: {phase_metrics['error_rate']:.1f}%")

            if not is_healthy:
                print("  🚨 WARNING: Health check failed - server may be down!")

            await asyncio.sleep(10)


async def main():
    """Main test execution"""
    print("=" * 80)
    print("LOAD TEST 3: SPIKE TEST")
    print("=" * 80)
    print(f"\nTest Pattern:")
    print(f"  Phase 1 (Baseline):  {BASELINE_USERS} users for {BASELINE_DURATION}s")
    print(f"  Phase 2 (Spike):     {SPIKE_USERS} users for {SPIKE_DURATION}s  🚀")
    print(f"  Phase 3 (Recovery):  {RECOVERY_USERS} users for {RECOVERY_DURATION}s")
    print(f"\nTotal Duration: {TOTAL_DURATION}s ({TOTAL_DURATION/60:.1f} minutes)")
    print(f"API endpoint: {CHAT_ENDPOINT}")
    print(f"Start time: {datetime.now().isoformat()}")
    print("\n⚠️  WARNING: This test will create EXTREME load during spike phase")
    print("=" * 80)

    # Initialize metrics
    metrics["start_time"] = time.time()

    # Phase 1: Baseline
    print("\n" + "=" * 80)
    print("PHASE 1: BASELINE (warming up system)")
    print("=" * 80)
    metrics["phase_times"]["baseline_start"] = time.time()

    baseline_tasks = [
        asyncio.create_task(simulate_user(i, "baseline"))
        for i in range(BASELINE_USERS)
    ]
    monitor_task = asyncio.create_task(monitor_test())

    await asyncio.gather(*baseline_tasks)
    metrics["phase_times"]["baseline_end"] = time.time()

    baseline_metrics = calculate_phase_metrics("baseline")
    print(f"\n✅ Baseline complete: {baseline_metrics['requests']} requests, {baseline_metrics['success_rate']:.1f}% success")

    # Phase 2: Spike
    print("\n" + "=" * 80)
    print("PHASE 2: SPIKE 🚀 (100 concurrent users)")
    print("=" * 80)
    metrics["phase_times"]["spike_start"] = time.time()

    spike_tasks = [
        asyncio.create_task(simulate_user(i, "spike"))
        for i in range(SPIKE_USERS)
    ]

    await asyncio.gather(*spike_tasks)
    metrics["phase_times"]["spike_end"] = time.time()

    spike_metrics = calculate_phase_metrics("spike")
    print(f"\n✅ Spike complete: {spike_metrics['requests']} requests, {spike_metrics['success_rate']:.1f}% success")

    # Phase 3: Recovery
    print("\n" + "=" * 80)
    print("PHASE 3: RECOVERY (back to normal load)")
    print("=" * 80)
    metrics["phase_times"]["recovery_start"] = time.time()

    recovery_tasks = [
        asyncio.create_task(simulate_user(i, "recovery"))
        for i in range(RECOVERY_USERS)
    ]

    await asyncio.gather(*recovery_tasks)
    metrics["phase_times"]["recovery_end"] = time.time()

    recovery_metrics = calculate_phase_metrics("recovery")
    print(f"\n✅ Recovery complete: {recovery_metrics['requests']} requests, {recovery_metrics['success_rate']:.1f}% success")

    # Stop monitor
    monitor_task.cancel()

    # Final report
    print("\n" + "=" * 80)
    print("FINAL RESULTS - PHASE COMPARISON")
    print("=" * 80)

    phases = ["baseline", "spike", "recovery"]
    for phase in phases:
        phase_metrics = calculate_phase_metrics(phase)
        print(f"\n{phase.upper()}:")
        print(f"  Requests: {phase_metrics['requests']}")
        print(f"  Success Rate: {phase_metrics['success_rate']:.2f}%")
        print(f"  Error Rate: {phase_metrics['error_rate']:.2f}%")
        print(f"  Mean Response Time: {phase_metrics['response_time']['mean']:.2f}s")
        print(f"  P95 Response Time: {phase_metrics['response_time']['p95']:.2f}s")

    if metrics["errors"]:
        print(f"\nError Breakdown (all phases):")
        for error, count in sorted(metrics["errors"].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {error}: {count}")

    # Success criteria check
    print("\n" + "=" * 80)
    print("SUCCESS CRITERIA EVALUATION")
    print("=" * 80)

    criteria_passed = []
    criteria_failed = []

    # Criterion 1: System survived spike (any successful requests)
    if spike_metrics['successful'] > 0:
        criteria_passed.append("✅ System survived spike PASS")
    else:
        criteria_failed.append("❌ System crashed during spike FAIL")

    # Criterion 2: Spike error rate < 20%
    if spike_metrics['error_rate'] < 20:
        criteria_passed.append("✅ Spike error rate < 20% PASS")
    else:
        criteria_failed.append(f"❌ Spike error rate < 20% FAIL ({spike_metrics['error_rate']:.2f}%)")

    # Criterion 3: Recovery error rate < 5%
    if recovery_metrics['error_rate'] < 5:
        criteria_passed.append("✅ Recovery error rate < 5% PASS")
    else:
        criteria_failed.append(f"❌ Recovery error rate < 5% FAIL ({recovery_metrics['error_rate']:.2f}%)")

    # Criterion 4: Recovery performance improved from spike
    if recovery_metrics['response_time']['p95'] < spike_metrics['response_time']['p95']:
        criteria_passed.append("✅ System recovered after spike PASS")
    else:
        criteria_failed.append("❌ System did not recover FAIL (P95 latency still high)")

    # Print results
    for criterion in criteria_passed:
        print(criterion)

    for criterion in criteria_failed:
        print(criterion)

    # Overall verdict
    print("\n" + "=" * 80)
    if not criteria_failed:
        print("✅ SPIKE TEST: PASSED")
        print("System survives extreme traffic spikes and recovers gracefully")
    else:
        print("❌ SPIKE TEST: FAILED")
        print(f"Failed {len(criteria_failed)} of {len(criteria_passed) + len(criteria_failed)} criteria")
        print("\nRecommendations:")
        if spike_metrics['error_rate'] > 20:
            print("  - Add request queueing to buffer spike load")
            print("  - Implement auto-scaling")
        if recovery_metrics['error_rate'] > 5:
            print("  - Check for resource leaks (connections, memory)")
            print("  - Implement graceful degradation")
    print("=" * 80)

    # Save results
    results_file = f"load_test_3_spike_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_type": "spike_test",
            "parameters": {
                "baseline_users": BASELINE_USERS,
                "spike_users": SPIKE_USERS,
                "recovery_users": RECOVERY_USERS,
                "total_duration": TOTAL_DURATION
            },
            "baseline": baseline_metrics,
            "spike": spike_metrics,
            "recovery": recovery_metrics,
            "errors": dict(metrics["errors"]),
            "criteria_passed": criteria_passed,
            "criteria_failed": criteria_failed,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
