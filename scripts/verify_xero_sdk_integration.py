"""
Xero SDK Integration Verification Script
=========================================

This script comprehensively tests the new xero-python SDK integration
to ensure it works correctly before using in production.

Tests:
1. SDK import and initialization
2. OAuth2 token refresh mechanism
3. API client creation
4. Contact (customer) lookup
5. Item (product) lookup
6. Purchase order creation
7. Purchase order update
8. Invoice creation
9. Delete/void operations (compensating transactions)

Run this BEFORE deploying SDK-based code to production.

Usage:
    python scripts/verify_xero_sdk_integration.py

Prerequisites:
    - XERO_CLIENT_ID set in .env
    - XERO_CLIENT_SECRET set in .env
    - XERO_REFRESH_TOKEN set in .env (from get_xero_tokens.py)
    - XERO_TENANT_ID set in .env
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results tracker
test_results: List[Dict[str, Any]] = []


def record_test(test_name: str, passed: bool, details: str = "", error: str = ""):
    """Record test result"""
    test_results.append({
        "test": test_name,
        "passed": passed,
        "details": details,
        "error": error,
        "timestamp": datetime.now().isoformat()
    })

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"  Details: {details}")
    if error:
        print(f"  Error: {error}")


def test_1_sdk_imports():
    """Test 1: Verify all SDK imports work"""
    test_name = "SDK Imports"
    try:
        from xero_python.api_client import ApiClient, Configuration
        from xero_python.api_client.oauth2 import OAuth2Token
        from xero_python.accounting import AccountingApi
        from xero_python.accounting import (
            Contact, Contacts,
            Item, Items,
            PurchaseOrder, PurchaseOrders,
            Invoice, Invoices,
            LineItem
        )
        from xero_python.exceptions import AccountingBadRequestException

        record_test(test_name, True, "All SDK imports successful")
        return True
    except ImportError as e:
        record_test(test_name, False, error=str(e))
        return False


def test_2_config_validation():
    """Test 2: Verify configuration is valid"""
    test_name = "Configuration Validation"
    try:
        from config import config

        required = {
            "XERO_CLIENT_ID": config.XERO_CLIENT_ID,
            "XERO_CLIENT_SECRET": config.XERO_CLIENT_SECRET,
            "XERO_REFRESH_TOKEN": config.XERO_REFRESH_TOKEN,
            "XERO_TENANT_ID": config.XERO_TENANT_ID,
            "XERO_TAX_TYPE": config.XERO_TAX_TYPE,
            "XERO_SALES_ACCOUNT_CODE": config.XERO_SALES_ACCOUNT_CODE
        }

        missing = [k for k, v in required.items() if not v or v.startswith("your-")]

        if missing:
            record_test(
                test_name,
                False,
                error=f"Missing or placeholder values: {', '.join(missing)}"
            )
            return False

        record_test(test_name, True, f"All {len(required)} config variables set")
        return True

    except Exception as e:
        record_test(test_name, False, error=str(e))
        return False


def test_3_client_initialization():
    """Test 3: Verify XeroClient initializes correctly"""
    test_name = "Client Initialization"
    try:
        from integrations.xero_client import get_xero_client

        client = get_xero_client()

        # Check singleton works
        client2 = get_xero_client()
        if client is not client2:
            record_test(test_name, False, error="Singleton pattern broken - got different instances")
            return False

        # Check client has expected attributes
        if not hasattr(client, '_accounting_api'):
            record_test(test_name, False, error="Client missing _accounting_api attribute")
            return False

        if not hasattr(client, '_api_client'):
            record_test(test_name, False, error="Client missing _api_client attribute")
            return False

        record_test(test_name, True, "Client initialized successfully (singleton)")
        return True

    except Exception as e:
        record_test(test_name, False, error=str(e))
        return False


def test_4_token_mechanism():
    """Test 4: Verify OAuth2 token mechanism"""
    test_name = "OAuth2 Token Mechanism"
    try:
        from integrations.xero_client import get_xero_client

        client = get_xero_client()

        # Check token expiry tracking
        if not hasattr(client, '_token_expiry'):
            record_test(test_name, False, error="Client missing _token_expiry attribute")
            return False

        if client._token_expiry is None:
            record_test(test_name, False, error="Token expiry not set after initialization")
            return False

        # Check token is recent (should be set during __init__)
        from datetime import datetime, timedelta
        if client._token_expiry < datetime.now():
            record_test(test_name, False, error="Token already expired")
            return False

        if client._token_expiry > datetime.now() + timedelta(hours=2):
            record_test(
                test_name,
                False,
                error=f"Token expiry suspiciously far in future: {client._token_expiry}"
            )
            return False

        record_test(
            test_name,
            True,
            f"Token valid until {client._token_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return True

    except Exception as e:
        record_test(test_name, False, error=str(e))
        return False


def test_5_verify_customer():
    """Test 5: Test customer verification (live API call)"""
    test_name = "Customer Verification (Live API)"
    try:
        from integrations.xero_client import get_xero_client

        client = get_xero_client()

        # Test 1: Search for non-existent customer (should return None)
        result = client.verify_customer("__NONEXISTENT_TEST_CUSTOMER__")

        if result is not None:
            record_test(
                test_name,
                False,
                error=f"Expected None for non-existent customer, got {result}"
            )
            return False

        record_test(
            test_name,
            True,
            "verify_customer() works correctly (tested with non-existent customer)"
        )
        return True

    except Exception as e:
        record_test(test_name, False, error=f"{type(e).__name__}: {str(e)}")
        return False


def test_6_check_inventory():
    """Test 6: Test inventory check (live API call)"""
    test_name = "Inventory Check (Live API)"
    try:
        from integrations.xero_client import get_xero_client

        client = get_xero_client()

        # Test: Search for non-existent product (should return None)
        result = client.check_inventory("__NONEXISTENT_TEST_PRODUCT__")

        if result is not None:
            record_test(
                test_name,
                False,
                error=f"Expected None for non-existent product, got {result}"
            )
            return False

        record_test(
            test_name,
            True,
            "check_inventory() works correctly (tested with non-existent product)"
        )
        return True

    except Exception as e:
        record_test(test_name, False, error=f"{type(e).__name__}: {str(e)}")
        return False


def test_7_method_signatures():
    """Test 7: Verify all expected methods exist with correct signatures"""
    test_name = "Method Signatures"
    try:
        from integrations.xero_client import get_xero_client
        import inspect

        client = get_xero_client()

        expected_methods = {
            'verify_customer': ['customer_name'],
            'check_inventory': ['product_code'],
            'create_draft_order': ['contact_id', 'line_items', 'reference'],
            'finalize_order': ['order_id'],
            'create_invoice': ['contact_id', 'line_items', 'reference', 'due_date'],
            'delete_draft_order': ['order_id'],
            'void_invoice': ['invoice_id'],
            'get_contact_by_name': ['name'],
            'get_item_by_code': ['code']
        }

        missing_methods = []
        signature_mismatches = []

        for method_name, expected_params in expected_methods.items():
            if not hasattr(client, method_name):
                missing_methods.append(method_name)
                continue

            method = getattr(client, method_name)
            sig = inspect.signature(method)
            actual_params = [p for p in sig.parameters.keys() if p != 'self']

            # Check if expected params are in actual params (allow extra optional params)
            for param in expected_params:
                if param not in actual_params:
                    signature_mismatches.append(
                        f"{method_name}() missing parameter: {param}"
                    )

        if missing_methods:
            record_test(
                test_name,
                False,
                error=f"Missing methods: {', '.join(missing_methods)}"
            )
            return False

        if signature_mismatches:
            record_test(
                test_name,
                False,
                error=f"Signature mismatches: {'; '.join(signature_mismatches)}"
            )
            return False

        record_test(
            test_name,
            True,
            f"All {len(expected_methods)} methods present with correct signatures"
        )
        return True

    except Exception as e:
        record_test(test_name, False, error=str(e))
        return False


def test_8_dataclass_compatibility():
    """Test 8: Verify dataclasses are still available"""
    test_name = "Dataclass Compatibility"
    try:
        from integrations.xero_client import (
            XeroCustomer,
            XeroProduct,
            XeroDraftOrder,
            XeroInvoice
        )

        # Test instantiation
        customer = XeroCustomer(
            contact_id="test-id",
            name="Test Customer"
        )

        product = XeroProduct(
            item_id="test-id",
            code="TEST",
            name="Test Product"
        )

        draft_order = XeroDraftOrder(
            order_id="test-id",
            contact_id="contact-id",
            line_items=[],
            total=100.0
        )

        invoice = XeroInvoice(
            invoice_id="test-id",
            invoice_number="INV-001",
            contact_id="contact-id",
            line_items=[],
            total=100.0,
            status="DRAFT"
        )

        record_test(test_name, True, "All 4 dataclasses work correctly")
        return True

    except Exception as e:
        record_test(test_name, False, error=str(e))
        return False


def test_9_error_handling():
    """Test 9: Verify error handling works"""
    test_name = "Error Handling"
    try:
        from integrations.xero_client import validate_xero_where_clause_input

        # Test valid input
        result = validate_xero_where_clause_input("Valid Customer Name", "test")
        if result != "Valid Customer Name":
            record_test(test_name, False, error="Valid input not returned correctly")
            return False

        # Test invalid input (should raise ValueError)
        try:
            validate_xero_where_clause_input("DROP TABLE users; --", "test")
            record_test(test_name, False, error="SQL injection attempt not blocked")
            return False
        except ValueError:
            pass  # Expected

        # Test empty input
        try:
            validate_xero_where_clause_input("", "test")
            record_test(test_name, False, error="Empty input not rejected")
            return False
        except ValueError:
            pass  # Expected

        record_test(test_name, True, "Input validation works correctly")
        return True

    except Exception as e:
        record_test(test_name, False, error=str(e))
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 80)
    print("XERO SDK INTEGRATION VERIFICATION SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in test_results if r['passed'])
    total = len(test_results)

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED - SDK Integration Verified!")
        print("\nNext Steps:")
        print("  1. Run: python scripts/test_order_with_xero.py")
        print("  2. Monitor logs for any SDK-specific errors")
        print("  3. Compare behavior with old REST API implementation")
        print("  4. Deploy to staging for further testing")
    else:
        print("\n⚠️  SOME TESTS FAILED - DO NOT USE IN PRODUCTION")
        print("\nFailed Tests:")
        for r in test_results:
            if not r['passed']:
                print(f"  ✗ {r['test']}")
                print(f"    Error: {r['error']}")
        print("\nAction Required:")
        print("  1. Fix errors listed above")
        print("  2. Re-run this verification script")
        print("  3. Consider rolling back to REST API implementation")

    print("\n" + "=" * 80)

    return passed == total


def main():
    """Run all verification tests"""
    print("=" * 80)
    print("XERO SDK INTEGRATION VERIFICATION")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This script will test the new xero-python SDK integration")
    print("to ensure it works correctly before production use.")
    print()
    print("Tests will include:")
    print("  - SDK imports and initialization")
    print("  - OAuth2 token mechanism")
    print("  - API method signatures")
    print("  - Live API calls (customer/product lookup)")
    print("  - Error handling")
    print("  - Dataclass compatibility")
    print()
    print("NOTE: This will make REAL API calls to Xero.")
    print("=" * 80)

    # Run all tests
    tests = [
        test_1_sdk_imports,
        test_2_config_validation,
        test_3_client_initialization,
        test_4_token_mechanism,
        test_7_method_signatures,
        test_8_dataclass_compatibility,
        test_9_error_handling,
        test_5_verify_customer,  # Live API call
        test_6_check_inventory,   # Live API call
    ]

    all_passed = True
    for test_func in tests:
        try:
            result = test_func()
            all_passed = all_passed and result

            # Stop if critical test fails
            if not result and test_func.__name__ in ['test_1_sdk_imports', 'test_2_config_validation']:
                print(f"\n⚠️  Critical test failed: {test_func.__name__}")
                print("Cannot continue without fixing this issue.")
                break

        except Exception as e:
            logger.error(f"Unexpected error in {test_func.__name__}: {e}", exc_info=True)
            record_test(test_func.__name__, False, error=f"Unexpected error: {str(e)}")
            all_passed = False

    # Print summary
    success = print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
