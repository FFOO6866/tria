"""
Tier 3: End-to-End Integration Tests
======================================

Comprehensive system-level tests that verify the complete TRIA chatbot
platform with all components working together.

Test Strategy:
- NO MOCKING - All tests use real infrastructure
- Real OpenAI API (with test key and rate limits)
- Real Redis cache
- Real ChromaDB vector store
- Real PostgreSQL database

Test Categories:
1. Full request flow (uncached)
2. Cache hit flows (L1, L2)
3. Streaming responses
4. A/B testing
5. DSPy optimization
6. Error scenarios
7. Performance benchmarks
8. Load testing

Running Tests:
--------------

# Run all tier 3 tests
pytest tests/tier3_e2e/ -v

# Run specific test
pytest tests/tier3_e2e/test_full_integration.py::test_full_request_flow_uncached -v

# Run performance tests (slow)
pytest tests/tier3_e2e/ -v -m slow

# Skip slow tests
pytest tests/tier3_e2e/ -v -m "not slow"

Environment Setup:
------------------

Required environment variables:
- OPENAI_API_KEY_TEST (or OPENAI_API_KEY)
- DATABASE_URL (PostgreSQL)
- REDIS_URL (optional, defaults to localhost)

Optional environment variables:
- CHROMADB_HOST (defaults to localhost)
- CHROMADB_PORT (defaults to 8000)

Prerequisites:
--------------

1. PostgreSQL running with test database
2. Redis running (for L1 cache)
3. ChromaDB running (for L2 semantic cache)
4. OpenAI API key with credits

Performance Targets:
--------------------

- Uncached request: <20s
- L1 cache hit: <10ms
- L2 semantic cache hit: <100ms
- Streaming first token: <1s
- 100 concurrent requests: P95 < 8s
- Sustained 10 req/s: 95% success rate
- Cache hit rate: >80%

NO MOCKING PHILOSOPHY:
----------------------

Tier 3 tests MUST use real infrastructure to ensure production readiness.
This includes:
- Real API calls (cost-aware, use test keys with limits)
- Real databases (use separate test instances)
- Real cache stores (Redis, ChromaDB)
- Real network latency
- Real error scenarios

This ensures we test actual production behavior, not mocked idealizations.
"""

# Test markers
import pytest

# Register custom markers
def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: marks performance benchmark tests"
    )
