#!/usr/bin/env python3
"""
Phase 1: System State Verification
===================================

This script checks the current state of the system before testing:
1. Environment configuration
2. Database connectivity
3. Redis connectivity
4. Xero API configuration
5. ChromaDB knowledge base status
6. Product catalog in database
7. Customer data in database

Run this FIRST to understand what's configured and what's missing.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def print_header(text: str):
    """Print section header"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def print_check(name: str, status: bool, details: str = ""):
    """Print check result"""
    symbol = "[OK]" if status else "[FAIL]"
    print(f"{symbol} {name}")
    if details:
        print(f"   {details}")


def check_environment() -> Dict[str, Any]:
    """Check environment configuration"""
    print_header("1. ENVIRONMENT CONFIGURATION")

    results = {
        "openai_configured": False,
        "database_configured": False,
        "redis_configured": False,
        "xero_configured": False,
        "sentry_configured": False
    }

    try:
        from config import config

        # Check OpenAI
        if config.OPENAI_API_KEY:
            print_check("OpenAI API Key", True, f"Model: {config.OPENAI_MODEL}")
            results["openai_configured"] = True
        else:
            print_check("OpenAI API Key", False, "OPENAI_API_KEY not set")

        # Check Database
        db_url = config.get_database_url()
        if db_url:
            print_check("Database URL", True, db_url[:50] + "...")
            results["database_configured"] = True
        else:
            print_check("Database URL", False, "DATABASE_URL not set")

        # Check Redis
        if config.REDIS_HOST:
            print_check("Redis", True, f"{config.REDIS_HOST}:{config.REDIS_PORT}")
            results["redis_configured"] = True
        else:
            print_check("Redis", False, "REDIS_HOST not set")

        # Check Xero
        if config.xero_configured:
            print_check("Xero API", True, f"Tenant: {config.XERO_TENANT_ID}")
            print(f"   Sales Account: {config.XERO_SALES_ACCOUNT_CODE}")
            print(f"   Tax Type: {config.XERO_TAX_TYPE}")
            results["xero_configured"] = True
        else:
            print_check("Xero API", False, "Xero credentials not configured")

        # Check Sentry
        if config.SENTRY_DSN:
            print_check("Sentry Error Tracking", True, f"Environment: {config.ENVIRONMENT}")
            results["sentry_configured"] = True
        else:
            print_check("Sentry Error Tracking", False, "Optional - not configured")

    except Exception as e:
        print_check("Configuration Load", False, f"Error: {e}")

    return results


def check_database_connection() -> Dict[str, Any]:
    """Check database connectivity and data"""
    print_header("2. DATABASE CONNECTIVITY & DATA")

    results = {
        "connected": False,
        "outlets_count": 0,
        "products_count": 0,
        "orders_count": 0
    }

    try:
        from database import get_db_engine
        from config import config
        from sqlalchemy import text

        engine = get_db_engine(config.DATABASE_URL)

        with engine.connect() as conn:
            # Test connection
            conn.execute(text("SELECT 1"))
            print_check("Database Connection", True)
            results["connected"] = True

            # Check outlets
            result = conn.execute(text("SELECT COUNT(*) FROM outlets"))
            outlets_count = result.fetchone()[0]
            print_check("Outlets/Customers", outlets_count > 0, f"Found {outlets_count} outlets")
            results["outlets_count"] = outlets_count

            # Check products
            result = conn.execute(text("SELECT COUNT(*) FROM products WHERE is_active = true"))
            products_count = result.fetchone()[0]
            print_check("Active Products", products_count > 0, f"Found {products_count} active products")
            results["products_count"] = products_count

            # Check orders
            result = conn.execute(text("SELECT COUNT(*) FROM orders"))
            orders_count = result.fetchone()[0]
            print(f"   Orders in database: {orders_count}")
            results["orders_count"] = orders_count

    except Exception as e:
        print_check("Database Connection", False, f"Error: {e}")

    return results


def check_redis_connection() -> Dict[str, Any]:
    """Check Redis connectivity"""
    print_header("3. REDIS CACHE CONNECTIVITY")

    results = {
        "connected": False,
        "keys_count": 0
    }

    try:
        import redis
        from config import config

        r = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
            db=config.REDIS_DB
        )

        # Test connection
        r.ping()
        print_check("Redis Connection", True, f"{config.REDIS_HOST}:{config.REDIS_PORT}")
        results["connected"] = True

        # Check existing keys
        keys = r.keys('*')
        print(f"   Existing cache keys: {len(keys)}")
        results["keys_count"] = len(keys)

    except Exception as e:
        print_check("Redis Connection", False, f"Error: {e}")

    return results


def check_chromadb_knowledge_base() -> Dict[str, Any]:
    """Check ChromaDB knowledge base status"""
    print_header("4. CHROMADB KNOWLEDGE BASE")

    results = {
        "connected": False,
        "policies_count": 0,
        "faqs_count": 0,
        "escalation_rules_count": 0,
        "tone_guidelines_count": 0
    }

    try:
        from rag.chroma_client import get_chroma_client, health_check

        # Health check
        is_healthy = health_check()
        print_check("ChromaDB Connection", is_healthy)

        if is_healthy:
            results["connected"] = True
            client = get_chroma_client()

            # Check each collection
            try:
                policies = client.get_collection('policies_en')
                policies_count = policies.count()
                print_check("Policies Collection", policies_count > 0, f"{policies_count} documents")
                results["policies_count"] = policies_count
            except Exception:
                print_check("Policies Collection", False, "Collection not found or empty")

            try:
                faqs = client.get_collection('faqs_en')
                faqs_count = faqs.count()
                print_check("FAQs Collection", faqs_count > 0, f"{faqs_count} documents")
                results["faqs_count"] = faqs_count
            except Exception:
                print_check("FAQs Collection", False, "Collection not found or empty")

            try:
                escalation = client.get_collection('escalation_rules_en')
                escalation_count = escalation.count()
                print_check("Escalation Rules Collection", escalation_count > 0, f"{escalation_count} documents")
                results["escalation_rules_count"] = escalation_count
            except Exception:
                print_check("Escalation Rules Collection", False, "Collection not found or empty")

            try:
                tone = client.get_collection('tone_guidelines_en')
                tone_count = tone.count()
                print_check("Tone Guidelines Collection", tone_count > 0, f"{tone_count} documents")
                results["tone_guidelines_count"] = tone_count
            except Exception:
                print_check("Tone Guidelines Collection", False, "Collection not found or empty")

    except Exception as e:
        print_check("ChromaDB Connection", False, f"Error: {e}")

    return results


def check_xero_connectivity() -> Dict[str, Any]:
    """Check Xero API connectivity"""
    print_header("5. XERO API CONNECTIVITY")

    results = {
        "connected": False,
        "organization_name": None,
        "customers_count": 0,
        "products_count": 0
    }

    try:
        from config import config

        if not config.xero_configured:
            print_check("Xero Configuration", False, "Xero credentials not configured in .env")
            return results

        from integrations.xero_client import get_xero_client

        client = get_xero_client()

        # Test API connectivity
        response = client._make_request('GET', '/Organisation')

        if response.status_code == 200:
            print_check("Xero API Connection", True)
            results["connected"] = True

            org_data = response.json()
            if org_data.get('Organisations'):
                org = org_data['Organisations'][0]
                org_name = org.get('Name', 'Unknown')
                print(f"   Organization: {org_name}")
                results["organization_name"] = org_name

            # Check contacts (customers)
            try:
                contacts_response = client._make_request('GET', '/Contacts?where=IsCustomer==true')
                if contacts_response.status_code == 200:
                    contacts_data = contacts_response.json()
                    contacts_count = len(contacts_data.get('Contacts', []))
                    print_check("Xero Customers", contacts_count > 0, f"{contacts_count} customers")
                    results["customers_count"] = contacts_count
            except Exception as e:
                print_check("Xero Customers", False, f"Error fetching: {e}")

            # Check items (products)
            try:
                items_response = client._make_request('GET', '/Items')
                if items_response.status_code == 200:
                    items_data = items_response.json()
                    items_count = len(items_data.get('Items', []))
                    print_check("Xero Products", items_count > 0, f"{items_count} items")
                    results["products_count"] = items_count
            except Exception as e:
                print_check("Xero Products", False, f"Error fetching: {e}")

        else:
            print_check("Xero API Connection", False, f"HTTP {response.status_code}")

    except Exception as e:
        print_check("Xero API Connection", False, f"Error: {e}")

    return results


def generate_summary(all_results: Dict[str, Dict[str, Any]]):
    """Generate summary and recommendations"""
    print_header("SUMMARY & RECOMMENDATIONS")

    env = all_results.get("environment", {})
    db = all_results.get("database", {})
    redis = all_results.get("redis", {})
    chroma = all_results.get("chromadb", {})
    xero = all_results.get("xero", {})

    # Calculate readiness score
    checks = [
        env.get("openai_configured", False),
        env.get("database_configured", False),
        env.get("redis_configured", False),
        env.get("xero_configured", False),
        db.get("connected", False),
        db.get("outlets_count", 0) > 0,
        db.get("products_count", 0) > 0,
        redis.get("connected", False),
        chroma.get("connected", False),
        chroma.get("policies_count", 0) > 0,
        chroma.get("faqs_count", 0) > 0,
        xero.get("connected", False),
        xero.get("customers_count", 0) > 0,
        xero.get("products_count", 0) > 0
    ]

    passed = sum(checks)
    total = len(checks)
    score = (passed / total) * 100

    print(f"\nReadiness Score: {passed}/{total} ({score:.0f}%)")
    print()

    # Recommendations
    print("NEXT STEPS:")
    print()

    if not env.get("openai_configured"):
        print("[BLOCKER] Set OPENAI_API_KEY in .env file")

    if not db.get("connected"):
        print("[BLOCKER] Fix database connection (check DATABASE_URL)")

    if not env.get("xero_configured"):
        print("[BLOCKER] Configure Xero credentials in .env")
        print("   - XERO_CLIENT_ID")
        print("   - XERO_CLIENT_SECRET")
        print("   - XERO_REFRESH_TOKEN")
        print("   - XERO_TENANT_ID")

    if db.get("products_count", 0) == 0:
        print("[WARNING] No products in database")
        print("   Action: Import product catalog")

    if db.get("outlets_count", 0) == 0:
        print("[WARNING] No outlets/customers in database")
        print("   Action: Import customer data")

    if not chroma.get("connected") or chroma.get("policies_count", 0) == 0:
        print("[WARNING] ChromaDB knowledge base empty or not accessible")
        print("   Action: Run knowledge base population script")
        print("   Command: python scripts/build_knowledge_base_from_markdown.py")

    if not xero.get("connected"):
        print("[BLOCKER] Cannot connect to Xero API")
        print("   Action: Check Xero credentials and refresh token")
    elif xero.get("customers_count", 0) == 0 or xero.get("products_count", 0) == 0:
        print("[WARNING] Xero master data not loaded")
        print("   Action: Run master data loading script")
        print("   Command: python scripts/load_xero_demo_data.py")

    if not redis.get("connected"):
        print("[WARNING] Redis not connected (caching will be disabled)")
        print("   Action: Start Redis or fix connection")

    if score == 100:
        print("\n[SUCCESS] EXCELLENT: All systems ready for testing!")
        print("   Next: Run end-to-end tests")
        print("   Command: python scripts/test_order_with_xero.py")
    elif score >= 75:
        print("\n[WARNING] GOOD: Most systems ready, fix warnings above")
        print("   Next: Address warnings, then test")
    elif score >= 50:
        print("\n[WARNING] NEEDS WORK: Several critical issues")
        print("   Next: Fix blockers above before testing")
    else:
        print("\n[FAIL] NOT READY: Multiple critical issues")
        print("   Next: Fix all blockers before proceeding")

    print()


def main():
    """Main entry point"""
    print("\n" + "=" * 80)
    print("PHASE 1: SYSTEM STATE VERIFICATION")
    print("=" * 80)
    print("\nThis script checks if all components are configured and ready for testing.")
    print()

    all_results = {}

    # Run all checks
    all_results["environment"] = check_environment()
    all_results["database"] = check_database_connection()
    all_results["redis"] = check_redis_connection()
    all_results["chromadb"] = check_chromadb_knowledge_base()
    all_results["xero"] = check_xero_connectivity()

    # Generate summary
    generate_summary(all_results)

    # Save results
    import json
    results_file = Path(__file__).parent.parent / "phase1_verification_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"📊 Detailed results saved to: {results_file}")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
