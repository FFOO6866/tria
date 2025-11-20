#!/bin/bash
# Tria AIBPO - Ubuntu Server Deployment Script
# Automates complete production setup on Ubuntu 20.04+ servers
#
# Usage:
#   sudo ./scripts/deploy_ubuntu.sh [options]
#
# Options:
#   --production    Use Let's Encrypt SSL certificates (requires domain)
#   --dev           Use self-signed certificates (default)
#   --domain=DOMAIN Set domain name for production SSL
#   --email=EMAIL   Set email for Let's Encrypt notifications

set -e  # Exit on error
set -u  # Exit on undefined variable

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_USER="${DEPLOY_USER:-tria}"
APP_DIR="${APP_DIR:-/opt/tria-aibpo}"

# Deployment mode
DEPLOY_MODE="dev"
DOMAIN=""
EMAIL=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot detect OS. This script is designed for Ubuntu."
        exit 1
    fi

    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        log_error "This script is designed for Ubuntu. Detected: $ID"
        exit 1
    fi

    VERSION_NUM=$(echo "$VERSION_ID" | cut -d. -f1)
    if [[ $VERSION_NUM -lt 20 ]]; then
        log_error "Ubuntu 20.04 or higher required. Detected: $VERSION_ID"
        exit 1
    fi

    log_success "Ubuntu $VERSION_ID detected"
}

# =============================================================================
# System Requirements
# =============================================================================

check_system_requirements() {
    log_info "Checking system requirements..."

    # Memory check (minimum 2GB recommended)
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $TOTAL_MEM -lt 1800 ]]; then
        log_warning "System has ${TOTAL_MEM}MB RAM. Minimum 2GB recommended."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_success "Memory: ${TOTAL_MEM}MB"
    fi

    # Disk space check (minimum 10GB)
    AVAILABLE_DISK=$(df -BG "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $AVAILABLE_DISK -lt 10 ]]; then
        log_warning "Available disk space: ${AVAILABLE_DISK}GB. Minimum 10GB recommended."
    else
        log_success "Disk space: ${AVAILABLE_DISK}GB available"
    fi

    # CPU check
    CPU_CORES=$(nproc)
    log_success "CPU cores: $CPU_CORES"
}

# =============================================================================
# Install Dependencies
# =============================================================================

install_docker() {
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        log_info "Docker already installed: $DOCKER_VERSION"
        return 0
    fi

    log_info "Installing Docker..."

    # Update package index
    apt-get update -qq

    # Install prerequisites
    apt-get install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start Docker service
    systemctl enable docker
    systemctl start docker

    log_success "Docker installed successfully"
}

install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f4 | cut -d',' -f1)
        log_info "Docker Compose already installed: $COMPOSE_VERSION"
        return 0
    fi

    log_info "Installing Docker Compose..."

    # Install Docker Compose standalone (fallback if plugin not available)
    COMPOSE_VERSION="2.24.5"
    curl -L "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose

    log_success "Docker Compose installed successfully"
}

install_system_dependencies() {
    log_info "Installing system dependencies..."

    apt-get update -qq
    apt-get install -y -qq \
        git \
        curl \
        wget \
        ufw \
        certbot \
        python3-certbot-nginx \
        jq \
        htop \
        vim \
        net-tools

    log_success "System dependencies installed"
}

# =============================================================================
# User and Directory Setup
# =============================================================================

setup_deploy_user() {
    if id "$DEPLOY_USER" &>/dev/null; then
        log_info "Deploy user '$DEPLOY_USER' already exists"
    else
        log_info "Creating deploy user: $DEPLOY_USER"
        useradd -m -s /bin/bash "$DEPLOY_USER"
        log_success "User created: $DEPLOY_USER"
    fi

    # Add user to docker group
    usermod -aG docker "$DEPLOY_USER"
    log_success "User added to docker group"
}

setup_directories() {
    log_info "Setting up application directories..."

    # Create application directory
    mkdir -p "$APP_DIR"

    # Copy project files
    if [[ "$PROJECT_ROOT" != "$APP_DIR" ]]; then
        log_info "Copying project files to $APP_DIR..."
        rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
            "$PROJECT_ROOT/" "$APP_DIR/"
    fi

    # Create required directories
    mkdir -p "$APP_DIR/logs/nginx"
    mkdir -p "$APP_DIR/data/chromadb_cache"
    mkdir -p "$APP_DIR/nginx/ssl"

    # Set permissions
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"
    chmod 755 "$APP_DIR"

    log_success "Directories configured"
}

# =============================================================================
# Environment Configuration
# =============================================================================

setup_environment() {
    log_info "Setting up environment configuration..."

    ENV_FILE="$APP_DIR/.env"

    if [[ -f "$ENV_FILE" ]]; then
        log_info ".env file already exists"
        read -p "Overwrite existing .env? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Using existing .env file"
            return 0
        fi
    fi

    # Copy .env.example if it exists
    if [[ -f "$APP_DIR/.env.example" ]]; then
        cp "$APP_DIR/.env.example" "$ENV_FILE"
        log_success ".env file created from template"
    else
        log_warning ".env.example not found. Creating minimal .env..."
        cat > "$ENV_FILE" << 'EOF'
# Database Configuration
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD_123
POSTGRES_DB=tria_aibpo

# Redis Configuration
REDIS_PASSWORD=CHANGE_THIS_REDIS_PASSWORD_456

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Security
SECRET_KEY=CHANGE_THIS_SECRET_KEY_789

# Application
ENVIRONMENT=production
EOF
        log_success "Minimal .env file created"
    fi

    # Set secure permissions
    chmod 600 "$ENV_FILE"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$ENV_FILE"

    log_warning "IMPORTANT: Edit $ENV_FILE and configure all required environment variables"
}

# =============================================================================
# SSL Certificate Setup
# =============================================================================

generate_self_signed_cert() {
    log_info "Generating self-signed SSL certificates..."

    SSL_DIR="$APP_DIR/nginx/ssl"

    openssl req -x509 \
        -nodes \
        -days 365 \
        -newkey rsa:2048 \
        -keyout "$SSL_DIR/tria.key" \
        -out "$SSL_DIR/tria.crt" \
        -subj "/C=SG/ST=Singapore/L=Singapore/O=Tria AIBPO/OU=Production/CN=tria.local" \
        -addext "subjectAltName=DNS:tria.local,DNS:localhost,IP:127.0.0.1"

    chmod 600 "$SSL_DIR/tria.key"
    chmod 644 "$SSL_DIR/tria.crt"

    log_success "Self-signed certificates generated"
    log_warning "Self-signed certificates are for DEVELOPMENT/TESTING only"
}

setup_letsencrypt() {
    if [[ -z "$DOMAIN" ]]; then
        log_error "Domain name required for Let's Encrypt. Use --domain=yourdomain.com"
        exit 1
    fi

    if [[ -z "$EMAIL" ]]; then
        log_error "Email required for Let's Encrypt. Use --email=you@example.com"
        exit 1
    fi

    log_info "Setting up Let's Encrypt certificates for $DOMAIN..."

    # Stop nginx if running
    docker-compose -f "$APP_DIR/docker-compose.yml" stop nginx 2>/dev/null || true

    # Obtain certificate
    certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        -d "$DOMAIN"

    # Create symbolic links in nginx/ssl directory
    SSL_DIR="$APP_DIR/nginx/ssl"
    ln -sf "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/tria.crt"
    ln -sf "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/tria.key"

    # Set up auto-renewal
    systemctl enable certbot.timer
    systemctl start certbot.timer

    log_success "Let's Encrypt certificates configured"
    log_info "Auto-renewal enabled via certbot.timer"
}

setup_ssl() {
    if [[ "$DEPLOY_MODE" == "production" ]]; then
        setup_letsencrypt
    else
        generate_self_signed_cert
    fi
}

# =============================================================================
# Firewall Configuration
# =============================================================================

configure_firewall() {
    log_info "Configuring firewall (UFW)..."

    # Enable UFW if not already enabled
    if ! ufw status | grep -q "Status: active"; then
        log_info "Enabling UFW..."
        ufw --force enable
    fi

    # Allow SSH (critical!)
    ufw allow 22/tcp comment 'SSH'

    # Allow HTTP/HTTPS
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'

    # Reload firewall
    ufw reload

    log_success "Firewall configured"
    log_info "Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)"
}

# =============================================================================
# Application Deployment
# =============================================================================

build_and_deploy() {
    log_info "Building and deploying application..."

    cd "$APP_DIR"

    # Pull latest Docker images
    log_info "Pulling base images..."
    docker pull postgres:16-alpine
    docker pull redis:7-alpine
    docker pull nginx:alpine

    # Build application images
    log_info "Building backend image (this may take several minutes)..."
    docker-compose --env-file .env build backend

    if [[ -d "$APP_DIR/frontend" ]]; then
        log_info "Building frontend image..."
        docker-compose --env-file .env build frontend
    fi

    # Start services
    log_info "Starting services..."
    docker-compose --env-file .env up -d

    log_success "Application deployed"
}

# =============================================================================
# Health Checks
# =============================================================================

wait_for_services() {
    log_info "Waiting for services to start..."

    # Wait for PostgreSQL
    log_info "Checking PostgreSQL..."
    for i in {1..30}; do
        if docker-compose --env-file "$APP_DIR/.env" exec -T postgres pg_isready -U tria_admin &>/dev/null; then
            log_success "PostgreSQL ready"
            break
        fi
        sleep 2
    done

    # Wait for Redis
    log_info "Checking Redis..."
    for i in {1..30}; do
        if docker-compose --env-file "$APP_DIR/.env" exec -T redis redis-cli ping &>/dev/null; then
            log_success "Redis ready"
            break
        fi
        sleep 2
    done

    # Wait for backend
    log_info "Checking backend API..."
    for i in {1..60}; do
        if curl -sf http://localhost:8003/health &>/dev/null; then
            log_success "Backend API ready"
            break
        fi
        sleep 2
    done

    # Wait for nginx
    log_info "Checking Nginx..."
    for i in {1..30}; do
        if curl -sf http://localhost/health &>/dev/null; then
            log_success "Nginx ready"
            break
        fi
        sleep 2
    done
}

verify_deployment() {
    log_info "Verifying deployment..."

    cd "$APP_DIR"

    # Check container status
    log_info "Container status:"
    docker-compose --env-file .env ps

    # Test health endpoints
    log_info "Testing health endpoints..."

    if curl -sf http://localhost/health | jq . &>/dev/null; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        return 1
    fi

    log_success "Deployment verified successfully"
}

# =============================================================================
# systemd Service Setup
# =============================================================================

setup_systemd_service() {
    log_info "Setting up systemd service for auto-restart..."

    cat > /etc/systemd/system/tria-aibpo.service << EOF
[Unit]
Description=Tria AIBPO Docker Compose Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker-compose --env-file .env up -d
ExecStop=/usr/bin/docker-compose --env-file .env down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    # Enable service
    systemctl daemon-reload
    systemctl enable tria-aibpo.service

    log_success "systemd service configured"
    log_info "Service will auto-start on boot"
}

# =============================================================================
# Post-Deployment Info
# =============================================================================

show_deployment_info() {
    echo
    echo "=================================================================="
    log_success "Tria AIBPO Deployment Complete!"
    echo "=================================================================="
    echo
    echo "Application Details:"
    echo "  - Install Directory: $APP_DIR"
    echo "  - Deploy User: $DEPLOY_USER"
    echo "  - Environment: $DEPLOY_MODE"
    echo
    echo "Services:"
    echo "  - HTTP:  http://$(hostname -I | awk '{print $1}')/"
    echo "  - HTTPS: https://$(hostname -I | awk '{print $1}')/"
    echo "  - API:   http://$(hostname -I | awk '{print $1}')/api/"
    echo
    echo "Management Commands:"
    echo "  - View logs:       cd $APP_DIR && docker-compose logs -f"
    echo "  - Restart:         cd $APP_DIR && docker-compose restart"
    echo "  - Stop:            cd $APP_DIR && docker-compose stop"
    echo "  - Start:           cd $APP_DIR && docker-compose up -d"
    echo "  - View status:     cd $APP_DIR && docker-compose ps"
    echo
    echo "systemd Service:"
    echo "  - Status:          systemctl status tria-aibpo"
    echo "  - Start:           systemctl start tria-aibpo"
    echo "  - Stop:            systemctl stop tria-aibpo"
    echo "  - Restart:         systemctl restart tria-aibpo"
    echo
    if [[ "$DEPLOY_MODE" == "dev" ]]; then
        log_warning "Using self-signed SSL certificates (development mode)"
        log_warning "For production, run with: sudo ./scripts/deploy_ubuntu.sh --production --domain=yourdomain.com --email=you@example.com"
    else
        log_success "Production SSL certificates configured"
    fi
    echo
    log_warning "IMPORTANT: Edit $APP_DIR/.env and configure all environment variables"
    echo "=================================================================="
}

# =============================================================================
# Main Deployment Flow
# =============================================================================

parse_arguments() {
    for arg in "$@"; do
        case $arg in
            --production)
                DEPLOY_MODE="production"
                ;;
            --dev)
                DEPLOY_MODE="dev"
                ;;
            --domain=*)
                DOMAIN="${arg#*=}"
                ;;
            --email=*)
                EMAIL="${arg#*=}"
                ;;
            --help)
                echo "Usage: sudo $0 [options]"
                echo ""
                echo "Options:"
                echo "  --production       Use Let's Encrypt SSL certificates"
                echo "  --dev              Use self-signed certificates (default)"
                echo "  --domain=DOMAIN    Set domain for SSL certificate"
                echo "  --email=EMAIL      Set email for Let's Encrypt"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $arg"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

main() {
    echo "=================================================================="
    echo "  Tria AIBPO - Ubuntu Server Deployment"
    echo "=================================================================="
    echo

    # Parse command line arguments
    parse_arguments "$@"

    # Pre-flight checks
    check_root
    check_ubuntu
    check_system_requirements

    # Install dependencies
    install_system_dependencies
    install_docker
    install_docker_compose

    # Setup user and directories
    setup_deploy_user
    setup_directories

    # Configure environment
    setup_environment

    # Setup SSL certificates
    setup_ssl

    # Configure firewall
    configure_firewall

    # Deploy application
    build_and_deploy

    # Wait for services
    wait_for_services

    # Verify deployment
    verify_deployment

    # Setup systemd service
    setup_systemd_service

    # Show deployment info
    show_deployment_info
}

# Run main function
main "$@"
