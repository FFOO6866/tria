#!/bin/bash
# Deployment Verification Script
# Run this on the production server to diagnose issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Tria AIBPO Deployment Verification${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check 1: Docker installation
echo -e "${BLUE}[1/10] Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker version: $(docker --version)"
else
    echo -e "${RED}✗${NC} Docker not installed"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose version: $(docker-compose --version)"
else
    echo -e "${RED}✗${NC} Docker Compose not installed"
    exit 1
fi
echo ""

# Check 2: Environment file
echo -e "${BLUE}[2/10] Checking environment configuration...${NC}"
if [ -f .env.docker ]; then
    echo -e "${GREEN}✓${NC} .env.docker exists"

    # Check for required variables
    required_vars=("OPENAI_API_KEY" "DATABASE_URL" "REDIS_HOST" "SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env.docker; then
            echo -e "${GREEN}✓${NC} $var is set"
        else
            echo -e "${RED}✗${NC} $var is missing"
        fi
    done
else
    echo -e "${RED}✗${NC} .env.docker not found"
fi
echo ""

# Check 3: Container status
echo -e "${BLUE}[3/10] Checking container status...${NC}"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=tria_aibpo"
echo ""

# Check 4: Container health
echo -e "${BLUE}[4/10] Checking container health...${NC}"
containers=("tria_aibpo_postgres" "tria_aibpo_redis" "tria_aibpo_backend" "tria_aibpo_frontend" "tria_aibpo_nginx")
for container in "${containers[@]}"; do
    if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        echo -e "${GREEN}✓${NC} $container is running"
    else
        echo -e "${RED}✗${NC} $container is not running"
    fi
done
echo ""

# Check 5: Database connectivity
echo -e "${BLUE}[5/10] Checking database connectivity...${NC}"
if docker exec tria_aibpo_postgres pg_isready -U tria_admin -d tria_aibpo 2>/dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL is accepting connections"

    # Check if tables exist
    table_count=$(docker exec tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
    echo -e "${GREEN}✓${NC} Database has $table_count tables"
else
    echo -e "${RED}✗${NC} PostgreSQL is not responding"
fi
echo ""

# Check 6: Redis connectivity
echo -e "${BLUE}[6/10] Checking Redis connectivity...${NC}"
if docker exec tria_aibpo_redis redis-cli -a change_this_redis_password_456 ping 2>/dev/null | grep -q PONG; then
    echo -e "${GREEN}✓${NC} Redis is responding"
else
    echo -e "${RED}✗${NC} Redis is not responding"
fi
echo ""

# Check 7: Backend health
echo -e "${BLUE}[7/10] Checking backend health...${NC}"
if docker exec tria_aibpo_backend curl -sf http://localhost:8003/health > /tmp/health.json 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Backend health check passed"
    cat /tmp/health.json | grep -o '"[^"]*":\s*"[^"]*"' | head -5
else
    echo -e "${RED}✗${NC} Backend health check failed"
    echo "Checking backend logs for errors:"
    docker logs tria_aibpo_backend --tail 20
fi
echo ""

# Check 8: Frontend health
echo -e "${BLUE}[8/10] Checking frontend health...${NC}"
if docker exec tria_aibpo_frontend curl -sf http://localhost:3000 > /dev/null 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Frontend is responding"
else
    echo -e "${RED}✗${NC} Frontend is not responding"
fi
echo ""

# Check 9: Nginx routing
echo -e "${BLUE}[9/10] Checking Nginx routing...${NC}"
if docker exec tria_aibpo_nginx wget --spider -q http://localhost/health 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Nginx is routing traffic correctly"
else
    echo -e "${RED}✗${NC} Nginx routing failed"
fi
echo ""

# Check 10: External access
echo -e "${BLUE}[10/10] Checking external access...${NC}"
server_ip=$(hostname -I | awk '{print $1}')
if curl -sf http://localhost/health > /dev/null 2>/dev/null; then
    echo -e "${GREEN}✓${NC} API is accessible from localhost"
    echo -e "${GREEN}✓${NC} Try accessing: http://$server_ip"
else
    echo -e "${RED}✗${NC} API is not accessible"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Troubleshooting Commands${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}View all logs:${NC}"
echo "  docker-compose logs"
echo ""
echo -e "${YELLOW}View backend logs:${NC}"
echo "  docker logs tria_aibpo_backend --tail 100 -f"
echo ""
echo -e "${YELLOW}View database logs:${NC}"
echo "  docker logs tria_aibpo_postgres --tail 50"
echo ""
echo -e "${YELLOW}Restart all services:${NC}"
echo "  docker-compose restart"
echo ""
echo -e "${YELLOW}Check environment variables:${NC}"
echo "  docker exec tria_aibpo_backend env | grep -E 'DATABASE|OPENAI|REDIS'"
echo ""
echo -e "${YELLOW}Test chatbot API:${NC}"
echo "  curl -X POST http://localhost/api/chatbot -H 'Content-Type: application/json' -d '{\"message\":\"hello\",\"user_id\":\"test\"}'"
echo ""
