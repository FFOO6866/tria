# Tier 3: End-to-End Integration Tests

## Overview

Comprehensive end-to-end integration tests for the complete TRIA chatbot system with all components working together.

**Test Philosophy**: NO MOCKING - All tests use real infrastructure to ensure production readiness.

## Test Coverage

### 1. Full Request Flow (Uncached)
**File**: `test_full_integration.py::test_full_request_flow_uncached`

Tests the complete request pipeline for an uncached message:
- Parallel execution (intent classification + RAG retrieval)
- Response generation with GPT-4
- Caching of results (L1, L2, L3, L4)
- Timing verification (<20s target)

**Verifies**:
- ✓ Intent classification accuracy
- ✓ RAG retrieval working
- ✓ Parallel execution benefits
- ✓ Response caching
- ✓ Performance within target

### 2. Cache Hit Flow (L1 Exact Match)
**File**: `test_full_integration.py::test_cache_hit_l1`

Tests L1 cache for exact message matches:
- First request caches result
- Second identical request hits L1 cache
- Latency <10ms for cache hit

**Verifies**:
- ✓ L1 cache stores responses
- ✓ L1 cache retrieves responses
- ✓ Sub-10ms latency
- ✓ Cache hit metrics tracked

### 3. Semantic Cache Hit (L2)
**File**: `test_full_integration.py::test_semantic_cache_hit_l2`

Tests L2 semantic cache for similar queries:
- Semantically similar messages hit cache
- Uses vector similarity matching
- Latency <100ms for semantic match

**Verifies**:
- ✓ Vector embeddings working
- ✓ Similarity threshold effective
- ✓ Cache returns relevant results
- ✓ Sub-100ms latency

**Requires**: ChromaDB running

### 4. Streaming Response
**File**: `test_full_integration.py::test_streaming_response`

Tests SSE (Server-Sent Events) streaming:
- Progressive chunk delivery
- First token <1s
- Complete response assembly

**Verifies**:
- ✓ SSE format compliance
- ✓ Chunks delivered progressively
- ✓ First token latency target met
- ✓ Complete response matches non-streaming

### 5. A/B Testing Distribution
**File**: `test_full_integration.py::test_ab_testing_distribution`

Tests A/B testing framework:
- DSPy optimized vs manual prompts
- 90/10 distribution (or configured ratio)
- Metrics tracking per variant

**Status**: Placeholder (requires feature flag implementation)

### 6. DSPy Optimization
**File**: `test_full_integration.py::test_dspy_optimization`

Tests DSPy optimized prompts:
- Loads optimized prompts
- Compares accuracy vs baseline
- Verifies token usage reduction

**Status**: Placeholder (requires pre-trained models)

### 7. Error Scenarios

#### 7.1 Cache Unavailable
**File**: `test_full_integration.py::test_error_cache_unavailable`

Tests graceful degradation when cache fails:
- Agent continues to function
- Falls back to direct processing
- No system crash

#### 7.2 Invalid Input
**File**: `test_full_integration.py::test_error_invalid_input`

Tests input validation:
- Empty messages
- Too long messages (>5000 chars)
- Control characters

**Verifies**:
- ✓ Validation catches issues
- ✓ Appropriate error responses
- ✓ No system crashes

#### 7.3 API Timeout
**File**: `test_full_integration.py::test_error_api_timeout`

Tests OpenAI API timeout handling:
- Timeout error caught gracefully
- Appropriate error response
- Retry logic (if implemented)

**Status**: Placeholder (requires mock or very short timeout)

### 8. Performance Benchmarks
**File**: `test_full_integration.py::test_performance_benchmarks_concurrent`

Tests 100 concurrent requests:
- Measures P50, P95, P99 latency
- Tracks cache hit rate
- Calculates cost per request
- Verifies success rate

**Metrics Tracked**:
- Latency percentiles (P50, P95, P99)
- Success rate (target: >90%)
- Cache hit rate (target: >80%)
- Cost savings from caching
- Memory usage

**Performance Targets**:
- P95 latency: <8s
- Success rate: >90%
- Cache hit rate: >80%

### 9. Load Test
**File**: `test_full_integration.py::test_load_sustained_throughput`

Tests sustained load:
- 10 req/s for 1 minute
- No performance degradation
- Memory usage stable
- Cache hit rate improves over time

**Verifies**:
- ✓ System handles sustained load
- ✓ No memory leaks
- ✓ Performance remains stable
- ✓ Cache effectiveness

**Status**: Marked as slow (skip by default)

## Prerequisites

### Infrastructure Requirements

1. **PostgreSQL Database**
   - Running on localhost or remote
   - Test database created
   - Environment: `DATABASE_URL`

2. **Redis Cache**
   - Running on localhost:6379 or remote
   - Environment: `REDIS_URL` (optional, defaults to localhost)

3. **ChromaDB Vector Store**
   - Running on localhost:8000 or remote
   - Environment: `CHROMADB_HOST`, `CHROMADB_PORT`

4. **OpenAI API**
   - Valid API key with credits
   - Environment: `OPENAI_API_KEY_TEST` or `OPENAI_API_KEY`

### Environment Variables

```bash
# Required
export OPENAI_API_KEY_TEST="sk-..."
export DATABASE_URL="postgresql://user:pass@localhost/tria_test"

# Optional (with defaults)
export REDIS_URL="redis://localhost:6379"
export CHROMADB_HOST="localhost"
export CHROMADB_PORT="8000"
```

## Running Tests

### Run All Tests

```bash
# Run all tier 3 tests
pytest tests/tier3_e2e/ -v

# Run with detailed output
pytest tests/tier3_e2e/ -v -s
```

### Run Specific Tests

```bash
# Run full integration test only
pytest tests/tier3_e2e/test_full_integration.py::test_full_request_flow_uncached -v

# Run cache tests only
pytest tests/tier3_e2e/test_full_integration.py::test_cache_hit_l1 -v
pytest tests/tier3_e2e/test_full_integration.py::test_semantic_cache_hit_l2 -v

# Run error handling tests
pytest tests/tier3_e2e/test_full_integration.py -k "error" -v
```

### Run Performance Tests

```bash
# Run all performance tests (including slow)
pytest tests/tier3_e2e/ -v -m slow

# Skip slow tests
pytest tests/tier3_e2e/ -v -m "not slow"

# Run only benchmark tests
pytest tests/tier3_e2e/ -v -m benchmark
```

### Run with Coverage

```bash
# Generate coverage report
pytest tests/tier3_e2e/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

## Test Structure

```
tests/tier3_e2e/
├── __init__.py              # Package initialization, markers
├── conftest.py              # Shared fixtures and configuration
├── README.md                # This file
├── test_full_integration.py # Main integration test suite
└── SUMMARY.md               # Test results summary
```

## Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Uncached request | <20s | <30s |
| L1 cache hit | <10ms | <1000ms |
| L2 cache hit | <100ms | <500ms |
| Streaming first token | <1s | <10s |
| P95 latency (100 concurrent) | <8s | <30s |
| Success rate | >95% | >90% |
| Cache hit rate | >80% | >50% |
| Sustained throughput | 10 req/s | 5 req/s |

## Expected Test Results

### Success Criteria

✓ **All core functionality tests pass** (9/11 tests)
- Full request flow
- Cache hit flows (L1, L2)
- Streaming response
- Error handling
- Performance benchmarks

⊘ **Placeholder tests skipped** (2/11 tests)
- A/B testing (requires feature flags)
- DSPy optimization (requires pre-trained models)

### Performance Benchmarks

Expected results with real infrastructure:

```
📊 Performance Benchmark Results:
  Total requests: 100
  Successful: 100
  Failed: 0
  Success rate: 100.0%
  Total time: ~15.0s

  Latency:
    Mean: 150ms
    P50: 50ms
    P95: 5000ms
    P99: 8000ms

  Cache Performance:
    Overall hit rate: 85.0%
    L1 hit rate: 75.0%
    L2 hit rate: 10.0%
    Cost saved: $0.0250
```

## Troubleshooting

### Common Issues

1. **ChromaDB connection failed**
   ```
   ValueError: Could not connect to tenant default_tenant
   ```
   **Solution**: Ensure ChromaDB is running on the configured host/port

2. **Redis connection failed**
   ```
   ConnectionError: Error connecting to Redis
   ```
   **Solution**: Ensure Redis is running and accessible

3. **OpenAI API rate limit**
   ```
   RateLimitError: Rate limit exceeded
   ```
   **Solution**: Reduce concurrent requests or wait for rate limit reset

4. **Database connection failed**
   ```
   OperationalError: could not connect to server
   ```
   **Solution**: Check DATABASE_URL and ensure PostgreSQL is running

### Performance Issues

If tests are consistently slow:

1. **Check network latency** to external services (OpenAI, Redis, ChromaDB)
2. **Verify cache is working** (should see high hit rates after warmup)
3. **Monitor API rate limits** (may need to reduce concurrency)
4. **Check database performance** (indexes, connection pooling)

## Test Maintenance

### Adding New Tests

1. Add test function to `test_full_integration.py`
2. Use shared fixtures from `conftest.py`
3. Follow naming convention: `test_<category>_<specific_test>`
4. Add docstring with test description and verification points
5. Update this README with test description

### Updating Performance Targets

Edit performance targets in:
- `conftest.py` (performance_targets fixture)
- Test assertions in `test_full_integration.py`
- This README (Performance Targets table)

### Skipping Expensive Tests

Mark expensive tests with `@pytest.mark.slow`:

```python
@pytest.mark.asyncio
@pytest.mark.slow
async def test_expensive_operation():
    ...
```

Then skip with: `pytest tests/tier3_e2e/ -m "not slow"`

## Cost Considerations

### API Cost Estimation

Approximate costs per test run (with OpenAI API):

| Test | API Calls | Estimated Cost |
|------|-----------|----------------|
| Full request flow | 1-2 | $0.002 |
| Cache hit tests | 1-2 | $0.002 |
| Streaming test | 1 | $0.001 |
| Error tests | 3-5 | $0.005 |
| Performance benchmark | 100 | $0.20 |
| Load test (1 min) | 600 | $1.20 |

**Total for full suite**: ~$1.50 per run

### Cost Optimization

- Use `gpt-3.5-turbo` for tests (6x cheaper than GPT-4)
- Cache warm tests run cheaper after first run
- Skip slow tests during development
- Use test API key with rate limits

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Tier 3 E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s

      chromadb:
        image: chromadb/chroma:latest
        options: >-
          --health-cmd "curl -f http://localhost:8000/api/v1/heartbeat"
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tier 3 tests (fast only)
        env:
          OPENAI_API_KEY_TEST: ${{ secrets.OPENAI_API_KEY_TEST }}
          DATABASE_URL: postgresql://postgres:postgres@localhost/postgres
          REDIS_URL: redis://localhost:6379
          CHROMADB_HOST: localhost
          CHROMADB_PORT: 8000
        run: |
          pytest tests/tier3_e2e/ -v -m "not slow" --cov=src

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Support

For issues or questions:
1. Check this README
2. Review test output for error details
3. Check logs in `logs/` directory
4. Verify all prerequisites are running
5. Consult TRIA documentation

---

**Last Updated**: 2025-11-08
**Test Suite Version**: 1.0.0
**Status**: Production Ready
