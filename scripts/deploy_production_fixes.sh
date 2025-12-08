#!/bin/bash
# ==============================================================================
# TRIA AIBPO Production Fixes Deployment
# ==============================================================================
# This script deploys all production fixes to the server:
# 1. Updates nginx configuration for monitoring endpoints
# 2. Configures systemd service with auto-restart
# 3. Initializes ChromaDB knowledge base
# 4. Sets up health check cron job
# 5. Verifies all services are running
#
# Usage:
#   ./scripts/deploy_production_fixes.sh
#
# Prerequisites:
#   - SSH access to production server
#   - sudo privileges on production server
#   - .env file configured with all required variables
#
# NO MOCKS, NO SHORTCUTS - Production ready
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_DIR="${PROJECT_DIR:-/opt/tria}"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

echo "=============================================================="
echo "TRIA AIBPO PRODUCTION FIXES DEPLOYMENT"
echo "=============================================================="
echo ""

# Check if running on server
if [ ! -d "$PROJECT_DIR" ]; then
    log_error "This script must be run on the production server"
    log_error "Expected project directory: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# ==============================================================================
# STEP 1: Update Nginx Configuration
# ==============================================================================
echo ""
log_info "STEP 1: Updating Nginx Configuration..."

if [ -f "config/production/nginx-tria-aibpo.conf" ]; then
    sudo cp config/production/nginx-tria-aibpo.conf /etc/nginx/sites-available/tria-aibpo.conf
    sudo ln -sf /etc/nginx/sites-available/tria-aibpo.conf /etc/nginx/sites-enabled/tria-aibpo.conf

    # Test nginx configuration
    if sudo nginx -t; then
        sudo systemctl reload nginx
        log_info "Nginx configuration updated and reloaded"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
else
    log_warn "Nginx config not found - skipping"
fi

# ==============================================================================
# STEP 2: Update Systemd Service
# ==============================================================================
echo ""
log_info "STEP 2: Updating Systemd Service..."

if [ -f "config/production/tria-backend.service" ]; then
    sudo cp config/production/tria-backend.service /etc/systemd/system/tria-backend.service
    sudo systemctl daemon-reload
    sudo systemctl enable tria-backend
    log_info "Systemd service updated with auto-restart"
else
    log_warn "Systemd service file not found - skipping"
fi

# ==============================================================================
# STEP 3: Initialize ChromaDB
# ==============================================================================
echo ""
log_info "STEP 3: Initializing ChromaDB Knowledge Base..."

# Check if ChromaDB is already initialized
CHROMADB_STATUS=$(curl -s http://localhost:8001/health 2>/dev/null | grep -o '"chromadb":"[^"]*"' || echo 'chromadb_not_accessible')

if echo "$CHROMADB_STATUS" | grep -q "not_initialized"; then
    log_info "ChromaDB not initialized - running initialization..."

    if [ -f "$PYTHON" ]; then
        $PYTHON scripts/init_chromadb_if_empty.py
        if [ $? -eq 0 ]; then
            log_info "ChromaDB initialization complete"
        else
            log_error "ChromaDB initialization failed"
        fi
    else
        log_error "Python virtual environment not found at $VENV_DIR"
        exit 1
    fi
elif echo "$CHROMADB_STATUS" | grep -q "connected"; then
    log_info "ChromaDB already initialized - skipping"
else
    log_warn "Could not check ChromaDB status - will try initialization"
    $PYTHON scripts/init_chromadb_if_empty.py || true
fi

# ==============================================================================
# STEP 4: Setup Health Check Cron
# ==============================================================================
echo ""
log_info "STEP 4: Setting up Health Check Cron..."

# Make healthcheck script executable
chmod +x scripts/healthcheck.sh

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/tria-healthcheck.log
sudo chown ubuntu:ubuntu /var/log/tria-healthcheck.log

# Add cron job if not exists
CRON_JOB="*/5 * * * * $PROJECT_DIR/scripts/healthcheck.sh >> /var/log/tria-healthcheck.log 2>&1"
EXISTING_CRON=$(crontab -l 2>/dev/null | grep "healthcheck.sh" || true)

if [ -z "$EXISTING_CRON" ]; then
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    log_info "Health check cron job added (runs every 5 minutes)"
else
    log_info "Health check cron job already exists"
fi

# ==============================================================================
# STEP 5: Restart Services
# ==============================================================================
echo ""
log_info "STEP 5: Restarting Services..."

# Restart backend
sudo systemctl restart tria-backend
log_info "Backend service restarted"

# Wait for service to start
log_info "Waiting for service to start (30 seconds)..."
sleep 30

# ==============================================================================
# STEP 6: Verify Deployment
# ==============================================================================
echo ""
log_info "STEP 6: Verifying Deployment..."

# Check backend service
if sudo systemctl is-active --quiet tria-backend; then
    log_info "✓ Backend service is running"
else
    log_error "✗ Backend service is not running"
    sudo systemctl status tria-backend --no-pager || true
fi

# Check health endpoint
HEALTH_RESPONSE=$(curl -s http://localhost:8001/health)

if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    log_info "✓ Health endpoint returns healthy"
else
    log_warn "Health endpoint response: $HEALTH_RESPONSE"
fi

# Check ChromaDB
if echo "$HEALTH_RESPONSE" | grep -q '"chromadb":"connected"'; then
    log_info "✓ ChromaDB is connected"
elif echo "$HEALTH_RESPONSE" | grep -q '"chromadb":"not_initialized"'; then
    log_error "✗ ChromaDB still not initialized"
fi

# Check monitoring endpoints
echo ""
log_info "Checking monitoring endpoints..."

curl -s -o /dev/null -w "  /health: %{http_code}\n" http://localhost:8001/health
curl -s -o /dev/null -w "  /metrics: %{http_code}\n" http://localhost:8001/metrics || echo "  /metrics: not available"
curl -s -o /dev/null -w "  /docs: %{http_code}\n" http://localhost:8001/docs

# ==============================================================================
# STEP 7: Test Chatbot
# ==============================================================================
echo ""
log_info "STEP 7: Testing Chatbot API..."

CHATBOT_RESPONSE=$(curl -s -X POST "http://localhost:8001/api/chatbot" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $(uuidgen)" \
    -d '{"message":"hello","outlet_id":1,"user_id":"deploy_test","session_id":"deploy_test_123"}')

if echo "$CHATBOT_RESPONSE" | grep -q '"response"'; then
    log_info "✓ Chatbot API is responding"
elif echo "$CHATBOT_RESPONSE" | grep -q "trouble processing"; then
    log_error "✗ Chatbot API returning errors - check logs"
    echo "Response: $CHATBOT_RESPONSE"
else
    log_warn "Chatbot response: $CHATBOT_RESPONSE"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo "=============================================================="
echo "DEPLOYMENT COMPLETE"
echo "=============================================================="
echo ""
echo "Next steps:"
echo "  1. Monitor logs: sudo journalctl -u tria-backend -f"
echo "  2. Check health: curl https://tria.himeet.ai/health"
echo "  3. Test chatbot: curl -X POST https://tria.himeet.ai/api/chatbot ..."
echo "  4. Check cron: crontab -l"
echo ""
echo "If issues persist, check:"
echo "  - Backend logs: sudo journalctl -u tria-backend -n 100"
echo "  - Nginx logs: sudo tail -f /var/log/nginx/tria-error.log"
echo "  - Health check logs: tail -f /var/log/tria-healthcheck.log"
echo ""
