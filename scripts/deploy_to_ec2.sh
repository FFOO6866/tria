#!/bin/bash
# =============================================================================
# Automated Deployment Script for Tria AI-BPO on EC2
# Run this script after SSHing into your EC2 instance
# =============================================================================

set -e

echo "======================================================================"
echo " 🚀 Tria AI-BPO Automated Deployment"
echo "======================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on EC2
if [ ! -f /home/ubuntu/.cloud-locale-test.skip ]; then
    echo -e "${YELLOW}⚠️  Warning: This script is designed to run on Ubuntu EC2 instances${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Run setup script if Docker is not installed
echo -e "${GREEN}Step 1: Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Running setup script..."

    if [ ! -f setup_ec2.sh ]; then
        echo "Downloading setup script..."
        wget -q https://raw.githubusercontent.com/fujifruity/tria/main/scripts/setup_ec2.sh
        chmod +x setup_ec2.sh
    fi

    ./setup_ec2.sh

    echo -e "${YELLOW}⚠️  Docker installed. Please log out and run this script again.${NC}"
    echo "Run: exit"
    echo "Then reconnect and run: ./deploy_to_ec2.sh"
    exit 0
else
    echo -e "${GREEN}✓ Docker is installed${NC}"
fi

# Step 2: Clone repository
echo ""
echo -e "${GREEN}Step 2: Cloning repository...${NC}"
PROJECT_DIR="/home/ubuntu/tria-aibpo"

if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo "Creating project directory..."
    mkdir -p $PROJECT_DIR
    cd $PROJECT_DIR

    echo "Cloning repository..."
    git clone https://github.com/fujifruity/tria.git .
    echo -e "${GREEN}✓ Repository cloned${NC}"
else
    echo "Repository already exists. Pulling latest changes..."
    cd $PROJECT_DIR
    git pull origin main
    echo -e "${GREEN}✓ Repository updated${NC}"
fi

# Step 3: Setup environment variables
echo ""
echo -e "${GREEN}Step 3: Setting up environment variables...${NC}"

if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.template .env

    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: You need to configure your environment variables${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Generating secure passwords..."
    POSTGRES_PWD=$(openssl rand -base64 20)
    REDIS_PWD=$(openssl rand -base64 20)
    SECRET_KEY=$(openssl rand -hex 32)

    echo ""
    echo -e "${GREEN}Generated credentials (save these!):${NC}"
    echo "POSTGRES_PASSWORD: $POSTGRES_PWD"
    echo "REDIS_PASSWORD: $REDIS_PWD"
    echo "SECRET_KEY: $SECRET_KEY"
    echo ""

    # Update .env file
    sed -i "s/POSTGRES_PASSWORD=CHANGE_THIS_SECURE_PASSWORD/POSTGRES_PASSWORD=$POSTGRES_PWD/" .env
    sed -i "s/CHANGE_THIS_SECURE_PASSWORD/$POSTGRES_PWD/g" .env
    sed -i "s/REDIS_PASSWORD=change_this_redis_password_456/REDIS_PASSWORD=$REDIS_PWD/" .env
    sed -i "s/change_this_redis_password_456/$REDIS_PWD/g" .env
    sed -i "s/SECRET_KEY=GENERATE_32_CHAR_SECRET_KEY_HERE/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s/ENVIRONMENT=development/ENVIRONMENT=production/" .env

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Please enter your OpenAI API Key:${NC}"
    echo -e "${YELLOW}(Get it from: https://platform.openai.com/api-keys)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    read -p "OpenAI API Key: " OPENAI_KEY

    if [ -z "$OPENAI_KEY" ]; then
        echo -e "${RED}❌ OpenAI API Key is required!${NC}"
        echo "Please edit .env file manually:"
        echo "  nano .env"
        exit 1
    fi

    sed -i "s/OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE/OPENAI_API_KEY=$OPENAI_KEY/" .env

    echo -e "${GREEN}✓ Environment configured${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Step 4: Deploy with Docker Compose
echo ""
echo -e "${GREEN}Step 4: Deploying application...${NC}"

# Determine which compose file to use
COMPOSE_FILE="docker-compose.small.yml"
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')

if [ $TOTAL_MEM -gt 3500 ]; then
    COMPOSE_FILE="docker-compose.yml"
    echo "Detected 4GB+ RAM - using standard configuration"
else
    echo "Detected 2GB RAM - using memory-optimized configuration"
fi

echo "Building and starting containers (this may take 5-10 minutes)..."
docker-compose -f $COMPOSE_FILE up -d --build

# Step 5: Wait for services
echo ""
echo -e "${GREEN}Step 5: Waiting for services to start...${NC}"
echo "This may take 30-60 seconds..."
sleep 30

# Step 6: Health check
echo ""
echo -e "${GREEN}Step 6: Running health checks...${NC}"

MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8003/health &>/dev/null; then
        echo -e "${GREEN}✓ Backend is healthy!${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for backend to be ready... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "Checking logs..."
    docker-compose -f $COMPOSE_FILE logs backend | tail -50
    exit 1
fi

# Step 7: Show status
echo ""
echo -e "${GREEN}Step 7: Deployment status${NC}"
echo ""
echo "Running containers:"
docker-compose -f $COMPOSE_FILE ps
echo ""
echo "Memory usage:"
docker stats --no-stream
echo ""

# Get public IP
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "======================================================================"
echo ""
echo "Your Tria AI-BPO chatbot is now live at:"
echo ""
echo "  🌐 API:    http://$PUBLIC_IP:8003"
echo "  🏥 Health: http://$PUBLIC_IP:8003/health"
echo "  📚 Docs:   http://$PUBLIC_IP:8003/docs"
echo ""
echo "Useful commands:"
echo "  View logs:    docker-compose -f $COMPOSE_FILE logs -f backend"
echo "  Restart:      docker-compose -f $COMPOSE_FILE restart"
echo "  Stop:         docker-compose -f $COMPOSE_FILE down"
echo "  Status:       docker-compose -f $COMPOSE_FILE ps"
echo ""
echo "To test the chatbot, open in your browser:"
echo "  http://$PUBLIC_IP:8003/docs"
echo ""
echo "======================================================================"
