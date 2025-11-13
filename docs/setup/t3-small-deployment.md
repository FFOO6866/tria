# t3.small Deployment Guide (2 GB RAM)

**Quick Reference for AWS EC2 t3.small instances**

---

## 🎯 Overview

This guide is for deploying Tria AI-BPO on **t3.small** instances (2 GB RAM, ~$19/month). Perfect for MVP testing and small production workloads.

## ⚡ Quick Start

### 1. Launch EC2 Instance

| Setting | Value |
|---------|-------|
| **Instance Type** | t3.small |
| **RAM** | 2 GB |
| **vCPU** | 2 |
| **AMI** | Ubuntu Server 22.04 LTS (ami-0eeab253db7e765a9) |
| **Architecture** | 64-bit (x86) |
| **Storage** | 20-30 GB GP3 |
| **Cost** | ~$19/month |

### 2. Run Setup Script

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@YOUR-EC2-IP

# Download and run setup
wget https://raw.githubusercontent.com/YOUR-USERNAME/tria/main/scripts/setup_ec2.sh
chmod +x setup_ec2.sh
./setup_ec2.sh

# Log out and back in
exit
ssh -i your-key.pem ubuntu@YOUR-EC2-IP
```

### 3. Clone and Configure

```bash
cd /home/ubuntu/tria-aibpo
git clone https://github.com/YOUR-USERNAME/tria.git .

# Create .env file
cp .env.template .env
nano .env
```

### 4. Deploy with Memory-Optimized Config

```bash
# Use the t3.small optimized configuration
docker-compose -f docker-compose.small.yml up -d

# Check status
docker-compose -f docker-compose.small.yml ps
docker stats

# Check health
curl http://localhost:8003/health
```

---

## 📊 Memory Allocation

The `docker-compose.small.yml` file optimizes for 2 GB RAM:

| Component | Memory Limit | Purpose |
|-----------|--------------|---------|
| PostgreSQL | 400 MB | Database with reduced buffers |
| Redis | 256 MB | Cache with LRU eviction |
| Backend | 1200 MB | API + AI models |
| System | ~192 MB | Ubuntu + Docker overhead |
| **Total** | **2048 MB** | **2 GB** |

## 🔧 Optimizations Applied

### PostgreSQL
- `shared_buffers`: 128MB (default: 256MB)
- `effective_cache_size`: 256MB (default: 512MB)
- `work_mem`: 4MB (default: 16MB)

### Redis
- `maxmemory`: 200MB
- `maxmemory-policy`: allkeys-lru
- Persistence disabled (save "" / appendonly no)

### Backend
- Gunicorn workers: 2 (default: 4)
- Gunicorn threads: 2 (default: 4)
- ChromaDB memory limit: 256MB

### Services Disabled
- **Frontend (Next.js)**: Disabled to save ~300MB
- **Nginx**: Disabled to save ~50MB

Access the API directly on port 8003.

---

## 🔍 Monitoring Commands

```bash
# Check memory usage
docker stats

# Check container status
docker-compose -f docker-compose.small.yml ps

# View logs
docker-compose -f docker-compose.small.yml logs -f backend

# Check available memory
free -h

# Monitor processes
htop
```

---

## 🚨 Warning Signs

Watch for these indicators that you need to upgrade:

### Memory Issues
```bash
# Check for OOM (Out of Memory) kills
dmesg | grep -i "out of memory"

# Check swap usage
free -h
# If swap is high (>500MB), upgrade to t3.medium
```

### Performance Issues
- Response times > 5 seconds
- Frequent 503 errors
- Docker containers restarting
- High swap usage

### Scale Indicators
- More than 5-10 concurrent users
- Database > 100k records
- RAG knowledge base > 500 documents
- 24/7 production usage

---

## 📈 Upgrade Path

### When to Upgrade to t3.medium (4 GB)?

Upgrade when you experience:
- Consistent memory usage > 80%
- Frequent OOM kills
- Need for frontend + Nginx
- Production workload (>10 concurrent users)
- 24/7 uptime requirement

### How to Upgrade

**Option 1: Resize Instance**
1. Stop EC2 instance (Actions → Instance State → Stop)
2. Change instance type (Actions → Instance Settings → Change Instance Type)
3. Select t3.medium
4. Start instance
5. Update deployment to use `docker-compose.yml`

**Option 2: Launch New Instance**
1. Launch new t3.medium instance
2. Run same setup process
3. Use standard `docker-compose.yml` (not .small.yml)
4. Migrate data from old instance
5. Update DNS/load balancer

---

## 🎛️ GitHub Actions Configuration

The deployment workflow automatically detects instance size:

```yaml
# In GitHub repository settings:
# Settings → Secrets and variables → Actions

# Required secrets:
EC2_SSH_PRIVATE_KEY: (your SSH private key)
EC2_HOST: (your EC2 public IP)

# Optional secret (defaults to "small"):
EC2_INSTANCE_SIZE: "small"  # or "medium" for t3.medium+
```

### Deployment Behavior

- **If EC2_INSTANCE_SIZE = "small"** or not set:
  - Uses `docker-compose.small.yml`
  - Memory-optimized configuration
  - Backend-only deployment

- **If EC2_INSTANCE_SIZE = "medium"**:
  - Uses `docker-compose.yml`
  - Full stack (Backend + Frontend + Nginx)
  - Standard memory allocation

---

## 🐛 Troubleshooting

### Issue: Containers Keep Restarting

```bash
# Check container logs
docker-compose -f docker-compose.small.yml logs backend

# Common causes:
# 1. Out of memory - check: free -h
# 2. Missing env vars - check: cat .env
# 3. Database not ready - check: docker-compose ps
```

### Issue: Slow Performance

```bash
# Check memory pressure
docker stats

# If memory is maxed out:
# 1. Restart containers to clear memory
docker-compose -f docker-compose.small.yml restart

# 2. Clear Docker cache
docker system prune -f

# 3. If persistent, upgrade to t3.medium
```

### Issue: Health Check Failing

```bash
# Check backend logs
docker-compose -f docker-compose.small.yml logs -f backend

# Test health endpoint
curl -v http://localhost:8003/health

# Check if port is listening
sudo netstat -tulpn | grep 8003
```

---

## 💰 Cost Comparison

| Instance Type | RAM | vCPU | Cost/Month | Use Case |
|---------------|-----|------|------------|----------|
| **t3.micro** | 1 GB | 2 | FREE | Testing only (will crash) |
| **t3.small** | 2 GB | 2 | ~$19 | **MVP/Small production** ✅ |
| **t3.medium** | 4 GB | 2 | ~$30 | Production recommended |
| **t3.large** | 8 GB | 2 | ~$60 | High traffic production |

---

## 📋 Daily Operations

### Restart Services
```bash
docker-compose -f docker-compose.small.yml restart
```

### Update Code
```bash
cd /home/ubuntu/tria-aibpo
git pull origin main
docker-compose -f docker-compose.small.yml up -d --build
```

### Backup Database
```bash
docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup_$(date +%Y%m%d).sql
```

### View Logs
```bash
# All logs
docker-compose -f docker-compose.small.yml logs

# Follow logs real-time
docker-compose -f docker-compose.small.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.small.yml logs --tail=100
```

---

## ✅ Performance Benchmarks

Expected performance on t3.small:

| Metric | Value | Notes |
|--------|-------|-------|
| Concurrent Users | 5-10 | Before slowdown |
| Response Time (avg) | 1-3s | For simple queries |
| Response Time (AI) | 3-8s | For complex AI queries |
| Requests/minute | ~100 | Sustained load |
| Database Records | 100k | Reasonable limit |
| Uptime | 95%+ | With auto-restart |

---

## 🔐 Security Checklist

- [ ] Security groups allow only necessary ports (22, 80, 443)
- [ ] SSH key permissions set to 400
- [ ] Strong passwords in .env file
- [ ] Firewall (UFW) enabled
- [ ] Automatic security updates enabled
- [ ] Regular backups configured
- [ ] Monitoring and alerts set up

---

## 📚 Additional Resources

- **Full Setup Guide**: `docs/setup/simple-ec2-mvp-deployment.md`
- **Standard Deployment**: Use `docker-compose.yml` for t3.medium+
- **Scaling Guide**: `docs/setup/aws-deployment-guide.md`
- **GitHub Actions**: `.github/workflows/simple-deploy.yml`

---

**Last Updated**: 2025-11-13
**Configuration**: t3.small (2 GB RAM)
**Status**: Optimized for MVP deployment
