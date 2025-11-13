# Tria AI-BPO Deployment Quick Start

**Version**: 2.0.0 | **Target**: AWS EC2 t3.small (13.54.39.187) | **Date**: 2025-11-13

---

## One-Command Deployment

```bash
python scripts\deploy_agent_v2.py
```

That's it! Everything else is automated.

---

## First-Time Setup (5 Minutes)

### 1. Create .env File

```bash
# Copy template
cp .env.unified.example .env

# Edit with your values
notepad .env  # Windows
# or
nano .env     # Linux/Mac
```

### 2. Set These REQUIRED Values

```bash
# Server Configuration
SERVER_IP=13.54.39.187
SERVER_USER=ubuntu
PEM_KEY_PATH=C:\Users\fujif\Downloads\tria.pem
SERVER_PROJECT_PATH=/home/ubuntu/tria

# Environment
ENVIRONMENT=production
DEPLOYMENT_SIZE=small  # small=2GB, medium=4GB+

# Generate Passwords (use these commands)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)

# API Keys (CRITICAL!)
OPENAI_API_KEY=<your-key-from-platform.openai.com>

# Business Config
TAX_RATE=0.08
XERO_SALES_ACCOUNT_CODE=200
XERO_TAX_TYPE=TAX001

# Validation Limits
MAX_QUANTITY_PER_ITEM=10000
MAX_ORDER_TOTAL=100000.00
MAX_LINE_ITEMS=100
MIN_ORDER_TOTAL=0.01
```

### 3. Server Setup (One-Time)

```bash
# SSH into server
ssh -i C:\Users\fujif\Downloads\tria.pem ubuntu@13.54.39.187

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone repo
git clone https://github.com/fujifruity/tria.git ~/tria

# Log out and back in
exit
```

### 4. Deploy

```bash
# From local machine
python scripts\deploy_agent_v2.py
```

---

## Regular Deployment (30 Seconds)

```bash
# 1. Make changes
git add .
git commit -m "Your changes"

# 2. Deploy
python scripts\deploy_agent_v2.py

# 3. Verify
curl http://13.54.39.187:8003/health
```

---

## Key Commands

```bash
# Check configuration
python scripts\deploy_agent_v2.py --troubleshoot

# Deploy without git checks
python scripts\deploy_agent_v2.py --skip-git

# Deploy without verification
python scripts\deploy_agent_v2.py --skip-verify

# Check server status
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose ps'

# View logs
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose logs -f backend'

# Restart services
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose restart'
```

---

## Health Checks

```bash
# API Health
curl http://13.54.39.187:8003/health

# Container Status
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose ps'

# Resource Usage
ssh ubuntu@13.54.39.187 'docker stats --no-stream'

# Logs
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose logs --tail=100 backend'
```

---

## Troubleshooting

### Issue: OPENAI_API_KEY not set

```bash
# Fix in .env
nano .env
# Set: OPENAI_API_KEY=sk-proj-...

# Redeploy
python scripts\deploy_agent_v2.py
```

### Issue: Container won't start

```bash
# Check logs
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose logs backend'

# Rebuild
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose down && docker-compose build --no-cache && docker-compose up -d'
```

### Issue: Out of memory

```bash
# Check usage
ssh ubuntu@13.54.39.187 'free -h && docker stats --no-stream'

# Restart containers
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose restart'

# Or reduce workers in .env:
GUNICORN_WORKERS=1
```

### Issue: Git push fails

```bash
# Check authentication
git remote -v
git push origin main

# Re-authenticate with GitHub if needed
```

### Issue: SSH fails

```bash
# Check key permissions
# Windows: Properties → Security → Only your user
# Linux/Mac: chmod 400 tria.pem

# Test connection
ssh -i C:\Users\fujif\Downloads\tria.pem ubuntu@13.54.39.187
```

---

## Rollback

```bash
# Option 1: Git revert
git revert HEAD
git push origin main
python scripts\deploy_agent_v2.py

# Option 2: Server rollback
ssh ubuntu@13.54.39.187
cd ~/tria
git checkout HEAD~1
docker-compose down
docker-compose up -d
```

---

## File Structure

```
tria/
├── .env                          # Your configuration (NOT in git)
├── .env.example                  # Template
├── docker-compose.yml            # Service definitions
├── scripts/
│   └── deploy_agent.py           # Deployment automation
└── docs/
    ├── DEPLOYMENT.md             # Full guide
    └── DEPLOYMENT_ANALYSIS.md    # Technical details
```

---

## Key Principles

1. **Git-based workflow**: Code via git, .env via scp
2. **ONE .env file**: Single source of truth
3. **Automated deployment**: Always use deploy_agent.py
4. **No manual env passing**: Docker Compose reads .env automatically
5. **Environment-aware**: DEPLOYMENT_SIZE controls resources

---

## Environment Profiles

### t3.small (2GB RAM) - Backend Only

```bash
DEPLOYMENT_SIZE=small
POSTGRES_SHARED_BUFFERS=128MB
REDIS_MAX_MEMORY=200mb
GUNICORN_WORKERS=2

# Deploy
docker-compose up -d
```

### t3.medium (4GB+ RAM) - Full Stack

```bash
DEPLOYMENT_SIZE=medium
POSTGRES_SHARED_BUFFERS=256MB
REDIS_MAX_MEMORY=512mb
GUNICORN_WORKERS=4

# Deploy
docker-compose --profile full-stack up -d
```

---

## Critical Rules

### DO ✅

- ✅ Use `python scripts\deploy_agent_v2.py` for ALL deployments
- ✅ Use git for code sync (local → git → server)
- ✅ Use scp for .env sync (agent does this automatically)
- ✅ Keep .env out of git (.gitignore)
- ✅ Verify health after deployment

### DON'T ❌

- ❌ Deploy manually with docker-compose commands
- ❌ Use rsync/scp for code files
- ❌ Pass environment variables on command line
- ❌ Commit .env to git
- ❌ Skip validation checks

---

## Quick Reference

### Generate Secrets

```bash
# Passwords (32 characters)
openssl rand -base64 32

# Keys (64 hex characters)
openssl rand -hex 32
```

### Port Configuration

- **22**: SSH
- **80**: HTTP (nginx, full-stack only)
- **443**: HTTPS (nginx, full-stack only)
- **8003**: Backend API
- **3000**: Frontend (full-stack only)
- **5433**: PostgreSQL (mapped from 5432)
- **6379**: Redis

### Memory Allocation (t3.small)

- **PostgreSQL**: 400 MB
- **Redis**: 256 MB
- **Backend**: 1200 MB
- **System**: ~192 MB
- **Total**: 2048 MB (2 GB)

---

## Getting Help

```bash
# Show troubleshooting guide
python scripts\deploy_agent_v2.py --troubleshoot

# Check deployment logs
cat deployment.log

# Check Docker logs
ssh ubuntu@13.54.39.187 'cd ~/tria && docker-compose logs'

# Full documentation
# docs/DEPLOYMENT.md
# docs/DEPLOYMENT_ANALYSIS.md
```

---

## Success Checklist

- [ ] .env file created and configured
- [ ] Server has Docker and Docker Compose
- [ ] Repository cloned on server
- [ ] Deploy agent runs without errors
- [ ] All containers showing "Up (healthy)"
- [ ] Health check returns success
- [ ] API docs accessible
- [ ] No errors in logs

---

**Quick Start**: Copy `.env.unified.example` to `.env`, fill in values, run `python scripts\deploy_agent_v2.py`

**That's it!**
