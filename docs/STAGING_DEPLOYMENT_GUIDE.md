# Staging Deployment Guide
**Tria AI-BPO Customer Service Chatbot**

**Version**: 1.0
**Last Updated**: 2025-11-14
**Purpose**: Deploy to staging environment for validation testing before production

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Deployment Steps](#deployment-steps)
4. [Validation Testing](#validation-testing)
5. [Monitoring Setup](#monitoring-setup)
6. [Load Testing](#load-testing)
7. [Success Criteria](#success-criteria)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedure](#rollback-procedure)

---

## Prerequisites

### Required Access

- [ ] AWS account with EC2 access (or target cloud provider)
- [ ] SSH key for server access
- [ ] GitHub repository access
- [ ] OpenAI API key
- [ ] Xero API credentials (if testing Xero integration)
- [ ] Domain name for staging (optional but recommended)

### Required Tools

- [ ] Terraform 1.5+ (for AWS deployment)
- [ ] Docker 20.10+
- [ ] Docker Compose 2.0+
- [ ] Git
- [ ] SSH client
- [ ] curl or Postman (for API testing)

###Required Information

- [ ] Staging server IP address or hostname
- [ ] Database credentials
- [ ] Redis password
- [ ] SSL certificates (if using HTTPS)
- [ ] Alert notification endpoints (Slack/PagerDuty)

---

## Infrastructure Setup

### Option A: AWS EC2 (Recommended)

**Step 1: Configure Terraform Variables**

```bash
cd terraform/aws
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

Edit with staging values:
```hcl
# terraform.tfvars
project_name = "tria-aibpo-staging"
environment = "staging"
aws_region = "us-east-1"
instance_type = "t3.medium"  # 4GB RAM recommended for staging
key_name = "your-ssh-key-name"
allowed_ssh_ips = ["YOUR_IP/32"]
enable_monitoring = true
```

**Step 2: Deploy Infrastructure**

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy
terraform apply

# Save outputs
terraform output > ../staging_outputs.txt
```

**Step 3: Note Server Details**

```bash
# Get server IP
export STAGING_IP=$(terraform output -raw public_ip)
echo "Staging server: $STAGING_IP"

# Test SSH access
ssh -i ~/.ssh/your-key.pem ubuntu@$STAGING_IP
```

### Option B: DigitalOcean Droplet

**Create Droplet**:
- Size: Basic - 4GB RAM / 2 vCPUs ($24/month)
- Image: Ubuntu 22.04 LTS
- Datacenter: Choose closest to your users
- Add SSH key
- Enable monitoring
- Enable backups (optional for staging)

**Note IP Address**:
```bash
export STAGING_IP=YOUR_DROPLET_IP
```

### Option C: Existing Server

Requirements:
- Ubuntu 22.04 LTS (or similar)
- 4GB RAM minimum
- 20GB disk space
- Ports 22, 80, 443, 8003 open
- Docker and Docker Compose installed

---

## Deployment Steps

### Step 1: Server Preparation

```bash
# SSH into server
ssh ubuntu@$STAGING_IP

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Log out and back in for group changes to take effect
exit
ssh ubuntu@$STAGING_IP
```

### Step 2: Clone Repository

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/your-org/tria.git
sudo chown -R $USER:$USER tria
cd tria

# Checkout staging branch (or main)
git checkout main
```

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Critical Settings for Staging**:

```bash
# Environment
ENVIRONMENT=staging

# Database
DATABASE_URL=postgresql://tria_admin:CHANGE_THIS_PASSWORD_123@postgres:5432/tria_aibpo
POSTGRES_USER=tria_admin
POSTGRES_PASSWORD=CHANGE_THIS_PASSWORD_123
POSTGRES_DB=tria_aibpo
POSTGRES_PORT=5433

# PostgreSQL optimization (4GB server)
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=512MB
POSTGRES_WORK_MEM=16MB
POSTGRES_MAINTENANCE_WORK_MEM=128MB

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=CHANGE_THIS_REDIS_PASSWORD_456
REDIS_DB=0
REDIS_MAX_MEMORY=512mb

# OpenAI
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# Xero (optional for staging)
XERO_CLIENT_ID=YOUR_CLIENT_ID
XERO_CLIENT_SECRET=YOUR_CLIENT_SECRET
XERO_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
XERO_TENANT_ID=YOUR_TENANT_ID
XERO_SALES_ACCOUNT_CODE=200
XERO_TAX_TYPE=OUTPUT2

# Business settings
TAX_RATE=0.08
CUTOFF_TIME=14:00

# Monitoring (enable for staging)
ENABLE_METRICS=true
SENTRY_DSN=  # Optional: Add Sentry for error tracking

# Deployment size
DEPLOYMENT_SIZE=medium  # For 4GB server
```

**Security Notes**:
- Generate strong passwords (use `openssl rand -base64 32`)
- Never commit .env file to git
- Use separate credentials from production

### Step 4: Deploy Services

```bash
# Start services with medium profile (includes frontend + nginx)
docker-compose --profile full-stack up -d

# Or for 2GB server (backend only):
# docker-compose up -d

# Wait for startup (30 seconds)
sleep 30

# Check container status
docker ps
```

**Expected Containers** (4GB deployment):
- tria_aibpo_postgres
- tria_aibpo_redis
- tria_aibpo_backend
- tria_aibpo_frontend (if full-stack)
- tria_aibpo_nginx (if full-stack)

### Step 5: Initialize Database

```bash
# Check if database is ready
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "SELECT 1;"

# Run any migrations (if applicable)
# docker exec -it tria_aibpo_backend python migrations/migrate.py

# Load sample data (optional for staging)
docker exec -it tria_aibpo_backend python scripts/setup_test_environment.py
```

### Step 6: Initialize Knowledge Base

```bash
# Build ChromaDB knowledge base from policies
docker exec -it tria_aibpo_backend python scripts/build_knowledge_base_from_markdown.py --yes

# Verify indexing
docker logs tria_aibpo_backend | grep "chunks indexed"
# Expected: "57 total policy chunks indexed"
```

### Step 7: Configure Firewall

```bash
# Install UFW (if not already installed)
sudo apt-get install ufw

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow backend API (if not using nginx)
sudo ufw allow 8003/tcp

# Enable firewall
sudo ufw --force enable

# Verify rules
sudo ufw status
```

---

## Validation Testing

### Quick Smoke Test

```bash
# Test health endpoint
curl http://$STAGING_IP:8003/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected",
#   "chromadb": "connected"
# }
```

### Test Chat API

```bash
# Send test message
curl -X POST http://$STAGING_IP:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, what is your refund policy?",
    "session_id": "staging-test-1"
  }' | jq .

# Expected: JSON response with chatbot answer
```

### Run Production E2E Tests

```bash
# From your local machine or on server
cd /opt/tria
python tests/test_production_e2e.py

# Expected: All 3 test cases pass
```

---

## Monitoring Setup

### Step 1: Install Node Exporter

```bash
# Install node_exporter for system metrics
cd /opt
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvf node_exporter-1.7.0.linux-amd64.tar.gz
cd node_exporter-1.7.0.linux-amd64

# Run as systemd service
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/opt/node_exporter-1.7.0.linux-amd64/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter
```

### Step 2: Set Up Basic Monitoring

```bash
# Install Docker stats monitoring
docker stats --no-stream

# Set up log rotation
sudo tee /etc/logrotate.d/tria-aibpo > /dev/null <<EOF
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  size=10M
  missingok
  delaycompress
  copytruncate
}
EOF
```

### Step 3: Configure Alerts (Optional)

Follow `/monitoring/README.md` to set up:
- Prometheus (for metrics collection)
- Grafana (for dashboards)
- Alertmanager (for alerts)

**Quick Setup**:
```bash
# On your local machine or monitoring server
# Install and configure Prometheus to scrape staging server
# Point to http://STAGING_IP:9100 (node_exporter)
# Point to http://STAGING_IP:8003/metrics (if backend metrics enabled)
```

---

## Load Testing

### Step 1: Prepare Load Test Environment

```bash
# Install dependencies on your local machine
pip install aiohttp

# Or run from staging server
ssh ubuntu@$STAGING_IP
cd /opt/tria/scripts
```

### Step 2: Run Test Suite

**Option A: Quick Test Suite** (recommended for staging):

```bash
# Run shortened load tests (~1 hour total)
python run_all_load_tests.py --quick

# Tests will run:
# 1. Sustained: 10 users for 10 minutes
# 2. Burst: 50 users for 2 minutes
# 3. Spike: 5→100→5 users for 2 minutes
# 4. Soak: 5 users for 30 minutes
# 5. Chaos: 20 users for 5 minutes
```

**Option B: Individual Tests**:

```bash
# Test 1: Sustained load (most important)
python load_test_1_sustained.py

# Test 2: Burst load
python load_test_2_burst.py

# Test 3: Spike test
python load_test_3_spike.py

# Skip soak and chaos for quick validation
```

### Step 3: Review Test Results

```bash
# Check test results
ls -lh load_test_*_results_*.json

# View summary
cat load_test_suite_summary_*.json | jq .

# Review detailed results
cat load_test_1_sustained_results_*.json | jq .metrics
```

---

## Success Criteria

### Staging Approval Checklist

**Infrastructure** ✅:
- [ ] All Docker containers running
- [ ] Database accessible and seeded
- [ ] Redis operational
- [ ] ChromaDB indexed (57 chunks)
- [ ] Health check returns "healthy"
- [ ] Firewall configured

**Functional Testing** ✅:
- [ ] Chat API responds correctly
- [ ] Policy retrieval working (RAG)
- [ ] Intent classification accurate
- [ ] Tone adaptation working
- [ ] Response validation functioning
- [ ] Production E2E tests pass (3/3)

**Performance** ✅:
- [ ] Sustained load test passed (10 users, error rate <5%)
- [ ] Burst load test passed (50 users, error rate <10%)
- [ ] P95 latency <10s with cache
- [ ] Cache hit rate >50%
- [ ] No memory leaks detected

**Monitoring** ✅:
- [ ] System metrics visible (CPU, memory, disk)
- [ ] Application logs accessible
- [ ] Health checks automated
- [ ] (Optional) Grafana dashboards configured
- [ ] (Optional) Alerts tested

**Security** ✅:
- [ ] Firewall rules applied
- [ ] Secrets in environment variables (not code)
- [ ] SSL configured (if using domain)
- [ ] Database password changed from default
- [ ] Redis password set

### Go/No-Go Decision

**Criteria for Production Deployment**:
1. ✅ All staging tests passed
2. ✅ System stable for 7+ days
3. ✅ No critical issues found
4. ✅ Performance meets SLAs
5. ✅ Monitoring and alerting operational
6. ✅ Runbooks tested
7. ✅ Rollback procedure verified
8. ✅ Stakeholder approval obtained

---

## Troubleshooting

### Issue: Containers Won't Start

```bash
# Check Docker logs
docker-compose logs

# Check specific container
docker logs tria_aibpo_backend

# Check disk space
df -h

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Database Connection Failed

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check database logs
docker logs tria_aibpo_postgres

# Verify credentials
cat .env | grep POSTGRES

# Test connection manually
docker exec -it tria_aibpo_postgres psql -U tria_admin -d tria_aibpo -c "SELECT 1;"
```

### Issue: High Latency in Tests

```bash
# Check cache is working
docker exec -it tria_aibpo_redis redis-cli -a YOUR_PASSWORD DBSIZE

# Check backend logs for errors
docker logs tria_aibpo_backend | grep -i error

# Monitor resource usage
docker stats

# Check if OpenAI API is slow
curl https://status.openai.com/
```

### Issue: Load Tests Fail

```bash
# Increase timeout values in load test scripts
# Edit TEST_DURATION_SECONDS or timeout values

# Reduce concurrent users for constrained resources
# Edit NUM_CONCURRENT_USERS in test scripts

# Check system resources during test
docker stats
free -h
df -h
```

---

## Rollback Procedure

If staging deployment fails:

### Step 1: Stop Services

```bash
cd /opt/tria
docker-compose down
```

### Step 2: Restore Previous Version (if applicable)

```bash
# Rollback git to previous version
git log --oneline  # Find previous commit
git checkout PREVIOUS_COMMIT_HASH

# Or checkout previous branch/tag
git checkout v1.0.0
```

### Step 3: Restore Database Backup (if needed)

```bash
# List backups
ls -lh backups/

# Restore from backup
cat backups/backup_YYYYMMDD_HHMMSS.sql | \
  docker exec -i tria_aibpo_postgres psql -U tria_admin tria_aibpo
```

### Step 4: Restart Services

```bash
docker-compose up -d

# Verify health
curl http://localhost:8003/health
```

### Step 5: Document Issues

Create incident report:
- What failed
- When it failed
- Error messages
- Steps attempted
- Root cause (if known)
- Remediation plan

---

## Next Steps After Staging Success

1. **Document Lessons Learned** - Update runbooks with staging findings
2. **Plan Production Deployment** - Schedule maintenance window
3. **Prepare Communication** - Notify stakeholders of production deployment
4. **Create Production Checklist** - Based on staging experience
5. **Set Up Production Monitoring** - Replicate staging monitoring
6. **Test Rollback in Staging** - Ensure rollback procedure works
7. **Conduct Tabletop Exercise** - Walk through incident scenarios
8. **Get Final Approvals** - Security, compliance, stakeholders

---

## Staging Environment Maintenance

### Daily Checks

```bash
# Check service health
curl http://STAGING_IP:8003/health

# Check disk space
ssh ubuntu@STAGING_IP 'df -h'

# Check Docker containers
ssh ubuntu@STAGING_IP 'docker ps'
```

### Weekly Maintenance

```bash
# Update system packages
ssh ubuntu@STAGING_IP 'sudo apt-get update && sudo apt-get upgrade -y'

# Clean Docker system
ssh ubuntu@STAGING_IP 'docker system prune -f'

# Restart services
ssh ubuntu@STAGING_IP 'cd /opt/tria && docker-compose restart'
```

### Data Refresh

```bash
# Rebuild knowledge base (if policies updated)
ssh ubuntu@STAGING_IP 'docker exec -it tria_aibpo_backend python scripts/build_knowledge_base_from_markdown.py --yes'

# Reload sample data
ssh ubuntu@STAGING_IP 'docker exec -it tria_aibpo_backend python scripts/setup_test_environment.py'
```

---

## Contact Information

- **Staging Environment**: http://STAGING_IP:8003
- **DevOps Lead**: [Contact Info]
- **Engineering Manager**: [Contact Info]
- **On-Call Engineer**: See /docs/OPERATIONAL_RUNBOOK.md

---

## References

- Production Readiness Review: `/docs/reports/production-readiness/COMPREHENSIVE_PRODUCTION_READINESS_REVIEW_2025-11-14.md`
- Operational Runbook: `/docs/OPERATIONAL_RUNBOOK.md`
- Load Testing Guide: `/scripts/README.md`
- Monitoring Setup: `/monitoring/README.md`
- Deployment Guide: `/docs/DEPLOYMENT.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
**Next Review**: After staging validation complete

---

**End of Staging Deployment Guide**
