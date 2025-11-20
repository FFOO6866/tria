"""
Quick Performance Test
======================

Fast validation of optimization improvements.
Tests single request latency before running full load tests.
"""

import sys
from pathlib import Path
import time
import os

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent


def test_single_request_performance():
    """Test single request to measure latency improvement"""
    print("=" * 80)
    print("Quick Performance Test - Single Request")
    print("=" * 80)
    print()

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set")
        return 1

    # Create agent with optimizations enabled
    print("Creating agent...")
    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=True,
        enable_rate_limiting=True,
        enable_rag=True
    )
    print("[OK] Agent created")
    print()

    # Test messages
    test_cases = [
        {
            "message": "What is your return policy?",
            "intent": "policy_question",
            "description": "Policy question (RAG)"
        },
        {
            "message": "Do you have pizza boxes?",
            "intent": "product_inquiry",
            "description": "Product inquiry (RAG)"
        },
        {
            "message": "I need 500 meal trays",
            "intent": "order_placement",
            "description": "Order placement"
        }
    ]

    print("Running tests...")
    print()

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}/3: {test['description']}")
        print(f"  Message: {test['message']}")

        start_time = time.time()

        try:
            response = agent.handle_message(
                message=test['message'],
                user_id=f"test_user_{i}"
            )

            duration_ms = (time.time() - start_time) * 1000

            print(f"  Duration: {duration_ms:.0f}ms")
            print(f"  Intent: {response.intent}")
            print(f"  Action: {response.action_taken}")

            results.append({
                "test": test['description'],
                "duration_ms": duration_ms,
                "success": True,
                "intent": response.intent
            })

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            print(f"  [ERROR] {str(e)}")
            results.append({
                "test": test['description'],
                "duration_ms": duration_ms,
                "success": False,
                "error": str(e)
            })

        print()

    # Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"Total Tests:    {len(results)}")
    print(f"Successful:     {len(successful)} ({len(successful)/len(results)*100:.0f}%)")
    print(f"Failed:         {len(failed)}")
    print()

    if successful:
        durations = [r['duration_ms'] for r in successful]
        print("Performance:")
        print(f"  Mean:   {sum(durations)/len(durations):.0f}ms")
        print(f"  Min:    {min(durations):.0f}ms")
        print(f"  Max:    {max(durations):.0f}ms")
        print()

    # Expected improvements
    print("Expected Improvements vs Baseline:")
    print("  Intent Classification: 2-5x faster (GPT-3.5-Turbo)")
    print("  RAG Context: 40% fewer tokens (3 chunks vs 5)")
    print("  ChromaDB: 100% reliable (fixed race condition)")
    print("  Overall Target: <8s for policy questions")
    print()

    # Verdict
    if successful and len(successful) == len(results):
        avg_duration = sum(r['duration_ms'] for r in successful) / len(successful)
        if avg_duration < 8000:
            print(f"[OK] Average duration {avg_duration:.0f}ms < 8000ms target!")
        elif avg_duration < 15000:
            print(f"[PARTIAL] Average duration {avg_duration:.0f}ms - needs more optimization")
        else:
            print(f"[SLOW] Average duration {avg_duration:.0f}ms - still too slow")
    else:
        print("[ERROR] Some tests failed")

    print()
    print("=" * 80)

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    exit(test_single_request_performance())
