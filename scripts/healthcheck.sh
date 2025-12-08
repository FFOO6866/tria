#!/bin/bash
# ==============================================================================
# TRIA AIBPO Health Check Script
# ==============================================================================
# Checks if the production site is healthy and sends alerts on failure.
#
# Installation:
#   chmod +x scripts/healthcheck.sh
#
# Cron (check every 5 minutes):
#   */5 * * * * /opt/tria/scripts/healthcheck.sh >> /var/log/tria-healthcheck.log 2>&1
#
# Environment variables (optional):
#   SLACK_WEBHOOK_URL - Slack webhook for alerts
#   PAGERDUTY_KEY - PagerDuty routing key
# ==============================================================================

set -e

# Configuration
HEALTH_URL="${HEALTH_URL:-https://tria.himeet.ai/health}"
TIMEOUT=10
MAX_RETRIES=3
LOG_FILE="/var/log/tria-healthcheck.log"

# Alert configuration (set these in environment)
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
PAGERDUTY_KEY="${PAGERDUTY_KEY:-}"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$TIMESTAMP] $1"
}

send_slack_alert() {
    local message="$1"
    local severity="$2"  # warning or critical

    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local color="warning"
        if [ "$severity" = "critical" ]; then
            color="danger"
        fi

        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"TRIA AIBPO Alert\",
                    \"text\": \"$message\",
                    \"footer\": \"Health Check | $TIMESTAMP\"
                }]
            }" > /dev/null 2>&1 || true
    fi
}

send_pagerduty_alert() {
    local message="$1"
    local severity="$2"

    if [ -n "$PAGERDUTY_KEY" ]; then
        curl -s -X POST "https://events.pagerduty.com/v2/enqueue" \
            -H 'Content-Type: application/json' \
            -d "{
                \"routing_key\": \"$PAGERDUTY_KEY\",
                \"event_action\": \"trigger\",
                \"payload\": {
                    \"summary\": \"$message\",
                    \"severity\": \"$severity\",
                    \"source\": \"tria-healthcheck\"
                }
            }" > /dev/null 2>&1 || true
    fi
}

check_health() {
    local retry=0
    local response=""
    local http_code=""

    while [ $retry -lt $MAX_RETRIES ]; do
        # Get HTTP response code and body
        response=$(curl -s -w "\n%{http_code}" --connect-timeout $TIMEOUT "$HEALTH_URL" 2>&1)
        http_code=$(echo "$response" | tail -1)
        body=$(echo "$response" | sed '$d')

        if [ "$http_code" = "200" ]; then
            # Check if response contains "healthy" status
            if echo "$body" | grep -q '"status":"healthy"'; then
                return 0
            fi

            # Check for degraded services
            if echo "$body" | grep -q '"chromadb":"not_initialized"'; then
                log "WARNING: ChromaDB not initialized"
                send_slack_alert "ChromaDB not initialized - RAG functionality degraded" "warning"
            fi

            return 0
        fi

        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            log "Retry $retry/$MAX_RETRIES..."
            sleep 5
        fi
    done

    return 1
}

# Main execution
log "Starting health check..."

if check_health; then
    log "Health check PASSED"
    exit 0
else
    log "Health check FAILED after $MAX_RETRIES retries"

    # Send alerts
    send_slack_alert "CRITICAL: TRIA AIBPO health check failed at $HEALTH_URL" "critical"
    send_pagerduty_alert "TRIA AIBPO health check failed" "critical"

    # Attempt auto-recovery
    log "Attempting service restart..."

    # Only restart if running as root or with sudo
    if [ "$(id -u)" = "0" ] || sudo -n true 2>/dev/null; then
        sudo systemctl restart tria-backend || log "Failed to restart tria-backend"

        # Wait and re-check
        sleep 30
        if check_health; then
            log "Service recovered after restart"
            send_slack_alert "RECOVERED: TRIA AIBPO service recovered after restart" "warning"
            exit 0
        else
            log "Service still unhealthy after restart"
            send_slack_alert "CRITICAL: TRIA AIBPO still unhealthy after restart - manual intervention required" "critical"
        fi
    else
        log "Cannot restart service - insufficient permissions"
    fi

    exit 1
fi
