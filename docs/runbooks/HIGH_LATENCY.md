# Runbook: High Latency

**Alert**: `HighP95Latency` or `HighP99Latency`
**Severity**: Critical
**Component**: API

## Symptoms

- P95 latency > 5 seconds
- P99 latency > 10 seconds
- User complaints about slow responses

## Immediate Actions

### Step 1: Check System Health (2 min)

```bash
# Check if server is healthy
curl http://localhost:8003/health

# Check metrics endpoint
curl http://localhost:8003/api/v1/metrics/cache
```

**Expected**: All services should be "healthy"

### Step 2: Check Cache Hit Rate (1 min)

```bash
# Get cache metrics
curl http://localhost:8003/api/v1/metrics/cache | jq '.redis_chat_cache'
```

**Expected**: Hit rate > 50%

**If hit rate < 50%**:
- Cache may be cleared → Will improve as cache warms up
- Redis may be down → Check Redis status

### Step 3: Check OpenAI API Status (1 min)

```bash
# Check if OpenAI is experiencing issues
curl https://status.openai.com/api/v2/status.json
```

**If OpenAI is degraded**:
- Wait for resolution (external issue)
- Monitor status page
- Consider enabling fallback responses

### Step 4: Check Database Connection Pool (2 min)

```bash
# SSH into server
ssh -i ~/.ssh/your-key.pem ubuntu@your-server-ip

# Check PostgreSQL connections
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
  SELECT count(*) as active_connections,
         max_connections::int
  FROM pg_stat_activity,
       (SELECT setting::int as max_connections FROM pg_settings WHERE name='max_connections') s;
"
```

**Expected**: active_connections < 80% of max_connections

**If pool exhausted (> 90%)**:
- Connection leak detected
- Restart backend service
- Investigate code for connection leaks

### Step 5: Check System Resources (2 min)

```bash
# Check CPU, memory, disk
docker stats tria_aibpo_backend

# Check disk space
df -h
```

**If CPU > 80%**:
- Scale horizontally (add more instances)
- Investigate CPU-intensive queries

**If memory > 90%**:
- Memory leak suspected
- Restart backend service
- Review memory profiling

## Investigation

### Check Recent Logs

```bash
# View recent errors
docker logs tria_aibpo_backend --tail 100 | grep ERROR

# View slow queries
docker logs tria_aibpo_backend --tail 100 | grep "took.*ms" | sort -n
```

### Run Performance Benchmark

```bash
# From project root
python tests/performance/test_comprehensive_performance.py
```

Review output for:
- Which query types are slow?
- Is cache working?
- Any errors?

## Resolution

### Quick Fixes

1. **Restart Backend** (if memory/connection leak):
   ```bash
   docker-compose restart backend
   ```

2. **Clear and Warm Cache**:
   ```bash
   # Clear Redis cache
   docker exec -it tria_aibpo_redis redis-cli FLUSHDB

   # Warm up with common queries
   python scripts/warm_cache.py
   ```

3. **Scale Horizontally** (if high load):
   ```bash
   docker-compose up -d --scale backend=3
   ```

### Long-term Fixes

1. **Optimize Slow Queries**:
   - Review database query plans
   - Add indexes if needed
   - Optimize complex joins

2. **Improve Caching**:
   - Increase cache TTL for static content
   - Add more cacheable endpoints
   - Implement cache warming

3. **Parallelize Operations**:
   - Run RAG + intent classification in parallel
   - Move validation to background jobs

## Escalation

**Escalate to engineering if**:
- Latency remains high after 30 minutes
- No obvious cause found
- System resources normal but latency high

**Contact**: #engineering-oncall on Slack

## Post-Incident

1. Document root cause
2. Update this runbook if new issues discovered
3. Create follow-up tasks for long-term fixes
4. Update alerting thresholds if needed
