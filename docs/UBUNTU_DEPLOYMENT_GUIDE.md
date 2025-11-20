# Tria AIBPO - Ubuntu Server Deployment Guide

Complete guide for deploying Tria AIBPO on Ubuntu 20.04+ servers with Docker, Nginx, SSL, and production-ready configuration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Manual Deployment](#manual-deployment)
- [Configuration](#configuration)
- [SSL Certificates](#ssl-certificates)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)
- [Security Hardening](#security-hardening)
- [Backup & Recovery](#backup--recovery)

## Prerequisites

### Server Requirements

**Minimum (Development/Testing):**
- Ubuntu 20.04 LTS or higher
- 2 GB RAM
- 2 CPU cores
- 20 GB disk space
- Root or sudo access

**Recommended (Production):**
- Ubuntu 22.04 LTS
- 4 GB RAM
- 4 CPU cores
- 50 GB SSD disk space
- Static IP address
- Domain name (for SSL)

### Network Requirements

- Open ports: 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Internet connectivity for package installation
- DNS configured (if using domain name)

## Quick Start

### Automated Deployment

For the fastest deployment with all features enabled:

```bash
# 1. Clone repository
git clone https://github.com/yourusername/tria-aibpo.git
cd tria-aibpo

# 2. Configure environment variables
cp .env.example .env
nano .env  # Edit with your credentials

# 3. Run automated deployment script
sudo ./scripts/deploy_ubuntu.sh --dev

# For production with Let's Encrypt SSL:
sudo ./scripts/deploy_ubuntu.sh --production --domain=your-domain.com --email=you@example.com
```

The script will:
- ✅ Install Docker and Docker Compose
- ✅ Install system dependencies
- ✅ Configure firewall (UFW)
- ✅ Generate SSL certificates
- ✅ Deploy all services (PostgreSQL, Redis, Backend, Frontend, Nginx)
- ✅ Set up systemd services for auto-restart
- ✅ Configure automated backups

**Deployment time: 10-15 minutes**

Access your application at:
- HTTP: `http://your-server-ip/`
- HTTPS: `https://your-server-ip/` (or your domain)
- API: `http://your-server-ip/api/`

## Manual Deployment

For step-by-step control over the deployment process:

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install basic tools
sudo apt install -y git curl wget vim htop net-tools ufw
```

### 2. Install Docker

```bash
# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl enable docker
sudo systemctl start docker

# Verify installation
sudo docker --version
sudo docker compose version
```

### 3. Clone Repository

```bash
# Clone to /opt/tria-aibpo (recommended for production)
sudo mkdir -p /opt/tria-aibpo
sudo git clone https://github.com/yourusername/tria-aibpo.git /opt/tria-aibpo
cd /opt/tria-aibpo
```

### 4. Configure Environment

```bash
# Copy and edit environment file
sudo cp .env.example .env
sudo nano .env
```

**Required environment variables:**

```bash
# Database
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=your-secure-password-here
POSTGRES_DB=tria_aibpo

# Redis
REDIS_PASSWORD=your-redis-password-here

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Security
SECRET_KEY=your-secret-key-here

# Application
ENVIRONMENT=production
```

**Generate secure passwords:**
```bash
# Generate random passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 32  # For REDIS_PASSWORD
openssl rand -base64 48  # For SECRET_KEY
```

**Set secure permissions:**
```bash
sudo chmod 600 .env
```

### 5. Generate SSL Certificates

**Option A: Self-Signed (Development/Testing)**

```bash
sudo bash scripts/generate_ssl_certs.sh
```

**Option B: Let's Encrypt (Production)**

```bash
# Install Certbot
sudo apt install -y certbot

# Stop Nginx if running
sudo docker compose down nginx

# Obtain certificate
sudo certbot certonly --standalone \
  --non-interactive \
  --agree-tos \
  --email you@example.com \
  -d your-domain.com

# Create symbolic links
sudo ln -sf /etc/letsencrypt/live/your-domain.com/fullchain.pem /opt/tria-aibpo/nginx/ssl/tria.crt
sudo ln -sf /etc/letsencrypt/live/your-domain.com/privkey.pem /opt/tria-aibpo/nginx/ssl/tria.key

# Set up auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 6. Configure Firewall

```bash
# Enable UFW
sudo ufw --force enable

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow 22/tcp comment 'SSH'

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Reload firewall
sudo ufw reload

# Check status
sudo ufw status
```

### 7. Build and Deploy

```bash
cd /opt/tria-aibpo

# Pull base images
sudo docker pull postgres:16-alpine
sudo docker pull redis:7-alpine
sudo docker pull nginx:alpine

# Build application images
sudo docker compose --env-file .env build backend
sudo docker compose --env-file .env build frontend

# Start all services
sudo docker compose --env-file .env up -d

# View logs
sudo docker compose logs -f
```

### 8. Verify Deployment

```bash
# Check container status
sudo docker compose ps

# Check health endpoint
curl http://localhost/health

# View Nginx logs
sudo docker compose logs nginx

# View backend logs
sudo docker compose logs backend
```

### 9. Set Up systemd Services

```bash
# Copy service files
sudo cp systemd/tria-aibpo.service /etc/systemd/system/
sudo cp systemd/tria-aibpo-backup.service /etc/systemd/system/
sudo cp systemd/tria-aibpo-backup.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable tria-aibpo
sudo systemctl enable tria-aibpo-backup.timer

# Start backup timer
sudo systemctl start tria-aibpo-backup.timer
```

## Configuration

### Nginx Configuration

Nginx configuration files are located in:
- `nginx/nginx.conf` - Main configuration
- `nginx/conf.d/tria-aibpo.conf` - Site-specific configuration

**Key features:**
- Rate limiting (10 req/s for API, 5 req/s for chatbot)
- SSL/TLS termination
- WebSocket support
- Security headers (HSTS, X-Frame-Options, etc.)
- Gzip compression

**To modify:**
```bash
sudo nano nginx/conf.d/tria-aibpo.conf
sudo docker compose restart nginx
```

### Docker Compose Services

**Services overview:**
- `postgres` - PostgreSQL 16 database (port 5433)
- `redis` - Redis 7 cache (port 6379)
- `backend` - FastAPI application (port 8003)
- `frontend` - Next.js application (port 3000)
- `nginx` - Reverse proxy (ports 80, 443)

**To scale services:**
```bash
# Scale backend to 3 instances
sudo docker compose up -d --scale backend=3
```

### Environment Variables

All configuration is managed through `.env` file:

```bash
# Edit environment variables
sudo nano /opt/tria-aibpo/.env

# Apply changes (restart services)
cd /opt/tria-aibpo
sudo docker compose --env-file .env up -d --force-recreate
```

## SSL Certificates

### Let's Encrypt Auto-Renewal

Certbot automatically renews certificates via systemd timer:

```bash
# Check renewal timer status
sudo systemctl status certbot.timer

# Test renewal (dry run)
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal

# View certificates
sudo certbot certificates
```

### Certificate Renewal Process

1. Certbot runs automatically twice daily
2. Certificates within 30 days of expiry are renewed
3. Nginx is reloaded automatically
4. Renewal logs: `/var/log/letsencrypt/`

### Manual Renewal

```bash
# Stop Nginx
sudo docker compose stop nginx

# Renew certificate
sudo certbot renew

# Start Nginx
sudo docker compose start nginx
```

## Monitoring & Maintenance

### Service Status

```bash
# systemd service status
sudo systemctl status tria-aibpo

# Container status
cd /opt/tria-aibpo && sudo docker compose ps

# Resource usage
sudo docker stats

# Health check
curl http://localhost/health | jq .
```

### Logs

```bash
# Application logs (systemd)
sudo journalctl -u tria-aibpo -f

# Docker container logs
cd /opt/tria-aibpo
sudo docker compose logs -f

# Specific service logs
sudo docker compose logs -f backend
sudo docker compose logs -f nginx

# Nginx access logs
sudo docker compose exec nginx tail -f /var/log/nginx/access.log

# Nginx error logs
sudo docker compose exec nginx tail -f /var/log/nginx/error.log
```

### Updates

```bash
cd /opt/tria-aibpo

# Pull latest code
sudo git pull

# Rebuild images
sudo docker compose --env-file .env build

# Restart services (zero-downtime)
sudo docker compose --env-file .env up -d --force-recreate

# Verify deployment
curl http://localhost/health
```

### Database Management

```bash
# Connect to PostgreSQL
sudo docker compose exec postgres psql -U tria_admin -d tria_aibpo

# Backup database manually
sudo docker compose exec -T postgres pg_dump -U tria_admin tria_aibpo | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore database
gunzip -c backup_YYYYMMDD.sql.gz | sudo docker compose exec -T postgres psql -U tria_admin -d tria_aibpo

# View database size
sudo docker compose exec postgres psql -U tria_admin -d tria_aibpo -c "SELECT pg_size_pretty(pg_database_size('tria_aibpo'));"
```

## Troubleshooting

### Service Won't Start

**Check Docker service:**
```bash
sudo systemctl status docker
sudo systemctl start docker
```

**Check logs:**
```bash
sudo journalctl -u tria-aibpo -n 100
sudo docker compose logs
```

**Verify environment file:**
```bash
sudo ls -l /opt/tria-aibpo/.env
sudo cat /opt/tria-aibpo/.env | grep -v PASSWORD | grep -v KEY
```

### Container Issues

**Restart specific container:**
```bash
sudo docker compose restart backend
sudo docker compose restart nginx
```

**Rebuild container:**
```bash
sudo docker compose up -d --force-recreate backend
```

**Remove and recreate:**
```bash
sudo docker compose down
sudo docker compose up -d
```

### Port Conflicts

**Check port usage:**
```bash
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
sudo netstat -tlnp | grep :8003
```

**Kill process on port:**
```bash
sudo kill $(sudo lsof -t -i:80)
```

### SSL Certificate Issues

**Verify certificate:**
```bash
sudo openssl x509 -in /opt/tria-aibpo/nginx/ssl/tria.crt -text -noout
```

**Check certificate expiry:**
```bash
echo | openssl s_client -servername your-domain.com -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates
```

**Test SSL connection:**
```bash
curl -vI https://your-domain.com/
```

### Database Connection Issues

**Test PostgreSQL connection:**
```bash
sudo docker compose exec postgres pg_isready -U tria_admin
```

**Check PostgreSQL logs:**
```bash
sudo docker compose logs postgres
```

**Verify connection from backend:**
```bash
sudo docker compose exec backend python -c "from database import get_db_engine; engine = get_db_engine(); print('Connected!' if engine else 'Failed')"
```

### Performance Issues

**Check resource usage:**
```bash
sudo docker stats
htop
df -h
free -m
```

**Check application performance:**
```bash
curl -w "@-" -o /dev/null -s http://localhost/health <<'EOF'
    time_namelookup:  %{time_namelookup}\n
       time_connect:  %{time_connect}\n
    time_appconnect:  %{time_appconnect}\n
      time_redirect:  %{time_redirect}\n
 time_starttransfer:  %{time_starttransfer}\n
                    ----------\n
         time_total:  %{time_total}\n
EOF
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Deny all incoming by default
sudo ufw default deny incoming

# Allow only necessary ports
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS

# Enable rate limiting on SSH
sudo ufw limit 22/tcp

# Enable firewall
sudo ufw enable
```

### 2. SSH Hardening

```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication (use SSH keys)
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Restart SSH
sudo systemctl restart sshd
```

### 3. Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt install -y unattended-upgrades

# Enable automatic updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 4. File Permissions

```bash
cd /opt/tria-aibpo

# Secure .env file
sudo chmod 600 .env

# Secure SSL keys
sudo chmod 600 nginx/ssl/tria.key
sudo chmod 644 nginx/ssl/tria.crt

# Set directory permissions
sudo chmod 755 /opt/tria-aibpo
sudo chown -R root:root /opt/tria-aibpo
```

### 5. Container Security

Update `docker-compose.yml` to add security options:

```yaml
services:
  backend:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

## Backup & Recovery

### Automated Backups

Backups run automatically daily at 2 AM via systemd timer:

```bash
# Check backup timer
sudo systemctl status tria-aibpo-backup.timer

# List backups
ls -lh /opt/tria-aibpo/backups/

# View backup logs
sudo journalctl -u tria-aibpo-backup -n 50
```

### Manual Backup

```bash
# Run backup immediately
sudo systemctl start tria-aibpo-backup.service

# Or run backup script manually
cd /opt/tria-aibpo

# Backup database
sudo docker compose exec -T postgres pg_dump -U tria_admin tria_aibpo | gzip > backups/manual_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup application data
sudo tar -czf backups/data_$(date +%Y%m%d_%H%M%S).tar.gz data/ logs/ .env
```

### Restore from Backup

**Restore Database:**
```bash
cd /opt/tria-aibpo

# Stop application
sudo docker compose stop backend

# Restore database
gunzip -c backups/postgres_YYYYMMDD_HHMMSS.sql.gz | \
  sudo docker compose exec -T postgres psql -U tria_admin -d tria_aibpo

# Start application
sudo docker compose start backend
```

**Restore Application Data:**
```bash
cd /opt/tria-aibpo

# Stop services
sudo docker compose down

# Extract backup
sudo tar -xzf backups/data_YYYYMMDD_HHMMSS.tar.gz

# Start services
sudo docker compose up -d
```

### Backup to Remote Storage

**Using rsync (to another server):**
```bash
# Install rsync
sudo apt install -y rsync

# Sync backups to remote server
rsync -avz /opt/tria-aibpo/backups/ user@backup-server:/backups/tria-aibpo/
```

**Using AWS S3:**
```bash
# Install AWS CLI
sudo apt install -y awscli

# Configure AWS credentials
aws configure

# Upload backups to S3
aws s3 sync /opt/tria-aibpo/backups/ s3://your-bucket/tria-aibpo-backups/
```

## Appendix

### Directory Structure

```
/opt/tria-aibpo/
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Backend Docker image
├── .env                        # Environment variables (SECRET!)
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── nginx/                      # Nginx configuration
│   ├── nginx.conf              # Main Nginx config
│   ├── conf.d/                 # Site configurations
│   │   └── tria-aibpo.conf
│   └── ssl/                    # SSL certificates
│       ├── tria.crt
│       └── tria.key
├── systemd/                    # systemd service files
│   ├── tria-aibpo.service
│   ├── tria-aibpo-backup.service
│   └── tria-aibpo-backup.timer
├── scripts/                    # Utility scripts
│   ├── deploy_ubuntu.sh        # Automated deployment
│   └── generate_ssl_certs.sh  # SSL certificate generation
├── src/                        # Application source code
├── data/                       # Application data
│   └── chromadb_cache/
├── logs/                       # Application logs
│   └── nginx/
└── backups/                    # Database backups
```

### Useful Commands Reference

```bash
# System
sudo systemctl status tria-aibpo           # Service status
sudo journalctl -u tria-aibpo -f           # View logs
df -h                                       # Disk usage
free -m                                     # Memory usage
htop                                        # System monitor

# Docker
sudo docker compose ps                      # Container status
sudo docker compose logs -f                 # View logs
sudo docker compose restart                 # Restart all
sudo docker compose down                    # Stop all
sudo docker compose up -d                   # Start all
sudo docker stats                           # Resource usage

# Application
curl http://localhost/health                # Health check
sudo docker compose exec backend python     # Python shell
sudo docker compose exec postgres psql -U tria_admin -d tria_aibpo  # Database shell

# Backups
sudo systemctl start tria-aibpo-backup      # Manual backup
sudo systemctl status tria-aibpo-backup.timer  # Backup timer
ls -lh /opt/tria-aibpo/backups/             # List backups

# SSL
sudo certbot certificates                   # List certificates
sudo certbot renew                          # Renew certificates
sudo systemctl status certbot.timer         # Auto-renewal status
```

### Support & Resources

- **Documentation**: `/opt/tria-aibpo/docs/`
- **systemd Services**: `/opt/tria-aibpo/systemd/README.md`
- **Docker Logs**: `sudo docker compose logs -f`
- **System Logs**: `sudo journalctl -u tria-aibpo -f`

---

**Need help?** Check the troubleshooting section or review service logs for detailed error messages.
