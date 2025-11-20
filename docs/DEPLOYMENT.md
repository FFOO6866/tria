# TRIA AI-BPO Deployment Guide

## Overview

This document describes the deployment strategy for the TRIA AI-BPO platform. The deployment uses a git-based workflow with Docker containers for consistency across environments.

## Deployment Philosophy

### Core Principles

1. **Same Configuration Everywhere**: Local and server environments use the same settings and environment variables
2. **Git-Based Sync**: Always use git to sync code between local and server (NEVER use rsync or direct file copy)
3. **Single Source of Truth**: Use the same `docker-compose.yml` and `.env.docker` on both environments
4. **Environment Flag Awareness**: Handle `ENVIRONMENT` flag carefully (development vs production)
5. **Documented Dependencies**: All docker-compose environment variables are documented and verified
6. **Agent-Based Deployment**: Never deploy without using the deployment agent

## Deployment Agent

### What is the Deployment Agent?

The deployment agent (`scripts/deploy_agent.py`) is a comprehensive Python script that handles the entire deployment workflow:

- ✅ Validates all required environment variables
- ✅ Checks git status and ensures code is synced
- ✅ Deploys via git (not rsync/copy)
- ✅ Passes all necessary env vars to docker-compose (prevents "OPENAI_API_KEY not set" errors)
- ✅ Verifies deployment success
- ✅ Provides troubleshooting guidance

### Why Use the Deployment Agent?

**Problem**: Docker-compose requires many environment variables. When running `docker-compose up -d` manually, it's easy to forget critical env vars like `OPENAI_API_KEY`, causing the application to fail silently or with cryptic errors.

**Solution**: The deployment agent automatically loads all required env vars from `.env.docker` and passes them explicitly to docker-compose, ensuring nothing is forgotten.

## Configuration Files

### `.env` (Main Configuration)

Contains:
- Local development settings
- Deployment configuration (SERVER_IP, PEM_KEY_PATH, etc.)
- ENVIRONMENT flag (development/production)

**Location**: Project root
**Version Control**: ❌ **NOT** committed (in `.gitignore`)
**Template**: `.env.example`

### `.env.docker` (Docker-Specific Configuration)

Contains:
- All variables required by docker-compose
- Database credentials
- API keys (OPENAI, Xero)
- Business configuration (TAX_RATE, etc.)

**Location**: Project root
**Version Control**: ❌ **NOT** committed (in `.gitignore`)
**Template**: `.env.docker.example`

### `.env.production` (Production Reference)

Production-ready configuration with security documentation.

**Location**: Project root
**Version Control**: ❌ **NOT** committed (in `.gitignore`)
**Template**: `.env.production.example`

## Required Environment Variables

### Critical Variables (MUST be set)

These are **required** for docker-compose to work. The deployment agent will fail if any are missing:

```bash
# Database
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=tria_aibpo
DATABASE_URL=postgresql://tria_admin:<password>@postgres:5432/tria_aibpo

# OpenAI (CRITICAL - docker-compose fails without this)
OPENAI_API_KEY=sk-proj-...

# Security
SECRET_KEY=<generated_secret_key>

# Business Configuration
TAX_RATE=0.08
XERO_SALES_ACCOUNT_CODE=200
XERO_TAX_TYPE=OUTPUT2
```

### Recommended Variables (Optional but recommended)

```bash
# Xero Integration (for accounting features)
XERO_CLIENT_ID=your_client_id
XERO_CLIENT_SECRET=your_client_secret
XERO_TENANT_ID=your_tenant_id
XERO_REFRESH_TOKEN=your_refresh_token
```

### Deployment Configuration (in `.env`)

```bash
# Server Configuration
SERVER_IP=192.168.1.100        # Your server IP
SERVER_USER=ubuntu              # SSH username
PEM_KEY_PATH=~/.ssh/server.pem  # Path to SSH key
ENVIRONMENT=development         # or 'production'
```

## Deployment Workflow

### Step 1: Initial Setup (One-Time)

#### On Local Machine:

1. **Copy environment templates**:
   ```bash
   cp .env.example .env
   cp .env.docker.example .env.docker
   ```

2. **Edit `.env`** and set deployment configuration:
   ```bash
   SERVER_IP=<your_server_ip>
   SERVER_USER=ubuntu
   PEM_KEY_PATH=~/.ssh/your-key.pem
   ENVIRONMENT=development
   ```

3. **Edit `.env.docker`** and set all required variables:
   - Database credentials
   - OPENAI_API_KEY
   - Business configuration
   - Optional: Xero credentials

#### On Server:

1. **Install Docker and Docker Compose**:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Clone repository**:
   ```bash
   cd ~  # or /opt or /var/www
   git clone <your-repo-url> tria
   cd tria
   ```

3. **Copy `.env.docker` from local** (one-time setup):
   ```bash
   # On local machine:
   scp -i ~/.ssh/your-key.pem .env.docker ubuntu@<server-ip>:~/tria/
   ```

4. **Ensure SSH key has correct permissions**:
   ```bash
   chmod 400 ~/.ssh/your-key.pem
   ```

### Step 2: Regular Deployment

Once initial setup is complete, use the deployment agent for all deployments:

```bash
# From project root on local machine:
python scripts/deploy_agent.py
```

The agent will:
1. ✅ Check all required files exist
2. ✅ Validate all environment variables
3. ✅ Check git status
4. ✅ Push changes to git remote
5. ✅ SSH to server and pull changes
6. ✅ Deploy with docker-compose (passing all env vars)
7. ✅ Verify deployment success

### Step 3: Verify Deployment

The agent automatically verifies deployment, but you can also check manually:

```bash
# Check container status
ssh -i ~/.ssh/your-key.pem ubuntu@<server-ip> 'docker-compose ps'

# Check logs
ssh -i ~/.ssh/your-key.pem ubuntu@<server-ip> 'docker-compose logs -f backend'

# Check API health
curl http://<server-ip>:8001/health
```

## Common Deployment Scenarios

### Scenario 1: Deploy Code Changes

```bash
# 1. Make changes
git add .
git commit -m "Your changes"

# 2. Deploy
python scripts/deploy_agent.py
```

### Scenario 2: Update Environment Variables

```bash
# 1. Edit .env.docker on local machine
nano .env.docker

# 2. Copy updated .env.docker to server
scp -i ~/.ssh/your-key.pem .env.docker ubuntu@<server-ip>:~/tria/

# 3. Deploy
python scripts/deploy_agent.py
```

### Scenario 3: Deploy to Production

```bash
# 1. Set ENVIRONMENT to production in .env
echo "ENVIRONMENT=production" >> .env

# 2. Review changes
git diff

# 3. Deploy (agent will ask for confirmation)
python scripts/deploy_agent.py
```

### Scenario 4: Rollback

```bash
# On server:
ssh -i ~/.ssh/your-key.pem ubuntu@<server-ip>

# Stop containers
docker-compose down

# Checkout previous commit
git checkout HEAD~1

# Restart containers
docker-compose up -d
```

## Troubleshooting

### Issue 1: OPENAI_API_KEY not set

**Symptom**: Backend fails with "OPENAI_API_KEY environment variable not set"

**Cause**: Environment variable not passed to docker-compose

**Solution**:
1. Verify `OPENAI_API_KEY` is set in `.env.docker`
2. Use deployment agent (it automatically passes all env vars)
3. If deploying manually, use:
   ```bash
   OPENAI_API_KEY="sk-..." docker-compose up -d
   ```

### Issue 2: Database Connection Error

**Symptom**: Backend fails to connect to PostgreSQL

**Causes & Solutions**:
- **Cause**: PostgreSQL container not running
  - **Solution**: `docker-compose up -d postgres`
- **Cause**: Wrong DATABASE_URL
  - **Solution**: Check `.env.docker` has `DATABASE_URL=postgresql://tria_admin:...@postgres:5432/tria_aibpo`
- **Cause**: Network issue
  - **Solution**: `docker-compose down && docker-compose up -d`

### Issue 3: Git Sync Fails

**Symptom**: Deployment agent can't pull changes on server

**Causes & Solutions**:
- **Cause**: Repository not cloned on server
  - **Solution**: Clone repo first: `git clone <repo-url> ~/tria`
- **Cause**: SSH key permissions wrong
  - **Solution**: `chmod 400 ~/.ssh/your-key.pem`
- **Cause**: Git not installed on server
  - **Solution**: `sudo apt-get install git`

### Issue 4: Port Already in Use

**Symptom**: Container fails to start, "port already allocated"

**Solutions**:
```bash
# Check what's using the port
sudo lsof -i :8001

# Stop conflicting service
sudo kill <PID>

# Or change port in docker-compose.yml
```

### Issue 5: Container Build Fails

**Symptom**: Docker build errors

**Solutions**:
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check disk space
df -h
```

### Issue 6: Production/Development Mix-up

**Symptom**: Wrong settings applied, demo data in production

**Causes & Solutions**:
- **Cause**: ENVIRONMENT variable not set correctly
  - **Solution**: Check `.env` has `ENVIRONMENT=production`
- **Cause**: Using wrong .env file
  - **Solution**: Verify `.env.docker` matches intended environment
- **Cause**: Hardcoded environment values
  - **Solution**: Search code for hardcoded environment strings

### Issue 7: Deployment Agent Permission Error

**Symptom**: "Permission denied" when running deployment agent

**Solution**:
```bash
chmod +x scripts/deploy_agent.py
python scripts/deploy_agent.py  # Use python instead of ./
```

## Best Practices

### 1. Always Use the Deployment Agent

❌ **DON'T** deploy manually:
```bash
# Manual deployment is error-prone
docker-compose up -d  # Might forget env vars!
```

✅ **DO** use the deployment agent:
```bash
python scripts/deploy_agent.py
```

### 2. Git-Based Workflow Only

❌ **DON'T** use rsync or scp for code:
```bash
# NEVER do this
rsync -avz . ubuntu@server:/opt/tria/
```

✅ **DO** use git:
```bash
# Correct workflow
git push origin main
python scripts/deploy_agent.py  # Agent pulls via git
```

### 3. Keep .env.docker Synchronized

- Update `.env.docker` on local machine first
- Copy to server using `scp`
- Deploy with deployment agent

### 4. Environment Awareness

- Always verify `ENVIRONMENT` variable before deploying
- Use different databases for development and production
- Never deploy with `DEMO_MODE=true` to production

### 5. Document All Changes

```bash
# Good commit messages help with rollback
git commit -m "Add customer validation feature"
git commit -m "Update Xero API integration"
git commit -m "Fix order processing bug"
```

### 6. Test Locally First

```bash
# Test with docker-compose locally
docker-compose up -d

# Verify everything works
curl http://localhost:8001/health

# Then deploy to server
python scripts/deploy_agent.py
```

## Deployment Checklist

Before every deployment:

- [ ] Changes committed to git
- [ ] Tests passing locally
- [ ] `.env.docker` updated with any new variables
- [ ] `ENVIRONMENT` flag verified (development/production)
- [ ] Deployment agent ready (`scripts/deploy_agent.py` exists)
- [ ] Server SSH access working
- [ ] Git remote accessible

During deployment:

- [ ] Use deployment agent (not manual commands)
- [ ] Monitor deployment output
- [ ] Check for errors or warnings
- [ ] Verify all containers start successfully

After deployment:

- [ ] Test API endpoints
- [ ] Check application logs
- [ ] Verify database connectivity
- [ ] Test critical features
- [ ] Monitor for errors

## Advanced Topics

### Multiple Environments

For staging/production separation:

1. Create separate `.env.staging` and `.env.production`
2. Update deployment agent to accept `--env` flag
3. Use different servers for each environment

### Blue-Green Deployment

For zero-downtime deployments:

1. Deploy to new containers (green)
2. Run health checks
3. Switch traffic from old (blue) to new (green)
4. Keep old containers for rollback

### Automated Deployments (CI/CD)

For GitHub Actions or similar:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [ main ]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy
        run: python scripts/deploy_agent.py --skip-git
        env:
          SERVER_IP: ${{ secrets.SERVER_IP }}
          PEM_KEY_PATH: ${{ secrets.PEM_KEY }}
```

## Security Considerations

### Environment Files

- ❌ **NEVER** commit `.env`, `.env.docker`, or `.env.production` to git
- ✅ Use secrets management for production (AWS Secrets Manager, Azure Key Vault, etc.)
- ✅ Rotate all secrets regularly (minimum every 90 days)

### SSH Keys

- Use strong key pairs (minimum 2048-bit RSA or ed25519)
- Set correct permissions: `chmod 400 key.pem`
- Never share private keys
- Use different keys for different environments

### API Keys

- Use different API keys for development and production
- Rotate keys regularly
- Monitor API usage for anomalies
- Use API key restrictions where possible

### Network Security

- Use firewall rules to restrict access
- Enable SSL/TLS for all connections
- Use private networks for database access
- Implement rate limiting

## Support

### Getting Help

1. Check this deployment guide
2. Run troubleshooting guide: `python scripts/deploy_agent.py --troubleshoot`
3. Check deployment logs: `cat deployment.log`
4. Check Docker logs: `docker-compose logs`

### Reporting Issues

When reporting deployment issues, include:
- Deployment command used
- Full error message
- Relevant logs from `deployment.log`
- Environment (development/production)
- Server OS and Docker version

---

**Last Updated**: 2025-11-07
**Version**: 1.0.0
**Maintainer**: TRIA AI-BPO DevOps Team
