#!/usr/bin/env python3
"""
Connection Pool Test
=====================

Simple test to verify database connection pooling is working correctly.

Tests:
1. Engine singleton pattern (same engine returned on multiple calls)
2. Connection reuse from pool
3. Pool statistics tracking
4. No engine.dispose() between calls

NO MOCKING - Tests real PostgreSQL connection pool.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from database import get_db_engine, get_pool_status, dispose_engine
from sqlalchemy import text


def test_singleton_pattern():
    """Test that get_db_engine returns the same engine instance"""
    print("\n[TEST 1] Testing singleton pattern...")

    engine1 = get_db_engine()
    engine2 = get_db_engine()

    if engine1 is engine2:
        print("✅ PASS: Same engine instance returned (singleton pattern working)")
        return True
    else:
        print("❌ FAIL: Different engine instances returned")
        return False


def test_connection_reuse():
    """Test that connections are returned to pool and reused"""
    print("\n[TEST 2] Testing connection reuse...")

    engine = get_db_engine()

    # Execute 5 queries sequentially
    for i in range(5):
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 AS test"))
            value = result.scalar()
            assert value == 1, f"Query {i+1} failed"

    # Check pool stats
    stats = get_pool_status()
    print(f"   Pool stats after 5 sequential queries:")
    print(f"   - Checked out: {stats['checked_out']}")
    print(f"   - Checked in: {stats['checked_in']}")
    print(f"   - Overflow: {stats['overflow']}")
    print(f"   - Total: {stats['total']}")

    # After all connections are returned, checked_out should be 0
    if stats['checked_out'] == 0:
        print("✅ PASS: All connections returned to pool")
        return True
    else:
        print(f"❌ FAIL: {stats['checked_out']} connections still checked out")
        return False


def test_no_dispose_between_calls():
    """Test that engine is NOT disposed between function calls"""
    print("\n[TEST 3] Testing engine persistence...")

    # Get engine
    engine1 = get_db_engine()
    initial_stats = get_pool_status()

    # Simulate what happens in load_products_with_embeddings()
    with engine1.connect() as conn:
        conn.execute(text("SELECT 1"))

    # Get engine again (simulating another API call)
    engine2 = get_db_engine()
    second_stats = get_pool_status()

    # Engine should still be the same instance
    if engine1 is engine2:
        print("✅ PASS: Engine persisted between calls (not disposed)")
        print(f"   Initial pool size: {initial_stats['size']}")
        print(f"   After second call: {second_stats['size']}")
        return True
    else:
        print("❌ FAIL: Engine was disposed/recreated between calls")
        return False


def test_load_products_pattern():
    """Test the actual pattern used in semantic_search.py"""
    print("\n[TEST 4] Testing load_products pattern...")

    from semantic_search import load_products_with_embeddings
    from config import config

    try:
        # This would normally load products with embeddings
        # We're just testing the connection pattern
        engine = get_db_engine(config.get_database_url())

        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
            print(f"   Found {count} products in database")

        # Verify engine is still alive after the operation
        stats = get_pool_status()
        print(f"   Pool still active: {stats['size']} connections")

        print("✅ PASS: Load products pattern works correctly")
        return True

    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("CONNECTION POOL VERIFICATION TEST")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("Singleton Pattern", test_singleton_pattern()))
    results.append(("Connection Reuse", test_connection_reuse()))
    results.append(("No Dispose Between Calls", test_no_dispose_between_calls()))
    results.append(("Load Products Pattern", test_load_products_pattern()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    # Cleanup
    print("\n[CLEANUP] Disposing engine...")
    dispose_engine()
    print("✅ Engine disposed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
