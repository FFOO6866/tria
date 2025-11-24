#!/bin/bash
################################################################################
# SSL Setup Script for Tria AIBPO
################################################################################
# This script sets up HTTPS for your production server using:
# - Let's Encrypt SSL certificate (free, auto-renewing)
# - Nginx reverse proxy
# - Automatic HTTP → HTTPS redirect
#
# Prerequisites:
# - Domain name pointing to your server (A record)
# - Port 80 and 443 open in firewall
# - Root or sudo access
#
# Usage:
#   ./scripts/setup_ssl.sh yourdomain.com your-email@example.com
#
# Example:
#   ./scripts/setup_ssl.sh aibpo.com admin@aibpo.com
################################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN=$1
EMAIL=$2
APP_PORT=8003
FRONTEND_PORT=3000

################################################################################
# Functions
################################################################################

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

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check arguments
    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        print_error "Missing required arguments"
        echo ""
        echo "Usage: $0 <domain> <email>"
        echo "Example: $0 aibpo.com admin@aibpo.com"
        exit 1
    fi

    print_success "Domain: $DOMAIN"
    print_success "Email: $EMAIL"

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root or with sudo"
        exit 1
    fi

    # Check DNS resolution
    echo ""
    echo "Checking DNS resolution..."
    if ! host "$DOMAIN" > /dev/null 2>&1; then
        print_error "Domain $DOMAIN does not resolve"
        echo ""
        echo "Please ensure:"
        echo "  1. Your domain's A record points to this server's IP"
        echo "  2. DNS has propagated (can take up to 48 hours)"
        echo ""
        exit 1
    fi

    RESOLVED_IP=$(host "$DOMAIN" | grep "has address" | awk '{print $4}')
    SERVER_IP=$(curl -s ifconfig.me)

    echo "Domain resolves to: $RESOLVED_IP"
    echo "Server IP: $SERVER_IP"

    if [ "$RESOLVED_IP" != "$SERVER_IP" ]; then
        print_warning "Domain IP ($RESOLVED_IP) doesn't match server IP ($SERVER_IP)"
        echo ""
        echo "This might cause SSL certificate issuance to fail."
        read -p "Continue anyway? (yes/no): " CONTINUE
        if [ "$CONTINUE" != "yes" ]; then
            exit 1
        fi
    fi

    print_success "Prerequisites check passed"
}

install_dependencies() {
    print_header "Installing Dependencies"

    # Update package list
    echo "Updating package list..."
    apt-get update -qq

    # Install nginx
    if ! command -v nginx &> /dev/null; then
        echo "Installing nginx..."
        apt-get install -y nginx
        print_success "Nginx installed"
    else
        print_success "Nginx already installed"
    fi

    # Install certbot
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        apt-get install -y certbot python3-certbot-nginx
        print_success "Certbot installed"
    else
        print_success "Certbot already installed"
    fi
}

configure_firewall() {
    print_header "Configuring Firewall"

    # Check if ufw is installed
    if command -v ufw &> /dev/null; then
        echo "Configuring UFW firewall..."

        # Allow SSH (important!)
        ufw allow 22/tcp

        # Allow HTTP and HTTPS
        ufw allow 80/tcp
        ufw allow 443/tcp

        # Enable firewall
        ufw --force enable

        print_success "Firewall configured"
    else
        print_warning "UFW not installed, skipping firewall configuration"
        echo "Ensure ports 80 and 443 are open in your cloud provider's security group"
    fi
}

create_nginx_config() {
    print_header "Creating Nginx Configuration"

    # Backup existing config if it exists
    if [ -f "/etc/nginx/sites-available/$DOMAIN" ]; then
        cp "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-available/$DOMAIN.backup.$(date +%Y%m%d_%H%M%S)"
        print_success "Backed up existing config"
    fi

    # Create nginx config
    cat > "/etc/nginx/sites-available/$DOMAIN" <<EOF
# Tria AIBPO - Initial HTTP configuration
# SSL will be added by certbot

upstream backend {
    server 127.0.0.1:$APP_PORT;
    keepalive 64;
}

upstream frontend {
    server 127.0.0.1:$FRONTEND_PORT;
    keepalive 64;
}

# HTTP server (will be redirected to HTTPS after SSL setup)
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    # Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        access_log off;
    }

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

    print_success "Nginx config created"

    # Create symlink to enable site
    ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
    print_success "Site enabled"

    # Remove default site if it exists
    if [ -f "/etc/nginx/sites-enabled/default" ]; then
        rm -f "/etc/nginx/sites-enabled/default"
        print_success "Removed default site"
    fi

    # Test nginx configuration
    echo ""
    echo "Testing nginx configuration..."
    if nginx -t; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration test failed"
        exit 1
    fi

    # Reload nginx
    echo "Reloading nginx..."
    systemctl reload nginx
    print_success "Nginx reloaded"
}

obtain_ssl_certificate() {
    print_header "Obtaining SSL Certificate"

    echo "Requesting SSL certificate from Let's Encrypt..."
    echo "This may take a minute..."
    echo ""

    # Run certbot
    if certbot --nginx \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --redirect \
        --hsts \
        --staple-ocsp; then

        print_success "SSL certificate obtained successfully"
    else
        print_error "Failed to obtain SSL certificate"
        echo ""
        echo "Common issues:"
        echo "  1. Domain doesn't point to this server"
        echo "  2. Port 80 is not accessible"
        echo "  3. Rate limit reached (5 certs per week per domain)"
        echo ""
        exit 1
    fi
}

setup_auto_renewal() {
    print_header "Setting Up Auto-Renewal"

    # Test renewal
    echo "Testing certificate renewal..."
    if certbot renew --dry-run; then
        print_success "Certificate renewal test passed"
    else
        print_warning "Certificate renewal test failed"
        echo "Manual renewal may be required"
    fi

    # Certbot automatically sets up a systemd timer for renewal
    print_success "Auto-renewal configured (certbot timer)"
}

update_application_config() {
    print_header "Updating Application Configuration"

    # Find .env file
    if [ -f ".env" ]; then
        ENV_FILE=".env"
    elif [ -f "/home/ubuntu/tria/.env" ]; then
        ENV_FILE="/home/ubuntu/tria/.env"
    else
        print_warning ".env file not found in current directory"
        echo "Please manually update XERO_REDIRECT_URI to: https://$DOMAIN/api/xero/callback"
        return
    fi

    echo "Updating $ENV_FILE..."

    # Backup .env
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"

    # Update XERO_REDIRECT_URI
    if grep -q "XERO_REDIRECT_URI" "$ENV_FILE"; then
        sed -i "s|XERO_REDIRECT_URI=.*|XERO_REDIRECT_URI=https://$DOMAIN/api/xero/callback|" "$ENV_FILE"
        print_success "Updated XERO_REDIRECT_URI in .env"
    else
        echo "XERO_REDIRECT_URI=https://$DOMAIN/api/xero/callback" >> "$ENV_FILE"
        print_success "Added XERO_REDIRECT_URI to .env"
    fi

    echo ""
    print_warning "IMPORTANT: Update Xero app settings!"
    echo ""
    echo "Go to: https://developer.xero.com/app/manage"
    echo "Update redirect URI to: https://$DOMAIN/api/xero/callback"
}

verify_ssl() {
    print_header "Verifying SSL Setup"

    echo "Testing HTTPS connection..."

    # Wait for nginx to reload
    sleep 2

    # Test HTTPS
    if curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/health" | grep -q "200"; then
        print_success "HTTPS connection successful"
    else
        print_warning "HTTPS health check returned non-200 status"
        echo "This might be normal if backend is not running yet"
    fi

    # Check certificate
    echo ""
    echo "Certificate information:"
    echo "Issued by: Let's Encrypt"
    echo "Valid for: $DOMAIN"
    echo "Expires: $(date -d "$(openssl x509 -in /etc/letsencrypt/live/$DOMAIN/cert.pem -noout -enddate | cut -d= -f2)" '+%Y-%m-%d')"
    echo ""

    print_success "SSL setup complete!"
}

print_next_steps() {
    print_header "Next Steps"

    echo -e "${GREEN}SSL has been successfully configured!${NC}"
    echo ""
    echo "Your application is now available at:"
    echo -e "  ${BLUE}https://$DOMAIN${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Update Xero App Settings:"
    echo "   - Go to: https://developer.xero.com/app/manage"
    echo "   - Update redirect URI to: https://$DOMAIN/api/xero/callback"
    echo ""
    echo "2. Restart Your Application:"
    echo "   docker-compose restart"
    echo "   # Or:"
    echo "   systemctl restart tria-backend"
    echo ""
    echo "3. Test HTTPS:"
    echo "   curl https://$DOMAIN/health"
    echo ""
    echo "4. Get New Xero Tokens (with HTTPS redirect):"
    echo "   python scripts/get_xero_tokens.py"
    echo ""
    echo "Certificate Auto-Renewal:"
    echo "  - Certbot will automatically renew before expiry"
    echo "  - Check status: certbot renew --dry-run"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "Tria AIBPO - SSL Setup Script"

    check_prerequisites
    install_dependencies
    configure_firewall
    create_nginx_config
    obtain_ssl_certificate
    setup_auto_renewal
    update_application_config
    verify_ssl
    print_next_steps

    echo ""
    print_success "SSL setup completed successfully!"
    echo ""
}

# Run main function
main "$@"
