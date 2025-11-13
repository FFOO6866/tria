# Operational Runbook
**Tria AI-BPO Customer Service Chatbot**

**Version**: 1.0
**Last Updated**: 2025-11-14
**On-Call Contact**: [Your team contact info]
**Escalation Path**: [Your escalation contacts]

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Health Checks](#health-checks)
3. [Common Issues & Solutions](#common-issues--solutions)
4. [Alert Response Procedures](#alert-response-procedures)
5. [Deployment & Rollback](#deployment--rollback)
6. [Performance Troubleshooting](#performance-troubleshooting)
7. [Security Incidents](#security-incidents)
8. [Escalation Procedures](#escalation-procedures)
9. [Useful Commands](#useful-commands)
10. [Contact Information](#contact-information)

---

## System Overview

### Architecture Components

```
User → Nginx (port 80) → FastAPI Backend (port 8003)
                              ↓
         ┌──────────────────────┼──────────────────────┐
         ↓                      ↓                      ↓
    PostgreSQL            Redis Cache          ChromaDB
    (port 5433)           (port 6379)          (in-memory)
         ↓                      ↓                      ↓
    [Orders, Products]    [Sessions, Cache]   [Policy KB]

External APIs:
- OpenAI GPT-4 (chat completions, embeddings)
- Xero API (accounting, invoicing)
```

### Key Metrics

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Response Time (P95) | <5s | 5-10s | >10s |
| Error Rate | <1% | 1-5% | >5% |
| Cache Hit Rate | >60% | 40-60% | <40% |
| Memory Usage | <1.5GB | 1.5-1.9GB | >1.9GB |
| Disk Usage | <70% | 70-90% | >90% |
| CPU Usage | <60% | 60-80% | >80% |
| Database Connections | <20 | 20-28 | >28 |

### Service Endpoints

- **API Base**: `http://YOUR_IP:8003`
- **Health Check**: `GET /health`
- **Chat API**: `POST /api/chatbot`
- **Metrics** (if configured): `GET /metrics`

---

## Health Checks

### Quick Health Check

```bash
# Check all services
curl http://localhost:8003/health | jq .

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-11-14T...",
  "version": "2.0.0",
  "database": "connected",
  "redis": "connected",
  "chromadb": "connected",
  "circuit_breakers": {
    "xero": "closed",
    "openai": "closed",
    "database": "closed"
  }
}
```

### Service-Specific Health Checks

**Docker Containers**:
```bash
# Check all container status
docker ps

# Expected: 3-5 containers running
# - tria_aibpo_postgres
# - tria_aibpo_redis
# - tria_aibpo_backend
# - tria_aibpo_frontend (optional)
# - tria_aibpo_nginx (optional)

# Check container logs
docker logs tria_aibpo_backend --tail 50
docker logs tria_aibpo_postgres --tail 50
docker logs tria_aibpo_redis --tail 50
```

**PostgreSQL**:
```bash
# Check database connectivity
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "SELECT 1;"

# Check database size
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname))
FROM pg_database
WHERE datname = 'tria_aibpo';
"

# Check active connections
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';
"
```

**Redis**:
```bash
# Check Redis connectivity
docker exec -it tria_aibpo_redis redis-cli -a YOUR_REDIS_PASSWORD ping
# Expected: PONG

# Check Redis memory usage
docker exec -it tria_aibpo_redis redis-cli -a YOUR_REDIS_PASSWORD INFO memory | grep used_memory_human

# Check cache keys
docker exec -it tria_aibpo_redis redis-cli -a YOUR_REDIS_PASSWORD DBSIZE
```

**API Backend**:
```bash
# Check if API is responding
curl http://localhost:8003/health

# Check API logs
docker logs tria_aibpo_backend --tail 100 --follow

# Check for errors in last hour
docker logs tria_aibpo_backend --since 1h 2>&1 | grep -i "error"
```

---

## Common Issues & Solutions

### Issue 1: API Returns HTTP 500

**Symptoms**:
- `/health` endpoint returns 500
- User requests fail with "Internal Server Error"
- Logs show Python exceptions

**Diagnosis**:
```bash
# Check backend logs
docker logs tria_aibpo_backend --tail 100

# Look for:
# - Python tracebacks
# - "Failed to initialize"
# - "Connection refused"
# - "Module not found"
```

**Common Causes & Solutions**:

**A. Database Connection Failed**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# If not running, start it:
docker-compose up -d postgres

# Check database logs
docker logs tria_aibpo_postgres --tail 50

# Verify DATABASE_URL in .env file:
cat .env | grep DATABASE_URL
```

**B. Redis Connection Failed**:
```bash
# Check if Redis is running
docker ps | grep redis

# If not running:
docker-compose up -d redis

# Test connection manually:
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD ping
```

**C. Missing Environment Variables**:
```bash
# Check if .env file exists
ls -la .env

# Verify required variables are set:
cat .env | grep -E "OPENAI_API_KEY|DATABASE_URL|TAX_RATE"

# If missing, copy from example:
cp .env.example .env
# Then edit .env with proper values
nano .env
```

**D. Python Dependencies Missing**:
```bash
# Rebuild container with fresh dependencies
docker-compose build --no-cache backend
docker-compose up -d backend
```

**Resolution**: Restart backend after fixing root cause
```bash
docker-compose restart backend

# Verify fix:
curl http://localhost:8003/health
```

---

### Issue 2: Slow Response Times (>10s)

**Symptoms**:
- Users report slow chatbot responses
- P95 latency >10 seconds
- Timeout errors

**Diagnosis**:
```bash
# Check current cache hit rate
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD INFO stats | grep keyspace_hits

# Check memory usage
docker stats tria_aibpo_backend --no-stream

# Check for slow queries in database
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT pid, now() - query_start as duration, state, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC
LIMIT 5;
"
```

**Common Causes & Solutions**:

**A. Low Cache Hit Rate (<40%)**:
```bash
# Check cache statistics
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD INFO stats

# Check cache keys
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD KEYS "*" | wc -l

# Solution: Clear and warm cache
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD FLUSHDB
# Then restart backend to rebuild cache
docker-compose restart backend
```

**B. OpenAI API Slow/Rate Limited**:
```bash
# Check for rate limit errors in logs
docker logs tria_aibpo_backend 2>&1 | grep -i "rate.*limit"

# Check OpenAI API status:
curl https://status.openai.com/

# Solution: Implement request queuing or upgrade OpenAI tier
```

**C. Database Connection Pool Exhausted**:
```bash
# Check active connections
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
"

# If >28 connections (near pool limit):
# Solution: Restart backend to reset pool
docker-compose restart backend

# Or increase pool size in .env:
DB_POOL_SIZE=15  # Default is 10
DB_MAX_OVERFLOW=30  # Default is 20
```

**D. ChromaDB Index Too Large**:
```bash
# Check ChromaDB data size
du -sh data/chromadb_cache/

# If >1GB:
# Solution: Rebuild with smaller chunks or prune old data
cd scripts/
python build_knowledge_base_from_markdown.py --yes
```

---

### Issue 3: Database Connection Errors

**Symptoms**:
- "Connection refused" errors
- "FATAL: password authentication failed"
- "Too many connections"

**Diagnosis**:
```bash
# Check PostgreSQL status
docker ps | grep postgres

# Check PostgreSQL logs
docker logs tria_aibpo_postgres --tail 100

# Check connection count
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"
```

**Solutions**:

**A. PostgreSQL Not Running**:
```bash
docker-compose up -d postgres

# Wait 10 seconds for startup
sleep 10

# Verify:
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "SELECT 1;"
```

**B. Wrong Password**:
```bash
# Check password in .env
cat .env | grep POSTGRES_PASSWORD

# Update if incorrect:
nano .env
# Set: POSTGRES_PASSWORD=your_correct_password

# Restart PostgreSQL:
docker-compose down postgres
docker-compose up -d postgres
```

**C. Too Many Connections**:
```bash
# Kill idle connections:
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' AND state_change < NOW() - INTERVAL '10 minutes';
"

# Restart backend to reset pool:
docker-compose restart backend
```

**D. Database Disk Full**:
```bash
# Check disk usage:
df -h

# If >90%, clean up:
# 1. Check database size
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT pg_size_pretty(pg_database_size('tria_aibpo'));
"

# 2. Clean old Docker logs
docker system prune -a

# 3. Clean old backups if any
rm -f backups/*.sql.gz
```

---

### Issue 4: Cache Not Working

**Symptoms**:
- Every query takes 14+ seconds (no cache benefit)
- Cache hit rate = 0%
- Redis errors in logs

**Diagnosis**:
```bash
# Check Redis status
docker ps | grep redis

# Check Redis logs
docker logs tria_aibpo_redis --tail 50

# Test Redis connection
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD ping

# Check cache size
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD INFO memory

# Check if keys exist
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD KEYS "*" | head -10
```

**Solutions**:

**A. Redis Not Running**:
```bash
docker-compose up -d redis

# Wait 5 seconds
sleep 5

# Verify:
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD ping
```

**B. Wrong Redis Password**:
```bash
# Check password in .env
cat .env | grep REDIS_PASSWORD

# Update if needed:
nano .env
# Set: REDIS_PASSWORD=your_correct_password

# Restart services:
docker-compose restart redis backend
```

**C. Redis Memory Full (Eviction)**:
```bash
# Check memory usage
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD INFO memory | grep used_memory_human

# If near REDIS_MAX_MEMORY (default 512MB):
# Solution 1: Increase max memory in docker-compose.yml
REDIS_MAX_MEMORY=1024mb

# Solution 2: Flush and restart (will lose cache)
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD FLUSHDB
docker-compose restart backend
```

**D. Cache Keys Expired (TTL)**:
```bash
# Check TTL on sample key
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD KEYS "*" | head -1
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD TTL "key_name"

# If all keys expired, cache will rebuild over time
# Or warm cache manually:
cd scripts/
python simple_cache_test.py
```

---

### Issue 5: High Memory Usage (>1.9GB)

**Symptoms**:
- Backend container using >1.9GB RAM
- OOM (Out of Memory) errors
- Container restarts frequently

**Diagnosis**:
```bash
# Check memory usage
docker stats tria_aibpo_backend --no-stream

# Check for memory leaks in logs
docker logs tria_aibpo_backend 2>&1 | grep -i "memory"

# Monitor memory over time (5 samples, 10s apart)
for i in {1..5}; do
  docker stats tria_aibpo_backend --no-stream | tail -1
  sleep 10
done
```

**Solutions**:

**A. Memory Leak (Growing Over Time)**:
```bash
# Immediate fix: Restart backend
docker-compose restart backend

# Long-term fix: Schedule regular restarts (cron)
# Add to crontab: Restart daily at 3 AM
0 3 * * * docker-compose -f /path/to/docker-compose.yml restart backend
```

**B. Too Many Concurrent Requests**:
```bash
# Check concurrent connections
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
"

# If >20: Implement request queuing or increase resources
# Upgrade to t3.medium (4GB) or t3.large (8GB)
```

**C. Large ChromaDB Index in Memory**:
```bash
# Check ChromaDB size
du -sh data/chromadb_cache/

# If >500MB:
# Rebuild with smaller chunks
cd scripts/
python build_knowledge_base_from_markdown.py --yes
```

**D. OpenAI Response Buffering**:
```bash
# If using non-streaming responses:
# Enable streaming to reduce memory:
# Edit .env:
ENABLE_STREAMING=true

docker-compose restart backend
```

---

### Issue 6: Xero Integration Failures

**Symptoms**:
- Order processing fails
- "Xero API error" in logs
- Invoices not created

**Diagnosis**:
```bash
# Check Xero configuration
cat .env | grep XERO

# Check health endpoint
curl http://localhost:8003/health | jq '.xero'

# Check recent Xero errors
docker logs tria_aibpo_backend 2>&1 | grep -i "xero" | tail -20
```

**Solutions**:

**A. Xero Tokens Expired**:
```bash
# Tokens expire after 30 minutes (access) or 60 days (refresh)
# Check token expiry in logs
docker logs tria_aibpo_backend 2>&1 | grep -i "token.*expir"

# Solution: Refresh tokens
cd scripts/
python get_xero_tokens.py
# Follow prompts to re-authenticate
# Copy new tokens to .env

# Restart backend:
docker-compose restart backend
```

**B. Xero Rate Limit Exceeded (60 req/min)**:
```bash
# Check rate limit errors
docker logs tria_aibpo_backend 2>&1 | grep "429"

# Solution: Wait 1 minute or implement request queuing
# Rate limiting is automatic with retry logic
# Just wait 60 seconds and retry
```

**C. Xero API Down**:
```bash
# Check Xero status
curl https://status.xero.com/

# If down: Wait for Xero to recover
# Orders will fail gracefully with compensating transactions
```

**D. Invalid Xero Account Codes**:
```bash
# Check configuration
cat .env | grep XERO_SALES_ACCOUNT_CODE
cat .env | grep XERO_TAX_TYPE

# Common values:
# AU: XERO_TAX_TYPE=OUTPUT  (GST)
# NZ: XERO_TAX_TYPE=OUTPUT2 (GST)
# SG: XERO_TAX_TYPE=OUTPUT2 (GST)

# Verify with Xero chart of accounts:
# Log into Xero → Accounting → Chart of Accounts
```

---

### Issue 7: OpenAI API Errors

**Symptoms**:
- "OpenAI API error" in logs
- Chatbot responses fail
- Rate limit errors

**Diagnosis**:
```bash
# Check OpenAI errors
docker logs tria_aibpo_backend 2>&1 | grep -i "openai" | tail -20

# Check API key
cat .env | grep OPENAI_API_KEY

# Test API key manually:
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Solutions**:

**A. Invalid API Key**:
```bash
# Get new API key from: https://platform.openai.com/api-keys

# Update .env:
nano .env
# Set: OPENAI_API_KEY=sk-...

# Restart backend:
docker-compose restart backend
```

**B. Rate Limit Exceeded**:
```bash
# Check current tier limits
# Tier 1: 500 requests/minute

# Solution 1: Increase cache hit rate (reduces API calls)
# Solution 2: Upgrade OpenAI tier
# Solution 3: Implement request queuing
```

**C. OpenAI API Down**:
```bash
# Check OpenAI status
curl https://status.openai.com/api/v2/status.json | jq .

# If down: Wait for recovery
# Consider fallback to GPT-3.5-turbo (cheaper, faster):
# Edit .env:
OPENAI_MODEL=gpt-3.5-turbo

docker-compose restart backend
```

**D. Timeout Errors**:
```bash
# Increase timeout in code if needed
# Default is 30 seconds per request

# For slow responses:
# 1. Use streaming (reduces perceived latency)
# 2. Reduce max_tokens (faster responses)
# Edit .env:
OPENAI_MAX_TOKENS=1000  # Default 2000

docker-compose restart backend
```

---

## Alert Response Procedures

### Alert: High Latency (P95 > 10s)

**Severity**: Warning → Critical (if >30s)

**Response**:
1. Check health endpoint: `curl http://localhost:8003/health`
2. Check cache hit rate: See [Issue 2](#issue-2-slow-response-times-10s)
3. Check external API status (OpenAI, Xero)
4. Review recent deployments (possible regression)
5. If >30s: Escalate to engineering

### Alert: Error Rate > 5%

**Severity**: Critical

**Response**:
1. Check logs: `docker logs tria_aibpo_backend --tail 100`
2. Identify error type (500, timeout, API error)
3. Follow relevant issue guide above
4. If database down: Escalate immediately
5. Create incident report

### Alert: Service Down

**Severity**: Critical

**Response**:
1. Check all containers: `docker ps`
2. Start missing containers: `docker-compose up -d`
3. Check logs for crash reason
4. Notify users of downtime
5. Escalate if cannot resolve in 5 minutes

### Alert: Memory > 80%

**Severity**: Warning

**Response**:
1. Check memory usage: `docker stats`
2. Restart backend if >90%
3. Monitor for memory leaks
4. Schedule maintenance restart
5. Consider upgrading instance size

### Alert: Disk > 90%

**Severity**: Critical

**Response**:
1. Check disk usage: `df -h`
2. Clean Docker system: `docker system prune -a`
3. Clean old logs: `journalctl --vacuum-time=7d`
4. Clean old backups
5. Escalate if cannot free space

### Alert: Cache Hit Rate < 40%

**Severity**: Warning

**Response**:
1. Check Redis status
2. Review cache TTLs
3. Warm cache with common queries
4. Monitor for improvement
5. Review cache strategy if persistent

---

## Deployment & Rollback

### Deployment Procedure

**Pre-Deployment Checklist**:
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Database migrations prepared (if any)
- [ ] Backup created
- [ ] Rollback plan documented
- [ ] Maintenance window scheduled (if needed)

**Deployment Steps**:

```bash
# 1. Create backup
docker exec -it tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Pull latest code
cd /path/to/tria
git pull origin main

# 3. Rebuild containers
docker-compose build

# 4. Run database migrations (if any)
# docker exec -it tria_aibpo_backend python migrations/migrate.py

# 5. Stop old containers
docker-compose down

# 6. Start new containers
docker-compose up -d

# 7. Wait for startup (30 seconds)
sleep 30

# 8. Verify health
curl http://localhost:8003/health

# 9. Smoke test
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "session_id": "test"}'

# 10. Monitor for 5 minutes
docker logs tria_aibpo_backend --follow
```

### Rollback Procedure

**When to Rollback**:
- Error rate >10% for 5 minutes
- Critical functionality broken
- Data loss detected
- Security vulnerability discovered

**Rollback Steps**:

```bash
# 1. Stop current version
docker-compose down

# 2. Restore previous code version
cd /path/to/tria
git revert HEAD  # Or: git checkout <previous-commit>

# 3. Rebuild containers with previous code
docker-compose build

# 4. Restore database backup (if needed)
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i tria_aibpo_postgres psql -U tria_admin tria_aibpo

# 5. Start containers
docker-compose up -d

# 6. Verify health
curl http://localhost:8003/health

# 7. Notify stakeholders of rollback
# 8. Create incident postmortem
```

---

## Performance Troubleshooting

### Diagnostic Commands

```bash
# Check overall system performance
docker stats

# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8003/health

# Where curl-format.txt contains:
#   time_total: %{time_total}s
#   time_connect: %{time_connect}s
#   time_starttransfer: %{time_starttransfer}s

# Check database query performance
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Check Redis performance
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD --latency

# Check disk I/O
iostat -x 1 5
```

### Performance Optimization

**1. Increase Cache TTLs** (if data is stable):
```python
# Edit src/cache/chat_response_cache.py
RESPONSE_TTL = 3600  # 1 hour (default 1800)
INTENT_TTL = 7200  # 2 hours (default 3600)
POLICY_TTL = 86400  # 24 hours (default 43200)
```

**2. Optimize Database**:
```bash
# Vacuum and analyze
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "VACUUM ANALYZE;"

# Add indexes (if missing)
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
"
```

**3. Tune PostgreSQL**:
```bash
# Edit docker-compose.yml or .env
POSTGRES_SHARED_BUFFERS=256MB  # Was 128MB
POSTGRES_EFFECTIVE_CACHE_SIZE=512MB  # Was 256MB
POSTGRES_WORK_MEM=16MB  # Was 4MB

# Restart PostgreSQL
docker-compose restart postgres
```

**4. Enable Response Streaming**:
```bash
# Reduces perceived latency
# Edit .env:
ENABLE_STREAMING=true

docker-compose restart backend
```

---

## Security Incidents

### Potential Security Issues

**1. Unauthorized Access**:
- Check Nginx access logs
- Review API access patterns
- Block suspicious IPs in firewall

**2. Suspicious Query Patterns**:
- Check for SQL injection attempts
- Review prompt injection attempts
- Check rate limiting logs

**3. Data Breach Suspected**:
- Immediately notify security team
- Review database access logs
- Check for data exfiltration
- Follow incident response plan

### Security Commands

```bash
# Check Nginx access logs for suspicious patterns
docker logs tria_aibpo_nginx 2>&1 | grep -E "admin|script|union|select"

# Check failed authentication attempts
docker logs tria_aibpo_backend 2>&1 | grep -i "unauthorized\|forbidden"

# Block IP in firewall (Ubuntu/UFW)
sudo ufw deny from SUSPICIOUS_IP to any

# Review database access
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT usename, application_name, client_addr, state, query_start
FROM pg_stat_activity
WHERE usename != 'postgres';
"
```

---

## Escalation Procedures

### Escalation Levels

**Level 1: On-Call Engineer** (Response time: <5 minutes)
- All alerts initially go here
- Can handle most common issues
- Has access to this runbook

**Level 2: Senior Engineer** (Response time: <15 minutes)
- Complex issues requiring code changes
- Performance optimization
- Database issues

**Level 3: Engineering Manager** (Response time: <30 minutes)
- Critical outages affecting all users
- Security incidents
- Data loss events

**Level 4: CTO/Executive** (Response time: <1 hour)
- Major incidents with business impact
- Security breaches
- PR/customer communication needed

### When to Escalate

**Escalate Immediately If**:
- Service down >5 minutes and cannot restore
- Data loss or corruption detected
- Security breach suspected
- Multiple critical alerts simultaneously
- Unknown/unexpected behavior

**Escalate After Attempts If**:
- Issue not resolved after 15 minutes
- Requires code changes/deployment
- Affects >50% of users
- Recurring issue with unknown root cause

---

## Useful Commands

### Container Management

```bash
# View all containers
docker ps -a

# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend

# View logs
docker logs tria_aibpo_backend --tail 100 --follow

# Execute command in container
docker exec -it tria_aibpo_backend bash

# Rebuild and restart
docker-compose build && docker-compose up -d
```

### Database Operations

```bash
# Connect to database
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo

# Backup database
docker exec -it tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup.sql

# Restore database
cat backup.sql | docker exec -i tria_aibpo_postgres psql -U tria_admin tria_aibpo

# Check table sizes
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Redis Operations

```bash
# Connect to Redis
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD

# Inside redis-cli:
PING                  # Test connection
DBSIZE                # Count keys
KEYS *                # List all keys (use carefully in production)
FLUSHDB               # Delete all keys (CAUTION!)
INFO memory           # Memory usage
INFO stats            # Statistics
GET key_name          # Get value
TTL key_name          # Check time-to-live
```

### System Monitoring

```bash
# Docker resource usage
docker stats

# Disk usage
df -h
du -sh /var/lib/docker

# Memory usage
free -h

# CPU usage
top
# Or: htop (if installed)

# Network connections
netstat -tulpn | grep :8003

# Process list
ps aux | grep python
```

---

## Contact Information

### On-Call Schedule

| Day | Engineer | Phone | Backup |
|-----|----------|-------|--------|
| Mon-Tue | [Name] | [Phone] | [Backup] |
| Wed-Thu | [Name] | [Phone] | [Backup] |
| Fri-Sun | [Name] | [Phone] | [Backup] |

### Emergency Contacts

- **On-Call Engineer**: [Phone/Slack]
- **Engineering Manager**: [Phone/Email]
- **CTO**: [Phone/Email]
- **Security Team**: [Email/Slack]
- **DevOps Lead**: [Phone/Slack]

### External Support

- **AWS Support**: [Account link]
- **OpenAI Support**: support@openai.com
- **Xero Support**: https://developer.xero.com/support

### Useful Links

- **Health Dashboard**: http://YOUR_IP:8003/health
- **Grafana (if configured)**: http://YOUR_IP:3000
- **Production Logs**: `docker logs tria_aibpo_backend --follow`
- **GitHub Repo**: https://github.com/your-org/tria
- **Documentation**: /docs/
- **Runbook (this file)**: /docs/OPERATIONAL_RUNBOOK.md

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
**Next Review**: 2025-12-14

---

**End of Operational Runbook**
