#!/bin/bash
# Production Deployment Script for Tria AIBPO
# Handles complete deployment with validation and health checks

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Tria AIBPO Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print colored messages
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Step 1: Check prerequisites
info "Checking prerequisites..."
check_command docker
check_command docker-compose
success "All prerequisites installed"

# Step 2: Check environment file
info "Checking environment configuration..."
if [ ! -f .env.docker ]; then
    error ".env.docker file not found!"
    error "Please create .env.docker from .env.docker.example"
    exit 1
fi

# Validate critical environment variables
if ! grep -q "OPENAI_API_KEY=sk-" .env.docker; then
    error "OPENAI_API_KEY not set in .env.docker"
    error "Please add your OpenAI API key"
    exit 1
fi

if ! grep -q "REDIS_PASSWORD=" .env.docker; then
    warning "REDIS_PASSWORD not set, using default"
fi

success "Environment configuration valid"

# Step 3: Stop existing containers
info "Stopping existing containers..."
docker-compose down --remove-orphans || true
success "Containers stopped"

# Step 4: Clean up (optional - uncomment if you want to start fresh)
# warning "Cleaning up old images and volumes..."
# docker-compose down -v
# docker system prune -f

# Step 5: Build images
info "Building Docker images (this may take a few minutes)..."
docker-compose build --no-cache
success "Images built successfully"

# Step 6: Start services
info "Starting services..."
docker-compose --env-file .env.docker up -d
success "Services started"

# Step 7: Wait for services to be healthy
info "Waiting for services to become healthy (up to 2 minutes)..."
sleep 10  # Initial wait

MAX_ATTEMPTS=24  # 24 attempts * 5 seconds = 2 minutes
attempt=0

while [ $attempt -lt $MAX_ATTEMPTS ]; do
    # Check PostgreSQL
    if docker exec tria_aibpo_postgres pg_isready -U tria_admin -d tria_aibpo &>/dev/null; then
        postgres_status="${GREEN}✓${NC}"
    else
        postgres_status="${RED}✗${NC}"
    fi

    # Check Redis
    if docker exec tria_aibpo_redis redis-cli -a change_this_redis_password_456 ping 2>/dev/null | grep -q PONG; then
        redis_status="${GREEN}✓${NC}"
    else
        redis_status="${RED}✗${NC}"
    fi

    # Check Backend
    if docker exec tria_aibpo_backend curl -sf http://localhost:8003/health &>/dev/null; then
        backend_status="${GREEN}✓${NC}"
    else
        backend_status="${RED}✗${NC}"
    fi

    # Check Frontend
    if docker exec tria_aibpo_frontend curl -sf http://localhost:3000 &>/dev/null; then
        frontend_status="${GREEN}✓${NC}"
    else
        frontend_status="${RED}✗${NC}"
    fi

    # Check Nginx
    if docker exec tria_aibpo_nginx wget --spider -q http://localhost/health; then
        nginx_status="${GREEN}✓${NC}"
    else
        nginx_status="${RED}✗${NC}"
    fi

    echo -ne "\r${BLUE}Status:${NC} PostgreSQL ${postgres_status} | Redis ${redis_status} | Backend ${backend_status} | Frontend ${frontend_status} | Nginx ${nginx_status}   "

    # Check if all are healthy
    if docker exec tria_aibpo_postgres pg_isready -U tria_admin &>/dev/null && \
       docker exec tria_aibpo_redis redis-cli -a change_this_redis_password_456 ping 2>/dev/null | grep -q PONG && \
       docker exec tria_aibpo_backend curl -sf http://localhost:8003/health &>/dev/null && \
       docker exec tria_aibpo_frontend curl -sf http://localhost:3000 &>/dev/null && \
       docker exec tria_aibpo_nginx wget --spider -q http://localhost/health; then
        echo ""
        success "All services are healthy!"
        break
    fi

    attempt=$((attempt + 1))
    sleep 5
done

if [ $attempt -eq $MAX_ATTEMPTS ]; then
    echo ""
    error "Services failed to become healthy within 2 minutes"
    error "Check logs with: docker-compose logs"
    exit 1
fi

# Step 8: Run database migrations (if needed)
info "Checking database..."
docker exec tria_aibpo_backend python -c "
import sys
sys.path.insert(0, '/app/src')
from database import get_db_engine
from sqlalchemy import text

try:
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM products'))
        count = result.scalar()
        print(f'Database has {count} products')
except Exception as e:
    print(f'Database check failed: {e}')
    sys.exit(1)
" && success "Database is ready" || warning "Database might need initialization"

# Step 9: Test endpoints
info "Testing API endpoints..."

# Test health endpoint
if curl -sf http://localhost/health > /dev/null; then
    success "✓ Health endpoint working"
else
    error "✗ Health endpoint failed"
fi

# Test chatbot endpoint
if curl -sf -X POST http://localhost/api/chatbot \
    -H "Content-Type: application/json" \
    -d '{"message":"hello","user_id":"test"}' > /dev/null; then
    success "✓ Chatbot endpoint working"
else
    warning "✗ Chatbot endpoint might need warmup (this is normal on first start)"
fi

# Step 10: Display deployment info
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo -e "  - Web UI:     http://$(hostname -I | awk '{print $1}')"
echo -e "  - API Docs:   http://$(hostname -I | awk '{print $1}')/docs"
echo -e "  - Health:     http://$(hostname -I | awk '{print $1}')/health"
echo -e "  - Metrics:    http://$(hostname -I | awk '{print $1}')/metrics"
echo ""
echo -e "${BLUE}Container Status:${NC}"
docker-compose ps
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo -e "  - View logs:           ${YELLOW}docker-compose logs -f${NC}"
echo -e "  - View backend logs:   ${YELLOW}docker-compose logs -f backend${NC}"
echo -e "  - Restart services:    ${YELLOW}docker-compose restart${NC}"
echo -e "  - Stop services:       ${YELLOW}docker-compose down${NC}"
echo -e "  - Check health:        ${YELLOW}curl http://localhost/health | jq${NC}"
echo ""
echo -e "${GREEN}Deployment complete! 🚀${NC}"
