"""
Tier 3 E2E Test Configuration
==============================

Shared fixtures and configuration for end-to-end integration tests.
"""

import pytest
import asyncio
import os
from pathlib import Path
import sys

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest for tier 3 tests"""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: marks performance benchmark tests"
    )
    config.addinivalue_line(
        "markers",
        "requires_chromadb: marks tests that require ChromaDB"
    )
    config.addinivalue_line(
        "markers",
        "requires_redis: marks tests that require Redis"
    )


# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests

    Scope: session (shared across all tests)
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def openai_api_key() -> str:
    """
    Get OpenAI API key for testing

    Scope: session
    Returns:
        API key from environment

    Raises:
        pytest.skip: If API key not available
    """
    api_key = os.getenv("OPENAI_API_KEY_TEST") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY_TEST or OPENAI_API_KEY not set")
    return api_key


@pytest.fixture(scope="session")
def database_url() -> str:
    """
    Get database URL for testing

    Scope: session
    Returns:
        Database URL from environment

    Raises:
        pytest.skip: If database URL not available
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set")
    return db_url


@pytest.fixture(scope="session")
def redis_url() -> str:
    """
    Get Redis URL for testing

    Scope: session
    Returns:
        Redis URL (defaults to localhost if not set)
    """
    return os.getenv("REDIS_URL", "redis://localhost:6379")


@pytest.fixture(scope="session")
def chromadb_config() -> dict:
    """
    Get ChromaDB configuration

    Scope: session
    Returns:
        ChromaDB configuration dict
    """
    return {
        "host": os.getenv("CHROMADB_HOST", "localhost"),
        "port": int(os.getenv("CHROMADB_PORT", "8000")),
    }


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def sample_intents() -> list:
    """
    Sample messages for intent testing

    Scope: session (immutable)
    Returns:
        List of valid intent names
    """
    return [
        "greeting",
        "order_placement",
        "order_status",
        "product_inquiry",
        "policy_question",
        "complaint",
        "general_query"
    ]


@pytest.fixture(scope="session")
def performance_targets() -> dict:
    """
    Performance targets for validation

    Scope: session
    Returns:
        Dict of performance targets
    """
    return {
        "uncached_request_max_seconds": 20.0,
        "l1_cache_hit_max_ms": 10.0,
        "l2_cache_hit_max_ms": 100.0,
        "streaming_first_token_max_seconds": 1.0,
        "p95_latency_max_seconds": 8.0,
        "success_rate_min_percent": 95.0,
        "cache_hit_rate_min_percent": 80.0,
        "sustained_rps_target": 10.0
    }


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """
    Cleanup test data after each test

    Autouse: True (runs automatically)
    """
    # Setup: Nothing to do before test

    yield  # Run test

    # Teardown: Cleanup after test
    # Note: Specific cleanup should be done in individual test fixtures
    pass


# ============================================================================
# REPORTING FIXTURES
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def test_report(request):
    """
    Generate test report after session

    Scope: session
    Autouse: True
    """
    # Setup: Initialize report
    report = {
        "start_time": None,
        "end_time": None,
        "tests": []
    }

    import time
    report["start_time"] = time.time()

    yield report

    # Teardown: Finalize report
    report["end_time"] = time.time()

    # Print summary
    print("\n" + "=" * 80)
    print("TIER 3 END-TO-END INTEGRATION TEST SESSION SUMMARY")
    print("=" * 80)
    print(f"Session duration: {report['end_time'] - report['start_time']:.2f}s")
    print("=" * 80)
