#!/bin/bash
# =============================================================================
# TRIA AIBPO - Simple Deployment Script
# =============================================================================
# Deploys to production server using git workflow
# Usage: ./scripts/deploy_to_server.sh
# =============================================================================

set -e  # Exit on error

# Load environment variables
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    exit 1
fi

source .env

echo "==================================================================="
echo "  TRIA AIBPO - Deployment to Production"
echo "==================================================================="
echo "Server: $SERVER_IP"
echo "User: $SSH_USER"
echo "==================================================================="

# Step 1: Commit and push changes to git
echo ""
echo "Step 1: Pushing changes to git..."
git status
read -p "Commit message: " commit_msg
git add .
git commit -m "$commit_msg"
git push origin main

# Step 2: Deploy to server
echo ""
echo "Step 2: Deploying to server..."
ssh -i "$SSH_KEY_PATH" $SSH_USER@$SERVER_IP << 'ENDSSH'
cd /home/ubuntu/tria

# Pull latest changes
echo "=== Pulling from git ==="
git pull origin main

# Copy .env file (update DEPLOY_ENV to production)
echo "=== Updating .env for production ==="
sed -i 's/DEPLOY_ENV=development/DEPLOY_ENV=production/' .env
sed -i 's/localhost/postgres/g' .env | grep -E "DATABASE_URL|REDIS_HOST"

# Stop containers
echo "=== Stopping containers ==="
sudo docker-compose down

# Build and start
echo "=== Building and starting containers ==="
sudo docker-compose build
sudo docker-compose up -d

# Wait for containers to start
sleep 15

# Run migration
echo "=== Running database migration ==="
sudo docker-compose exec -T backend python scripts/migrate_conversation_tables.py || true

# Check status
echo "=== Container status ==="
sudo docker-compose ps

# Test health endpoint
echo "=== Testing health endpoint ==="
curl -f http://localhost:8003/health

ENDSSH

# Step 3: Verify deployment
echo ""
echo "Step 3: Verifying deployment..."
curl -f http://$SERVER_IP/health

echo ""
echo "==================================================================="
echo "  Deployment Complete!"
echo "==================================================================="
echo "API: http://$SERVER_IP:8003"
echo "Health: http://$SERVER_IP/health"
echo "==================================================================="
