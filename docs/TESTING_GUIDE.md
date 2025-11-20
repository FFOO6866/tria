# Production Testing Guide
## Step-by-Step Verification Process

This guide walks you through testing EVERYTHING to get an honest assessment of production readiness.

**Time Required**: 2-3 hours for complete verification

---

## ⚠️ Prerequisites

Before starting, ensure you have:

- [ ] Python 3.11+ installed
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file configured with all required variables
- [ ] PostgreSQL running (or Docker containers)
- [ ] Redis running (or Docker containers)
- [ ] OpenAI API key configured

---

## Phase 1: Pre-Flight Checks (15 minutes)

### Step 1.1: Run Automated Verification

```bash
# This checks file structure, syntax, and basic config
python scripts/verify_production_readiness.py
```

**Expected Output**:
- All files exist ✅
- No Python syntax errors ✅
- Environment variables configured ✅

**If Failed**:
- Fix missing files
- Fix syntax errors
- Set missing environment variables
- Re-run until all pass

### Step 1.2: Start Docker Services

```bash
# Start database and Redis
docker-compose up -d postgres redis

# Verify they're running
docker-compose ps

# Should show:
# tria_aibpo_postgres    Up (healthy)
# tria_aibpo_redis       Up (healthy)
```

**If Failed**:
```bash
# Check logs
docker-compose logs postgres
docker-compose logs redis

# Common fixes:
# - Port already in use: Stop conflicting service
# - Permission denied: Run with sudo or fix permissions
# - Out of disk: Clean up with docker system prune
```

### Step 1.3: Start Application Server

```bash
# Start in one terminal
python src/enhanced_api.py

# Should see:
# [OK] Environment configuration validated
# [OK] DataFlow initialized
# [OK] Redis chat response cache initialized
# [OK] Enhanced Platform ready!
```

**If Failed**:
- Check error messages
- Common issues:
  - `OPENAI_API_KEY not set`: Check .env file
  - `Cannot connect to database`: Check DATABASE_URL
  - `Redis connection failed`: Check REDIS_HOST
  - `Import errors`: Check dependencies installed

### Step 1.4: Quick Health Check

```bash
# In another terminal
curl http://localhost:8003/health

# Should return:
# {"status": "healthy", ...}
```

**✅ Checkpoint**: Server is running and healthy

---

## Phase 2: Cache Verification (10 minutes)

### Step 2.1: Test Cache Integration

```bash
# Make first request (cache miss)
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","outlet_id":1,"user_id":"test1","session_id":"test1"}' \
  | jq .

# Note the response time in logs

# Make same request again (should be cache hit)
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","outlet_id":1,"user_id":"test1","session_id":"test1"}' \
  | jq '.metadata.cache_hit'

# Should return: true
```

**Expected**:
- First request: 2-5 seconds
- Second request: < 500ms (cache hit)
- `metadata.cache_hit: true`

**If Cache Not Working**:
```bash
# Check Redis
docker exec -it tria_aibpo_redis redis-cli

# In Redis CLI:
KEYS "*"
# Should show cache keys

# Check cache metrics
curl http://localhost:8003/api/v1/metrics/cache | jq .
```

### Step 2.2: Verify Cache Metrics

```bash
curl http://localhost:8003/api/v1/metrics/cache | jq '.redis_chat_cache'

# Should show:
# {
#   "total_requests": X,
#   "cache_hits": Y,
#   "cache_misses": Z,
#   "hit_rate_percent": > 0
# }
```

**✅ Checkpoint**: Cache is working and hit rate > 0%

---

## Phase 3: Performance Benchmarks (30 minutes)

### Step 3.1: Run Performance Test Suite

```bash
# This will take 10-15 minutes
python tests/performance/test_comprehensive_performance.py
```

**Expected Output**:
```
PERFORMANCE BENCHMARK REPORT
============================
OVERALL RESULTS:
  Successful: X/X (100%)

LATENCY METRICS:
  Mean: XXXms
  P95: XXXms      ← Should be < 5000ms
  P99: XXXms

CACHE PERFORMANCE:
  Hit Rate: XX%   ← Should increase to > 50% by run 3
  Cache Speedup: Xx faster

COST ANALYSIS:
  Cost Saved: $X.XX
```

**Record Results**:
```bash
# Results are saved automatically
cat benchmark_results_*.json | jq '.analysis.latency'
```

**Pass Criteria**:
- ✅ P95 latency < 5000ms
- ✅ Mean latency < 3000ms
- ✅ Cache hit rate > 30% (after warm-up)
- ✅ No crashes or errors

**If Failed**:
- Latency > 5000ms: Check OpenAI API status, optimize queries
- Cache hit rate = 0%: Cache not working, debug Step 2
- Crashes: Check logs for errors

### Step 3.2: Analyze Results

```bash
# Extract key metrics
python -c "
import json
with open('benchmark_results_*.json') as f:
    data = json.load(f)
    print(f\"Mean Latency: {data['analysis']['latency']['mean_ms']:.0f}ms\")
    print(f\"P95 Latency: {data['analysis']['latency']['p95_ms']:.0f}ms\")
    print(f\"Cache Hit Rate: {data['analysis']['cache']['hit_rate']:.1f}%\")
    print(f\"Cost Saved: ${data['analysis']['cost']['cost_saved_usd']:.2f}\")
"
```

**✅ Checkpoint**: Performance meets targets

---

## Phase 4: Load Testing (30 minutes)

### Step 4.1: Run Basic Load Test (10 users)

```bash
python tests/load/test_concurrent_load.py
```

**This will run 3 load tests**:
1. 10 concurrent users (5 queries each)
2. 50 concurrent users (3 queries each)
3. 100 concurrent users (2 queries each)

**Total time**: ~20-30 minutes

**Expected Output**:
```
TEST 1: BASIC LOAD (10 Concurrent Users)
========================================
  Total: 50 requests
  Succeeded: 50 (100%)
  P95: XXXms
  Memory Growth: XX MB

  ✅ PASS: Success rate 100% ≥ 99%
  ✅ PASS: P95 latency XXXms ≤ 5000ms
  ✅ PASS: Memory growth XX MB ≤ 200MB

  🎉 VERDICT: TEST PASSED
```

**Pass Criteria**:
- ✅ 10 users: 99% success rate
- ✅ 50 users: 95% success rate
- ✅ 100 users: 90% success rate
- ✅ Memory growth < 200MB
- ✅ No server crashes

**If Failed**:
- Success rate < 99%: Check error logs
- Server crashes: Check memory/CPU limits
- Timeouts: Increase timeout or optimize
- Connection errors: Check connection pool size

**Record Results**:
```bash
cat load_test_results_*.json | jq '.basic_load_10_users'
```

**✅ Checkpoint**: System handles concurrent load

---

## Phase 5: Security Testing (20 minutes)

### Step 5.1: Run Security Test Suite

```bash
python tests/security/test_owasp_top_10.py
```

**Expected Output**:
```
SECURITY TEST SUMMARY
====================
Total Tests: 12
Passed: 12
Failed: 0

🎉 ALL SECURITY TESTS PASSED!
```

**Tests Include**:
1. SQL Injection protection
2. XSS protection
3. Authentication (if implemented)
4. Sensitive data exposure
5. Rate limiting
6. Command injection
7. File upload safety
8. CSRF protection
9. Security headers
10. Error handling
11. Prompt injection (AI-specific)
12. Session security

**Pass Criteria**:
- ✅ All 12 tests pass
- ⚠️  Warnings acceptable (auth not implemented yet)
- ❌ Any failures must be fixed

**If Failed**:
- Note which test failed
- Review error message
- Fix vulnerability
- Re-run until all pass

**✅ Checkpoint**: No critical security vulnerabilities

---

## Phase 6: Monitoring Verification (20 minutes)

### Step 6.1: Start Monitoring Stack

```bash
# Start Prometheus, Grafana, Alertmanager
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Wait for startup
sleep 30

# Check status
docker-compose -f monitoring/docker-compose.monitoring.yml ps

# Should show all containers "Up"
```

### Step 6.2: Verify Prometheus

```bash
# Open in browser: http://localhost:9090

# Or check via API:
curl http://localhost:9090/api/v1/targets

# Should show targets:
# - prometheus (up)
# - tria-backend (up or down if not exposing /metrics yet)
# - postgresql (up)
# - redis (up)
```

**If Prometheus fails to start**:
```bash
# Check logs
docker logs tria_prometheus

# Common issues:
# - YAML syntax error: Fix prometheus.yml
# - Port in use: Stop conflicting service
```

### Step 6.3: Verify Grafana

```bash
# Open in browser: http://localhost:3001
# Login: admin / admin

# Should see:
# - Grafana home page
# - Data source: Prometheus (configured)
```

### Step 6.4: Verify Alertmanager

```bash
# Open in browser: http://localhost:9093

# Should see:
# - Alertmanager UI
# - No active alerts (if system healthy)
```

**✅ Checkpoint**: Monitoring stack is running

---

## Phase 7: Integration Testing (30 minutes)

### Step 7.1: Apply Integration Patches

```bash
# Apply audit logging integration
# Follow instructions in patches/001_integrate_audit_logging.patch

# Apply Prometheus metrics
# Follow instructions in patches/002_add_prometheus_metrics.patch
```

### Step 7.2: Restart Server with Integrations

```bash
# Stop server (Ctrl+C in server terminal)

# Restart
python src/enhanced_api.py

# Verify new endpoints
curl http://localhost:8003/metrics
# Should return Prometheus metrics

# Make a request to generate audit logs
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Test audit","outlet_id":1,"user_id":"test","session_id":"test"}'

# Check audit log
cat logs/audit.log | jq .
```

**Expected**:
- `/metrics` endpoint returns Prometheus format metrics
- `logs/audit.log` contains JSON audit entries

**✅ Checkpoint**: All integrations working

---

## Phase 8: End-to-End Testing (20 minutes)

### Step 8.1: Test Complete User Flow

```bash
# 1. Greeting
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","outlet_id":1,"user_id":"e2e_test","session_id":"e2e_1"}' \
  | jq '.response'

# 2. Policy question
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"What is your return policy?","outlet_id":1,"user_id":"e2e_test","session_id":"e2e_1"}' \
  | jq '.response'

# 3. Product inquiry
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Do you have chicken burgers?","outlet_id":1,"user_id":"e2e_test","session_id":"e2e_1"}' \
  | jq '.response'

# 4. Order (if products exist)
# curl -X POST http://localhost:8003/api/chatbot \
#   -H "Content-Type: application/json" \
#   -d '{"message":"I want to order 5 burgers","outlet_id":1,"user_id":"e2e_test","session_id":"e2e_1"}' \
#   | jq '.'
```

**Verify**:
- ✅ All requests succeed (200 OK)
- ✅ Responses are relevant
- ✅ Cache works on repeated queries
- ✅ Conversation context maintained
- ✅ Audit logs created

### Step 8.2: Verify Streaming Endpoint

```bash
curl -X POST http://localhost:8003/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello streaming","outlet_id":1,"user_id":"stream_test","session_id":"stream_1"}'

# Should see Server-Sent Events format
```

**✅ Checkpoint**: All endpoints working end-to-end

---

## Phase 9: Results Documentation (10 minutes)

### Step 9.1: Collect All Results

```bash
# Create results directory
mkdir -p test_results

# Copy all result files
cp benchmark_results_*.json test_results/
cp load_test_results_*.json test_results/
cp verification_results.json test_results/

# Create summary report
cat > test_results/summary.md << 'EOF'
# Production Testing Results

**Date**: $(date)
**Tester**: Your Name

## Test Summary

### Performance Benchmarks
- Mean Latency: XXXms
- P95 Latency: XXXms
- Cache Hit Rate: XX%
- **Status**: PASS/FAIL

### Load Testing
- 10 concurrent users: XX% success
- 50 concurrent users: XX% success
- 100 concurrent users: XX% success
- **Status**: PASS/FAIL

### Security Testing
- Tests Passed: X/12
- **Status**: PASS/FAIL

### Monitoring
- Prometheus: UP/DOWN
- Grafana: UP/DOWN
- Alertmanager: UP/DOWN
- **Status**: PASS/FAIL

## Overall Verdict

**Production Ready**: YES/NO

**Issues Found**:
- (List any issues)

**Recommendations**:
- (List recommendations)
EOF
```

### Step 9.2: Generate Honest Assessment

Based on your test results, honestly answer:

**Performance** (tests/performance results):
- [ ] Mean latency < 3 seconds
- [ ] P95 latency < 5 seconds
- [ ] Cache hit rate > 50% (after warm-up)
- [ ] No crashes during benchmarks

**Load Testing** (tests/load results):
- [ ] 10 users: 99% success
- [ ] 50 users: 95% success
- [ ] Memory growth < 200MB
- [ ] No server crashes

**Security** (tests/security results):
- [ ] All OWASP tests pass
- [ ] No critical vulnerabilities
- [ ] Prompt injection protected

**Monitoring**:
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards accessible
- [ ] Alerts configured

**Final Score**: (Count checks passed / total checks) × 100

---

## Honest Production Readiness Assessment

### If ALL checks pass (100%):
**Status**: ✅ **PRODUCTION READY**
- Deploy to staging immediately
- User acceptance testing
- Production deployment within 1 week

### If 90-99% pass:
**Status**: ⚠️ **NEARLY READY**
- Fix remaining issues
- Re-run failed tests
- Production deployment within 2 weeks

### If 75-89% pass:
**Status**: ⚠️ **NEEDS WORK**
- Identify and fix critical issues
- Re-run all tests
- Production deployment within 3-4 weeks

### If < 75% pass:
**Status**: ❌ **NOT READY**
- Significant issues found
- Needs debugging and optimization
- Re-test after fixes
- Production deployment timeline: TBD

---

## Next Steps After Testing

### If Production Ready:
1. Deploy to staging environment
2. Run same tests on staging
3. User acceptance testing (10-20 users)
4. Production deployment preparation
5. Go-live with monitoring

### If Issues Found:
1. Document all issues in GitHub Issues
2. Prioritize by severity (P0, P1, P2)
3. Fix P0 issues first
4. Re-run verification
5. Repeat until production ready

---

## Support

**If stuck**:
1. Check logs: `docker-compose logs -f backend`
2. Review error messages
3. Search documentation
4. Open GitHub issue with:
   - Which test failed
   - Error message
   - Logs
   - Environment details

---

**Testing completed**: ____________________
**Production ready**: YES / NO
**Deployment date**: ____________________
