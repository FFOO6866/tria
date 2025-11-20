# TRIA AI-BPO Scripts

This directory contains utility scripts for deployment, maintenance, and operations.

## 📜 Scripts Overview

### `deploy_agent.py` - Deployment Agent ⭐

**Purpose**: Automated deployment script that handles the complete deployment workflow for TRIA AI-BPO platform.

**Key Features**:
- ✅ Validates all required environment variables before deployment
- ✅ Checks git status and ensures code is synced via git
- ✅ Deploys using git workflow (local → git → server)
- ✅ Passes all environment variables to docker-compose (prevents forgotten env vars)
- ✅ Verifies deployment success with health checks
- ✅ Provides comprehensive troubleshooting guidance

**Usage**:

```bash
# Standard deployment (uses settings from .env)
python scripts/deploy_agent.py

# Deploy with custom server settings
python scripts/deploy_agent.py --server 192.168.1.100 --user ubuntu --key ~/.ssh/key.pem

# Skip git checks (for testing)
python scripts/deploy_agent.py --skip-git

# Skip deployment verification
python scripts/deploy_agent.py --skip-verify

# Show troubleshooting guide only
python scripts/deploy_agent.py --troubleshoot
```

**Prerequisites**:
1. `.env` file configured with deployment settings (SERVER_IP, PEM_KEY_PATH, etc.)
2. `.env.docker` file configured with application settings (OPENAI_API_KEY, DATABASE_URL, etc.)
3. SSH access to server with PEM key
4. Git repository initialized and remote configured
5. Docker and Docker Compose installed on server

**What It Does**:

1. **File Validation**: Checks that all required configuration files exist
2. **Environment Validation**: Verifies all required env vars are set in `.env.docker`:
   - Database settings (POSTGRES_USER, POSTGRES_PASSWORD, DATABASE_URL)
   - API keys (OPENAI_API_KEY - CRITICAL)
   - Security settings (SECRET_KEY)
   - Business configuration (TAX_RATE, XERO settings)
3. **Git Status Check**: Ensures working directory is clean or gets user confirmation
4. **Git Sync**:
   - Pushes changes to git remote
   - SSHs to server and pulls latest changes
5. **Docker Deployment**:
   - Stops existing containers
   - Pulls latest images
   - Rebuilds with no cache
   - Starts containers with ALL required env vars explicitly passed
6. **Verification**: Checks container status and API health endpoint

**Output**:

- Console output with colored status messages
- `deployment.log` file with detailed deployment history

**Critical Environment Variables**:

The deployment agent requires these variables in `.env.docker`:
```bash
# REQUIRED (deployment will fail if missing)
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
DATABASE_URL
OPENAI_API_KEY      # CRITICAL - most common failure point
SECRET_KEY
TAX_RATE
XERO_SALES_ACCOUNT_CODE
XERO_TAX_TYPE
```

**Why This Agent Exists**:

Manual deployment with `docker-compose up -d` is error-prone because:
- Easy to forget environment variables like OPENAI_API_KEY
- Manual git sync can be inconsistent
- No validation of configuration before deployment
- No verification of successful deployment
- Troubleshooting requires remembering many commands

The deployment agent solves all these issues by automating and validating the entire process.

**Troubleshooting**:

If deployment fails, the agent provides detailed error messages and troubleshooting guidance. For common issues, see:

```bash
python scripts/deploy_agent.py --troubleshoot
```

Or consult the full deployment guide:
```bash
cat docs/DEPLOYMENT.md
```

**Best Practices**:

1. ✅ **Always use the deployment agent** - Never deploy manually
2. ✅ **Verify ENVIRONMENT variable** - Confirm development vs production
3. ✅ **Test locally first** - Run `docker-compose up -d` locally before deploying
4. ✅ **Check deployment logs** - Review `deployment.log` after each deployment
5. ✅ **Keep .env.docker synchronized** - Update on server when changed locally

**Anti-Patterns** ❌:

- ❌ Running `docker-compose up -d` manually on server (missing env vars)
- ❌ Using rsync or scp to copy code (use git instead)
- ❌ Deploying without validating environment variables
- ❌ Skipping verification checks
- ❌ Not reading deployment logs when issues occur

## 🔧 Other Scripts

*(Add documentation for other scripts as they are created)*

## 📚 Related Documentation

- **Full Deployment Guide**: `docs/DEPLOYMENT.md`
- **Quick Reference**: `DEPLOYMENT_QUICK_REF.md`
- **Environment Config**: `.env.example`, `.env.docker.example`

## 🆘 Getting Help

1. Run troubleshooting guide: `python scripts/deploy_agent.py --troubleshoot`
2. Check deployment logs: `cat deployment.log`
3. Read full documentation: `docs/DEPLOYMENT.md`
4. Check Docker logs: `docker-compose logs`

---

**Maintainer**: TRIA AI-BPO DevOps Team
**Last Updated**: 2025-11-07
