# Docker Deployment Guide

## Overview

The TRIA AI-BPO Platform is fully containerized with Docker, allowing you to deploy the entire stack (PostgreSQL + FastAPI Backend + Next.js Frontend) to any cloud platform independently.

## Architecture

The application consists of 3 Docker containers:

1. **postgres** - PostgreSQL 16 database
2. **backend** - FastAPI application (Python 3.11)
3. **frontend** - Next.js 15 application (Node 20)

All containers communicate via a dedicated Docker network (`tria_aibpo_network`).

---

## Quick Start (Local)

### Prerequisites
- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- OpenAI API key

### Step 1: Configure Environment

1. Copy the Docker environment template:
```bash
cp .env.docker .env.docker.local
```

2. Edit `.env.docker.local` and add your OpenAI API key:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

### Step 2: Start All Services

```bash
# Build and start all containers
docker-compose --env-file .env.docker.local up --build

# Or run in detached mode
docker-compose --env-file .env.docker.local up -d --build
```

### Step 3: Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **PostgreSQL**: localhost:5433 (external), postgres:5432 (internal)

### Step 4: Stop Services

```bash
docker-compose down
```

### Step 5: Clean Up (Optional)

```bash
# Stop and remove all containers, networks, and volumes
docker-compose down -v
```

---

## Container Details

### 1. PostgreSQL Container

**Image**: `postgres:16`
**Port**: `5433:5432` (host:container)
**Volume**: `tria_postgres_data` (persistent)

- Automatically creates database schema on first run
- Includes health check for startup verification
- Data persists across container restarts

### 2. Backend Container

**Base Image**: `python:3.11-slim`
**Port**: `8001:8001`
**Dependencies**: requirements.txt

Key features:
- Waits for PostgreSQL to be healthy before starting
- Includes health check endpoint (`/health`)
- Mounts `./data` directory for generated files
- Runs with uvicorn ASGI server

### 3. Frontend Container

**Base Image**: `node:20-alpine`
**Port**: `3000:3000`
**Build**: Multi-stage build with standalone output

Key features:
- Optimized production build
- Automatic API URL configuration
- Runs as non-root user
- Minimal image size

---

## Cloud Deployment

### AWS (EC2, ECS, or Lightsail)

#### Option 1: EC2 Instance

1. **Launch EC2 instance** (Ubuntu 22.04, t3.medium or larger)

2. **Install Docker**:
```bash
# SSH into instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. **Clone repository**:
```bash
git clone https://github.com/your-repo/new_project_template.git
cd new_project_template
```

4. **Configure environment**:
```bash
cp .env.docker .env.docker.local
nano .env.docker.local  # Add your API keys
```

5. **Start services**:
```bash
docker-compose --env-file .env.docker.local up -d --build
```

6. **Configure security group**:
   - Inbound: Port 3000 (Frontend), Port 8001 (API)
   - Optionally: Port 5433 (PostgreSQL) for external access

#### Option 2: AWS ECS (Fargate)

1. Push images to Amazon ECR
2. Create ECS Task Definition with 3 containers
3. Deploy to Fargate cluster
4. Use Application Load Balancer for traffic distribution

### Google Cloud Platform (GCP)

#### Option 1: Compute Engine

Similar to AWS EC2 - follow same Docker installation steps.

#### Option 2: Cloud Run

1. **Build and push images**:
```bash
# Backend
gcloud builds submit --tag gcr.io/your-project/tria-backend .

# Frontend
gcloud builds submit --tag gcr.io/your-project/tria-frontend ./frontend
```

2. **Deploy services**:
```bash
# Deploy backend
gcloud run deploy tria-backend \
  --image gcr.io/your-project/tria-backend \
  --platform managed \
  --set-env-vars OPENAI_API_KEY=your-key

# Deploy frontend
gcloud run deploy tria-frontend \
  --image gcr.io/your-project/tria-frontend \
  --platform managed \
  --set-env-vars NEXT_PUBLIC_API_URL=https://tria-backend-xxx.run.app
```

### Microsoft Azure

#### Option 1: Azure Container Instances

```bash
# Create resource group
az group create --name tria-rg --location eastus

# Create container group
az container create \
  --resource-group tria-rg \
  --name tria-app \
  --image your-registry/tria-backend:latest \
  --dns-name-label tria-app \
  --ports 8001 3000
```

#### Option 2: Azure App Service (Containers)

1. Push images to Azure Container Registry
2. Create App Service with Docker Compose
3. Configure environment variables in App Service

### DigitalOcean

1. **Create Droplet** (Ubuntu 22.04, $12/month or larger)

2. **Install Docker** (same as AWS EC2 steps)

3. **Deploy with Docker Compose**:
```bash
git clone your-repo
cd new_project_template
cp .env.docker .env.docker.local
# Add API keys to .env.docker.local
docker-compose --env-file .env.docker.local up -d --build
```

4. **Configure firewall**:
```bash
ufw allow 3000
ufw allow 8001
ufw enable
```

### Heroku

1. **Install Heroku CLI**

2. **Create apps**:
```bash
heroku create tria-backend
heroku create tria-frontend
```

3. **Add PostgreSQL addon**:
```bash
heroku addons:create heroku-postgresql:standard-0 -a tria-backend
```

4. **Deploy containers**:
```bash
# Backend
heroku container:push web -a tria-backend
heroku container:release web -a tria-backend

# Frontend
heroku container:push web -a tria-frontend
heroku container:release web -a tria-frontend
```

### Railway / Render / Fly.io

These platforms support Docker Compose directly:

1. Connect GitHub repository
2. Detect docker-compose.yml automatically
3. Add environment variables in dashboard
4. Deploy

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | `sk-...` |
| `DATABASE_URL` | PostgreSQL connection string | Auto-configured in Docker |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `XERO_CLIENT_ID` | Xero OAuth2 client ID | - |
| `XERO_CLIENT_SECRET` | Xero OAuth2 client secret | - |
| `XERO_TENANT_ID` | Xero organization ID | - |
| `XERO_ACCESS_TOKEN` | Xero API access token | - |

---

## Production Checklist

### Before Deployment

- [ ] Configure production environment variables
- [ ] Update database password (default is for development only)
- [ ] Add proper CORS origins in `src/enhanced_api.py`
- [ ] Set up SSL/TLS certificates (use Let's Encrypt)
- [ ] Configure domain DNS records
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy for PostgreSQL data

### Security Hardening

1. **Change database password**:
   - Update in `docker-compose.yml` under postgres service
   - Update `DATABASE_URL` in backend service

2. **Use secrets management**:
   - AWS Secrets Manager / Azure Key Vault / GCP Secret Manager
   - Or use Docker secrets:
   ```bash
   echo "sk-your-key" | docker secret create openai_key -
   ```

3. **Enable HTTPS**:
   - Use nginx reverse proxy with Let's Encrypt
   - Or use cloud load balancer with SSL termination

4. **Restrict database access**:
   - Remove port `5433:5432` mapping in production
   - Database should only be accessible within Docker network

### Scaling Considerations

1. **Database**:
   - Use managed PostgreSQL (AWS RDS, Azure Database, GCP Cloud SQL)
   - Update `DATABASE_URL` to point to managed instance

2. **Backend**:
   - Scale horizontally by running multiple containers
   - Use load balancer to distribute traffic

3. **Frontend**:
   - Can be served from CDN (build static export)
   - Or scale with container orchestration

---

## Monitoring & Logs

### View Container Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Health Checks

- **Backend**: `curl http://localhost:8001/health`
- **Frontend**: `curl http://localhost:3000`
- **Database**: `docker exec tria_aibpo_postgres pg_isready -U tria_admin`

### Container Status

```bash
docker-compose ps
```

---

## Troubleshooting

### Issue: Containers fail to start

**Solution**: Check logs
```bash
docker-compose logs backend
docker-compose logs frontend
```

### Issue: Database connection refused

**Solution**: Verify PostgreSQL is healthy
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Issue: API returns 500 errors

**Solution**: Check environment variables
```bash
docker-compose exec backend env | grep OPENAI_API_KEY
docker-compose exec backend env | grep DATABASE_URL
```

### Issue: Frontend can't reach backend

**Solution**: Verify network connectivity
```bash
docker-compose exec frontend ping backend
docker-compose exec frontend curl http://backend:8001/health
```

---

## Advanced: Kubernetes Deployment

For production-grade orchestration, deploy to Kubernetes:

1. **Create Kubernetes manifests** (or use Helm chart)
2. **Deploy PostgreSQL** with StatefulSet
3. **Deploy backend** with Deployment (replicas: 3)
4. **Deploy frontend** with Deployment (replicas: 2)
5. **Create Services** and **Ingress** for external access

Example kubectl commands:
```bash
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml
```

---

## Backup & Restore

### Backup PostgreSQL Data

```bash
# Backup to file
docker exec tria_aibpo_postgres pg_dump -U tria_admin tria_aibpo > backup.sql

# Backup with Docker volume
docker run --rm \
  -v tria_aibpo_postgres_data:/volume \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz -C /volume .
```

### Restore PostgreSQL Data

```bash
# Restore from SQL file
docker exec -i tria_aibpo_postgres psql -U tria_admin tria_aibpo < backup.sql

# Restore from volume backup
docker run --rm \
  -v tria_aibpo_postgres_data:/volume \
  -v $(pwd):/backup \
  alpine sh -c "rm -rf /volume/* && tar xzf /backup/postgres_backup.tar.gz -C /volume"
```

---

## Cost Estimation

### Development/Testing

- **DigitalOcean Droplet**: $12/month (2 GB RAM, 1 vCPU)
- **AWS EC2 t3.small**: ~$15/month
- **Render Free Tier**: $0 (limited resources)

### Production

- **AWS**:
  - EC2 t3.medium: ~$30/month
  - RDS PostgreSQL: ~$15/month
  - ALB: ~$20/month
  - **Total**: ~$65/month

- **GCP**:
  - Cloud Run: Pay-per-use (~$10-50/month depending on traffic)
  - Cloud SQL: ~$10/month

- **Azure**:
  - Container Instances: ~$30/month
  - PostgreSQL: ~$15/month
  - **Total**: ~$45/month

---

## Next Steps

1. **Set up CI/CD**:
   - GitHub Actions to build and push Docker images
   - Auto-deploy on push to main branch

2. **Add monitoring**:
   - Prometheus + Grafana for metrics
   - ELK Stack or Loki for logs
   - Sentry for error tracking

3. **Implement auto-scaling**:
   - Horizontal Pod Autoscaler (Kubernetes)
   - Auto Scaling Groups (AWS)
   - Container autoscaling (GCP Cloud Run)

4. **Set up staging environment**:
   - Separate docker-compose.staging.yml
   - Use different database instance

---

## Support

For deployment issues:
1. Check container logs: `docker-compose logs -f`
2. Verify environment variables: `docker-compose config`
3. Test health endpoints: `/health` (backend), homepage (frontend)
4. Review this guide's troubleshooting section

For cloud-specific issues, consult the respective cloud provider's documentation.
