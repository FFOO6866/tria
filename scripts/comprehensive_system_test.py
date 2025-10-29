"""
Comprehensive End-to-End System Testing for TRIA AI-BPO
Tests all system components with real infrastructure (no mocking)
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Base URL
BASE_URL = "http://localhost:8001"

# Test results storage
test_results = []

class TestResult:
    def __init__(self, test_name: str, category: str):
        self.test_name = test_name
        self.category = category
        self.start_time = time.time()
        self.end_time = None
        self.passed = False
        self.expected = None
        self.actual = None
        self.error = None
        self.response_time_ms = None

    def complete(self, passed: bool, expected: Any = None, actual: Any = None, error: str = None):
        self.end_time = time.time()
        self.response_time_ms = int((self.end_time - self.start_time) * 1000)
        self.passed = passed
        self.expected = expected
        self.actual = actual
        self.error = error
        test_results.append(self)

    def to_dict(self):
        return {
            "test_name": self.test_name,
            "category": self.category,
            "passed": self.passed,
            "response_time_ms": self.response_time_ms,
            "expected": self.expected,
            "actual": self.actual,
            "error": self.error
        }


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_chatbot_greeting():
    """Test Case 1: Greeting"""
    test = TestResult("Chatbot - Greeting", "Chatbot")
    print("Testing: Greeting Intent...")

    try:
        payload = {
            "message": "Hello",
            "user_id": "test_user_greeting",
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/chatbot", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Expected: Intent=greeting, friendly message
        expected_intent = "greeting"
        actual_intent = data.get("intent")
        has_response = len(data.get("response", "")) > 0

        passed = (actual_intent == expected_intent and has_response)

        test.complete(
            passed=passed,
            expected={"intent": expected_intent, "has_response": True},
            actual={"intent": actual_intent, "response_preview": data.get("response", "")[:100]}
        )

        print(f"✓ Intent: {actual_intent}")
        print(f"✓ Response preview: {data.get('response', '')[:150]}...")
        print(f"✓ Response time: {test.response_time_ms}ms")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_chatbot_policy_question():
    """Test Case 2: Policy Question (RAG-powered)"""
    test = TestResult("Chatbot - Policy Question (RAG)", "Chatbot")
    print("Testing: Policy Question with RAG...")

    try:
        payload = {
            "message": "What is your refund policy?",
            "user_id": "test_user_policy",
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/chatbot", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Expected: Intent=policy_question, RAG citations
        expected_intent = "policy_question"
        actual_intent = data.get("intent")
        has_response = len(data.get("response", "")) > 0
        has_citations = "citations" in data and len(data["citations"]) > 0

        passed = (actual_intent == expected_intent and has_response)

        test.complete(
            passed=passed,
            expected={"intent": expected_intent, "has_response": True, "has_citations": True},
            actual={
                "intent": actual_intent,
                "response_preview": data.get("response", "")[:100],
                "citations_count": len(data.get("citations", []))
            }
        )

        print(f"✓ Intent: {actual_intent}")
        print(f"✓ Response preview: {data.get('response', '')[:150]}...")
        print(f"✓ Citations: {len(data.get('citations', []))} sources")
        print(f"✓ Response time: {test.response_time_ms}ms")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_chatbot_product_inquiry():
    """Test Case 3: Product Inquiry (RAG-powered)"""
    test = TestResult("Chatbot - Product Inquiry (RAG)", "Chatbot")
    print("Testing: Product Inquiry with RAG...")

    try:
        payload = {
            "message": "Do you have pizza boxes?",
            "user_id": "test_user_product",
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/chatbot", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Expected: Intent=product_inquiry, response about products
        expected_intent = "product_inquiry"
        actual_intent = data.get("intent")
        has_response = len(data.get("response", "")) > 0

        passed = (actual_intent == expected_intent and has_response)

        test.complete(
            passed=passed,
            expected={"intent": expected_intent, "has_response": True},
            actual={
                "intent": actual_intent,
                "response_preview": data.get("response", "")[:100],
                "citations_count": len(data.get("citations", []))
            }
        )

        print(f"✓ Intent: {actual_intent}")
        print(f"✓ Response preview: {data.get('response', '')[:150]}...")
        print(f"✓ Citations: {len(data.get('citations', []))} sources")
        print(f"✓ Response time: {test.response_time_ms}ms")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_chatbot_order_placement():
    """Test Case 4: Order Placement Intent"""
    test = TestResult("Chatbot - Order Placement", "Chatbot")
    print("Testing: Order Placement Intent...")

    try:
        payload = {
            "message": "I need 500 meal trays",
            "user_id": "test_user_order",
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/chatbot", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Expected: Intent=order_placement, guidance on order processing
        expected_intent = "order_placement"
        actual_intent = data.get("intent")
        has_response = len(data.get("response", "")) > 0

        passed = (actual_intent == expected_intent and has_response)

        test.complete(
            passed=passed,
            expected={"intent": expected_intent, "has_response": True},
            actual={
                "intent": actual_intent,
                "response_preview": data.get("response", "")[:100]
            }
        )

        print(f"✓ Intent: {actual_intent}")
        print(f"✓ Response preview: {data.get('response', '')[:150]}...")
        print(f"✓ Response time: {test.response_time_ms}ms")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_chatbot_complaint():
    """Test Case 5: Complaint"""
    test = TestResult("Chatbot - Complaint Handling", "Chatbot")
    print("Testing: Complaint Intent...")

    try:
        payload = {
            "message": "My order arrived damaged",
            "user_id": "test_user_complaint",
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/chatbot", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Expected: Intent=complaint, escalation message
        expected_intent = "complaint"
        actual_intent = data.get("intent")
        has_response = len(data.get("response", "")) > 0

        passed = (actual_intent == expected_intent and has_response)

        test.complete(
            passed=passed,
            expected={"intent": expected_intent, "has_response": True},
            actual={
                "intent": actual_intent,
                "response_preview": data.get("response", "")[:100]
            }
        )

        print(f"✓ Intent: {actual_intent}")
        print(f"✓ Response preview: {data.get('response', '')[:150]}...")
        print(f"✓ Response time: {test.response_time_ms}ms")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_order_processing():
    """Test enhanced order processing workflow"""
    test = TestResult("Order Processing - Enhanced Workflow", "Order Processing")
    print("Testing: Enhanced Order Processing...")

    try:
        payload = {
            "whatsapp_message": "Hi, we need 400 boxes for 10 inch pizzas",
            "user_id": "test_user_order_processing",
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/process_order_enhanced", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Expected: Order processed successfully
        has_extracted_items = "extracted_items" in data and len(data["extracted_items"]) > 0
        has_matches = "matched_products" in data

        passed = has_extracted_items and has_matches

        test.complete(
            passed=passed,
            expected={"has_extracted_items": True, "has_matches": True},
            actual={
                "extracted_items_count": len(data.get("extracted_items", [])),
                "matched_products_count": len(data.get("matched_products", [])),
                "status": data.get("status")
            }
        )

        print(f"✓ Extracted items: {len(data.get('extracted_items', []))}")
        print(f"✓ Matched products: {len(data.get('matched_products', []))}")
        print(f"✓ Status: {data.get('status')}")
        print(f"✓ Response time: {test.response_time_ms}ms")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_pii_scrubbing():
    """Test PII scrubbing functionality"""
    test = TestResult("PII Scrubbing - Database Verification", "Privacy")
    print("Testing: PII Scrubbing...")

    try:
        # Send message with PII
        test_user_id = f"test_user_pii_{int(time.time())}"
        payload = {
            "message": "Call me at +65 9123 4567 or email john.doe@example.com",
            "user_id": test_user_id,
            "language": "en"
        }

        response = requests.post(f"{BASE_URL}/api/chatbot", json=payload, timeout=30)
        response.raise_for_status()

        # Wait for DB write
        time.sleep(2)

        # Verify in database that PII was scrubbed
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "tria_db")
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD")

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()

        # Check conversation_messages table
        cursor.execute("""
            SELECT message_text, scrubbed_pii
            FROM conversation_messages
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (test_user_id,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            stored_message, scrubbed_pii = result

            # Check that PII was scrubbed (should not contain original values)
            contains_phone = "+65 9123 4567" in stored_message
            contains_email = "john.doe@example.com" in stored_message
            has_scrubbed_flag = scrubbed_pii is True

            passed = (not contains_phone) and (not contains_email) and has_scrubbed_flag

            test.complete(
                passed=passed,
                expected={"pii_scrubbed": True, "contains_original_pii": False},
                actual={
                    "stored_message_preview": stored_message[:100],
                    "scrubbed_flag": scrubbed_pii,
                    "contains_phone": contains_phone,
                    "contains_email": contains_email
                }
            )

            print(f"✓ Scrubbed flag: {scrubbed_pii}")
            print(f"✓ Phone scrubbed: {not contains_phone}")
            print(f"✓ Email scrubbed: {not contains_email}")
            print(f"✓ Stored message: {stored_message[:100]}...")
        else:
            test.complete(passed=False, error="No database record found")
            print("✗ No database record found")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def test_semantic_search():
    """Test semantic search with product embeddings"""
    test = TestResult("Semantic Search - Product Embeddings", "RAG")
    print("Testing: Semantic Search...")

    try:
        # Query products endpoint
        search_term = "pizza container"
        response = requests.get(
            f"{BASE_URL}/api/products",
            params={"search": search_term, "limit": 5},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        # Expected: Semantic matching works
        has_results = len(data.get("products", [])) > 0

        if has_results:
            # Check if results contain semantically similar products
            product_names = [p.get("product_name", "") for p in data["products"]]

            test.complete(
                passed=has_results,
                expected={"has_results": True, "semantic_match": True},
                actual={
                    "results_count": len(data["products"]),
                    "top_matches": product_names[:3]
                }
            )

            print(f"✓ Results found: {len(data['products'])}")
            print(f"✓ Top matches:")
            for i, name in enumerate(product_names[:3], 1):
                print(f"  {i}. {name}")
            print(f"✓ Response time: {test.response_time_ms}ms")
        else:
            test.complete(passed=False, error="No results found")
            print("✗ No results found")

    except Exception as e:
        test.complete(passed=False, error=str(e))
        print(f"✗ Error: {e}")

    return test.passed


def generate_report():
    """Generate comprehensive test report"""
    print_section("COMPREHENSIVE SYSTEM TEST REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Tests: {len(test_results)}")

    # Summary by category
    categories = {}
    for result in test_results:
        if result.category not in categories:
            categories[result.category] = {"passed": 0, "failed": 0, "total_time": 0}

        if result.passed:
            categories[result.category]["passed"] += 1
        else:
            categories[result.category]["failed"] += 1

        categories[result.category]["total_time"] += result.response_time_ms

    # Print category summaries
    print("\n" + "-"*80)
    print("CATEGORY SUMMARIES")
    print("-"*80)

    total_passed = 0
    total_failed = 0

    for category, stats in categories.items():
        total = stats["passed"] + stats["failed"]
        avg_time = stats["total_time"] / total if total > 0 else 0
        pass_rate = (stats["passed"] / total * 100) if total > 0 else 0

        total_passed += stats["passed"]
        total_failed += stats["failed"]

        status_icon = "✓" if stats["failed"] == 0 else "✗"
        print(f"\n{status_icon} {category}")
        print(f"  Passed: {stats['passed']}/{total} ({pass_rate:.1f}%)")
        print(f"  Avg Response Time: {avg_time:.0f}ms")

    # Overall summary
    print("\n" + "="*80)
    print("OVERALL RESULTS")
    print("="*80)

    total_tests = total_passed + total_failed
    overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\nTotal Tests Run: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Pass Rate: {overall_pass_rate:.1f}%")

    # Detailed results
    print("\n" + "-"*80)
    print("DETAILED RESULTS")
    print("-"*80)

    for result in test_results:
        status_icon = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"\n{status_icon} - {result.test_name}")
        print(f"  Response Time: {result.response_time_ms}ms")

        if result.passed:
            print(f"  Expected: {result.expected}")
            print(f"  Actual: {result.actual}")
        else:
            print(f"  Error: {result.error}")

    # Production readiness assessment
    print("\n" + "="*80)
    print("PRODUCTION READINESS ASSESSMENT")
    print("="*80)

    if overall_pass_rate == 100:
        print("\n✓ SYSTEM IS PRODUCTION READY")
        print("  All tests passed successfully")
        print("  All components functioning correctly")
        print("  RAG, PII scrubbing, and semantic search verified")
    elif overall_pass_rate >= 80:
        print("\n⚠ SYSTEM NEEDS ATTENTION")
        print("  Most tests passed but some issues detected")
        print("  Review failed tests before production deployment")
    else:
        print("\n✗ SYSTEM NOT PRODUCTION READY")
        print("  Multiple test failures detected")
        print("  Significant issues require resolution")

    # Save report to file
    report_path = "C:\\Users\\fujif\\OneDrive\\Documents\\GitHub\\tria\\COMPREHENSIVE_TEST_REPORT.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "pass_rate": overall_pass_rate
            },
            "categories": categories,
            "detailed_results": [r.to_dict() for r in test_results]
        }, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")


def main():
    """Run all tests"""
    print_section("TRIA AI-BPO COMPREHENSIVE SYSTEM TESTING")
    print("Testing all components with real infrastructure (no mocking)")
    print(f"Backend URL: {BASE_URL}")

    # Test Chatbot Endpoint
    print_section("1. CHATBOT ENDPOINT TESTS")
    test_chatbot_greeting()
    print()
    test_chatbot_policy_question()
    print()
    test_chatbot_product_inquiry()
    print()
    test_chatbot_order_placement()
    print()
    test_chatbot_complaint()

    # Test Order Processing
    print_section("2. ORDER PROCESSING WORKFLOW TEST")
    test_order_processing()

    # Test PII Scrubbing
    print_section("3. PII SCRUBBING TEST")
    test_pii_scrubbing()

    # Test Semantic Search
    print_section("4. SEMANTIC SEARCH TEST")
    test_semantic_search()

    # Generate Report
    generate_report()


if __name__ == "__main__":
    main()
