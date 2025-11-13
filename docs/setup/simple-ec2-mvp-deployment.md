# Simple EC2 MVP Deployment Guide

**For**: Quick MVP deployment (NOT for high-scale production)
**Time**: 30 minutes
**Cost**: ~$30-50/month
**Complexity**: LOW ⭐

---

## 🎯 What This Guide Does

Deploy your Tria AI-BPO chatbot to a single AWS EC2 instance using Docker Compose. Perfect for MVP, demos, and small-scale production (up to ~100 users).

### What You Get:
- ✅ Everything runs on 1 EC2 instance
- ✅ Uses your existing `docker-compose.yml`
- ✅ Automatic deployment via GitHub Actions
- ✅ PostgreSQL + Redis + Backend all in Docker
- ✅ Simple to understand and maintain

### When to Upgrade:
- When you have 500+ concurrent users
- When you need 99.99% uptime
- When auto-scaling becomes critical

---

## 📋 Prerequisites

### Required:
1. **AWS Account** - Sign up at https://aws.amazon.com (Free tier available)
2. **GitHub Account** - For code hosting and CI/CD
3. **OpenAI API Key** - From https://platform.openai.com/
4. **Domain** (Optional) - For custom URL

### On Your Computer:
- SSH client (built into Windows 10+, Mac, Linux)
- Git

---

## Step 1: Launch EC2 Instance (10 minutes)

### 1.1 Log into AWS Console

Go to https://console.aws.amazon.com and navigate to **EC2**.

### 1.2 Launch Instance

Click **Launch Instance** and configure:

| Setting | Value | Notes |
|---------|-------|-------|
| **Name** | `tria-aibpo-mvp` | Any name you want |
| **AMI** | Ubuntu Server 22.04 LTS | Free tier eligible |
| **Instance Type** | `t3.medium` | 2 vCPU, 4 GB RAM (~$30/month) |
| | OR `t3.large` for better performance | 2 vCPU, 8 GB RAM (~$60/month) |
| **Key Pair** | Create new or use existing | Download the `.pem` file |
| **Storage** | 30 GB GP3 | Default is fine |
| **Security Group** | Create new with these rules: | |
| | - SSH (22) from My IP | For management |
| | - HTTP (80) from Anywhere | For the app |
| | - HTTPS (443) from Anywhere | For SSL (optional) |

### 1.3 Launch and Note Details

After launching, note down:
- **Public IPv4 Address**: e.g., `54.123.45.67`
- **Key Pair File**: e.g., `tria-key.pem`

### 1.4 Connect via SSH

```bash
# On Mac/Linux
chmod 400 tria-key.pem
ssh -i tria-key.pem ubuntu@54.123.45.67

# On Windows (PowerShell)
ssh -i tria-key.pem ubuntu@54.123.45.67
```

---

## Step 2: Setup EC2 Instance (5 minutes)

### 2.1 Run Setup Script

On your EC2 instance:

```bash
# Download setup script
wget https://raw.githubusercontent.com/YOUR-USERNAME/tria-aibpo/main/scripts/setup_ec2.sh

# Make it executable
chmod +x setup_ec2.sh

# Run it
./setup_ec2.sh
```

This installs:
- Docker & Docker Compose
- Git
- Monitoring tools
- Firewall configuration
- Useful aliases

**Important**: After the script completes, log out and log back in:
```bash
exit
ssh -i tria-key.pem ubuntu@54.123.45.67
```

### 2.2 Clone Your Repository

```bash
cd /home/ubuntu/tria-aibpo
git clone https://github.com/YOUR-USERNAME/tria-aibpo.git .
```

---

## Step 3: Configure Environment (5 minutes)

### 3.1 Create .env File

```bash
cd /home/ubuntu/tria-aibpo
cp .env.template .env
nano .env
```

### 3.2 Fill in Required Values

```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here_123
DATABASE_URL=postgresql://tria_admin:your_secure_password_here_123@postgres:5432/tria_aibpo

# Redis
REDIS_PASSWORD=your_redis_password_456

# OpenAI
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Application
SECRET_KEY=generate-a-32-character-secret-key-here
ENVIRONMENT=production
```

**Generate secure passwords**:
```bash
# Database password
openssl rand -base64 20

# Secret key
openssl rand -hex 32
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

---

## Step 4: Start Application (2 minutes)

### 4.1 Build and Start

```bash
docker-compose up -d
```

This will:
- Build the Docker images (~3-5 minutes first time)
- Start PostgreSQL, Redis, and Backend containers
- Set up networking

### 4.2 Verify Services

```bash
# Check running containers
docker-compose ps

# Should show:
# NAME                    STATUS
# tria_aibpo_backend      Up
# tria_aibpo_postgres     Up
# tria_aibpo_redis        Up

# Check logs
docker-compose logs -f backend

# Press Ctrl+C to exit logs
```

### 4.3 Test Locally

```bash
# Health check
curl http://localhost:8003/health

# Expected: {"status":"healthy"}

# Test chatbot
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","session_id":"test"}'
```

### 4.4 Access from Browser

Open in your browser:
- **App**: `http://YOUR-EC2-IP`
- **API Docs**: `http://YOUR-EC2-IP/docs`
- **Health**: `http://YOUR-EC2-IP/health`

Replace `YOUR-EC2-IP` with your actual EC2 public IP.

---

## Step 5: Setup GitHub Actions (5 minutes)

### 5.1 Generate SSH Key on EC2

On your EC2 instance:

```bash
# Generate SSH key for GitHub Actions
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github_actions_key -N ""

# View the private key
cat ~/.ssh/github_actions_key

# Copy this entire output (including BEGIN and END lines)
```

### 5.2 Add Public Key to Authorized Keys

```bash
cat ~/.ssh/github_actions_key.pub >> ~/.ssh/authorized_keys
```

### 5.3 Add Secrets to GitHub

Go to your GitHub repository:
1. Click **Settings** → **Secrets and variables** → **Actions**
2. Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `EC2_SSH_PRIVATE_KEY` | The private key you copied (entire content) |
| `EC2_HOST` | Your EC2 public IP (e.g., `54.123.45.67`) |

### 5.4 Test Deployment

```bash
# On your local machine
git add .
git commit -m "test: Trigger deployment"
git push origin main
```

Go to **GitHub** → **Actions** tab and watch the deployment!

---

## Step 6: Useful Commands

### On EC2 Instance:

```bash
# View logs
tria-logs

# Check status
tria-ps

# Restart all services
tria-restart

# Stop everything
tria-down

# Start everything
tria-up

# Rebuild and restart
tria-rebuild

# Check health
tria-health

# Clean up old Docker images
tria-clean
```

### Manual Deployment (without GitHub Actions):

```bash
cd /home/ubuntu/tria-aibpo
git pull origin main
docker-compose up -d --build
```

---

## Step 7: Monitoring & Maintenance

### View Application Logs

```bash
# All logs
docker-compose logs

# Follow logs (real-time)
docker-compose logs -f

# Specific service
docker-compose logs backend
docker-compose logs postgres
```

### Monitor Resource Usage

```bash
# CPU and Memory
htop

# Disk usage
df -h

# Docker stats
docker stats

# Network connections
sudo netstat -tulpn | grep LISTEN
```

### Database Backup

```bash
# Manual backup
docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup_$(date +%Y%m%d).sql

# Restore backup
cat backup_20250113.sql | docker exec -i tria_aibpo_postgres psql -U tria_admin tria_aibpo
```

### Automatic Backups

The setup script already configured daily backups at 2 AM to `/home/ubuntu/backups/`.

```bash
# View backups
ls -lh /home/ubuntu/backups/

# View backup log
cat /home/ubuntu/backup.log
```

---

## Step 8: Custom Domain (Optional)

### 8.1 Point Domain to EC2

In your domain registrar (GoDaddy, Namecheap, etc.):

1. Create an **A Record**
   - Name: `@` (or `api` for subdomain)
   - Value: Your EC2 public IP
   - TTL: 600

2. Wait for DNS propagation (~5-60 minutes)

### 8.2 Install SSL Certificate (HTTPS)

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx nginx

# Setup Nginx
sudo nano /etc/nginx/sites-available/tria-aibpo

# Add this configuration:
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/tria-aibpo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

---

## Troubleshooting

### Issue: Can't connect to EC2 instance

**Check**:
1. Security group allows SSH from your IP
2. Key file permissions: `chmod 400 tria-key.pem`
3. Using correct username (`ubuntu` for Ubuntu AMIs)

### Issue: Docker containers not starting

**Diagnosis**:
```bash
docker-compose logs
docker ps -a
```

**Common fixes**:
- Check .env file has correct values
- Restart Docker: `sudo systemctl restart docker`
- Rebuild images: `docker-compose up -d --build --force-recreate`

### Issue: Out of disk space

**Check**:
```bash
df -h
docker system df
```

**Fix**:
```bash
tria-clean
docker system prune -af --volumes
```

### Issue: High memory usage

**Check**:
```bash
docker stats
htop
```

**Fix**:
- Upgrade to t3.large (8 GB RAM)
- Adjust Docker memory limits in docker-compose.yml

---

## Cost Breakdown

| Item | Cost |
|------|------|
| EC2 t3.medium (2 vCPU, 4 GB) | ~$30/month |
| EBS Storage (30 GB) | ~$3/month |
| Data Transfer (10 GB/month) | Free tier |
| **Total** | **~$33/month** |

**Optional upgrades**:
- t3.large (8 GB RAM): +$30/month
- Elastic IP (static IP): Free if attached
- Domain name: ~$12/year

---

## Scaling Up

When you outgrow this setup (500+ concurrent users):

1. **Keep the complex setup** we created earlier:
   - Terraform for infrastructure
   - ECS Fargate for auto-scaling
   - RDS for managed database
   - ElastiCache for Redis
   - Load Balancer for HA

2. **OR upgrade gradually**:
   - Add a second EC2 instance
   - Use AWS RDS for PostgreSQL
   - Use ElastiCache for Redis
   - Add Application Load Balancer

---

## Summary

You now have:
- ✅ Tria AI-BPO running on AWS EC2
- ✅ Automatic deployment via GitHub Actions
- ✅ Docker Compose for easy management
- ✅ Daily automatic backups
- ✅ Monitoring and logging
- ✅ Cost: ~$30/month

**Next Steps**:
1. Test your chatbot thoroughly
2. Set up custom domain (optional)
3. Monitor performance and costs
4. Scale up when needed

---

**Questions?** Check the main documentation or open a GitHub issue.

**Last Updated**: 2025-11-13
**Guide Version**: 1.0 (MVP)
