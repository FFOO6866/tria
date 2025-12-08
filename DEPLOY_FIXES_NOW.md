# DEPLOY PRODUCTION FIXES NOW

**Date**: 2025-12-08
**Status**: Ready to Deploy
**Priority**: P0 - Critical

---

## Quick Deploy Commands

SSH to production server and run these commands:

```bash
# 1. SSH to server
ssh ubuntu@13.214.14.130

# 2. Go to project directory
cd /opt/tria

# 3. Pull latest changes
git pull origin main

# 4. Run deployment script
chmod +x scripts/deploy_production_fixes.sh
./scripts/deploy_production_fixes.sh
```

---

## What Gets Deployed

### 1. ChromaDB Initialization (CRITICAL)
**File**: `scripts/init_chromadb_if_empty.py`
- Checks if ChromaDB collections are empty
- If empty, indexes all policy markdown files
- Runs automatically at service startup

### 2. Nginx Configuration
**File**: `config/production/nginx-tria-aibpo.conf`
- Exposes `/metrics` endpoint for Prometheus
- Exposes `/docs` and `/redoc` for API documentation
- Rate limiting on API endpoints
- Proper proxy headers for all routes

### 3. Systemd Service with Auto-Restart
**File**: `config/production/tria-backend.service`
- `Restart=always` - Auto-restart on crash
- `RestartSec=10` - Wait 10 seconds before restart
- `WatchdogSec=30` - Restart if unresponsive for 30s
- `ExecStartPre` - Initialize ChromaDB before starting

### 4. Health Check Cron
**File**: `scripts/healthcheck.sh`
- Runs every 5 minutes via cron
- Checks `/health` endpoint
- Sends Slack/PagerDuty alerts on failure
- Attempts auto-recovery by restarting service

---

## Manual Steps (If Script Fails)

### Fix ChromaDB Manually

```bash
# Activate virtual environment
source /opt/tria/.venv/bin/activate

# Run initialization script
python scripts/init_chromadb_if_empty.py

# Or run full knowledge base build
python scripts/build_knowledge_base_from_markdown.py

# Verify
python -c "from src.rag.chroma_client import health_check; print(health_check())"
```

### Update Nginx Manually

```bash
# Copy nginx config
sudo cp config/production/nginx-tria-aibpo.conf /etc/nginx/sites-available/tria-aibpo.conf

# Enable site
sudo ln -sf /etc/nginx/sites-available/tria-aibpo.conf /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

### Update Systemd Manually

```bash
# Copy service file
sudo cp config/production/tria-backend.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and restart
sudo systemctl enable tria-backend
sudo systemctl restart tria-backend

# Check status
sudo systemctl status tria-backend
```

### Setup Health Check Cron

```bash
# Make script executable
chmod +x scripts/healthcheck.sh

# Add to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/tria/scripts/healthcheck.sh >> /var/log/tria-healthcheck.log 2>&1") | crontab -

# Verify
crontab -l
```

---

## Verification After Deployment

```bash
# 1. Check health
curl https://tria.himeet.ai/health | jq .

# Expected:
# "chromadb": "connected" (NOT "not_initialized")

# 2. Check monitoring endpoints
curl -I https://tria.himeet.ai/docs
# Expected: HTTP 200

curl -I https://tria.himeet.ai/metrics
# Expected: HTTP 200

# 3. Test chatbot
curl -X POST "https://tria.himeet.ai/api/chatbot" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"message":"hello","outlet_id":1,"user_id":"test","session_id":"test123"}'

# Expected: Valid response with "response" field (not error message)
```

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/init_chromadb_if_empty.py` | Auto-initialize ChromaDB at startup |
| `scripts/deploy_production_fixes.sh` | One-click deployment script |
| `scripts/healthcheck.sh` | Health monitoring with alerting |
| `config/production/nginx-tria-aibpo.conf` | Nginx configuration |
| `config/production/tria-backend.service` | Systemd service with auto-restart |

---

## Troubleshooting

### ChromaDB Still Shows "not_initialized"

```bash
# Check if policy files exist
ls -la /opt/tria/docs/policy/en/*.md

# Check OpenAI API key
echo $OPENAI_API_KEY | head -c 10

# Run with verbose output
python scripts/init_chromadb_if_empty.py 2>&1 | tee init.log
```

### Chatbot Still Returns Errors

```bash
# Check backend logs
sudo journalctl -u tria-backend -n 100 --no-pager

# Check for Python errors
sudo journalctl -u tria-backend | grep -i error | tail -20
```

### Nginx Returns 502

```bash
# Check if backend is running
curl http://localhost:8001/health

# Check nginx error log
sudo tail -f /var/log/nginx/tria-error.log
```

---

**Deploy now to fix production!**
