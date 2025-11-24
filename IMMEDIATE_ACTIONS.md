# 🚨 IMMEDIATE ACTIONS - Fix Production Server NOW

## Current Problem
- **Server:** 13.214.14.130
- **Error:** 502 Bad Gateway on /api/chatbot
- **Impact:** Chatbot not working, React hydration errors

## Root Cause Identified
1. ❌ Missing REDIS configuration in .env.docker
2. ❌ Backend container failing to start properly
3. ❌ Frontend missing favicon (minor)

## ✅ SOLUTION READY - Choose Your Path

---

## Path 1: ONE-COMMAND FIX (Recommended - 3 minutes)

### On Your Server (13.214.14.130):

```bash
# SSH into your server
ssh user@13.214.14.130

# Navigate to your project
cd /path/to/tria   # <-- Replace with actual path

# Pull latest fixes
git pull origin main

# Make script executable
chmod +x QUICKFIX.sh

# RUN THE FIX
./QUICKFIX.sh
```

**This will:**
- ✅ Stop all containers
- ✅ Check/fix environment variables
- ✅ Rebuild everything clean
- ✅ Start services with health monitoring
- ✅ Test all endpoints
- ✅ Show you the access URL

**Time:** 3-5 minutes total

---

## Path 2: Manual Fix (If script fails - 10 minutes)

### Step 1: Connect to Server
```bash
ssh user@13.214.14.130
cd /path/to/tria
git pull origin main
```

### Step 2: Fix Environment File
```bash
# Check if .env.docker exists
ls -la .env.docker

# If missing, create it:
cp .env.docker.example .env.docker
```

### Step 3: Update .env.docker with These Critical Variables
```bash
nano .env.docker

# ADD/UPDATE these lines:
OPENAI_API_KEY=sk-your-actual-openai-key-here

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change_this_redis_password_456
REDIS_DB=0

SECRET_KEY=8f7d6e5c4b3a2918f7d6e5c4b3a2918f7d6e5c4b3a2918f7d6e5c4b3a2918
ENVIRONMENT=production

# Save and exit (Ctrl+X, then Y, then Enter)
```

### Step 4: Rebuild and Restart
```bash
# Stop everything
docker-compose down

# Clean rebuild
docker-compose build --no-cache

# Start with new environment
docker-compose --env-file .env.docker up -d

# Monitor startup
docker-compose logs -f backend
```

### Step 5: Verify (Wait 1-2 minutes, then test)
```bash
# Check health
curl http://localhost/health | jq

# Test chatbot
curl -X POST http://localhost/api/chatbot \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-123" \
  -d '{"message":"hello","user_id":"test"}' | jq
```

---

## What I Fixed for You

### 1. Environment Configuration (.env.docker)
**Added missing variables:**
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB` (Critical for caching)
- `ENVIRONMENT=production`
- `SECRET_KEY` (for session encryption)
- Validation limits

### 2. Deployment Automation
**Created new scripts:**
- `QUICKFIX.sh` - One-command emergency fix
- `scripts/production_deploy.sh` - Full automated deployment
- `scripts/verify_deployment.sh` - Diagnostic tool

### 3. Documentation
**Created comprehensive guides:**
- `DEPLOY_NOW.md` - Quick deployment guide
- `PRODUCTION_DEPLOYMENT.md` - Full production manual

### 4. Frontend
**Fixed:**
- Added favicon to prevent 404 error
- Updated layout.tsx with proper metadata

---

## After Fix Succeeds

### Verify Everything Works:
```bash
# Run verification script
chmod +x scripts/verify_deployment.sh
./scripts/verify_deployment.sh
```

### Access Your Application:
- **Web UI:** http://13.214.14.130/
- **API Docs:** http://13.214.14.130/docs
- **Health:** http://13.214.14.130/health

### Monitor:
```bash
# View all logs
docker-compose logs -f

# View just backend
docker-compose logs -f backend

# Check container status
docker ps
```

---

## If You Still See Errors

### Collect Diagnostics:
```bash
./scripts/verify_deployment.sh > diagnostics.txt
docker-compose logs > all-logs.txt
docker logs tria_aibpo_backend > backend-logs.txt
```

### Common Issues:

**1. Backend still showing 502:**
```bash
# Check backend logs
docker logs tria_aibpo_backend --tail 50

# Most likely: OPENAI_API_KEY not set
docker exec tria_aibpo_backend env | grep OPENAI_API_KEY

# Fix: Update .env.docker and restart
docker-compose restart backend
```

**2. Database connection error:**
```bash
# Check database
docker logs tria_aibpo_postgres --tail 20

# Restart database and backend
docker-compose restart postgres backend
```

**3. Redis connection error:**
```bash
# Check Redis password matches
grep REDIS_PASSWORD .env.docker
docker logs tria_aibpo_redis

# Restart Redis and backend
docker-compose restart redis backend
```

---

## Emergency Contacts

If nothing works:
1. Send me diagnostics.txt
2. Send me backend-logs.txt
3. Tell me exact error message you see

---

## Success Indicators

You'll know it's working when you see:

**Container Status:**
```
✓ tria_aibpo_postgres    (healthy)
✓ tria_aibpo_redis       (healthy)
✓ tria_aibpo_backend     (healthy)
✓ tria_aibpo_frontend    (running)
✓ tria_aibpo_nginx       (healthy)
```

**Health Check Returns:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "chromadb": "operational"
  }
}
```

**Website Loads:**
- No more 502 errors
- Chatbot responds
- No React errors in console

---

## Next Steps After Fix

1. **Set up backups:**
   ```bash
   # Database backup
   docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup.sql
   ```

2. **Monitor performance:**
   ```bash
   # View metrics
   curl http://localhost/metrics
   ```

3. **Consider SSL (optional):**
   - Install certbot
   - Get Let's Encrypt certificate

---

## Files Changed in This Fix

```
New Files:
  ✅ QUICKFIX.sh                      - Emergency fix script
  ✅ DEPLOY_NOW.md                    - Quick deployment guide
  ✅ PRODUCTION_DEPLOYMENT.md         - Full deployment manual
  ✅ scripts/production_deploy.sh     - Automated deployment
  ✅ scripts/verify_deployment.sh     - Diagnostics tool
  ✅ IMMEDIATE_ACTIONS.md             - This file

Modified Files:
  ✅ .env.docker                      - Added REDIS config
  ✅ frontend/app/layout.tsx          - Added favicon

Already Committed & Pushed to GitHub:
  ✅ All changes committed
  ✅ Pushed to origin/main
  ✅ Ready to pull on server
```

---

## GO! Deploy NOW!

**Choose your path and execute:**

**Option A (Fastest):**
```bash
ssh user@13.214.14.130
cd /path/to/tria
git pull origin main
chmod +x QUICKFIX.sh
./QUICKFIX.sh
```

**Option B (Manual):**
Follow "Path 2: Manual Fix" above

---

**Questions? Issues? Send me the diagnostics and I'll help immediately.**

**Your production deployment will be working in less than 5 minutes! 🚀**
