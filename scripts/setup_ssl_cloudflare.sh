#!/bin/bash
################################################################################
# Cloudflare Tunnel SSL Setup (No Domain Required)
################################################################################
# This script sets up HTTPS using Cloudflare Tunnel
# - FREE HTTPS without a domain name
# - No DNS configuration needed
# - Automatic SSL certificate
# - Cloudflare-provided subdomain
#
# Result: Your app will be available at:
#   https://random-words-123.trycloudflare.com
#
# Usage:
#   ./scripts/setup_ssl_cloudflare.sh
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

################################################################################
# Main Setup
################################################################################

print_header "Cloudflare Tunnel SSL Setup (No Domain Required)"

echo "This will set up FREE HTTPS for your application using Cloudflare Tunnel."
echo ""
echo "Advantages:"
echo "  ✓ No domain name required"
echo "  ✓ Automatic HTTPS"
echo "  ✓ Free forever"
echo ""
echo "Limitations:"
echo "  ⚠ URL will be: https://random-words-123.trycloudflare.com"
echo "  ⚠ URL changes on restart (unless you use Cloudflare account)"
echo ""
read -p "Continue? (yes/no): " CONTINUE

if [ "$CONTINUE" != "yes" ]; then
    exit 0
fi

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Don't run this as root - run as normal user"
    exit 1
fi

print_header "Installing Cloudflared"

# Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."

    # Download and install
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i cloudflared-linux-amd64.deb
    rm cloudflared-linux-amd64.deb

    print_success "Cloudflared installed"
else
    print_success "Cloudflared already installed"
fi

print_header "Creating Tunnel Configuration"

# Create config directory
mkdir -p ~/.cloudflared

# Create tunnel config
cat > ~/.cloudflared/config.yml <<EOF
# Tria AIBPO Cloudflare Tunnel Configuration

tunnel: tria-aibpo
credentials-file: ~/.cloudflared/tria-aibpo.json

ingress:
  # Backend API
  - hostname: "*.trycloudflare.com"
    path: /api/*
    service: http://localhost:8003

  # Health check
  - hostname: "*.trycloudflare.com"
    path: /health
    service: http://localhost:8003

  # Frontend
  - hostname: "*.trycloudflare.com"
    service: http://localhost:3000

  # Catch-all
  - service: http_status:404
EOF

print_success "Tunnel configuration created"

print_header "Starting Tunnel"

echo "Starting Cloudflare tunnel..."
echo ""
print_warning "IMPORTANT: Keep this terminal window open!"
echo ""

# Start tunnel (this will run in foreground)
cloudflared tunnel --url http://localhost:8003

# Note: This script will block here until Ctrl+C
# The tunnel URL will be displayed in the output
