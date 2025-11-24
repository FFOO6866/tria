#!/bin/bash
# QUICKFIX for Tria AIBPO Production 502 Error
# Run this script on your production server (13.214.14.130)

set -e

echo "======================================"
echo "Tria AIBPO - Emergency Quick Fix"
echo "======================================"
echo ""

# Step 1: Stop all containers
echo "[1/6] Stopping containers..."
docker-compose down 2>/dev/null || true
echo "✓ Containers stopped"
echo ""

# Step 2: Verify .env.docker exists and has required variables
echo "[2/6] Checking environment configuration..."
if [ ! -f .env.docker ]; then
    echo "ERROR: .env.docker not found!"
    echo "Creating from .env.docker.example..."
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env.docker
        echo "⚠ WARNING: Please edit .env.docker and add your OPENAI_API_KEY"
        echo "   Run: nano .env.docker"
        exit 1
    else
        echo "ERROR: .env.docker.example not found either!"
        exit 1
    fi
fi

# Check for critical variables
if ! grep -q "^OPENAI_API_KEY=sk-" .env.docker; then
    echo "⚠ WARNING: OPENAI_API_KEY not set or invalid in .env.docker"
    echo "   The chatbot will not work without this!"
    echo "   Edit .env.docker and add: OPENAI_API_KEY=sk-your-key-here"
fi

if ! grep -q "^REDIS_PASSWORD=" .env.docker; then
    echo "⚠ WARNING: REDIS_PASSWORD not set in .env.docker"
    echo "   Adding default value..."
    echo "REDIS_PASSWORD=change_this_redis_password_456" >> .env.docker
fi

if ! grep -q "^SECRET_KEY=" .env.docker; then
    echo "⚠ WARNING: SECRET_KEY not set in .env.docker"
    echo "   Generating one..."
    echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env.docker
fi

echo "✓ Environment configuration checked"
echo ""

# Step 3: Remove old volumes (fresh start)
echo "[3/6] Cleaning up old volumes..."
docker-compose down -v 2>/dev/null || true
echo "✓ Old volumes removed"
echo ""

# Step 4: Build images
echo "[4/6] Building Docker images..."
docker-compose build --no-cache
echo "✓ Images built"
echo ""

# Step 5: Start services
echo "[5/6] Starting services..."
docker-compose --env-file .env.docker up -d
echo "✓ Services started"
echo ""

# Step 6: Wait for health checks
echo "[6/6] Waiting for services to become healthy (this may take 1-2 minutes)..."
echo ""

for i in {1..40}; do
    # Check each service
    postgres_status=$(docker inspect --format='{{.State.Health.Status}}' tria_aibpo_postgres 2>/dev/null || echo "starting")
    redis_status=$(docker inspect --format='{{.State.Health.Status}}' tria_aibpo_redis 2>/dev/null || echo "starting")
    backend_status=$(docker inspect --format='{{.State.Health.Status}}' tria_aibpo_backend 2>/dev/null || echo "starting")

    echo -ne "\rPostgreSQL: $postgres_status | Redis: $redis_status | Backend: $backend_status   "

    # Check if all are healthy
    if [ "$postgres_status" = "healthy" ] && [ "$redis_status" = "healthy" ] && [ "$backend_status" = "healthy" ]; then
        echo ""
        echo ""
        echo "✓ All services are healthy!"
        break
    fi

    if [ $i -eq 40 ]; then
        echo ""
        echo ""
        echo "⚠ Services taking longer than expected. Checking logs..."
        echo ""
        echo "=== Backend Logs (last 20 lines) ==="
        docker logs tria_aibpo_backend --tail 20
        echo ""
        echo "=== What to do next ==="
        echo "1. Check if OPENAI_API_KEY is set: docker exec tria_aibpo_backend env | grep OPENAI"
        echo "2. View full backend logs: docker logs tria_aibpo_backend"
        echo "3. Check database: docker logs tria_aibpo_postgres"
        exit 1
    fi

    sleep 3
done

echo ""
echo "======================================"
echo "Quick Fix Complete!"
echo "======================================"
echo ""

# Test the endpoints
echo "Testing endpoints..."
echo ""

# Test health
if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "✓ Health endpoint: WORKING"
else
    echo "✗ Health endpoint: FAILED"
    echo "  Checking nginx logs..."
    docker logs tria_aibpo_nginx --tail 10
fi

# Test chatbot
if curl -sf -X POST http://localhost/api/chatbot \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: quickfix-test" \
    -d '{"message":"hello","user_id":"test"}' > /dev/null 2>&1; then
    echo "✓ Chatbot endpoint: WORKING"
else
    echo "⚠ Chatbot endpoint: May need warmup (normal on first start)"
fi

echo ""
echo "======================================"
echo "Access your application at:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f"
echo "  View backend:     docker logs tria_aibpo_backend -f"
echo "  Check health:     curl http://localhost/health | jq"
echo "  Restart:          docker-compose restart"
echo "======================================"
