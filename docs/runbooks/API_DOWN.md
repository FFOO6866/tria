# Runbook: API Down

**Alert**: `APIDown`
**Severity**: Critical (Page On-Call)
**Component**: API

## Symptoms

- API unreachable
- Health check failing
- 502/504 errors from Nginx
- User unable to access service

## Immediate Actions (< 5 minutes)

### Step 1: Verify Alert is Real (30 seconds)

```bash
# Check from external location
curl https://your-domain.com/health

# Expected: 200 OK with JSON response
```

**If returns 200 OK**: False alarm → Acknowledge alert

**If fails**: Proceed to Step 2

### Step 2: Check Docker Containers (1 min)

```bash
# SSH into server
ssh -i ~/.ssh/your-key.pem ubuntu@your-server-ip

# Check all containers
docker-compose ps
```

**Expected Output**:
```
NAME                  STATUS
tria_aibpo_backend    Up (healthy)
tria_aibpo_postgres   Up (healthy)
tria_aibpo_redis      Up (healthy)
tria_aibpo_nginx      Up
```

**If backend is not "Up (healthy)"**:
- Container crashed → See logs
- Health check failing → See logs

### Step 3: Check Backend Logs (1 min)

```bash
# View recent logs
docker logs tria_aibpo_backend --tail 50

# Common issues to look for:
# - "Failed to connect to database"
# - "OPENAI_API_KEY not set"
# - Python crash/traceback
```

### Step 4: Quick Restart (2 min)

```bash
# Restart backend only (fastest)
docker-compose restart backend

# Wait 30 seconds for startup
sleep 30

# Check health
curl http://localhost:8003/health
```

**If still failing**: Restart all services

```bash
# Full restart
docker-compose down
docker-compose up -d

# Wait for startup
sleep 60

# Check health
curl http://localhost:8003/health
```

## Investigation

### Check Configuration

```bash
# Verify environment variables are set
docker exec tria_aibpo_backend env | grep -E "DATABASE_URL|OPENAI_API_KEY|REDIS"
```

**Expected**:
- DATABASE_URL set
- OPENAI_API_KEY set (starts with sk-)
- REDIS_HOST set

**If missing**: Check `.env.docker` file

### Check Database Connectivity

```bash
# Test database connection
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "SELECT 1"
```

**Expected**: Returns "1"

**If fails**:
- PostgreSQL not running → Restart
- Wrong credentials → Check `.env.docker`

### Check Redis

```bash
# Test Redis connection
docker exec -it tria_aibpo_redis redis-cli ping
```

**Expected**: Returns "PONG"

**If fails**: Restart Redis

### Check Disk Space

```bash
# Check available disk space
df -h

# Docker may stop if disk full
```

**If disk > 90% full**:
```bash
# Clean up old logs
docker system prune -a --volumes

# Clean up old containers
docker container prune
```

### Check System Resources

```bash
# Check if system is under heavy load
top

# Check memory
free -h
```

**If out of memory**: Restart server or scale up

## Resolution

### Quick Recovery

**Option 1: Rollback to Previous Version** (if recent deploy)
```bash
# Check recent commits
git log --oneline -5

# Rollback to previous version
git checkout HEAD~1

# Rebuild and restart
docker-compose build
docker-compose up -d
```

**Option 2: Full Restart**
```bash
# Stop everything
docker-compose down

# Clear any stuck processes
docker system prune -f

# Restart
docker-compose up -d

# Monitor logs
docker-compose logs -f backend
```

**Option 3: Failover** (if using blue-green deployment)
```bash
# Switch to backup instance
# Update Nginx to point to backup
# See blue-green deployment docs
```

### Verify Recovery

```bash
# Health check
curl http://localhost:8003/health

# Test chatbot endpoint
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","outlet_id":1,"user_id":"test","session_id":"test"}'
```

## Communication

### Internal

Post to #incidents channel:
```
🚨 API OUTAGE - INVESTIGATING
Start Time: [timestamp]
Impact: All users unable to access service
Status: Investigating / Identified / Resolved
ETA: [estimate]
```

### External (if > 5 minutes)

Update status page:
- Mark API as "Major Outage"
- Post investigation updates every 10 minutes
- Notify customers via email if > 30 minutes

## Post-Incident

### Required Actions

1. **Write Post-Mortem** (within 24 hours)
   - What happened?
   - Root cause?
   - Why didn't monitoring catch it earlier?
   - What will prevent this in future?

2. **Create Follow-up Tasks**
   - Improve monitoring
   - Fix root cause
   - Update runbooks
   - Add automated recovery

3. **Share Learnings**
   - Present in team meeting
   - Update documentation
   - Share with engineering team

## Escalation

**Escalate immediately if**:
- Cannot restart service within 10 minutes
- Root cause unknown
- Data loss suspected
- External service (AWS, OpenAI) is down

**Contact**:
- Engineering Lead: [phone]
- CTO: [phone]
- #engineering-oncall: Slack
