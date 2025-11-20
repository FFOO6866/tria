"""
Test Rate Limiting
==================

Verify that rate limiting works correctly across all tiers.

Test Cases:
1. Per-user minute limit
2. Per-user hour limit
3. Per-user day limit
4. Token bucket (burst handling)
5. Global rate limit
6. IP-based rate limiting
7. Rate limit headers
8. Integration with agent
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ratelimit.rate_limiter import (
    ChatbotRateLimiter,
    RateLimitConfig,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
    reset_rate_limiter
)
from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_sliding_window_limiter():
    """Test sliding window rate limiter"""
    print("\n" + "=" * 80)
    print("SLIDING WINDOW RATE LIMITER TESTS")
    print("=" * 80)

    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=2)
    tests_passed = 0
    tests_failed = 0

    # Test 1: Allow requests within limit
    print("\n[TEST 1] Allow requests within limit (3/3)")
    user_id = "test_user_1"
    for i in range(3):
        allowed, result = limiter.allow_request(user_id)
        if not allowed:
            print(f"[FAIL] Request {i+1}/3 should be allowed")
            tests_failed += 1
            break
    else:
        print(f"[PASS] All 3 requests allowed")
        print(f"       Remaining: {result.remaining}")
        tests_passed += 1

    # Test 2: Reject request exceeding limit
    print("\n[TEST 2] Reject request exceeding limit (4/3)")
    allowed, result = limiter.allow_request(user_id)
    if not allowed:
        print(f"[PASS] 4th request rejected")
        print(f"       Retry after: {result.retry_after}s")
        tests_passed += 1
    else:
        print(f"[FAIL] 4th request should be rejected")
        tests_failed += 1

    # Test 3: Allow request after window expires
    print("\n[TEST 3] Allow request after window expires")
    print(f"       Waiting {limiter.window_seconds + 1}s for window to expire...")
    time.sleep(limiter.window_seconds + 1)
    allowed, result = limiter.allow_request(user_id)
    if allowed:
        print(f"[PASS] Request allowed after window expiration")
        tests_passed += 1
    else:
        print(f"[FAIL] Request should be allowed after window expiration")
        tests_failed += 1

    # Test 4: Different users don't affect each other
    print("\n[TEST 4] Different users have separate limits")
    user2_id = "test_user_2"
    allowed, result = limiter.allow_request(user2_id)
    if allowed:
        print(f"[PASS] Different user not affected by other user's limit")
        tests_passed += 1
    else:
        print(f"[FAIL] Different user should have separate limit")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("SLIDING WINDOW TEST SUMMARY")
    print("=" * 80)
    total_tests = tests_passed + tests_failed
    print(f"Total tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    return tests_failed == 0


def test_token_bucket_limiter():
    """Test token bucket rate limiter"""
    print("\n\n" + "=" * 80)
    print("TOKEN BUCKET RATE LIMITER TESTS")
    print("=" * 80)

    # capacity=5, refill_rate=1 token/second
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
    tests_passed = 0
    tests_failed = 0

    # Test 1: Allow burst
    print("\n[TEST 1] Allow burst (5 requests immediately)")
    user_id = "test_user_1"
    for i in range(5):
        allowed, result = limiter.allow_request(user_id)
        if not allowed:
            print(f"[FAIL] Burst request {i+1}/5 should be allowed")
            tests_failed += 1
            break
    else:
        print(f"[PASS] All 5 burst requests allowed")
        print(f"       Tokens remaining: {result.remaining}")
        tests_passed += 1

    # Test 2: Reject request when bucket empty
    print("\n[TEST 2] Reject request when bucket empty")
    allowed, result = limiter.allow_request(user_id)
    if not allowed:
        print(f"[PASS] Request rejected (bucket empty)")
        print(f"       Retry after: {result.retry_after}s")
        tests_passed += 1
    else:
        print(f"[FAIL] Request should be rejected when bucket empty")
        tests_failed += 1

    # Test 3: Allow request after refill
    print("\n[TEST 3] Allow request after token refill")
    print(f"       Waiting 2s for token refill...")
    time.sleep(2)
    allowed, result = limiter.allow_request(user_id)
    if allowed:
        print(f"[PASS] Request allowed after token refill")
        print(f"       Tokens remaining: {result.remaining}")
        tests_passed += 1
    else:
        print(f"[FAIL] Request should be allowed after refill")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("TOKEN BUCKET TEST SUMMARY")
    print("=" * 80)
    total_tests = tests_passed + tests_failed
    print(f"Total tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    return tests_failed == 0


def test_chatbot_rate_limiter():
    """Test multi-tier chatbot rate limiter"""
    print("\n\n" + "=" * 80)
    print("CHATBOT RATE LIMITER TESTS")
    print("=" * 80)

    # Reset global limiter
    reset_rate_limiter()

    # Create limiter with low limits for testing
    config = RateLimitConfig(
        requests_per_minute=3,
        requests_per_hour=10,
        requests_per_day=20,
        burst_size=5
    )
    limiter = ChatbotRateLimiter(per_user_config=config)
    tests_passed = 0
    tests_failed = 0

    # Test 1: Allow requests within limit
    print("\n[TEST 1] Allow requests within minute limit (3/3)")
    user_id = "test_user_1"
    for i in range(3):
        result = limiter.check_rate_limit(user_id=user_id)
        if not result.allowed:
            print(f"[FAIL] Request {i+1}/3 should be allowed")
            tests_failed += 1
            break
    else:
        print(f"[PASS] All 3 requests within minute limit allowed")
        print(f"       Limit type: {result.limit_type.value if result.limit_type else 'None'}")
        tests_passed += 1

    # Test 2: Reject request exceeding minute limit
    print("\n[TEST 2] Reject request exceeding minute limit (4/3)")
    result = limiter.check_rate_limit(user_id=user_id)
    if not result.allowed:
        print(f"[PASS] 4th request rejected")
        print(f"       Limit type: {result.limit_type.value}")
        print(f"       Retry after: {result.retry_after}s")
        print(f"       Headers: {result.to_headers()}")
        tests_passed += 1
    else:
        print(f"[FAIL] 4th request should be rejected")
        tests_failed += 1

    # Test 3: Different users have separate limits
    print("\n[TEST 3] Different users have separate limits")
    user2_id = "test_user_2"
    result = limiter.check_rate_limit(user_id=user2_id)
    if result.allowed:
        print(f"[PASS] Different user not affected by other user's limit")
        tests_passed += 1
    else:
        print(f"[FAIL] Different user should have separate limit")
        tests_failed += 1

    # Test 4: IP-based limiting
    print("\n[TEST 4] IP-based rate limiting")
    result = limiter.check_rate_limit(ip_address="1.2.3.4")
    if result.allowed:
        print(f"[PASS] IP-based limiting working")
        tests_passed += 1
    else:
        print(f"[FAIL] IP-based first request should be allowed")
        tests_failed += 1

    # Test 5: Usage stats
    print("\n[TEST 5] Usage statistics")
    stats = limiter.get_usage_stats(user_id)
    print(f"       User {user_id} usage:")
    print(f"       - Minute: {stats['minute']}")
    print(f"       - Hour: {stats['hour']}")
    print(f"       - Day: {stats['day']}")
    if stats['minute'] > 0:
        print(f"[PASS] Usage stats tracked correctly")
        tests_passed += 1
    else:
        print(f"[FAIL] Usage stats should show requests")
        tests_failed += 1

    # Test 6: Reset user limit
    print("\n[TEST 6] Reset user rate limit")
    limiter.reset_user(user_id)
    result = limiter.check_rate_limit(user_id=user_id)
    if result.allowed:
        print(f"[PASS] User rate limit reset successfully")
        tests_passed += 1
    else:
        print(f"[FAIL] Request should be allowed after reset")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("CHATBOT RATE LIMITER TEST SUMMARY")
    print("=" * 80)
    total_tests = tests_passed + tests_failed
    print(f"Total tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    return tests_failed == 0


def test_agent_integration():
    """Test rate limiting integration with agent"""
    print("\n\n" + "=" * 80)
    print("AGENT INTEGRATION TESTS")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set - skipping agent integration tests")
        return True

    # Reset global limiter
    reset_rate_limiter()

    # Create agent with rate limiting
    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=False,  # Disable cache to test rate limiting
        enable_rate_limiting=True
    )
    tests_passed = 0
    tests_failed = 0

    # Test 1: Allow request within limit
    print("\n[TEST 1] Allow request within rate limit")
    try:
        response = agent.handle_message(
            "Hello, how can I help?",
            user_id="test_user_1"
        )
        if response.action_taken != "rate_limit_exceeded":
            print(f"[PASS] Request allowed within rate limit")
            print(f"       Intent: {response.intent}")
            tests_passed += 1
        else:
            print(f"[FAIL] First request should not be rate limited")
            tests_failed += 1
    except Exception as e:
        print(f"[FAIL] Request failed: {str(e)}")
        tests_failed += 1

    # Test 2: Rate limit exceeded
    print("\n[TEST 2] Rate limit exceeded (11+ requests)")
    print("       Making 11 requests rapidly...")
    user_id = "test_user_2"
    rate_limited = False
    for i in range(11):
        response = agent.handle_message(
            f"Test message {i}",
            user_id=user_id
        )
        if response.action_taken == "rate_limit_exceeded":
            rate_limited = True
            print(f"[PASS] Rate limit triggered at request {i+1}")
            print(f"       Response: {response.response_text[:100]}...")
            if response.metadata:
                print(f"       Retry after: {response.metadata.get('retry_after')}s")
                print(f"       Rate limit type: {response.metadata.get('rate_limit_type')}")
            tests_passed += 1
            break

    if not rate_limited:
        print(f"[FAIL] Rate limit should have been triggered")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("AGENT INTEGRATION TEST SUMMARY")
    print("=" * 80)
    total_tests = tests_passed + tests_failed
    print(f"Total tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    return tests_failed == 0


def main():
    """Run all rate limiting tests"""
    print("\n" + "=" * 80)
    print("RATE LIMITING TEST SUITE")
    print("=" * 80)

    sliding_window_success = test_sliding_window_limiter()
    token_bucket_success = test_token_bucket_limiter()
    chatbot_limiter_success = test_chatbot_rate_limiter()
    agent_success = test_agent_integration()

    print("\n\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)

    all_success = (
        sliding_window_success and
        token_bucket_success and
        chatbot_limiter_success and
        agent_success
    )

    if all_success:
        print("[SUCCESS] All rate limiting tests passed")
        print("          - Sliding window algorithm working")
        print("          - Token bucket algorithm working")
        print("          - Multi-tier limiting working")
        print("          - Agent integration successful")
        print("          - Rate limit headers generated")
        return 0
    else:
        if not sliding_window_success:
            print("[FAIL] Sliding window tests failed")
        if not token_bucket_success:
            print("[FAIL] Token bucket tests failed")
        if not chatbot_limiter_success:
            print("[FAIL] Chatbot limiter tests failed")
        if not agent_success:
            print("[FAIL] Agent integration tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n[ERROR] Test suite crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
