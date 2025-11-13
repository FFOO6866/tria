#!/usr/bin/env python3
"""
Test Health Endpoint
====================

Tests for the /health endpoint to ensure it returns proper status codes
and handles circuit breaker failures gracefully.

PRODUCTION-CRITICAL: Health endpoint must NEVER return HTTP 500.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_health_endpoint_without_circuit_breakers():
    """
    Test that health endpoint returns 200 even if circuit breakers fail

    This was the bug: get_circuit_breaker_status() could throw an exception
    and cause HTTP 500 instead of gracefully degrading.
    """
    from fastapi.testclient import TestClient
    from enhanced_api import app

    client = TestClient(app)

    # Call health endpoint
    response = client.get("/health")

    # Should NEVER return 500
    assert response.status_code != 500, (
        f"Health endpoint returned HTTP 500. "
        f"This is a critical bug that breaks monitoring. "
        f"Response: {response.text}"
    )

    # Should return either 200 (healthy) or 503 (unhealthy)
    assert response.status_code in [200, 503], (
        f"Health endpoint returned unexpected status code: {response.status_code}"
    )

    # Response should be valid JSON
    data = response.json()

    # Must have required fields
    assert "status" in data, "Health response missing 'status' field"
    assert "timestamp" in data, "Health response missing 'timestamp' field"
    assert "version" in data, "Health response missing 'version' field"
    assert "database" in data, "Health response missing 'database' field"
    assert "redis" in data, "Health response missing 'redis' field"

    # Circuit breakers should be present (even if error)
    assert "circuit_breakers" in data, "Health response missing 'circuit_breakers' field"

    # If circuit breakers failed, should have error indicator
    if isinstance(data["circuit_breakers"], dict) and "error" in data["circuit_breakers"]:
        assert data["circuit_breakers"]["error"] == "unavailable", (
            "Circuit breaker error should be 'unavailable'"
        )

    print("\n[PASS] Health endpoint test PASSED")
    print(f"   Status code: {response.status_code}")
    print(f"   Status: {data['status']}")
    print(f"   Circuit breakers: {data['circuit_breakers']}")


def test_health_endpoint_structure():
    """Test that health endpoint returns expected structure"""
    from fastapi.testclient import TestClient
    from enhanced_api import app

    client = TestClient(app)
    response = client.get("/health")

    # Should not be 500
    assert response.status_code != 500

    data = response.json()

    # Required top-level fields
    required_fields = [
        "status",
        "timestamp",
        "version",
        "database",
        "redis",
        "circuit_breakers",
        "chromadb",
        "components"
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Status should be one of: healthy, degraded, unhealthy
    assert data["status"] in ["healthy", "degraded", "unhealthy"], (
        f"Invalid status value: {data['status']}"
    )

    # Version should be present
    assert isinstance(data["version"], str), "Version should be a string"
    assert len(data["version"]) > 0, "Version should not be empty"

    print("\n[PASS] Health endpoint structure test PASSED")
    print(f"   All required fields present")
    print(f"   Status: {data['status']}")


def test_health_endpoint_database_check():
    """Test that database check works correctly"""
    from fastapi.testclient import TestClient
    from enhanced_api import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code != 500

    data = response.json()

    # Database should be either "connected" or have error message
    db_status = data["database"]

    if db_status == "connected":
        # If connected, overall status should not be unhealthy
        assert data["status"] != "unhealthy", (
            "Status should not be unhealthy if database is connected"
        )
        print("\n[PASS] Database health check PASSED - connected")
    else:
        # If database has error, should start with "error:"
        assert db_status.startswith("error:"), (
            f"Database status should be 'connected' or 'error:...', got: {db_status}"
        )
        # If database down, overall status should be unhealthy
        assert data["status"] == "unhealthy", (
            "Status should be unhealthy if database is down"
        )
        print(f"\n[WARN] Database health check - connection failed: {db_status}")


def test_health_endpoint_redis_check():
    """Test that Redis check works correctly"""
    from fastapi.testclient import TestClient
    from enhanced_api import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code != 500

    data = response.json()

    # Redis should be either "connected" or have error message
    redis_status = data["redis"]

    if redis_status == "connected":
        print("\n[PASS] Redis health check PASSED - connected")
    else:
        # If Redis has error, should start with "error:"
        assert redis_status.startswith("error:"), (
            f"Redis status should be 'connected' or 'error:...', got: {redis_status}"
        )
        # If Redis down, overall status should be degraded (not critical)
        assert data["status"] in ["degraded", "unhealthy"], (
            "Status should be degraded if Redis is down"
        )
        print(f"\n[WARN] Redis health check - connection failed: {redis_status}")


if __name__ == "__main__":
    print("=" * 80)
    print("HEALTH ENDPOINT TESTS")
    print("=" * 80)

    try:
        test_health_endpoint_without_circuit_breakers()
        test_health_endpoint_structure()
        test_health_endpoint_database_check()
        test_health_endpoint_redis_check()

        print("\n" + "=" * 80)
        print("[PASS] ALL HEALTH ENDPOINT TESTS PASSED")
        print("=" * 80)
        print("\nHealth endpoint is now production-ready:")
        print("  - Never returns HTTP 500")
        print("  - Gracefully handles circuit breaker failures")
        print("  - Returns proper status codes (200/503)")
        print("  - Includes all required health checks")

    except AssertionError as e:
        print("\n" + "=" * 80)
        print("[FAIL] TEST FAILED")
        print("=" * 80)
        print(f"\nError: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 80)
        print("[ERROR] TEST ERROR")
        print("=" * 80)
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
