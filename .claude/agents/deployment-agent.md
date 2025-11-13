# Deployment Agent for Tria AIBPO

**Purpose**: Complete deployment workflow for Tria AIBPO using Git-based deployment
**Last Updated**: 2025-11-13
**Owner**: Deployment Agent

---

## 🎯 CRITICAL RULES

1. **ALWAYS use Git for deployment** - Local → Git → Server (NEVER rsync/scp)
2. **Single .env file** - Same file used locally and on server
3. **Explicit env vars** - Always pass `--env-file .env` to docker-compose
4. **Production flag awareness** - Check `ENVIRONMENT=production` vs `development`
5. **NEVER deploy without this agent** - All deployments must follow these steps
6. **Test locally first** - Always verify with `docker-compose up` before pushing

---

## 📋 Environment Configuration

### .env File Structure

**Location**: Project root (same on local and server)

```bash
# ============================================================================
# SERVER CONFIGURATION (for deployment scripts)
# ============================================================================
SERVER_IP=YOUR_SERVER_IP_HERE
SERVER_USER=ubuntu
PEM_KEY_PATH=~/.ssh/your-key.pem
SERVER_PROJECT_PATH=/home/ubuntu/tria

# ============================================================================
# ENVIRONMENT FLAG (CRITICAL - Check before deploying!)
# ============================================================================
ENVIRONMENT=production  # or 'development' for local

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=CHANGE_THIS_SECURE_PASSWORD_123
POSTGRES_DB=tria_aibpo

# ============================================================================
# REDIS CONFIGURATION (Required for production features)
# ============================================================================
REDIS_PASSWORD=CHANGE_THIS_REDIS_PASSWORD_456

# ============================================================================
# OPENAI API (REQUIRED - Check this is set!)
# ============================================================================
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE
OPENAI_MODEL=gpt-4-turbo-preview

# ============================================================================
# APPLICATION SECRETS
# ============================================================================
SECRET_KEY=CHANGE_THIS_SECRET_KEY_789

# ============================================================================
# TAX AND ACCOUNTING (Required)
# ============================================================================
TAX_RATE=0.09
XERO_SALES_ACCOUNT_CODE=200
XERO_TAX_TYPE=TAX001

# ============================================================================
# XERO INTEGRATION (Optional)
# ============================================================================
XERO_CLIENT_ID=
XERO_CLIENT_SECRET=
XERO_REFRESH_TOKEN=
XERO_TENANT_ID=

# ============================================================================
# SENTRY ERROR TRACKING (Optional)
# ============================================================================
SENTRY_DSN=

# ============================================================================
# VALIDATION LIMITS
# ============================================================================
MAX_QUANTITY_PER_ITEM=10000
MAX_ORDER_TOTAL=100000.00
MAX_LINE_ITEMS=100
MIN_ORDER_TOTAL=0.01
```

---

## 🚀 DEPLOYMENT PROCEDURE

### Pre-Deployment Checklist

```bash
# 1. Verify .env file exists and has all required vars
cat .env | grep -E "OPENAI_API_KEY|POSTGRES_PASSWORD|SECRET_KEY|REDIS_PASSWORD|ENVIRONMENT"

# 2. Check ENVIRONMENT flag
grep "^ENVIRONMENT=" .env
# Should be 'development' for local, 'production' for server

# 3. Test locally FIRST
docker-compose --env-file .env down
docker-compose --env-file .env build
docker-compose --env-file .env up -d

# 4. Verify local deployment
curl http://localhost:8003/health | jq
docker-compose --env-file .env logs backend | tail -20

# 5. Stop local services before deploying
docker-compose --env-file .env down
```

### Deployment Steps (Local → Git → Server)

```bash
# STEP 1: Commit changes locally
git add .
git commit -m "Deploy: [description of changes]"

# STEP 2: Push to GitHub
git push origin main

# STEP 3: SSH to server and pull changes
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_SERVER_IP << 'EOF'
cd /home/ubuntu/tria
git pull origin main
EOF

# STEP 4: Deploy on server with explicit env vars
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_SERVER_IP << 'EOF'
cd /home/ubuntu/tria

# Verify .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found on server!"
    exit 1
fi

# Verify OPENAI_API_KEY is set
if ! grep -q "^OPENAI_API_KEY=sk-" .env; then
    echo "ERROR: OPENAI_API_KEY not set in .env!"
    exit 1
fi

# Check ENVIRONMENT flag
CURRENT_ENV=$(grep "^ENVIRONMENT=" .env | cut -d'=' -f2)
echo "Current ENVIRONMENT: $CURRENT_ENV"

# Stop existing containers
docker-compose --env-file .env down

# Build new images
docker-compose --env-file .env build

# Start services (ALWAYS with --env-file)
docker-compose --env-file .env up -d

# Wait for services to start
sleep 10

# Verify deployment
docker-compose --env-file .env ps
docker-compose --env-file .env logs backend | tail -20

# Check health endpoint
curl http://localhost:8003/health

EOF

# STEP 5: Verify from local machine
curl http://YOUR_SERVER_IP:8003/health | jq
```

---

## 🔧 COMMON ISSUES AND FIXES

### Issue 1: "OPENAI_API_KEY not set" error

**Cause**: Forgot to pass `--env-file .env` to docker-compose

**Fix**:
```bash
# ALWAYS use --env-file
docker-compose --env-file .env up -d

# Verify env vars are loaded
docker-compose --env-file .env config | grep OPENAI_API_KEY
```

### Issue 2: Changes not reflected on server

**Cause**: Forgot to git pull on server

**Fix**:
```bash
# SSH to server
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_SERVER_IP

# Pull latest changes
cd /home/ubuntu/tria
git pull origin main

# Rebuild and restart
docker-compose --env-file .env down
docker-compose --env-file .env build
docker-compose --env-file .env up -d
```

### Issue 3: "Permission denied" when accessing .env

**Cause**: .env file permissions

**Fix**:
```bash
# On server
chmod 600 .env
chown ubuntu:ubuntu .env
```

### Issue 4: Wrong ENVIRONMENT flag

**Cause**: ENVIRONMENT=development on production server

**Fix**:
```bash
# Check current value
grep "^ENVIRONMENT=" .env

# Update on server (via SSH)
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_SERVER_IP
cd /home/ubuntu/tria
sed -i 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' .env

# Restart services
docker-compose --env-file .env down
docker-compose --env-file .env up -d
```

### Issue 5: Database connection failed

**Cause**: PostgreSQL not ready when backend starts

**Fix**:
```bash
# Check postgres logs
docker-compose --env-file .env logs postgres

# Restart backend after postgres is ready
docker-compose --env-file .env restart backend

# Verify connection
docker-compose --env-file .env exec backend python -c "from database import get_db_engine; get_db_engine()"
```

### Issue 6: Redis authentication failed

**Cause**: REDIS_PASSWORD mismatch between .env and running container

**Fix**:
```bash
# Verify REDIS_PASSWORD in .env
grep "^REDIS_PASSWORD=" .env

# Restart redis and backend
docker-compose --env-file .env down redis backend
docker-compose --env-file .env up -d redis
sleep 5
docker-compose --env-file .env up -d backend
```

---

## 📝 DEPLOYMENT COMMANDS REFERENCE

### Full Deployment (Local → Server)

```bash
#!/bin/bash
# deploy.sh - Full deployment script

set -e  # Exit on error

echo "=== Tria AIBPO Deployment ==="

# 1. Verify .env
echo "[1/8] Verifying .env file..."
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    exit 1
fi

# 2. Check required vars
echo "[2/8] Checking required environment variables..."
required_vars=("OPENAI_API_KEY" "POSTGRES_PASSWORD" "SECRET_KEY" "REDIS_PASSWORD" "SERVER_IP")
for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env; then
        echo "ERROR: ${var} not set in .env!"
        exit 1
    fi
done

# 3. Load server config
source .env
echo "[3/8] Loaded server config: $SERVER_IP"

# 4. Test locally
echo "[4/8] Testing locally..."
docker-compose --env-file .env down
docker-compose --env-file .env build backend
docker-compose --env-file .env up -d

sleep 15

if ! curl -f http://localhost:8003/health > /dev/null 2>&1; then
    echo "ERROR: Local deployment failed!"
    docker-compose --env-file .env logs backend
    exit 1
fi
echo "Local test passed!"

docker-compose --env-file .env down

# 5. Commit and push
echo "[5/8] Committing changes..."
git add .
git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')" || echo "No changes to commit"
git push origin main

# 6. Pull on server
echo "[6/8] Pulling changes on server..."
ssh -i "$PEM_KEY_PATH" "$SERVER_USER@$SERVER_IP" << 'EOF'
cd $SERVER_PROJECT_PATH
git pull origin main
EOF

# 7. Deploy on server
echo "[7/8] Deploying on server..."
ssh -i "$PEM_KEY_PATH" "$SERVER_USER@$SERVER_IP" << 'EOF'
cd $SERVER_PROJECT_PATH

# Verify .env
if [ ! -f .env ]; then
    echo "ERROR: .env not found on server!"
    exit 1
fi

# Check ENVIRONMENT flag
if ! grep -q "^ENVIRONMENT=production" .env; then
    echo "WARNING: ENVIRONMENT is not set to 'production'"
    echo "Current value:"
    grep "^ENVIRONMENT=" .env
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Deploy
docker-compose --env-file .env down
docker-compose --env-file .env build
docker-compose --env-file .env up -d

# Wait for startup
sleep 15

# Verify
if ! curl -f http://localhost:8003/health > /dev/null 2>&1; then
    echo "ERROR: Deployment failed!"
    docker-compose --env-file .env logs backend | tail -50
    exit 1
fi

echo "Deployment successful!"
docker-compose --env-file .env ps

EOF

# 8. Verify from local
echo "[8/8] Verifying deployment from local..."
if curl -f "http://$SERVER_IP:8003/health" > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
    curl "http://$SERVER_IP:8003/health" | jq
else
    echo "❌ Server health check failed!"
    exit 1
fi

echo "=== Deployment Complete ==="
```

### Quick Commands

```bash
# View logs
docker-compose --env-file .env logs -f backend

# Restart specific service
docker-compose --env-file .env restart backend

# Check running containers
docker-compose --env-file .env ps

# Execute command in container
docker-compose --env-file .env exec backend bash

# View environment variables
docker-compose --env-file .env config

# Stop all services
docker-compose --env-file .env down

# Remove volumes (DANGEROUS!)
docker-compose --env-file .env down -v
```

---

## 🔍 MONITORING COMMANDS

### Health Check

```bash
# Local
curl http://localhost:8003/health | jq

# Server
curl http://YOUR_SERVER_IP:8003/health | jq

# Expected output:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "chromadb": "connected",
  "circuit_breakers": {
    "xero_api": "closed",
    "openai_api": "closed",
    "database": "closed"
  }
}
```

### Database Check

```bash
# Connect to database
docker-compose --env-file .env exec postgres psql -U tria_admin -d tria_aibpo

# Run query
docker-compose --env-file .env exec postgres psql -U tria_admin -d tria_aibpo -c "SELECT COUNT(*) FROM orders;"
```

### Redis Check

```bash
# Connect to Redis
docker-compose --env-file .env exec redis redis-cli -a YOUR_REDIS_PASSWORD

# Check keys
docker-compose --env-file .env exec redis redis-cli -a YOUR_REDIS_PASSWORD KEYS '*'
```

### Logs Analysis

```bash
# Backend logs
docker-compose --env-file .env logs backend | grep ERROR

# All services
docker-compose --env-file .env logs --tail=100

# Follow logs
docker-compose --env-file .env logs -f
```

---

## 🚨 EMERGENCY PROCEDURES

### Rollback to Previous Version

```bash
# On server
ssh -i ~/.ssh/your-key.pem ubuntu@YOUR_SERVER_IP
cd /home/ubuntu/tria

# Find last working commit
git log --oneline -10

# Rollback
git checkout COMMIT_HASH

# Redeploy
docker-compose --env-file .env down
docker-compose --env-file .env build
docker-compose --env-file .env up -d

# Verify
curl http://localhost:8003/health
```

### Complete Reset

```bash
# WARNING: This deletes all data!

# Stop and remove everything
docker-compose --env-file .env down -v

# Remove all images
docker-compose --env-file .env down --rmi all

# Pull latest code
git pull origin main

# Rebuild from scratch
docker-compose --env-file .env build --no-cache
docker-compose --env-file .env up -d
```

### Database Backup

```bash
# Create backup
docker-compose --env-file .env exec postgres pg_dump -U tria_admin tria_aibpo > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
docker-compose --env-file .env exec -T postgres psql -U tria_admin tria_aibpo < backup_20251113_120000.sql
```

---

## ✅ PRE-DEPLOYMENT CHECKLIST

Before every deployment, verify:

- [ ] `.env` file exists locally and on server
- [ ] `OPENAI_API_KEY` is set and valid
- [ ] `POSTGRES_PASSWORD` is set
- [ ] `REDIS_PASSWORD` is set
- [ ] `SECRET_KEY` is set
- [ ] `SERVER_IP` is correct
- [ ] `PEM_KEY_PATH` is correct
- [ ] `ENVIRONMENT` flag is correct (production on server, development locally)
- [ ] Tested locally with `docker-compose --env-file .env up`
- [ ] All changes committed to Git
- [ ] Health endpoint returns success locally
- [ ] No errors in local logs

## ✅ POST-DEPLOYMENT VERIFICATION

After deployment, verify:

- [ ] Git pull succeeded on server
- [ ] Docker images built successfully
- [ ] All containers are running (`docker-compose ps`)
- [ ] Health endpoint returns healthy
- [ ] No errors in logs (`docker-compose logs`)
- [ ] Database connection working
- [ ] Redis connection working
- [ ] Can access API from external IP
- [ ] Circuit breakers initialized
- [ ] No "OPENAI_API_KEY not set" errors

---

## 📚 REMEMBER

1. **ALWAYS use `--env-file .env`** with docker-compose commands
2. **Git is the source of truth** - Never manually copy files
3. **Test locally first** - Never deploy untested code
4. **Check ENVIRONMENT flag** - Wrong flag causes issues
5. **Keep this agent updated** - Document new issues/fixes here
6. **NEVER deploy without following this agent's procedures**

---

## 🎯 DEPLOYMENT WORKFLOW SUMMARY

```
Local Development
    ↓
Test with docker-compose --env-file .env up
    ↓
Verify health endpoint works
    ↓
git commit & git push
    ↓
SSH to server
    ↓
git pull origin main
    ↓
docker-compose --env-file .env down
    ↓
docker-compose --env-file .env build
    ↓
docker-compose --env-file .env up -d
    ↓
Verify health endpoint on server
    ↓
Done!
```

---

**Last Updated**: 2025-11-13
**Agent Version**: 1.0
**Maintainer**: Deployment Agent
