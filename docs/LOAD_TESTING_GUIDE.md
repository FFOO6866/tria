# Load Testing Guide

## Overview

Comprehensive load testing suite to verify system performance under concurrent load and validate the expected 5x performance improvement from Redis caching.

## Why Load Testing is Critical

From the production readiness assessment, load testing was identified as a **P0 blocker**:

- **Current Status**: 0/5 load tests completed (completely untested)
- **Known Risk**: System will crash at 10-20 concurrent users (no request queueing)
- **Production Requirement**: Must handle at least 50 concurrent users
- **Cache Validation**: Need to verify 80% cache hit rate under realistic load

## Test Scenarios

The load testing script (`scripts/load_test_chat_api.py`) includes 5 comprehensive scenarios:

### 1. Baseline: Single User
**Purpose**: Establish best-case performance metrics

- **Concurrent users**: 1
- **Requests**: 5
- **Expected**: < 3s average (after cache warming)
- **Validates**: Basic functionality, cache hit/miss behavior

### 2. Light Load: 5 Concurrent Users
**Purpose**: Test typical low-traffic scenario

- **Concurrent users**: 5
- **Requests per user**: 4 (20 total)
- **Expected**: < 4s average
- **Validates**: Connection pooling, cache sharing

### 3. Medium Load: 10 Concurrent Users
**Purpose**: Test normal business hours traffic

- **Concurrent users**: 10
- **Requests per user**: 3 (30 total)
- **Expected**: < 5s average
- **Validates**: Request queueing, resource management

### 4. Heavy Load: 20 Concurrent Users
**Purpose**: Test peak traffic scenario

- **Concurrent users**: 20
- **Requests per user**: 3 (60 total)
- **Expected**: < 10s average
- **Validates**: System stability under stress

### 5. Stress Test: 50 Concurrent Users
**Purpose**: Test graceful degradation

- **Concurrent users**: 50
- **Requests per user**: 2 (100 total)
- **Expected**: Should not crash, but may timeout
- **Validates**: Error handling, failover mechanisms

## Running Load Tests

### Prerequisites

1. **Start the API server**:
   ```bash
   uvicorn src.enhanced_api:app --host 127.0.0.1 --port 8003
   ```

2. **Verify server is running**:
   ```bash
   curl http://localhost:8003/health
   ```

3. **Optional: Start Redis for full cache testing**:
   ```bash
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

### Execute Load Tests

```bash
python scripts/load_test_chat_api.py
```

### Expected Output

```
======================================================================
 Chat API Load Testing Suite
======================================================================

Checking server health at http://localhost:8003...
✅ Server is healthy

======================================================================
Running: Baseline: Single User
======================================================================
Concurrent users: 1
Requests per user: 5
Total requests: 5

Progress: 5/5 requests completed

======================================================================
Results: Baseline: Single User
======================================================================

Overall Performance:
  Total requests: 5
  Successful: 5 (100.0%)
  Failed: 0
  Total time: 8.45s
  Throughput: 0.59 req/s

Cache Performance:
  Cache hits: 3
  Hit rate: 60.0%

Latency Metrics:
  Average: 1690ms
  Median: 1200ms
  P95: 3000ms
  P99: 3000ms
  Min: 98ms
  Max: 3000ms

  Performance Grade: EXCELLENT ✅

[... additional test scenarios ...]

======================================================================
 Load Testing Summary
======================================================================
✅ PASS - Baseline: Single User
      Success rate: 100.0%
      Avg latency: 1690ms
      Cache hit rate: 60.0%

✅ PASS - Light Load: 5 Concurrent Users
      Success rate: 100.0%
      Avg latency: 2340ms
      Cache hit rate: 75.0%

✅ PASS - Medium Load: 10 Concurrent Users
      Success rate: 100.0%
      Avg latency: 3450ms
      Cache hit rate: 80.0%

✅ PASS - Heavy Load: 20 Concurrent Users
      Success rate: 96.7%
      Avg latency: 6780ms
      Cache hit rate: 85.0%

⚠️  WARNING - Stress Test: 50 Concurrent Users
      Success rate: 88.0%
      Avg latency: 12340ms
      Cache hit rate: 90.0%

======================================================================
✅ All critical load tests PASSED!

Average cache hit rate: 78.0%

System is ready for production deployment at tested load levels.

Detailed report saved to: data/load_test_results.json
```

## Metrics Collected

### Performance Metrics

- **Success Rate**: % of requests that completed successfully
- **Average Latency**: Mean response time across all requests
- **Median Latency**: 50th percentile response time
- **P95/P99 Latency**: 95th/99th percentile response times
- **Min/Max Latency**: Fastest and slowest response times
- **Throughput**: Requests per second

### Cache Metrics

- **Cache Hit Rate**: % of requests served from cache
- **Cached Responses**: Total number of cache hits
- **Cache Efficiency**: Cost savings from caching

### Error Metrics

- **Failed Requests**: Number of failed requests
- **Error Types**: Breakdown of error categories (timeout, HTTP errors, etc.)

## Performance Targets

### Success Criteria

| Scenario | Target Success Rate | Target Avg Latency | Target Cache Hit Rate |
|----------|-------------------|-------------------|---------------------|
| Single User | > 95% | < 3s | > 50% |
| 5 Concurrent | > 95% | < 4s | > 70% |
| 10 Concurrent | > 95% | < 5s | > 75% |
| 20 Concurrent | > 90% | < 10s | > 80% |
| 50 Concurrent | > 80% | < 30s | > 85% |

### Performance Grades

- **EXCELLENT** (✅): Average latency < 3s
- **GOOD** (✅): Average latency < 5s
- **ACCEPTABLE** (⚠️): Average latency < 10s
- **POOR** (❌): Average latency > 10s

## Analyzing Results

### Detailed JSON Report

Load test results are saved to `data/load_test_results.json`:

```json
{
  "timestamp": "2025-11-13T11:45:00",
  "test_results": [
    {
      "scenario": "Baseline: Single User",
      "total_requests": 5,
      "successful": 5,
      "failed": 0,
      "success_rate": 1.0,
      "cached_responses": 3,
      "cache_hit_rate": 0.6,
      "avg_latency_ms": 1690,
      "median_latency_ms": 1200,
      "p95_latency_ms": 3000,
      "p99_latency_ms": 3000
    }
  ],
  "summary": {
    "total_scenarios": 5,
    "scenarios_passed": 4,
    "average_cache_hit_rate": 0.78
  }
}
```

### Interpreting Results

#### 1. Success Rate Analysis

- **100%**: System is stable ✅
- **95-99%**: Acceptable, investigate failures ⚠️
- **< 95%**: Critical issues, system not production-ready ❌

#### 2. Latency Analysis

**Without Caching** (Expected):
- Average: ~14.6s
- P95: ~20s
- Unacceptable for production

**With Caching** (Target):
- Average: ~3s (5x improvement)
- P95: ~5s
- Acceptable for MVP launch

#### 3. Cache Hit Rate Analysis

- **< 50%**: Cache configuration issues
- **50-70%**: Good, but can be improved
- **70-85%**: Excellent ✅
- **> 85%**: Outstanding (may indicate limited query diversity)

## Common Issues and Solutions

### Issue: Low Cache Hit Rate (< 50%)

**Symptoms**:
- Most requests show `cached: false`
- Average latency remains high (~10s+)
- Cost savings minimal

**Root Causes**:
1. Cache not initialized properly
2. TTL too short (cache expires before reuse)
3. Conversation context too specific (every context is unique)
4. Test queries too diverse

**Solutions**:

```python
# Solution 1: Verify cache is initialized
# Check API startup logs for:
# [OK] Redis chat response cache initialized (backend: redis)

# Solution 2: Increase TTL for stable data
# Edit src/cache/chat_response_cache.py
chat_cache = ChatResponseCache(
    default_ttl=3600,  # 1 hour (was 30 min)
    policy_ttl=86400*7  # 7 days (was 24 hours)
)

# Solution 3: Reduce context sensitivity
# Edit src/cache/chat_response_cache.py line 150
recent_messages = conversation_history[-1:]  # Only last 1 (was 3)

# Solution 4: Use more repetitive queries in tests
queries = [
    "What is your refund policy?",  # Repeat same queries
    "What is your refund policy?",
    "What is your refund policy?"
]
```

### Issue: High Failure Rate (> 5%)

**Symptoms**:
- Many requests fail with timeout or connection errors
- Success rate < 95%
- Error logs show connection pool exhaustion

**Root Causes**:
1. Database connection pool too small
2. Redis connection pool exhausted
3. Too many concurrent GPT-4 API calls
4. Memory exhaustion

**Solutions**:

```python
# Solution 1: Increase database pool size
# Edit src/database.py
_engine = create_engine(
    database_url,
    pool_size=20,  # Increase from 10
    max_overflow=40,  # Increase from 20
    pool_pre_ping=True
)

# Solution 2: Increase Redis pool size
# Edit src/cache/redis_cache.py
self.connection_pool = ConnectionPool(
    host=host,
    port=port,
    max_connections=100,  # Increase from 50
    socket_timeout=10  # Increase from 5
)

# Solution 3: Implement request queueing
# Add to src/enhanced_api.py
from asyncio import Semaphore

# Limit concurrent GPT-4 calls
openai_semaphore = Semaphore(10)  # Max 10 concurrent

async def process_with_limit():
    async with openai_semaphore:
        return await agent.handle_message(message)
```

### Issue: Performance Degrades with Load

**Symptoms**:
- Single user: 2s average ✅
- 10 concurrent: 15s average ❌
- 20 concurrent: 30s+ average ❌

**Root Cause**: Sequential processing, no request queueing

**Solution**: Implement proper async handling

```python
# Add request queue to src/enhanced_api.py
from asyncio import Queue, create_task

request_queue = Queue(maxsize=100)

async def queue_processor():
    """Process requests from queue"""
    while True:
        request = await request_queue.get()
        try:
            result = await process_request(request)
            request.set_result(result)
        except Exception as e:
            request.set_exception(e)
        finally:
            request_queue.task_done()

# Start queue processor at startup
@app.on_event("startup")
async def startup():
    for _ in range(10):  # 10 worker tasks
        create_task(queue_processor())
```

## Continuous Load Testing

### Automated Testing in CI/CD

```yaml
# .github/workflows/load-test.yml
name: Load Testing

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Run load tests
        run: python scripts/load_test_chat_api.py

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: load-test-results
          path: data/load_test_results.json
```

### Monitoring in Production

**Key Metrics to Track**:

1. **Response Time Distribution**
   - Alert if P95 > 10s
   - Alert if P99 > 30s

2. **Error Rate**
   - Alert if error rate > 1%
   - Alert if 5xx errors > 0.1%

3. **Cache Performance**
   - Alert if cache hit rate < 50%
   - Alert if cache becomes unhealthy

4. **Throughput**
   - Alert if requests/sec drops suddenly
   - Alert if queue depth > 100

## Next Steps After Load Testing

### If Tests Pass (Success Rate > 95%):
1. ✅ Document baseline performance metrics
2. ✅ Set up monitoring alerts based on test results
3. ✅ Proceed to production deployment (MVP launch)
4. ⏳ Monitor real-world performance
5. ⏳ Iterate based on production data

### If Tests Fail (Success Rate < 95%):
1. ❌ Analyze failure patterns in `data/load_test_results.json`
2. ❌ Implement fixes (connection pooling, request queueing, etc.)
3. ❌ Re-run load tests to verify fixes
4. ❌ Repeat until success rate > 95%
5. ❌ Do NOT proceed to production until tests pass

## Cost Estimate Under Load

### Without Caching:
```
Scenario: 20 concurrent users
- Requests: 60 total
- Cost per request: $0.06 (3.5 GPT-4 calls)
- Total cost: $3.60 per test run
- Monthly (1K queries/day): $4,200
```

### With Caching (80% hit rate):
```
Scenario: 20 concurrent users
- Requests: 60 total
- Cache hits: 48 (80%)
- Cache misses: 12 (20%)
- Cost: 12 × $0.06 = $0.72 per test run
- Savings: $2.88 per test run (80% reduction)
- Monthly (1K queries/day): $840
```

## Conclusion

Load testing is essential to:
1. Verify system stability under concurrent load
2. Validate cache performance improvements
3. Identify bottlenecks before production
4. Establish baseline metrics for monitoring

**Success Criteria**:
- ✅ All scenarios achieve > 95% success rate
- ✅ Average cache hit rate > 70%
- ✅ Average latency < 5s for < 20 concurrent users
- ✅ System handles 20 concurrent users without crashing

Once load tests pass, the system is ready for MVP production deployment with confidence.

---

**Last Updated**: 2025-11-13
**Status**: Load testing script implemented, ready for execution
**Next**: Run tests and analyze results
