# TRIA AI-BPO Digital Ocean Hosting Sizing Guide

## Executive Summary

Based on the TRIA AI-BPO architecture analysis, this document provides detailed Digital Ocean sizing recommendations for different deployment scenarios.

## Architecture Analysis

### Current Stack

**Services (from docker-compose.yml)**:
1. **PostgreSQL 16** - Relational database
2. **FastAPI Backend** (Python 3.10+) with:
   - Kailash SDK (workflow automation framework)
   - DataFlow (database operations with auto-generated nodes)
   - OpenAI GPT-4 integration (external API calls)
   - ChromaDB (vector database for RAG/semantic search)
   - Multi-agent system (intent classification, customer service)
   - Session management and conversation memory
   - Excel processing (openpyxl)
   - PDF generation (reportlab)
   - Xero API integration
3. **Next.js 15 Frontend** (React 19)

### Resource Characteristics

**Backend (Memory-Heavy)**:
- AI agent coordination and inference
- ChromaDB vector database (in-memory operations)
- OpenAI response processing (large JSON payloads)
- Connection pooling (20 base + 40 overflow = 60 max connections)
- Excel file loading and manipulation
- Session data caching
- **Estimated Base Memory**: 2-4 GB (idle), 4-8 GB (active load)

**Database (I/O-Heavy)**:
- PostgreSQL with connection pooling
- Conversation history storage
- Product catalog, customers, orders
- Vector embeddings (if stored in PostgreSQL)
- **Estimated Base Memory**: 1-2 GB (minimal), 2-4 GB (active)

**Frontend (CPU-Light)**:
- Next.js server-side rendering
- Static asset serving
- **Estimated Base Memory**: 512 MB - 1 GB

## Digital Ocean Droplet Sizing Recommendations

### Scenario 1: POV/Demo Environment

**Use Case**:
- Proof of Value demonstration
- Internal testing and development
- Low concurrent users (< 20)
- Acceptable response times (2-5 seconds)

**Recommended Droplet: Premium Intel - $84/month**

```yaml
Droplet Type: Premium Intel
CPU: 4 vCPUs
Memory: 8 GB RAM
Storage: 160 GB SSD
Transfer: 5 TB
Price: $84/month
```

**Resource Allocation**:
```
PostgreSQL:  2 GB RAM, 1 vCPU
Backend:     4 GB RAM, 2 vCPUs
Frontend:    1 GB RAM, 1 vCPU
System:      1 GB RAM (buffer)
```

**Why This Works**:
- ✅ Adequate memory for ChromaDB vector operations
- ✅ Sufficient CPU for AI agent coordination
- ✅ Room for Docker overhead and system processes
- ✅ Database can handle 20-40 connections comfortably
- ✅ Fast SSD for database and ChromaDB persistence
- ⚠️ Will struggle with >20 concurrent users
- ⚠️ No horizontal scaling

**Alternative: Basic - $48/month (Tight Budget)**

```yaml
Droplet Type: Basic (Regular)
CPU: 2 vCPUs
Memory: 4 GB RAM
Storage: 80 GB SSD
Transfer: 4 TB
Price: $48/month
```

**Resource Allocation**:
```
PostgreSQL:  1 GB RAM, 1 vCPU
Backend:     2 GB RAM, 1 vCPU
Frontend:    512 MB RAM, shared CPU
System:      512 MB RAM (buffer)
```

**Limitations**:
- ❌ ChromaDB performance degraded (memory swapping likely)
- ❌ Only 5-10 concurrent users maximum
- ❌ Slower response times (5-10 seconds)
- ✅ Adequate for single-user demos
- ⚠️ Use ONLY for development/testing, NOT for client demos

---

### Scenario 2: Production-Ready (Small Business)

**Use Case**:
- Production deployment for 1-3 small businesses
- Moderate concurrent users (20-50)
- Professional response times (< 2 seconds)
- 99.5% uptime target

**Recommended Droplet: Premium Intel - $168/month**

```yaml
Droplet Type: Premium Intel
CPU: 8 vCPUs
Memory: 16 GB RAM
Storage: 320 GB SSD
Transfer: 6 TB
Price: $168/month
```

**Resource Allocation**:
```
PostgreSQL:  4 GB RAM, 2 vCPUs (with tuning)
Backend:     8 GB RAM, 4 vCPUs
Frontend:    2 GB RAM, 1 vCPU
ChromaDB:    Dedicated within backend (2-3 GB)
System:      2 GB RAM (buffer)
```

**PostgreSQL Tuning for 16 GB**:
```ini
# /etc/postgresql/16/main/postgresql.conf
shared_buffers = 4GB                  # 25% of RAM
effective_cache_size = 12GB           # 75% of RAM
maintenance_work_mem = 1GB
work_mem = 64MB
max_connections = 100
checkpoint_completion_target = 0.9
wal_buffers = 16MB
random_page_cost = 1.1                # SSD optimized
```

**Why This Works**:
- ✅ Comfortable memory for all services
- ✅ Good CPU for parallel processing
- ✅ Fast response times even under load
- ✅ Room for traffic spikes
- ✅ Can handle 50-75 concurrent users
- ✅ Production-grade performance
- ⚠️ Single point of failure (no redundancy)

---

### Scenario 3: Production-Ready (Enterprise)

**Use Case**:
- Multiple enterprise clients
- High concurrent users (100-200)
- Fast response times (< 1 second)
- 99.9% uptime target
- Horizontal scaling capability

**Option A: Single Large Droplet - $336/month**

```yaml
Droplet Type: Premium Intel
CPU: 16 vCPUs
Memory: 32 GB RAM
Storage: 640 GB SSD
Transfer: 7 TB
Price: $336/month
```

**Resource Allocation**:
```
PostgreSQL:  8 GB RAM, 4 vCPUs
Backend:     16 GB RAM, 8 vCPUs
Frontend:    4 GB RAM, 2 vCPUs
ChromaDB:    Dedicated (4-6 GB)
System:      4 GB RAM (buffer)
```

**Option B: Multi-Droplet Architecture (RECOMMENDED) - $420/month**

```yaml
Database Droplet (Premium Intel):
  CPU: 4 vCPUs
  Memory: 8 GB RAM
  Storage: 160 GB SSD
  Price: $84/month

Backend Droplet 1 (Premium Intel):
  CPU: 8 vCPUs
  Memory: 16 GB RAM
  Storage: 160 GB SSD
  Price: $168/month

Backend Droplet 2 (Premium Intel):
  CPU: 8 vCPUs
  Memory: 16 GB RAM
  Storage: 160 GB SSD
  Price: $168/month

Total: $420/month
```

**Architecture Diagram (Option B)**:
```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │  (DO LB: $12/mo)│
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
    ┌───────▼──────┐  ┌──────▼───────┐  ┌───▼────────┐
    │  Backend 1   │  │  Backend 2   │  │  Frontend  │
    │  16GB, 8vCPU │  │  16GB, 8vCPU │  │  (Vercel)  │
    └───────┬──────┘  └──────┬───────┘  └────────────┘
            │                │
            └────────┬───────┘
                     │
              ┌──────▼───────┐
              │  PostgreSQL  │
              │  8GB, 4vCPU  │
              └──────────────┘
```

**Why Option B is Better**:
- ✅ Database isolation (no resource contention)
- ✅ Horizontal scaling (2 backend instances)
- ✅ High availability (one backend can fail)
- ✅ Better resource utilization
- ✅ Can add more backend droplets easily
- ✅ Database can be upgraded independently
- ✅ Frontend can be deployed to Vercel (free tier)

**Total Cost Option B with Load Balancer**: $432/month
- Database: $84/month
- Backend 1: $168/month
- Backend 2: $168/month
- Load Balancer: $12/month
- Frontend: $0 (Vercel free tier) or $20 (Vercel Pro)

---

## Additional Digital Ocean Services

### Managed Database (Alternative to Self-Hosted PostgreSQL)

**Managed PostgreSQL Pricing**:

| Plan | vCPUs | RAM | Storage | Price |
|------|-------|-----|---------|-------|
| DB-s-1vcpu-1gb | 1 | 1 GB | 10 GB | $15/month |
| DB-s-2vcpu-4gb | 2 | 4 GB | 38 GB | $60/month |
| DB-s-4vcpu-8gb | 4 | 8 GB | 115 GB | $120/month |
| DB-s-6vcpu-16gb | 6 | 16 GB | 270 GB | $240/month |

**Recommended for Production**: DB-s-4vcpu-8gb ($120/month)

**Benefits of Managed Database**:
- ✅ Automated backups (daily)
- ✅ Point-in-time recovery
- ✅ Automatic failover
- ✅ Monitoring and alerting
- ✅ Automatic minor version upgrades
- ✅ Connection pooling (PgBouncer)
- ✅ No database maintenance overhead
- ❌ More expensive than self-hosted

**Revised Enterprise Cost with Managed DB**: $468/month
- Managed PostgreSQL: $120/month
- Backend 1: $168/month
- Backend 2: $168/month
- Load Balancer: $12/month

---

### Block Storage (for Large Files and Backups)

```yaml
Use Case: Store Excel files, generated PDFs, backups
Pricing: $0.10/GB/month ($10 for 100GB)
Recommended: 100-250 GB ($10-25/month)
```

**Mount to Backend Containers**:
```bash
/mnt/tria_storage/
├── inventory/          # Master inventory Excel files
├── templates/          # DO templates
├── generated/          # Generated DOs and invoices
│   ├── deliveries/
│   └── invoices/
└── backups/           # Database backups
```

---

### Spaces (S3-Compatible Object Storage)

```yaml
Use Case: Long-term file archival, CDN for frontend assets
Pricing: $5/month (250 GB storage + 1 TB transfer)
Additional Storage: $0.02/GB/month
Additional Transfer: $0.01/GB
```

**When to Use**:
- ✅ Archiving old invoices and DOs
- ✅ Serving frontend static assets via CDN
- ✅ Long-term backup retention
- ❌ Not needed for POV/Demo

---

### Load Balancer

```yaml
Pricing: $12/month (includes SSL termination)
Use Case: Multi-backend deployment (Scenario 3)
```

**Features**:
- Health checks and automatic failover
- SSL/TLS termination
- Sticky sessions (for stateful apps)
- Monitoring and metrics

---

### Monitoring and Alerts

```yaml
Included: Basic metrics (CPU, memory, disk, network)
Cost: Free
```

**Recommended Add-On**: **Datadog** or **New Relic** for application monitoring
- Datadog: ~$15/host/month
- New Relic: ~$25/user/month

---

## Recommended Deployment Scenarios

### 🎯 Recommended: POV/Demo ($84/month)

```yaml
Single Droplet: Premium Intel 8GB
- Cost: $84/month
- Users: < 20 concurrent
- Uptime: 99%
- Response Time: 2-5 seconds
```

**Total First Month Cost**: ~$100
- Droplet: $84
- Domain: ~$12/year ($1/month)
- Setup time: ~$0 (self-managed)

**Use For**:
- Client demonstrations
- Internal testing
- POV validation
- Development staging

---

### 🚀 Recommended: Production Small Business ($240/month)

```yaml
Droplet: Premium Intel 16GB ($168/month)
Managed PostgreSQL: DB-s-4vcpu-8gb ($120/month)
Block Storage: 100GB ($10/month)

Total: $298/month
```

**Benefits**:
- No database maintenance
- Automated backups
- Professional performance
- Room to grow

**Total First Month Cost**: ~$350
- Droplet: $168
- Managed DB: $120
- Block Storage: $10
- SSL Certificate: Free (Let's Encrypt)
- Domain: ~$12/year
- Monitoring (optional): $15-25

**Use For**:
- 1-3 small business clients
- 20-50 concurrent users
- Production workloads

---

### 🏢 Recommended: Production Enterprise ($480/month)

```yaml
Backend 1: Premium Intel 16GB ($168/month)
Backend 2: Premium Intel 16GB ($168/month)
Managed PostgreSQL: DB-s-4vcpu-8gb ($120/month)
Load Balancer: $12/month
Block Storage: 250GB ($25/month)

Total: $493/month
```

**Benefits**:
- High availability (no single point of failure)
- Horizontal scaling
- Load distribution
- Professional infrastructure
- Enterprise-ready

**Total First Month Cost**: ~$550
- Backend droplets: $336
- Managed DB: $120
- Load Balancer: $12
- Block Storage: $25
- Monitoring: $30-50

**Use For**:
- Multiple enterprise clients
- 100-200 concurrent users
- Mission-critical workloads
- 99.9% uptime SLA

---

## Cost Optimization Strategies

### 1. Frontend on Vercel (Save $20-40/month)

Deploy Next.js frontend to Vercel:
- **Free Tier**: 100 GB bandwidth, unlimited builds
- **Pro Tier**: $20/month (1 TB bandwidth, better performance)

**Savings**: $20-40/month (no frontend droplet needed)

### 2. ChromaDB on Separate Droplet (Scale Independently)

For high-volume vector search:
- **Small ChromaDB Droplet**: $24/month (2GB, 1 vCPU)
- **Medium ChromaDB Droplet**: $48/month (4GB, 2 vCPUs)

**When to Use**: >100,000 documents indexed or >1000 searches/day

### 3. Use Managed Redis for Session Storage

Instead of in-memory sessions:
- **Managed Redis**: $15/month (512 MB)

**Benefits**:
- Shared sessions across multiple backend instances
- Persistent session storage
- Better for load-balanced setups

### 4. Reserved Instances (Save 10-15%)

Digital Ocean offers reserved pricing for 1-year commitments:
- **1 Year Prepay**: 10% discount
- **2 Year Prepay**: 15% discount

**Example Savings** (16GB droplet):
- Monthly: $168/month
- 1 Year Reserved: ~$151/month (save ~$204/year)

---

## Deployment Recommendations by Budget

### Budget: $100/month (Minimal)
```
Single 8GB Droplet: $84/month
Block Storage: 50GB: $5/month
Domain: ~$1/month
Total: ~$90/month

✅ POV/Demo only
❌ NOT for production
```

### Budget: $300/month (Production-Ready)
```
16GB Droplet: $168/month
Managed PostgreSQL 8GB: $120/month
Block Storage: 100GB: $10/month
Total: ~$298/month

✅ Small business production
✅ 20-50 concurrent users
✅ Automated backups
```

### Budget: $500/month (Enterprise)
```
Backend 1 (16GB): $168/month
Backend 2 (16GB): $168/month
Managed PostgreSQL 8GB: $120/month
Load Balancer: $12/month
Block Storage: 250GB: $25/month
Monitoring: $30/month
Total: ~$523/month

✅ Enterprise production
✅ 100-200 concurrent users
✅ High availability
✅ Horizontal scaling
```

---

## Performance Benchmarks (Estimated)

### POV/Demo (8GB Droplet)

| Metric | Value |
|--------|-------|
| Concurrent Users | 15-20 |
| Avg Response Time | 2-5 seconds |
| Database Queries/sec | 50-100 |
| Vector Searches/sec | 5-10 |
| OpenAI Calls/min | 20-30 |
| Uptime | 99% |

### Production Small (16GB Droplet + Managed DB)

| Metric | Value |
|--------|-------|
| Concurrent Users | 40-50 |
| Avg Response Time | 1-2 seconds |
| Database Queries/sec | 200-300 |
| Vector Searches/sec | 20-30 |
| OpenAI Calls/min | 60-100 |
| Uptime | 99.5% |

### Production Enterprise (2x16GB + LB + Managed DB)

| Metric | Value |
|--------|-------|
| Concurrent Users | 150-200 |
| Avg Response Time | < 1 second |
| Database Queries/sec | 500-800 |
| Vector Searches/sec | 50-100 |
| OpenAI Calls/min | 200-300 |
| Uptime | 99.9% |

---

## Migration Path

### Phase 1: Start Small (Month 1-3)
```
POV/Demo: 8GB Droplet ($84/month)
- Validate product-market fit
- Gather performance metrics
- Identify bottlenecks
```

### Phase 2: Production Ready (Month 4-6)
```
Upgrade to: 16GB Droplet + Managed DB ($298/month)
- Onboard first 1-3 clients
- Monitor performance and usage
- Plan for scaling
```

### Phase 3: Scale Up (Month 7+)
```
Multi-Droplet: 2x16GB + LB + Managed DB ($493/month)
- Support 5-10 clients
- High availability
- Room for growth
```

---

## Monitoring and Alerting Setup

### Essential Metrics to Monitor

**Droplet Metrics**:
- CPU usage (alert if > 80% for 5 minutes)
- Memory usage (alert if > 85%)
- Disk usage (alert if > 80%)
- Network I/O

**Application Metrics**:
- API response times (alert if p95 > 3 seconds)
- OpenAI API errors (alert if error rate > 5%)
- Database connection pool (alert if > 90% utilized)
- ChromaDB query times

**Database Metrics** (Managed PostgreSQL):
- Connection count (alert if > 80 connections)
- Query duration (alert if slow queries > 1 second)
- Replication lag
- Disk I/O

---

## Final Recommendations

### For POV/Demo (Budget: ~$100/month)
```yaml
✅ Start with: Premium Intel 8GB ($84/month)
✅ Add: 50GB Block Storage ($5/month)
✅ Total: ~$90/month
```

### For Production (Budget: ~$300/month) ⭐ RECOMMENDED
```yaml
✅ Droplet: Premium Intel 16GB ($168/month)
✅ Database: Managed PostgreSQL 8GB ($120/month)
✅ Storage: 100GB Block Storage ($10/month)
✅ Total: ~$298/month
```

### For Enterprise (Budget: ~$500/month)
```yaml
✅ Backend 1: Premium Intel 16GB ($168/month)
✅ Backend 2: Premium Intel 16GB ($168/month)
✅ Database: Managed PostgreSQL 8GB ($120/month)
✅ Load Balancer: $12/month
✅ Storage: 250GB Block Storage ($25/month)
✅ Total: ~$493/month
```

---

## Next Steps

1. **Decide on deployment scenario** (POV, Production Small, or Enterprise)
2. **Create Digital Ocean account** and add payment method
3. **Reserve domain name** (if not already owned)
4. **Provision droplet(s)** based on chosen scenario
5. **Set up deployment agent** (use `scripts/deploy_agent.py`)
6. **Configure monitoring** (Digital Ocean built-in + optional Datadog)
7. **Test performance** under expected load
8. **Plan scaling path** based on actual usage

---

**Last Updated**: 2025-11-07
**Version**: 1.0.0
**Maintainer**: TRIA AI-BPO DevOps Team
