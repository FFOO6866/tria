# Tria AI-BPO Production Deployment Analysis & Implementation Plan

**Date**: 2025-11-13
**Server**: AWS EC2 t3.small (2GB RAM) at 13.54.39.187
**SSH Key**: C:\Users\fujif\Downloads\tria.pem
**Repository**: https://github.com/fujifruity/tria

---

## Executive Summary

This document provides a comprehensive analysis of the current deployment setup and proposes a unified, production-ready deployment architecture following the TRIA deployment philosophy: **git-based workflow**, **single source of truth**, and **automated deployment agent**.

### Current Status: NEEDS CONSOLIDATION

The project currently has multiple deployment approaches that need to be unified:
1. **Two docker-compose files** (main and small) - should be unified with environment-based resource limits
2. **Multiple .env templates** - should consolidate to one comprehensive template
3. **Three deployment scripts** (deploy_to_ec2.sh, deploy_ubuntu.sh, deploy_agent.py) - deploy_agent.py is the keeper
4. **GitHub Actions workflow** - needs alignment with deployment agent

---

## 1. CRITICAL ISSUES IDENTIFIED

### Issue 1: Multiple Docker Compose Files

**Problem**:
- `docker-compose.yml` - Full stack (4GB+ RAM): postgres, redis, backend, frontend, nginx
- `docker-compose.small.yml` - Minimal (2GB RAM): postgres, redis, backend only

**Impact**:
- Duplication of configuration
- Easy to update one but forget the other
- Manual decision on which file to use

**Solution**: Unified docker-compose.yml with environment-based resource limits

### Issue 2: Environment Variable Confusion

**Current Files**:
- `.env` - Main configuration with deployment settings
- `.env.example` - Template for .env
- `.env.docker` - Docker-specific variables (has actual credentials)
- `.env.docker.example` - Template for docker variables
- `.env.production` - Production configuration (also has credentials)
- `.env.production.example` - Template for production

**Problems**:
- Multiple files with overlapping variables
- Unclear which file docker-compose uses
- Credentials scattered across multiple files
- Risk of committing secrets to git

**Solution**: Single .env file that docker-compose reads automatically

### Issue 3: Manual Environment Variable Passing

**Current Pattern** (in deploy scripts):
```bash
# WRONG: Manually passing env vars to docker-compose
OPENAI_API_KEY="..." POSTGRES_PASSWORD="..." docker-compose up -d
```

**Why This Fails**:
- Easy to forget critical variables
- Error-prone for 20+ variables
- Not maintainable

**Correct Pattern**:
Docker Compose **automatically** reads `.env` file in same directory. No manual passing needed.

### Issue 4: Deployment Agent Configuration

**Current State**:
- `deploy_agent.py` exists and is well-designed
- Reads from `.env` for deployment config (SERVER_IP, PEM_KEY_PATH)
- Reads from `.env.docker` for docker variables
- BUT: Still manually passes env vars to docker-compose (line 353-377)

**Fix Needed**:
- Docker Compose reads `.env` automatically - no need to pass vars
- Deploy agent should verify .env exists on server, not pass vars manually

---

## 2. PROPOSED UNIFIED ARCHITECTURE

### File Structure

```
tria/
├── .env                          # SINGLE source of truth (not in git)
├── .env.example                  # Template with all variables documented
├── docker-compose.yml            # SINGLE compose file (environment-aware)
├── scripts/
│   └── deploy_agent.py           # ONLY deployment script (updated)
└── docs/
    └── DEPLOYMENT.md             # Complete deployment guide
```

### Environment Variable Strategy

**SINGLE .env FILE** with clear sections:

```bash
# =============================================================================
# DEPLOYMENT CONFIGURATION (Used by deploy_agent.py)
# =============================================================================
SERVER_IP=13.54.39.187
SERVER_USER=ubuntu
PEM_KEY_PATH=C:\Users\fujif\Downloads\tria.pem
SERVER_PROJECT_PATH=/home/ubuntu/tria
ENVIRONMENT=production              # 'development' or 'production'

# =============================================================================
# RESOURCE CONFIGURATION (Used by docker-compose.yml)
# =============================================================================
# Set to 'small' for 2GB RAM (t3.small), 'medium' for 4GB+ (t3.medium)
DEPLOYMENT_SIZE=small

# =============================================================================
# DATABASE CONFIGURATION (Used by docker-compose.yml)
# =============================================================================
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=<generate with: openssl rand -base64 32>
POSTGRES_DB=tria_aibpo

# PostgreSQL memory settings (auto-configured based on DEPLOYMENT_SIZE)
# small:  shared_buffers=128MB, effective_cache=256MB
# medium: shared_buffers=256MB, effective_cache=512MB

# =============================================================================
# API KEYS (CRITICAL - docker-compose needs these)
# =============================================================================
OPENAI_API_KEY=<your-key-here>
XERO_CLIENT_ID=<optional>
XERO_CLIENT_SECRET=<optional>
XERO_TENANT_ID=<optional>
XERO_REFRESH_TOKEN=<optional>

# =============================================================================
# SECURITY
# =============================================================================
SECRET_KEY=<generate with: openssl rand -hex 32>
REDIS_PASSWORD=<generate with: openssl rand -base64 32>

# =============================================================================
# BUSINESS CONFIGURATION
# =============================================================================
TAX_RATE=0.08
XERO_SALES_ACCOUNT_CODE=200
XERO_TAX_TYPE=TAX001

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================
# Validation limits
MAX_QUANTITY_PER_ITEM=10000
MAX_ORDER_TOTAL=100000.00
MAX_LINE_ITEMS=100
MIN_ORDER_TOTAL=0.01

# Ports (default values, adjust if conflicts)
BACKEND_PORT=8003
FRONTEND_PORT=3000
REDIS_PORT=6379
POSTGRES_PORT=5433

# Logging
LOG_LEVEL=INFO
SENTRY_DSN=<optional>
```

### Docker Compose Automatic .env Loading

**Critical Understanding**: Docker Compose **automatically** reads `.env` file from the same directory. You do NOT need to:
- Pass variables manually on command line
- Use `--env-file .env` flag (it's default)
- Export variables in shell

**How It Works**:

```yaml
# docker-compose.yml
services:
  backend:
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}  # Read from .env automatically
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

When you run `docker-compose up -d`, it:
1. Looks for `.env` in same directory
2. Loads all variables
3. Substitutes `${VAR}` with values
4. Passes to containers

**NO manual passing needed!**

---

## 3. UNIFIED DOCKER COMPOSE IMPLEMENTATION

### Strategy: Environment-Based Resource Profiles

Instead of two separate files, use conditional resource limits based on `DEPLOYMENT_SIZE` variable.

```yaml
# docker-compose.yml (UNIFIED)
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: tria_aibpo_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      # Conditional memory settings based on DEPLOYMENT_SIZE
      POSTGRES_SHARED_BUFFERS: ${POSTGRES_SHARED_BUFFERS:-256MB}
      POSTGRES_EFFECTIVE_CACHE_SIZE: ${POSTGRES_EFFECTIVE_CACHE_SIZE:-512MB}
      POSTGRES_WORK_MEM: ${POSTGRES_WORK_MEM:-16MB}
    ports:
      - "${POSTGRES_PORT:-5433}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./setup_postgres_docker.sql:/docker-entrypoint-initdb.d/setup.sql
    networks:
      - tria_network
    # Resource limits set via profiles (see below)
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: tria_aibpo_redis
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory ${REDIS_MAX_MEMORY:-512mb}
      --maxmemory-policy allkeys-lru
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    networks:
      - tria_network
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: tria_aibpo_backend
    environment:
      # Database
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

      # Redis
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}

      # OpenAI (CRITICAL)
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      OPENAI_MODEL: ${OPENAI_MODEL:-gpt-4-turbo-preview}

      # Xero (optional)
      XERO_CLIENT_ID: ${XERO_CLIENT_ID:-}
      XERO_CLIENT_SECRET: ${XERO_CLIENT_SECRET:-}
      XERO_TENANT_ID: ${XERO_TENANT_ID:-}
      XERO_REFRESH_TOKEN: ${XERO_REFRESH_TOKEN:-}

      # Business config
      TAX_RATE: ${TAX_RATE:-0.08}
      XERO_SALES_ACCOUNT_CODE: ${XERO_SALES_ACCOUNT_CODE:-200}
      XERO_TAX_TYPE: ${XERO_TAX_TYPE:-TAX001}

      # Security
      SECRET_KEY: ${SECRET_KEY}

      # Application
      ENVIRONMENT: ${ENVIRONMENT:-production}
      PYTHONUNBUFFERED: 1

      # Validation
      MAX_QUANTITY_PER_ITEM: ${MAX_QUANTITY_PER_ITEM:-10000}
      MAX_ORDER_TOTAL: ${MAX_ORDER_TOTAL:-100000.00}
      MAX_LINE_ITEMS: ${MAX_LINE_ITEMS:-100}
      MIN_ORDER_TOTAL: ${MIN_ORDER_TOTAL:-0.01}

      # Performance (set based on DEPLOYMENT_SIZE)
      GUNICORN_WORKERS: ${GUNICORN_WORKERS:-2}
      GUNICORN_THREADS: ${GUNICORN_THREADS:-2}
    ports:
      - "${BACKEND_PORT:-8003}:8003"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - tria_network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

  # Frontend (only for medium+ deployments)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: tria_aibpo_frontend
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8003
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    networks:
      - tria_network
    depends_on:
      - backend
    restart: unless-stopped
    profiles:
      - full-stack  # Only start if 'full-stack' profile is active

  # Nginx (only for medium+ deployments)
  nginx:
    image: nginx:alpine
    container_name: tria_aibpo_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./logs/nginx:/var/log/nginx
    networks:
      - tria_network
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    profiles:
      - full-stack  # Only start if 'full-stack' profile is active

networks:
  tria_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
```

### Usage

**For t3.small (2GB RAM) - Backend only**:
```bash
# .env
DEPLOYMENT_SIZE=small
POSTGRES_SHARED_BUFFERS=128MB
POSTGRES_EFFECTIVE_CACHE_SIZE=256MB
REDIS_MAX_MEMORY=200mb
GUNICORN_WORKERS=2

# Deploy
docker-compose up -d
# Starts: postgres, redis, backend (NO frontend, NO nginx)
```

**For t3.medium+ (4GB+ RAM) - Full stack**:
```bash
# .env
DEPLOYMENT_SIZE=medium
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=512MB
REDIS_MAX_MEMORY=512mb
GUNICORN_WORKERS=4

# Deploy
docker-compose --profile full-stack up -d
# Starts: postgres, redis, backend, frontend, nginx
```

---

## 4. UPDATED DEPLOYMENT AGENT

The current `deploy_agent.py` is excellent but needs two fixes:

### Fix 1: Remove Manual Environment Variable Passing

**Current Code** (lines 353-377):
```python
# Build env var string for docker-compose command
env_var_string = ' '.join([
    f'{key}="{value}"'
    for key, value in env_vars.items()
    if key in self.REQUIRED_DOCKER_ENV_VARS
])

# Pass vars manually
f"{env_var_string} docker-compose up -d",
```

**Fixed Code**:
```python
# Docker Compose reads .env automatically - NO manual passing needed!
# Just ensure .env exists on server

ssh_commands = [
    "cd ~/tria",

    # Verify .env exists
    "test -f .env || (echo 'ERROR: .env file missing' && exit 1)",

    # Verify critical env vars are set
    "grep -q 'OPENAI_API_KEY=' .env || (echo 'ERROR: OPENAI_API_KEY not set' && exit 1)",

    # Stop existing containers
    "docker-compose down",

    # Build with no cache
    "docker-compose build --no-cache",

    # Start (docker-compose reads .env automatically)
    "docker-compose up -d",

    # Show status
    "docker-compose ps",
    "docker-compose logs --tail=50"
]
```

### Fix 2: Add .env Sync to Server

**New Function**:
```python
def sync_env_to_server(self, server_ip: str, server_user: str, pem_key: str) -> bool:
    """
    Copy .env file to server (NEVER commit to git)

    This is the ONLY file we copy directly (not via git)
    because it contains secrets that should never be in version control.
    """
    self.print_header("STEP 3.5: Syncing .env to Server")

    # Use scp to copy .env
    scp_cmd = [
        'scp',
        '-i', pem_key,
        '-o', 'StrictHostKeyChecking=no',
        str(self.env_file),
        f'{server_user}@{server_ip}:~/tria/.env'
    ]

    returncode, stdout, stderr = self.run_command(scp_cmd)
    if returncode != 0:
        self.log(f"Failed to copy .env to server: {stderr}", 'ERROR')
        return False

    self.log("✓ .env file synced to server", 'SUCCESS')
    return True
```

---

## 5. DEPLOYMENT WORKFLOW

### One-Time Server Setup

```bash
# 1. SSH into EC2 instance
ssh -i C:\Users\fujif\Downloads\tria.pem ubuntu@13.54.39.187

# 2. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
# Log out and back in

# 3. Clone repository
git clone https://github.com/fujifruity/tria.git ~/tria
cd ~/tria

# 4. Create .env file (will be synced from local later)
# For now, just verify git is set up correctly
git status
```

### Regular Deployment (From Local Windows Machine)

```bash
# 1. Set up local .env file (ONE TIME)
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria
cp .env.example .env

# Edit .env with your values:
# - SERVER_IP=13.54.39.187
# - SERVER_USER=ubuntu
# - PEM_KEY_PATH=C:\Users\fujif\Downloads\tria.pem
# - OPENAI_API_KEY=<your-key>
# - etc.

# 2. Commit code changes to git (NOT .env)
git add <your-files>
git commit -m "Your changes"
git push origin main

# 3. Deploy with ONE command
python scripts\deploy_agent.py

# That's it! The agent will:
# - Validate all env vars
# - Check git status
# - Push to remote
# - Copy .env to server (via scp)
# - Pull latest code on server (via git)
# - Deploy with docker-compose
# - Verify deployment health
```

### Deployment Agent Output

```
================================================================================
                        TRIA AI-BPO DEPLOYMENT AGENT
================================================================================

[2025-11-13 10:00:00] [INFO] Deployment started

================================================================================
                           STEP 1: Checking Required Files
================================================================================

[2025-11-13 10:00:00] [SUCCESS] ✓ Found: .env
[2025-11-13 10:00:00] [SUCCESS] ✓ Found: docker-compose.yml

================================================================================
                      STEP 2: Validating Environment Variables
================================================================================

[2025-11-13 10:00:01] [INFO] Checking REQUIRED docker-compose environment variables:
[2025-11-13 10:00:01] [SUCCESS] ✓ POSTGRES_USER = tria_admin
[2025-11-13 10:00:01] [SUCCESS] ✓ POSTGRES_PASSWORD = MAv9crbSYm...
[2025-11-13 10:00:01] [SUCCESS] ✓ POSTGRES_DB = tria_aibpo
[2025-11-13 10:00:01] [SUCCESS] ✓ OPENAI_API_KEY = sk-proj-br...
[2025-11-13 10:00:01] [SUCCESS] ✓ SECRET_KEY = 3505bf4420...
[2025-11-13 10:00:01] [SUCCESS] ✓ TAX_RATE = 0.08

[2025-11-13 10:00:01] [INFO] Checking DEPLOYMENT configuration variables:
[2025-11-13 10:00:01] [SUCCESS] ✓ SERVER_IP = 13.54.39.187
[2025-11-13 10:00:01] [SUCCESS] ✓ SERVER_USER = ubuntu
[2025-11-13 10:00:01] [SUCCESS] ✓ PEM_KEY_PATH = C:\Users\fujif\Downloads\tria.pem
[2025-11-13 10:00:01] [WARNING] ✓ ENVIRONMENT = production (PRODUCTION MODE)

================================================================================
                           STEP 3: Checking Git Status
================================================================================

[2025-11-13 10:00:02] [SUCCESS] ✓ Working directory is clean
[2025-11-13 10:00:02] [INFO] Current branch: main

================================================================================
                      STEP 4: Syncing .env to Server
================================================================================

[2025-11-13 10:00:03] [INFO] Copying .env to server...
[2025-11-13 10:00:04] [SUCCESS] ✓ .env file synced to server

================================================================================
                      STEP 5: Syncing Code via Git
================================================================================

[2025-11-13 10:00:05] [INFO] Pushing to git remote...
[2025-11-13 10:00:07] [SUCCESS] ✓ Pushed to git remote
[2025-11-13 10:00:07] [INFO] Connecting to server ubuntu@13.54.39.187...
[2025-11-13 10:00:09] [SUCCESS] ✓ Server code synced via git

================================================================================
                   STEP 6: Deploying to Server (PRODUCTION MODE)
================================================================================

[2025-11-13 10:00:10] [INFO] Deploying via docker-compose on server...
[2025-11-13 10:00:15] [INFO] Stopping existing containers...
[2025-11-13 10:00:18] [INFO] Building images...
[2025-11-13 10:05:22] [INFO] Starting containers...
[2025-11-13 10:05:30] [SUCCESS] ✓ Deployment completed

================================================================================
                         STEP 7: Verifying Deployment
================================================================================

[2025-11-13 10:05:35] [SUCCESS] ✓ Containers are running
[2025-11-13 10:05:40] [SUCCESS] ✓ API health check passed

================================================================================
                            DEPLOYMENT SUCCESSFUL
================================================================================

[2025-11-13 10:05:40] [SUCCESS] ✓ Application deployed to 13.54.39.187
[2025-11-13 10:05:40] [SUCCESS] ✓ Environment: production
[2025-11-13 10:05:40] [SUCCESS] ✓ Deployment completed

Access the application at:
  Backend:  http://13.54.39.187:8003
  API Docs: http://13.54.39.187:8003/docs
  Health:   http://13.54.39.187:8003/health
```

---

## 6. ROLLBACK PROCEDURE

### Automatic Rollback (Via Git)

```bash
# On server, rollback to previous commit
ssh -i C:\Users\fujif\Downloads\tria.pem ubuntu@13.54.39.187

cd ~/tria
git log --oneline -5  # Find previous commit hash

# Rollback
git checkout <previous-commit-hash>
docker-compose down
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8003/health
```

### Manual Rollback (If Git Doesn't Work)

```bash
# On local machine, revert commit
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria
git revert HEAD
git push origin main

# Deploy again
python scripts\deploy_agent.py
```

---

## 7. MONITORING AND TROUBLESHOOTING

### Health Checks

```bash
# Check all containers
docker-compose ps

# Check backend health
curl http://localhost:8003/health

# Check logs
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis

# Check resource usage
docker stats
```

### Common Issues

**Issue: "OPENAI_API_KEY not set"**
```bash
# Solution 1: Check .env on server
ssh ubuntu@13.54.39.187
cat ~/tria/.env | grep OPENAI_API_KEY

# Solution 2: Re-sync .env from local
# Edit local .env, then:
python scripts\deploy_agent.py
```

**Issue: Container won't start**
```bash
# Check logs
docker-compose logs backend

# Rebuild without cache
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Issue: Out of memory**
```bash
# Check memory usage
free -h
docker stats

# Solution: Upgrade to t3.medium (4GB) or restart containers
docker-compose restart
```

---

## 8. SECURITY CHECKLIST

- [ ] `.env` is in `.gitignore` (NEVER commit secrets)
- [ ] SSH key has correct permissions: `chmod 400 tria.pem`
- [ ] All secrets generated with: `openssl rand -base64 32`
- [ ] Different secrets for development vs production
- [ ] Firewall configured (ports 22, 80, 443, 8003 only)
- [ ] HTTPS configured with Let's Encrypt (for production domain)
- [ ] Regular backups of database volumes
- [ ] Secrets rotation schedule (every 90 days)

---

## 9. NEXT STEPS

### Immediate (Phase 1)

1. **Unify docker-compose.yml** - Merge the two files with profiles
2. **Update deploy_agent.py** - Remove manual env passing, add .env sync
3. **Create comprehensive .env.example** - Document all variables
4. **Test deployment** - Verify on t3.small instance
5. **Document deployment** - Update DEPLOYMENT.md

### Short-term (Phase 2)

6. **Set up monitoring** - Add CloudWatch or Grafana
7. **Configure backups** - Automated database backups
8. **Add HTTPS** - Let's Encrypt for production domain
9. **Set up CI/CD** - GitHub Actions with deployment agent
10. **Load testing** - Verify performance under load

### Long-term (Phase 3)

11. **High availability** - Multi-instance deployment
12. **Auto-scaling** - ECS or Kubernetes
13. **CDN** - CloudFront for static assets
14. **Managed services** - RDS for PostgreSQL, ElastiCache for Redis

---

## 10. SUMMARY

### Key Principles

1. **Git-based workflow**: Local → Git → Server (NEVER rsync/scp for code)
2. **Single source of truth**: One `.env` file, one `docker-compose.yml`
3. **Automated deployment**: Always use `deploy_agent.py` (never manual)
4. **Environment-aware**: `DEPLOYMENT_SIZE` and `ENVIRONMENT` flags control behavior
5. **No manual env passing**: Docker Compose reads `.env` automatically

### Critical Files

- **`.env`** - All configuration (NOT in git)
- **`.env.example`** - Template with documentation
- **`docker-compose.yml`** - Single compose file (profiles for sizing)
- **`scripts/deploy_agent.py`** - ONLY deployment method

### One Command Deployment

```bash
python scripts\deploy_agent.py
```

That's it. Everything else is automated.

---

**Author**: TRIA AI-BPO DevOps Team
**Last Updated**: 2025-11-13
**Version**: 1.0.0
