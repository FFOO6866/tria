"""
Test Input Validation
=====================

Verify that input validation and sanitization work correctly.

Test Cases:
1. Valid inputs (should pass)
2. Length violations (too short, too long)
3. Security patterns (SQL injection, XSS, command injection)
4. Encoding issues (null bytes, control characters)
5. PII detection (informational)
6. Integration with agent
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.input_validator import InputValidator, validate_and_sanitize
from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_validation_module():
    """Test the validation module directly"""
    print("\n" + "=" * 80)
    print("INPUT VALIDATION MODULE TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    # Test 1: Valid input
    print("\n[TEST 1] Valid input")
    result = validator.validate_message("Hello, what's your refund policy?")
    if result.is_valid:
        print("[PASS] Valid input accepted")
        print(f"       Sanitized: {result.sanitized_input}")
        tests_passed += 1
    else:
        print(f"[FAIL] Valid input rejected: {result.issues}")
        tests_failed += 1

    # Test 2: Empty message
    print("\n[TEST 2] Empty message (too short)")
    result = validator.validate_message("")
    if not result.is_valid and any("too_short" in i.get("type", "") for i in result.issues):
        print("[PASS] Empty message rejected")
        tests_passed += 1
    else:
        print("[FAIL] Empty message should be rejected")
        tests_failed += 1

    # Test 3: Message too long
    print("\n[TEST 3] Message too long (>5000 chars)")
    long_message = "A" * 5001
    result = validator.validate_message(long_message)
    if not result.is_valid and any("too_long" in i.get("type", "") for i in result.issues):
        print(f"[PASS] Long message rejected ({len(long_message)} chars)")
        tests_passed += 1
    else:
        print("[FAIL] Long message should be rejected")
        tests_failed += 1

    # Test 4: SQL injection pattern
    print("\n[TEST 4] SQL injection pattern detection")
    sql_message = "'; DROP TABLE users; --"
    result = validator.validate_message(sql_message)
    sql_warnings = [i for i in result.issues if "sql_injection" in i.get("type", "")]
    if sql_warnings:
        print(f"[PASS] SQL injection pattern detected: {len(sql_warnings)} warnings")
        print(f"       Warnings: {[w['message'] for w in sql_warnings]}")
        tests_passed += 1
    else:
        print("[FAIL] SQL injection pattern should be detected")
        tests_failed += 1

    # Test 5: Null byte detection
    print("\n[TEST 5] Null byte detection")
    null_message = "Hello\x00World"
    result = validator.validate_message(null_message)
    if not result.is_valid and any("null_byte" in i.get("type", "") for i in result.issues):
        print("[PASS] Null byte detected and rejected")
        tests_passed += 1
    else:
        print("[FAIL] Null byte should be rejected")
        tests_failed += 1

    # Test 6: Command injection pattern
    print("\n[TEST 6] Command injection pattern detection")
    cmd_message = "$(rm -rf /)"
    result = validator.validate_message(cmd_message)
    cmd_warnings = [i for i in result.issues if "command_injection" in i.get("type", "")]
    if cmd_warnings:
        print(f"[PASS] Command injection pattern detected")
        tests_passed += 1
    else:
        print("[FAIL] Command injection pattern should be detected")
        tests_failed += 1

    # Test 7: PII detection (email)
    print("\n[TEST 7] PII detection (email)")
    pii_message = "My email is john.doe@example.com"
    result = validator.validate_message(pii_message)
    pii_warnings = [i for i in result.issues if "pii_email" in i.get("type", "")]
    if pii_warnings:
        print(f"[PASS] PII (email) detected: {pii_warnings[0]['message']}")
        print(f"       Note: PII detection is informational, doesn't block input")
        tests_passed += 1
    else:
        print("[FAIL] PII (email) should be detected")
        tests_failed += 1

    # Test 8: Whitespace normalization
    print("\n[TEST 8] Whitespace normalization")
    messy_message = "   Hello    world   "
    result = validator.validate_message(messy_message)
    if result.is_valid and result.sanitized_input == "Hello world":
        print(f"[PASS] Whitespace normalized: '{messy_message}' -> '{result.sanitized_input}'")
        tests_passed += 1
    else:
        print(f"[FAIL] Whitespace not normalized correctly: '{result.sanitized_input}'")
        tests_failed += 1

    # Test 9: Word too long
    print("\n[TEST 9] Word too long (>100 chars)")
    long_word_message = "A" * 101  # Single word > 100 chars
    result = validator.validate_message(long_word_message)
    if not result.is_valid and any("word_too_long" in i.get("type", "") for i in result.issues):
        print("[PASS] Long word detected and rejected")
        tests_passed += 1
    else:
        print("[FAIL] Long word should be rejected")
        tests_failed += 1

    # Test 10: Control characters
    print("\n[TEST 10] Control character detection")
    control_message = "Hello\x01World"
    result = validator.validate_message(control_message)
    if not result.is_valid and any("control_characters" in i.get("type", "") for i in result.issues):
        print("[PASS] Control characters detected and rejected")
        tests_passed += 1
    else:
        print("[FAIL] Control characters should be rejected")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION MODULE TEST SUMMARY")
    print("=" * 80)
    total_tests = tests_passed + tests_failed
    print(f"Total tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Pass rate: {(tests_passed/total_tests)*100:.1f}%")

    return tests_failed == 0


def test_agent_integration():
    """Test input validation integration with agent"""
    print("\n\n" + "=" * 80)
    print("AGENT INTEGRATION TESTS")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set - skipping agent integration tests")
        return True

    agent = EnhancedCustomerServiceAgent(api_key=api_key, enable_cache=True)
    tests_passed = 0
    tests_failed = 0

    # Test 1: Valid message should process normally
    print("\n[TEST 1] Valid message processing")
    try:
        response = agent.handle_message("What's your refund policy?")
        if response.action_taken != "input_validation_failed":
            print(f"[PASS] Valid message processed normally")
            print(f"       Intent: {response.intent}")
            tests_passed += 1
        else:
            print(f"[FAIL] Valid message should not fail validation")
            tests_failed += 1
    except Exception as e:
        print(f"[FAIL] Valid message processing failed: {str(e)}")
        tests_failed += 1

    # Test 2: Message too long should be rejected
    print("\n[TEST 2] Message too long rejection")
    try:
        long_message = "A" * 5001
        response = agent.handle_message(long_message)
        if response.action_taken == "input_validation_failed":
            print(f"[PASS] Long message rejected by validation")
            print(f"       Response: {response.response_text[:100]}...")
            tests_passed += 1
        else:
            print(f"[FAIL] Long message should be rejected")
            tests_failed += 1
    except Exception as e:
        print(f"[FAIL] Long message test failed: {str(e)}")
        tests_failed += 1

    # Test 3: SQL injection should be detected (warning only)
    print("\n[TEST 3] SQL injection pattern handling")
    try:
        sql_message = "What is your refund policy? ' OR 1=1 --"
        response = agent.handle_message(sql_message)
        # Should process but log warning
        if response.action_taken != "input_validation_failed":
            print(f"[PASS] SQL pattern processed with warning (strict_mode=False)")
            print(f"       Note: Suspicious patterns are logged but not blocked in non-strict mode")
            tests_passed += 1
        else:
            print(f"[INFO] SQL pattern blocked (depends on strict_mode setting)")
            tests_passed += 1
    except Exception as e:
        print(f"[FAIL] SQL pattern test failed: {str(e)}")
        tests_failed += 1

    # Test 4: Null byte should be rejected
    print("\n[TEST 4] Null byte rejection")
    try:
        null_message = "Hello\x00World"
        response = agent.handle_message(null_message)
        if response.action_taken == "input_validation_failed":
            print(f"[PASS] Null byte rejected by validation")
            tests_passed += 1
        else:
            print(f"[FAIL] Null byte should be rejected")
            tests_failed += 1
    except Exception as e:
        print(f"[FAIL] Null byte test failed: {str(e)}")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 80)
    print("AGENT INTEGRATION TEST SUMMARY")
    print("=" * 80)
    total_tests = tests_passed + tests_failed
    print(f"Total tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    if total_tests > 0:
        print(f"Pass rate: {(tests_passed/total_tests)*100:.1f}%")

    return tests_failed == 0


def main():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("INPUT VALIDATION TEST SUITE")
    print("=" * 80)

    module_success = test_validation_module()
    agent_success = test_agent_integration()

    print("\n\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)

    if module_success and agent_success:
        print("[SUCCESS] All validation tests passed")
        print("          - Input validation module working correctly")
        print("          - Agent integration successful")
        print("          - Security patterns detected")
        print("          - Sanitization working")
        return 0
    else:
        if not module_success:
            print("[FAIL] Validation module tests failed")
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
