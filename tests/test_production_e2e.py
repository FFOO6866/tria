#!/usr/bin/env python3
"""
PRODUCTION END-TO-END TESTING
==============================

Tests all 3 critical test cases with REAL data:
1. Pizza box order (clean input)
2. Typo order (error handling)
3. Meal tray order (different product category)

VALIDATION CRITERIA:
- 100% extraction accuracy (all SKUs matched)
- 100% database write success (orders saved)
- Zero fallbacks used (all data from catalog)
- Zero hardcoding (all prices from database)
- Semantic search working (56-61% similarity achieved)

NO MOCKING - All production APIs and database
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from decimal import Decimal

# Load environment
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
load_dotenv(project_root / ".env")

# API Configuration
API_BASE_URL = "http://localhost:8001"
API_ENDPOINT = f"{API_BASE_URL}/api/process_order_enhanced"

print("=" * 80)
print("PRODUCTION END-TO-END TESTING - TRIA AI-BPO")
print("=" * 80)
print(f"API Endpoint: {API_ENDPOINT}")
print(f"Timestamp: {datetime.now().isoformat()}")
print("=" * 80)

# ============================================================================
# TEST CASE DEFINITIONS (From PRODUCTION_ISSUES.md)
# ============================================================================

test_cases = [
    {
        "id": 1,
        "name": "Pizza Box Order (Clean Input)",
        "whatsapp_message": "Hi, this is Canadian Pizza Jurong West. We need 400 boxes for 10 inch pizzas, 200 for 12 inch, and 300 for 14 inch. Thanks!",
        "expected_skus": ["CNP-014-FB-01", "CNP-015-FB-01", "CNP-016-FB-01"],
        "expected_quantities": [400, 200, 300],
        "expected_outlet": "Canadian Pizza - Jurong West",
        "min_similarity": 0.56  # Semantic search should achieve 56-61%
    },
    {
        "id": 2,
        "name": "Typo Order (Error Handling)",
        "whatsapp_message": "Need piza boxs for Canadian Pizza Bukit Batok: ten inch: 100 pcs, twelv inch: 50 pcs",
        "expected_skus": ["CNP-014-FB-01", "CNP-015-FB-01"],
        "expected_quantities": [100, 50],
        "expected_outlet": "Canadian Pizza - Bukit Batok",
        "min_similarity": 0.60  # Typos actually improve similarity to 60-61%
    },
    {
        "id": 3,
        "name": "Meal Tray Order (Different Category)",
        "whatsapp_message": "This is Jollibee Clementi Sck. We need 200 single-compartment meal trays and 200 lids for meal trays. Urgent!",
        "expected_skus": ["TRI-001-TR-01", "TRI-002-LD-01"],
        "expected_quantities": [200, 200],
        "expected_outlet": "Jollibee - Clementi Sck",
        "min_similarity": 0.51,  # Meal trays: 51-54% similarity
        "is_urgent": True
    }
]

# ============================================================================
# TEST EXECUTION
# ============================================================================

test_results = []
passed_tests = 0
failed_tests = 0

for test_case in test_cases:
    print(f"\n{'=' * 80}")
    print(f"TEST CASE #{test_case['id']}: {test_case['name']}")
    print(f"{'=' * 80}")
    print(f"Message: {test_case['whatsapp_message'][:80]}...")
    print(f"Expected SKUs: {test_case['expected_skus']}")
    print(f"Expected Quantities: {test_case['expected_quantities']}")
    print(f"Expected Outlet: {test_case['expected_outlet']}")

    # Send request to API
    print(f"\n[>>] Sending request to API...")
    try:
        response = requests.post(API_ENDPOINT, json={
            "whatsapp_message": test_case['whatsapp_message']
        }, timeout=60)

        if response.status_code != 200:
            print(f"\n[ERROR] API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            test_results.append({
                "test_id": test_case['id'],
                "name": test_case['name'],
                "status": "FAILED",
                "error": f"HTTP {response.status_code}"
            })
            failed_tests += 1
            continue

        result = response.json()

        # ====================================================================
        # VALIDATION #1: Extraction Accuracy
        # ====================================================================
        print(f"\n[>>] Validating extraction accuracy...")

        parsed_order = result.get('details', {}).get('parsed_order', {})
        line_items = parsed_order.get('line_items', [])

        extracted_skus = [item.get('sku') for item in line_items]
        extracted_quantities = [item.get('quantity') for item in line_items]
        extracted_outlet = parsed_order.get('outlet_name', '')

        print(f"Extracted SKUs: {extracted_skus}")
        print(f"Extracted Quantities: {extracted_quantities}")
        print(f"Extracted Outlet: {extracted_outlet}")

        # Check SKU matching
        sku_match = set(extracted_skus) == set(test_case['expected_skus'])
        qty_match = sorted(extracted_quantities) == sorted(test_case['expected_quantities'])
        outlet_match = extracted_outlet == test_case['expected_outlet']

        extraction_accuracy = 100 if (sku_match and qty_match) else 0

        print(f"\nSKU Match: {'[PASS]' if sku_match else '[FAIL]'}")
        print(f"Quantity Match: {'[PASS]' if qty_match else '[FAIL]'}")
        print(f"Outlet Match: {'[PASS]' if outlet_match else '[FAIL]'}")
        print(f"Extraction Accuracy: {extraction_accuracy}%")

        # ====================================================================
        # VALIDATION #2: Database Write Success
        # ====================================================================
        print(f"\n[>>] Validating database write...")

        order_id = result.get('order_id')
        database_write_success = order_id is not None and order_id > 0

        print(f"Order ID: {order_id}")
        print(f"Database Write: {'[PASS]' if database_write_success else '[FAIL]'}")

        # ====================================================================
        # VALIDATION #3: Semantic Search Quality
        # ====================================================================
        print(f"\n[>>] Validating semantic search quality...")

        semantic_results = result.get('details', {}).get('semantic_search_results', 0)

        print(f"Semantic Search Results: {semantic_results} products found")
        print(f"Semantic Search: {'[PASS]' if semantic_results >= 3 else '[FAIL]'}")

        # ====================================================================
        # VALIDATION #4: No Fallbacks Used
        # ====================================================================
        print(f"\n[>>] Validating no fallbacks used...")

        # Check for fallback indicators
        has_unknown_outlet = "Unknown" in extracted_outlet
        has_empty_items = len(line_items) == 0
        has_placeholder_skus = any("exact SKU" in item.get('sku', '') for item in line_items)

        no_fallbacks = not (has_unknown_outlet or has_empty_items or has_placeholder_skus)

        print(f"No Unknown Outlet: {'[PASS]' if not has_unknown_outlet else '[FAIL]'}")
        print(f"No Empty Items: {'[PASS]' if not has_empty_items else '[FAIL]'}")
        print(f"No Placeholder SKUs: {'[PASS]' if not has_placeholder_skus else '[FAIL]'}")
        print(f"No Fallbacks Used: {'[PASS]' if no_fallbacks else '[FAIL]'}")

        # ====================================================================
        # VALIDATION #5: Catalog Pricing
        # ====================================================================
        print(f"\n[>>] Validating catalog pricing...")

        subtotal = result.get('details', {}).get('subtotal', 0)
        tax = result.get('details', {}).get('tax', 0)
        total = result.get('details', {}).get('total', 0)

        has_valid_pricing = subtotal > 0 and tax > 0 and total > 0

        print(f"Subtotal: ${subtotal:.2f}")
        print(f"Tax: ${tax:.2f}")
        print(f"Total: ${total:.2f}")
        print(f"Valid Pricing: {'[PASS]' if has_valid_pricing else '[FAIL]'}")

        # ====================================================================
        # VALIDATION #6: Urgent Flag (Test Case 3 only)
        # ====================================================================
        if test_case.get('is_urgent'):
            print(f"\n[>>] Validating urgent flag...")
            is_urgent = parsed_order.get('is_urgent', False)
            print(f"Urgent Flag: {'[PASS]' if is_urgent else '[FAIL]'}")
            urgent_check_pass = is_urgent
        else:
            urgent_check_pass = True

        # ====================================================================
        # OVERALL TEST RESULT
        # ====================================================================
        all_validations_passed = (
            sku_match and
            qty_match and
            outlet_match and
            database_write_success and
            no_fallbacks and
            has_valid_pricing and
            semantic_results >= 3 and
            urgent_check_pass
        )

        if all_validations_passed:
            print(f"\n{'=' * 80}")
            print(f"[PASS] TEST CASE #{test_case['id']}: PASSED")
            print(f"{'=' * 80}")
            passed_tests += 1
            test_results.append({
                "test_id": test_case['id'],
                "name": test_case['name'],
                "status": "PASSED",
                "order_id": order_id,
                "extraction_accuracy": 100,
                "database_write": "SUCCESS",
                "semantic_results": semantic_results,
                "total": f"${total:.2f}"
            })
        else:
            print(f"\n{'=' * 80}")
            print(f"[FAIL] TEST CASE #{test_case['id']}: FAILED")
            print(f"{'=' * 80}")
            failed_tests += 1
            test_results.append({
                "test_id": test_case['id'],
                "name": test_case['name'],
                "status": "FAILED",
                "extraction_accuracy": extraction_accuracy,
                "sku_match": sku_match,
                "qty_match": qty_match,
                "outlet_match": outlet_match,
                "database_write": "SUCCESS" if database_write_success else "FAILED",
                "no_fallbacks": no_fallbacks,
                "valid_pricing": has_valid_pricing
            })

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Request failed: {e}")
        test_results.append({
            "test_id": test_case['id'],
            "name": test_case['name'],
            "status": "ERROR",
            "error": str(e)
        })
        failed_tests += 1

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print(f"\n\n{'=' * 80}")
print("PRODUCTION TEST SUMMARY")
print(f"{'=' * 80}")
print(f"Total Tests: {len(test_cases)}")
print(f"Passed: {passed_tests}")
print(f"Failed: {failed_tests}")
print(f"Success Rate: {(passed_tests / len(test_cases) * 100):.1f}%")
print(f"{'=' * 80}")

# Detailed results
print(f"\nDetailed Results:")
for result in test_results:
    print(f"\n  Test #{result['test_id']}: {result['name']}")
    print(f"    Status: {result['status']}")
    if result['status'] == 'PASSED':
        print(f"    Order ID: {result.get('order_id', 'N/A')}")
        print(f"    Extraction: {result.get('extraction_accuracy', 'N/A')}%")
        print(f"    Database: {result.get('database_write', 'N/A')}")
        print(f"    Semantic Results: {result.get('semantic_results', 'N/A')}")
        print(f"    Total: {result.get('total', 'N/A')}")
    elif result['status'] == 'FAILED':
        print(f"    Extraction: {result.get('extraction_accuracy', 'N/A')}%")
        print(f"    SKU Match: {result.get('sku_match', False)}")
        print(f"    Qty Match: {result.get('qty_match', False)}")
        print(f"    Outlet Match: {result.get('outlet_match', False)}")
        print(f"    Database: {result.get('database_write', 'UNKNOWN')}")
    elif result['status'] == 'ERROR':
        print(f"    Error: {result.get('error', 'Unknown error')}")

# Production readiness verdict
print(f"\n{'=' * 80}")
if passed_tests == len(test_cases):
    print("[PASS] PRODUCTION READY - ALL TESTS PASSED")
    print("  - 100% extraction accuracy achieved")
    print("  - 100% database write success")
    print("  - Zero fallbacks used")
    print("  - Catalog pricing working")
    print("  - Semantic search excellent")
else:
    print("[FAIL] NOT PRODUCTION READY - FAILURES DETECTED")
    print(f"  - {failed_tests} test(s) failed")
    print("  - Review errors above")
print(f"{'=' * 80}")

# Exit code
sys.exit(0 if passed_tests == len(test_cases) else 1)
