# Tria AIBPO - Production Deployment Guide

## Quick Start (For Immediate Production Deployment)

### Prerequisites

1. **Server Requirements:**
   - Ubuntu 20.04+ or similar Linux distribution
   - 4GB+ RAM
   - 20GB+ disk space
   - Docker and Docker Compose installed

2. **Required Credentials:**
   - OpenAI API key (get from https://platform.openai.com/)
   - Xero API credentials (optional, get from https://developer.xero.com/)

---

## Option 1: Automated Deployment (Recommended)

### Step 1: Clone Repository on Server

```bash
# SSH into your server
ssh user@13.214.14.130

# Clone the repository
git clone https://github.com/your-org/tria.git
cd tria
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.docker.example .env.docker

# Edit the environment file
nano .env.docker

# CRITICAL: Set these variables:
# - OPENAI_API_KEY=sk-your-actual-key-here
# - REDIS_PASSWORD=your-secure-password
# - SECRET_KEY=your-secret-key
```

### Step 3: Run Production Deployment

```bash
# Make scripts executable
chmod +x scripts/production_deploy.sh
chmod +x scripts/verify_deployment.sh

# Run the deployment script
./scripts/production_deploy.sh
```

This script will:
- ✅ Validate environment configuration
- ✅ Build Docker images
- ✅ Start all services
- ✅ Wait for health checks
- ✅ Test all endpoints
- ✅ Display access information

### Step 4: Verify Deployment

```bash
# Run verification script
./scripts/verify_deployment.sh
```

---

## Option 2: Manual Deployment

### Step 1: Install Docker (if not installed)

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Step 2: Configure Environment

```bash
# Navigate to project directory
cd tria

# Copy environment file
cp .env.docker.example .env.docker

# Edit with your credentials
nano .env.docker
```

**Required Environment Variables:**

```bash
# Database (auto-configured)
DATABASE_URL=postgresql://tria_admin:password@postgres:5432/tria_aibpo

# OpenAI (REQUIRED - replace with your key)
OPENAI_API_KEY=sk-your-actual-key-here

# Redis (REQUIRED for production)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-password
REDIS_DB=0

# Security (REQUIRED)
SECRET_KEY=your-secret-key-here

# Business config
TAX_RATE=0.08
XERO_SALES_ACCOUNT_CODE=200

# Environment
ENVIRONMENT=production
```

### Step 3: Build and Start Services

```bash
# Stop any existing containers
docker-compose down

# Build images
docker-compose build --no-cache

# Start services with environment file
docker-compose --env-file .env.docker up -d

# Watch logs
docker-compose logs -f
```

### Step 4: Wait for Services to Start

```bash
# Check container status (wait until all show "healthy")
watch -n 2 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Typically takes 30-60 seconds for all services to be healthy
```

### Step 5: Verify Deployment

```bash
# Test health endpoint
curl http://localhost/health | jq

# Test chatbot endpoint
curl -X POST http://localhost/api/chatbot \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-$(date +%s)" \
  -d '{"message":"hello","user_id":"test"}' | jq
```

---

## Troubleshooting Common Issues

### Issue 1: 502 Bad Gateway

**Symptoms:** Nginx returns 502 when accessing the site

**Diagnosis:**
```bash
# Check backend status
docker logs tria_aibpo_backend --tail 100

# Check if backend is responding
docker exec tria_aibpo_backend curl http://localhost:8003/health
```

**Common Causes:**
1. **Missing OPENAI_API_KEY:**
   ```bash
   # Check if API key is set
   docker exec tria_aibpo_backend env | grep OPENAI_API_KEY

   # Fix: Update .env.docker and restart
   docker-compose restart backend
   ```

2. **Database not ready:**
   ```bash
   # Check database
   docker logs tria_aibpo_postgres --tail 50
   docker exec tria_aibpo_postgres pg_isready -U tria_admin

   # Fix: Wait or restart
   docker-compose restart postgres backend
   ```

3. **Redis connection failed:**
   ```bash
   # Check Redis
   docker logs tria_aibpo_redis --tail 50
   docker exec tria_aibpo_redis redis-cli -a your-password ping

   # Fix: Check REDIS_PASSWORD matches in .env.docker
   docker-compose restart redis backend
   ```

### Issue 2: Backend Container Exits Immediately

**Diagnosis:**
```bash
# View full logs
docker logs tria_aibpo_backend

# Common errors to look for:
# - "No module named 'src'" → PYTHONPATH issue
# - "Connection refused" → Database not ready
# - "API key not found" → Environment variable missing
```

**Fix:**
```bash
# Ensure .env.docker has all required variables
cat .env.docker | grep -E "OPENAI_API_KEY|DATABASE_URL|REDIS"

# Rebuild and restart
docker-compose down
docker-compose --env-file .env.docker up -d --build
```

### Issue 3: React Hydration Error (#418)

**Symptoms:** Frontend shows error about text content mismatch

**Cause:** Backend not responding, frontend can't fetch data

**Fix:** Resolve backend issues first (see Issue 1)

### Issue 4: Database Connection Failed

**Diagnosis:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check database logs
docker logs tria_aibpo_postgres --tail 50

# Test connection
docker exec tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "SELECT 1;"
```

**Fix:**
```bash
# Restart database
docker-compose restart postgres

# If database is corrupted, recreate (WARNING: deletes data)
docker-compose down -v
docker-compose up -d
```

---

## Monitoring and Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f nginx

# Last N lines
docker logs tria_aibpo_backend --tail 100
```

### Check Service Health

```bash
# Health endpoint
curl http://localhost/health | jq

# Metrics endpoint
curl http://localhost/metrics

# Container status
docker ps
```

### Restart Services

```bash
# Restart specific service
docker-compose restart backend

# Restart all services
docker-compose restart

# Full restart (rebuild)
docker-compose down
docker-compose up -d --build
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose --env-file .env.docker up -d

# Monitor startup
docker-compose logs -f
```

---

## Security Checklist

Before going to production:

- [ ] Change default PostgreSQL password in .env.docker
- [ ] Set strong REDIS_PASSWORD
- [ ] Generate unique SECRET_KEY (use: `openssl rand -hex 32`)
- [ ] Set ENVIRONMENT=production
- [ ] Configure firewall (allow only ports 80, 443, 22)
- [ ] Set up SSL/TLS certificates (use Let's Encrypt)
- [ ] Enable Sentry error tracking (set SENTRY_DSN)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Set up log rotation
- [ ] Review CORS settings
- [ ] Never commit .env.docker to git

---

## Performance Optimization

### Enable Production Caching

Ensure Redis is configured:
```bash
# In .env.docker
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-password
```

### Monitor Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df
```

### Scale Services (if needed)

```bash
# Scale backend (requires load balancer configuration)
docker-compose up -d --scale backend=3
```

---

## Backup and Recovery

### Backup Database

```bash
# Create backup
docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup_$(date +%Y%m%d).sql

# Compress
gzip backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Stop backend to prevent connections
docker-compose stop backend

# Restore
gunzip -c backup_20250124.sql.gz | docker exec -i tria_aibpo_postgres psql -U tria_admin -d tria_aibpo

# Restart backend
docker-compose start backend
```

---

## Access Points

After successful deployment, the application will be available at:

- **Web UI:** http://your-server-ip/
- **API Documentation:** http://your-server-ip/docs
- **Health Check:** http://your-server-ip/health
- **Metrics:** http://your-server-ip/metrics

---

## Support

If issues persist:

1. Run diagnostics: `./scripts/verify_deployment.sh`
2. Check logs: `docker-compose logs`
3. Review error messages in backend logs
4. Ensure all environment variables are set correctly
5. Verify server has sufficient resources (RAM, disk)

For urgent issues, collect:
- Output of `docker ps -a`
- Output of `docker-compose logs backend`
- Output of `./scripts/verify_deployment.sh`
