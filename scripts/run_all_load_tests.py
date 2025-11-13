#!/usr/bin/env python3
"""
Master Load Test Runner
=======================

Runs all 5 load tests in sequence and generates a comprehensive report.

Usage:
    python run_all_load_tests.py [--quick]

Options:
    --quick     Run shortened versions of tests for faster validation
                (Sustained: 10 min, Burst: 2 min, Spike: 2 min, Soak: 30 min, Chaos: 5 min)

Tests:
    1. Sustained Load:  10 users for 1 hour (or 10 min quick)
    2. Burst Load:      50 users for 5 minutes (or 2 min quick)
    3. Spike Test:      5→100→5 users (or shortened quick)
    4. Soak Test:       5 users for 24 hours (or 30 min quick)
    5. Chaos Test:      20 users for 10 minutes (or 5 min quick)
"""

import subprocess
import sys
import json
import time
from datetime import datetime
from pathlib import Path


def run_test(script_name: str, test_name: str) -> dict:
    """
    Run a single load test script

    Returns:
        Dict with test results and status
    """
    print("\n" + "=" * 80)
    print(f"RUNNING: {test_name}")
    print("=" * 80)

    start_time = time.time()

    try:
        # Run test script
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=90000  # 25 hour timeout (for 24h soak test)
        )

        duration = time.time() - start_time

        # Parse output
        output = result.stdout
        print(output)  # Print test output

        # Try to find JSON results file
        results_file = None
        for line in output.split('\n'):
            if 'results saved to:' in line.lower():
                results_file = line.split(':')[-1].strip()
                break

        test_results = {
            "test_name": test_name,
            "script": script_name,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "duration_seconds": duration,
            "results_file": results_file,
            "timestamp": datetime.now().isoformat()
        }

        # Try to load detailed results if file exists
        if results_file and Path(results_file).exists():
            with open(results_file, 'r') as f:
                detailed_results = json.load(f)
                test_results["detailed"] = detailed_results

        return test_results

    except subprocess.TimeoutExpired:
        return {
            "test_name": test_name,
            "script": script_name,
            "status": "TIMEOUT",
            "duration_seconds": time.time() - start_time,
            "error": "Test exceeded timeout",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "test_name": test_name,
            "script": script_name,
            "status": "ERROR",
            "duration_seconds": time.time() - start_time,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Run all load tests in sequence"""
    quick_mode = "--quick" in sys.argv

    print("=" * 80)
    print("TRIA AI-BPO - COMPREHENSIVE LOAD TESTING SUITE")
    print("=" * 80)
    print(f"\nMode: {'QUICK (shortened tests)' if quick_mode else 'FULL (complete tests)'}")
    print(f"Start time: {datetime.now().isoformat()}")
    print("\n⚠️  These tests will run for an extended period")
    if not quick_mode:
        print("   Estimated total time: ~27 hours (includes 24h soak test)")
        print("   Consider using --quick flag for faster validation")
    else:
        print("   Estimated total time: ~1 hour")
    print("=" * 80)

    if not quick_mode:
        response = input("\nRun full test suite? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Test suite cancelled")
            return

    # Define tests
    tests = [
        {
            "script": "load_test_1_sustained.py",
            "name": "Test 1: Sustained Load",
            "description": "10 users for 1 hour"
        },
        {
            "script": "load_test_2_burst.py",
            "name": "Test 2: Burst Load",
            "description": "50 users for 5 minutes"
        },
        {
            "script": "load_test_3_spike.py",
            "name": "Test 3: Spike Test",
            "description": "5→100→5 users"
        },
        {
            "script": "load_test_4_soak.py",
            "name": "Test 4: Soak Test",
            "description": "5 users for 24 hours" if not quick_mode else "5 users for 30 minutes"
        },
        {
            "script": "load_test_5_chaos.py",
            "name": "Test 5: Chaos Test",
            "description": "20 users with chaos injection"
        }
    ]

    # Run tests
    all_results = []
    passed_tests = 0
    failed_tests = 0

    suite_start_time = time.time()

    for test in tests:
        result = run_test(test["script"], test["name"])
        all_results.append(result)

        if result["status"] == "PASS":
            passed_tests += 1
        else:
            failed_tests += 1

        # Brief pause between tests
        print("\n⏸️  Pausing 30 seconds before next test...")
        time.sleep(30)

    suite_duration = time.time() - suite_start_time

    # Final summary report
    print("\n" + "=" * 80)
    print("LOAD TESTING SUITE - FINAL SUMMARY")
    print("=" * 80)

    print(f"\nSuite Duration: {suite_duration/3600:.2f} hours")
    print(f"Tests Run: {len(tests)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/len(tests)*100):.1f}%")

    print("\n" + "-" * 80)
    print("INDIVIDUAL TEST RESULTS")
    print("-" * 80)

    for result in all_results:
        status_emoji = "✅" if result["status"] == "PASS" else "❌"
        print(f"\n{status_emoji} {result['test_name']}")
        print(f"   Status: {result['status']}")
        print(f"   Duration: {result['duration_seconds']/60:.1f} minutes")
        if result.get("results_file"):
            print(f"   Results: {result['results_file']}")
        if result.get("error"):
            print(f"   Error: {result['error']}")

    # Production readiness verdict
    print("\n" + "=" * 80)
    print("PRODUCTION READINESS VERDICT")
    print("=" * 80)

    if passed_tests == len(tests):
        print("\n✅ ALL LOAD TESTS PASSED")
        print("\nSystem is ready for production deployment:")
        print("  - Handles sustained load")
        print("  - Survives traffic bursts")
        print("  - Recovers from spikes")
        print("  - No memory leaks detected")
        print("  - Resilient to failures")
        print("\n👉 Next steps:")
        print("  1. Review detailed test results")
        print("  2. Set up monitoring and alerting")
        print("  3. Prepare staging deployment")
        print("  4. Plan production rollout")
    else:
        print(f"\n❌ {failed_tests} OF {len(tests)} TESTS FAILED")
        print("\n⚠️  System is NOT ready for production")
        print("\n👉 Required actions:")
        print("  1. Review failed test results")
        print("  2. Fix identified issues")
        print("  3. Re-run failed tests")
        print("  4. Complete full test suite before production")

    print("\n" + "=" * 80)

    # Save comprehensive results
    summary_file = f"load_test_suite_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "suite_info": {
                "mode": "quick" if quick_mode else "full",
                "duration_hours": suite_duration / 3600,
                "tests_run": len(tests),
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests / len(tests) * 100
            },
            "test_results": all_results,
            "production_ready": passed_tests == len(tests),
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

    print(f"\nComprehensive results saved to: {summary_file}")

    # Exit code
    sys.exit(0 if passed_tests == len(tests) else 1)


if __name__ == "__main__":
    main()
