# DEPLOYMENT AGENT - Production Deployment Guide

**CRITICAL: This is the ONLY deployment procedure. Never deploy without following this guide.**

## 🎯 Core Principles

1. **Git-based workflow**: Local → Git → Server (NEVER rsync/scp)
2. **Consistent .env**: Same settings on local and server, only infrastructure URLs differ
3. **Docker Compose**: Use docker-compose.yml with .env file (NO manual env vars in commands)
4. **Environment awareness**: Watch for ENVIRONMENT=production/development flag
5. **Single source of truth**: This document contains all steps, commands, and troubleshooting

## 📋 Server Information

- **Elastic IP**: 13.214.14.130
- **Region**: ap-southeast-1 (Singapore)
- **SSH Key**: `C:\Users\fujif\Downloads\Tria (1).pem`
- **Server User**: ubuntu
- **Server Path**: /home/ubuntu/tria

## 🔧 Environment Variables Structure

### Local .env
```bash
# Environment
ENVIRONMENT=development

# Server Configuration (for deployment)
SERVER_IP=13.214.14.130
SSH_KEY_PATH=C:\Users\fujif\Downloads\Tria (1).pem
SSH_USER=ubuntu

# Database (local)
DATABASE_URL=postgresql://tria_user:tria_password@localhost:5432/tria_bpo

# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI
OPENAI_API_KEY=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

# Application
SECRET_KEY=your-secret-key-here
TAX_RATE=0.08

# Xero Integration
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_REDIRECT_URI=http://localhost:8003/api/xero/callback
XERO_SALES_ACCOUNT_CODE=200
XERO_TENANT_ID=your-tenant-id
```

### Server .env (Production)
```bash
# Environment
ENVIRONMENT=production

# Database (Docker service)
DATABASE_URL=postgresql://tria_user:tria_password@postgres:5432/tria_bpo

# Redis (Docker service)
REDIS_HOST=redis
REDIS_PORT=6379

# OpenAI (SAME AS LOCAL)
OPENAI_API_KEY=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

# Application (SAME AS LOCAL)
SECRET_KEY=your-secret-key-here
TAX_RATE=0.08

# Xero Integration (SAME AS LOCAL)
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_REDIRECT_URI=http://13.214.14.130:8003/api/xero/callback
XERO_SALES_ACCOUNT_CODE=200
XERO_TENANT_ID=your-tenant-id
```

**KEY DIFFERENCES**:
- `ENVIRONMENT`: development vs production
- `DATABASE_URL`: localhost vs postgres (Docker service name)
- `REDIS_HOST`: localhost vs redis (Docker service name)
- `XERO_REDIRECT_URI`: localhost vs server IP

**EVERYTHING ELSE MUST BE IDENTICAL**

## 🚀 Initial Server Setup (ONE-TIME)

### Step 1: SSH into Server
```bash
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130
```

### Step 2: Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose -y

# Install Nginx
sudo apt install nginx -y

# Install Git
sudo apt install git -y

# Log out and back in for docker group to take effect
exit
```

### Step 3: Configure Git on Server
```bash
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130

# Configure git
git config --global user.name "Tria Deployment"
git config --global user.email "deploy@tria-bpo.com"

# Set up SSH key for GitHub (if using private repo)
ssh-keygen -t ed25519 -C "deploy@tria-bpo.com"
cat ~/.ssh/id_ed25519.pub
# Add this key to GitHub: Settings > SSH and GPG keys > New SSH key
```

### Step 4: Clone Repository
```bash
cd /home/ubuntu
git clone https://github.com/your-username/tria.git
cd tria
```

### Step 5: Create Production .env
```bash
cd /home/ubuntu/tria

# Create .env file with production settings
cat > .env << 'EOF'
ENVIRONMENT=production
DATABASE_URL=postgresql://tria_user:tria_password@postgres:5432/tria_bpo
REDIS_HOST=redis
REDIS_PORT=6379
OPENAI_API_KEY=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
SECRET_KEY=your-secret-key-here
TAX_RATE=0.08
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_REDIRECT_URI=http://13.214.14.130:8003/api/xero/callback
XERO_SALES_ACCOUNT_CODE=200
XERO_TENANT_ID=your-tenant-id
EOF

# Verify .env file
cat .env
```

### Step 6: Configure Nginx
```bash
# Create Nginx config
sudo tee /etc/nginx/sites-available/tria > /dev/null << 'EOF'
server {
    listen 80;
    server_name 13.214.14.130;

    location / {
        proxy_pass http://localhost:8003;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/tria /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🔄 Deployment Workflow (EVERY DEPLOYMENT)

### Step 1: Local Development & Testing
```bash
# On local machine
cd "C:\Users\fujif\OneDrive\Documents\GitHub\tria"

# Test locally
docker-compose up -d
# Run tests, verify everything works
docker-compose down
```

### Step 2: Commit and Push to Git
```bash
# Add changes
git add .

# Commit with meaningful message
git commit -m "feat: Your feature description"

# Push to main branch
git push origin main
```

### Step 3: Deploy to Server
```bash
# SSH into server
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130

# Navigate to project directory
cd /home/ubuntu/tria

# Pull latest changes from Git
git pull origin main

# CRITICAL: Verify .env file exists and has correct settings
cat .env | grep -E "ENVIRONMENT|DATABASE_URL|REDIS_HOST|OPENAI_API_KEY"

# Expected output:
# ENVIRONMENT=production
# DATABASE_URL=postgresql://tria_user:tria_password@postgres:5432/tria_bpo
# REDIS_HOST=redis
# OPENAI_API_KEY=sk-proj-brP...

# Stop existing containers
docker-compose down

# Build new images
docker-compose build

# Start containers (NO manual env vars - uses .env file)
docker-compose up -d

# Wait for services to start
sleep 10

# Check container status
docker-compose ps

# Expected output: All containers should be "Up"
#     Name                   Command               State           Ports
# --------------------------------------------------------------------------------
# tria_backend_1    python src/enhanced_api.py       Up      0.0.0.0:8003->8003/tcp
# tria_postgres_1   docker-entrypoint.sh postgres    Up      5432/tcp
# tria_redis_1      docker-entrypoint.sh redis ...   Up      6379/tcp
```

### Step 4: Run Database Migration
```bash
# Run migration inside backend container
docker-compose exec backend python scripts/migrate_conversation_tables.py

# Verify migration succeeded
docker-compose logs backend | tail -20
```

### Step 5: Verify Deployment
```bash
# Check logs
docker-compose logs -f backend

# Press Ctrl+C to exit logs

# Test health endpoint from server
curl http://localhost:8003/health

# Test from outside (new terminal on local machine)
curl http://13.214.14.130/health

# Test chat endpoint
curl -X POST http://13.214.14.130/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!","user_id":"test","session_id":"test123"}'
```

### Step 6: Monitor Deployment
```bash
# Watch logs in real-time
docker-compose logs -f backend

# Check container resources
docker stats

# Check Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

## 🔍 Troubleshooting Guide

### Issue 1: "OPENAI_API_KEY not set"

**Cause**: .env file missing or incorrect

**Fix**:
```bash
# Verify .env exists
cat /home/ubuntu/tria/.env | grep OPENAI_API_KEY

# If missing, recreate .env file (see Step 5 in Initial Setup)

# Restart containers
docker-compose down
docker-compose up -d
```

### Issue 2: "Database connection failed"

**Cause**: DATABASE_URL pointing to wrong host

**Fix**:
```bash
# Verify DATABASE_URL in .env
cat /home/ubuntu/tria/.env | grep DATABASE_URL

# Should be: postgresql://tria_user:tria_password@postgres:5432/tria_bpo
# NOT: postgresql://...@localhost:5432/...

# If wrong, fix .env and restart
docker-compose down
docker-compose up -d
```

### Issue 3: "Redis connection failed"

**Cause**: REDIS_HOST pointing to wrong host

**Fix**:
```bash
# Verify REDIS_HOST in .env
cat /home/ubuntu/tria/.env | grep REDIS_HOST

# Should be: redis
# NOT: localhost

# If wrong, fix .env and restart
docker-compose down
docker-compose up -d
```

### Issue 4: Container build fails

**Cause**: Dependency issue or code error

**Fix**:
```bash
# Check build logs
docker-compose build 2>&1 | tee build.log

# Clean Docker cache and rebuild
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

### Issue 5: Nginx not working

**Cause**: Nginx misconfiguration or not running

**Fix**:
```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx error logs
sudo tail -50 /var/log/nginx/error.log

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Issue 6: Port 8003 already in use

**Cause**: Old container still running

**Fix**:
```bash
# Find process using port 8003
sudo lsof -i :8003

# Kill old containers
docker-compose down
docker ps -a | grep tria | awk '{print $1}' | xargs -r docker rm -f

# Restart
docker-compose up -d
```

## 📊 Pre-Deployment Checklist

Before EVERY deployment, verify:

- [ ] Code tested locally
- [ ] All tests passing
- [ ] Changes committed to git
- [ ] Changes pushed to GitHub
- [ ] .env file on server has correct settings
- [ ] ENVIRONMENT=production in server .env
- [ ] DATABASE_URL uses "postgres" not "localhost"
- [ ] REDIS_HOST uses "redis" not "localhost"
- [ ] OPENAI_API_KEY matches local .env

## 🚨 NEVER DO THESE

1. ❌ NEVER use `rsync` or `scp` to copy files
2. ❌ NEVER run `docker-compose up` with manual `-e` env vars
3. ❌ NEVER edit code directly on server
4. ❌ NEVER have different API keys between local and server
5. ❌ NEVER skip testing locally before deploying
6. ❌ NEVER deploy without pulling from git
7. ❌ NEVER use `localhost` in production .env

## ✅ ALWAYS DO THESE

1. ✅ ALWAYS use git to sync code (local → git → server)
2. ✅ ALWAYS use docker-compose with .env file (no manual env vars)
3. ✅ ALWAYS verify .env before starting containers
4. ✅ ALWAYS check ENVIRONMENT flag (development vs production)
5. ✅ ALWAYS test locally before deploying
6. ✅ ALWAYS run migration after deployment
7. ✅ ALWAYS verify health endpoint after deployment

## 🔄 Quick Deployment Command Reference

```bash
# Local: Push to Git
git add . && git commit -m "Your message" && git push origin main

# Server: Deploy
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130 << 'EOF'
cd /home/ubuntu/tria
git pull origin main
cat .env | grep -E "ENVIRONMENT|DATABASE_URL|REDIS_HOST|OPENAI_API_KEY"
docker-compose down
docker-compose build
docker-compose up -d
sleep 10
docker-compose ps
docker-compose exec backend python scripts/migrate_conversation_tables.py
curl http://localhost:8003/health
EOF

# Local: Verify
curl http://13.214.14.130/health
```

## 📝 Deployment Log Template

**Date**: YYYY-MM-DD HH:MM
**Deployed by**: Your Name
**Commit**: `git log -1 --oneline`
**Changes**:
- Feature/fix 1
- Feature/fix 2

**Verification**:
- [ ] Health endpoint: OK
- [ ] Chat endpoint: OK
- [ ] Database migration: OK
- [ ] Logs: No errors

**Issues**: None / [Describe any issues]

---

**REMEMBER**: This is the ONLY way to deploy. If you're not following this guide, STOP and use this guide.
