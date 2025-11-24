# 🚀 DEPLOY NOW - Emergency Production Fix

## For Server: 13.214.14.130

This is a **QUICKFIX GUIDE** to resolve your 502 Bad Gateway error immediately.

---

## Option A: One-Command Fix (Fastest)

SSH into your server and run:

```bash
cd /path/to/tria   # Update with your actual path
chmod +x QUICKFIX.sh
./QUICKFIX.sh
```

This will:
1. Stop all containers
2. Check environment variables
3. Clean up and rebuild
4. Start services
5. Wait for health checks
6. Test endpoints

**Time: 3-5 minutes**

---

## Option B: Manual Step-by-Step Fix

### Step 1: SSH into Server
```bash
ssh user@13.214.14.130
cd /path/to/tria
```

### Step 2: Stop Everything
```bash
docker-compose down
```

### Step 3: Check Environment File
```bash
# Verify .env.docker exists
ls -la .env.docker

# If it doesn't exist, create it:
cp .env.docker.example .env.docker

# Edit and add your OpenAI API key
nano .env.docker

# CRITICAL: Set these variables:
OPENAI_API_KEY=sk-your-actual-key-here
REDIS_PASSWORD=change_this_redis_password_456
SECRET_KEY=8f7d6e5c4b3a2918f7d6e5c4b3a2918f7d6e5c4b3a2918f7d6e5c4b3a2918
```

### Step 4: Rebuild Everything
```bash
docker-compose build --no-cache
```

### Step 5: Start Services
```bash
docker-compose --env-file .env.docker up -d
```

### Step 6: Monitor Startup
```bash
# Watch logs
docker-compose logs -f backend

# In another terminal, check health
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Wait until you see "healthy" status
```

### Step 7: Test
```bash
# Test health endpoint
curl http://localhost/health | jq

# Test chatbot
curl -X POST http://localhost/api/chatbot \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -d '{"message":"hello","user_id":"test"}' | jq
```

---

## Common Issues and Instant Fixes

### Issue: Backend keeps crashing

**Check logs:**
```bash
docker logs tria_aibpo_backend --tail 50
```

**Common errors:**

1. **"No module named 'openai'" or similar**
   ```bash
   # Rebuild with no cache
   docker-compose build --no-cache backend
   docker-compose up -d backend
   ```

2. **"OpenAI API key not found"**
   ```bash
   # Check if set
   docker exec tria_aibpo_backend env | grep OPENAI_API_KEY

   # Fix: Add to .env.docker
   echo "OPENAI_API_KEY=sk-your-key" >> .env.docker
   docker-compose restart backend
   ```

3. **"Connection refused" to database**
   ```bash
   # Wait for database to be healthy
   docker logs tria_aibpo_postgres
   docker-compose restart backend
   ```

### Issue: Frontend shows "Failed to fetch"

**Cause:** Backend not ready yet

**Fix:**
```bash
# Check backend health
docker logs tria_aibpo_backend --tail 20

# If backend is healthy, check nginx
docker logs tria_aibpo_nginx --tail 20

# Restart nginx
docker-compose restart nginx
```

### Issue: Redis connection error

**Fix:**
```bash
# Ensure Redis password matches
docker logs tria_aibpo_redis

# Check password in .env.docker
grep REDIS_PASSWORD .env.docker

# Restart Redis and backend
docker-compose restart redis backend
```

---

## Verification Checklist

After deployment, verify:

- [ ] All containers running: `docker ps`
- [ ] Backend healthy: `docker exec tria_aibpo_backend curl http://localhost:8003/health`
- [ ] Frontend responding: `curl http://localhost:3000`
- [ ] Nginx routing: `curl http://localhost/health`
- [ ] External access: `curl http://13.214.14.130/health` (from another machine)

---

## Emergency Rollback

If things get worse:

```bash
# Stop everything
docker-compose down

# Remove all data (WARNING: deletes database)
docker-compose down -v

# Start fresh
docker-compose --env-file .env.docker up -d

# Or restore from backup
gunzip -c backup.sql.gz | docker exec -i tria_aibpo_postgres psql -U tria_admin -d tria_aibpo
```

---

## Get Help

If still not working, collect diagnostics:

```bash
# Run this script
chmod +x scripts/verify_deployment.sh
./scripts/verify_deployment.sh > diagnostics.txt

# Send diagnostics.txt along with:
docker-compose logs > logs.txt
```

---

## Expected Successful Output

When everything works, you should see:

**Container Status:**
```
NAME                    STATUS
tria_aibpo_nginx        Up (healthy)
tria_aibpo_frontend     Up
tria_aibpo_backend      Up (healthy)
tria_aibpo_postgres     Up (healthy)
tria_aibpo_redis        Up (healthy)
```

**Health Check:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-24T10:30:00Z",
  "services": {
    "database": "connected",
    "redis": "connected",
    "chromadb": "operational"
  }
}
```

**Chatbot Response:**
```json
{
  "response": "Hello! How can I assist you today?",
  "intent": "greeting",
  "confidence": 0.95,
  "session_id": "abc123..."
}
```

---

## Post-Deployment

Once working:

1. **Set up monitoring:**
   ```bash
   # View metrics
   curl http://localhost/metrics
   ```

2. **Configure backups:**
   ```bash
   # Add to crontab
   0 2 * * * docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo | gzip > /backups/tria_$(date +\%Y\%m\%d).sql.gz
   ```

3. **Set up SSL (optional but recommended):**
   - Install certbot
   - Get Let's Encrypt certificate
   - Update nginx configuration

---

## Support Contacts

- **Documentation:** See PRODUCTION_DEPLOYMENT.md for full guide
- **Scripts:** Use ./scripts/production_deploy.sh for automated deployment
- **Verification:** Use ./scripts/verify_deployment.sh for diagnostics
