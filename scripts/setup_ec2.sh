#!/bin/bash
# =============================================================================
# EC2 Instance Setup Script for Tria AI-BPO
# Run this ONCE on your EC2 instance after launching it
# =============================================================================

set -e

echo "====================================================================="
echo " Tria AI-BPO - EC2 Setup Script"
echo "====================================================================="
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install essential tools
echo "🔧 Installing essential tools..."
sudo apt-get install -y \
    curl \
    wget \
    git \
    htop \
    vim \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add current user to docker group
    sudo usermod -aG docker $USER

    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose (standalone)
echo "🔧 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose already installed"
fi

# Verify installations
echo ""
echo "📋 Verifying installations..."
docker --version
docker-compose --version

# Create project directory
PROJECT_DIR="/home/ubuntu/tria-aibpo"
echo ""
echo "📁 Creating project directory at $PROJECT_DIR..."
mkdir -p $PROJECT_DIR

# Clone repository (you'll need to set this up)
echo ""
echo "📥 Ready to clone repository..."
echo "Run the following command to clone your repository:"
echo ""
echo "  cd $PROJECT_DIR"
echo "  git clone YOUR_GITHUB_REPO_URL ."
echo ""

# Create .env file template
echo "📝 Creating .env template..."
cat > $PROJECT_DIR/.env.template << 'EOF'
# =============================================================================
# Tria AI-BPO Environment Variables
# Copy this to .env and fill in your actual values
# =============================================================================

# Database
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=CHANGE_THIS_SECURE_PASSWORD
POSTGRES_DB=tria_aibpo
DATABASE_URL=postgresql://tria_admin:CHANGE_THIS_SECURE_PASSWORD@postgres:5432/tria_aibpo

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change_this_redis_password_456
REDIS_DB=0

# OpenAI
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE
OPENAI_MODEL=gpt-4-turbo-preview

# Application
SECRET_KEY=GENERATE_32_CHAR_SECRET_KEY_HERE
ENVIRONMENT=production
LOG_LEVEL=INFO

# Optional: Xero Integration
XERO_CLIENT_ID=
XERO_CLIENT_SECRET=
XERO_TENANT_ID=
XERO_REFRESH_TOKEN=

# Tax and Accounting
TAX_RATE=0.09
XERO_SALES_ACCOUNT_CODE=200
XERO_TAX_TYPE=TAX001

# Validation Limits
MAX_QUANTITY_PER_ITEM=10000
MAX_ORDER_TOTAL=100000.00
MAX_LINE_ITEMS=100
MIN_ORDER_TOTAL=0.01

EOF

echo "✅ .env template created at $PROJECT_DIR/.env.template"

# Setup automatic Docker service start
echo ""
echo "🔄 Configuring Docker to start on boot..."
sudo systemctl enable docker
sudo systemctl start docker

# Install monitoring tools (optional but recommended)
echo ""
echo "📊 Installing monitoring tools..."
sudo apt-get install -y \
    net-tools \
    iotop \
    iftop \
    ncdu

# Setup log rotation for Docker
echo ""
echo "📄 Configuring Docker log rotation..."
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

sudo systemctl restart docker

# Setup firewall (UFW)
echo ""
echo "🔥 Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
echo "✅ Firewall configured"

# Create useful aliases
echo ""
echo "⚡ Creating useful aliases..."
cat >> ~/.bashrc << 'EOF'

# Tria AI-BPO Aliases
alias tria-logs='cd /home/ubuntu/tria-aibpo && docker-compose logs -f'
alias tria-ps='cd /home/ubuntu/tria-aibpo && docker-compose ps'
alias tria-restart='cd /home/ubuntu/tria-aibpo && docker-compose restart'
alias tria-down='cd /home/ubuntu/tria-aibpo && docker-compose down'
alias tria-up='cd /home/ubuntu/tria-aibpo && docker-compose up -d'
alias tria-rebuild='cd /home/ubuntu/tria-aibpo && docker-compose up -d --build'
alias tria-health='curl -f http://localhost:8003/health'
alias tria-clean='docker system prune -af --volumes'
EOF

source ~/.bashrc

# Setup cron job for automatic backups (optional)
echo ""
echo "💾 Setup automatic backups..."
cat > /home/ubuntu/backup_tria.sh << 'EOF'
#!/bin/bash
# Backup script for Tria AI-BPO
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > $BACKUP_DIR/db_backup_$DATE.sql

# Backup .env file
cp /home/ubuntu/tria-aibpo/.env $BACKUP_DIR/env_backup_$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "env_backup_*" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /home/ubuntu/backup_tria.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/backup_tria.sh >> /home/ubuntu/backup.log 2>&1") | crontab -

echo ""
echo "====================================================================="
echo " ✅ EC2 Setup Complete!"
echo "====================================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Clone your repository:"
echo "   cd $PROJECT_DIR"
echo "   git clone YOUR_GITHUB_REPO_URL ."
echo ""
echo "2. Create .env file with your secrets:"
echo "   cp .env.template .env"
echo "   nano .env"
echo ""
echo "3. Start the application:"
echo "   docker-compose up -d"
echo ""
echo "4. Check status:"
echo "   docker-compose ps"
echo "   curl http://localhost:8003/health"
echo ""
echo "Useful commands:"
echo "  tria-logs       - View logs"
echo "  tria-ps         - Show running containers"
echo "  tria-restart    - Restart all services"
echo "  tria-health     - Check health"
echo ""
echo "⚠️  IMPORTANT: Log out and log back in for Docker group to take effect!"
echo ""
echo "====================================================================="
