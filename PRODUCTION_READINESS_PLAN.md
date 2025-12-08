# TRIA AIBPO Production Readiness Plan

**Created**: 2025-12-08
**Status**: Active
**Priority**: P0 - Critical

---

## Executive Summary

This document outlines the comprehensive plan to achieve 100% production readiness for the TRIA AIBPO platform. All tasks follow the **NO MOCKUP, NO HARDCODE, NO SIMULATED DATA** policy.

### Current State (2025-12-08)

| Component | Status | Issue |
|-----------|--------|-------|
| Frontend | Working | UI loads correctly |
| Backend Health | Healthy | All services show connected |
| ChromaDB | **NOT INITIALIZED** | RAG/Knowledge base not loaded |
| Chatbot API | **FAILING** | Returns error on all requests |
| Monitoring | Not Exposed | /metrics, /docs return 404 |
| Auto-Recovery | Missing | Server stayed down after stop |

---

## Phase 1: Critical Fixes (P0 - Immediate)

### 1.1 Fix ChromaDB Initialization

**Problem**: Production health check shows `"chromadb": "not_initialized"`

**Root Cause**: Knowledge base collections not created/loaded on server startup

**Existing Scripts**:
- `scripts/build_knowledge_base.py` - Indexes policy documents
- `scripts/build_knowledge_base_from_markdown.py` - Indexes from markdown

**Required Actions**:
```bash
# On production server (SSH to 13.214.14.130)
cd /path/to/tria

# Option 1: Build from .docx files
python scripts/build_knowledge_base.py

# Option 2: Build from markdown files
python scripts/build_knowledge_base_from_markdown.py

# Verify
python scripts/build_knowledge_base.py --verify-only
```

**Files to Check**:
- `docs/policy/*.docx` - Policy documents exist
- `data/chromadb/` - ChromaDB persistence directory
- `src/rag/chroma_client.py` - ChromaDB client singleton

**Validation**:
```bash
curl -sk https://tria.himeet.ai/health | jq .chromadb
# Expected: "connected" (not "not_initialized")
```

---

### 1.2 Fix Chatbot API Failures

**Problem**: All chatbot requests return:
```json
{"detail":"I apologize, but I'm having trouble processing your request right now..."}
```

**Root Cause**: Likely cascading failure from ChromaDB not being initialized

**Diagnosis Steps**:
```bash
# Check backend logs
journalctl -u tria-aibpo -f --since "10 minutes ago"
# OR
docker logs tria-backend --tail 100

# Look for:
# - ChromaDB connection errors
# - OpenAI API errors
# - Exception stack traces
```

**Files to Check**:
- `src/enhanced_api.py:542` - ChromaDB health check logic
- `src/agents/enhanced_customer_service_agent.py` - Agent initialization
- `src/rag/knowledge_base.py` - KnowledgeBase class

**Fix Order**:
1. Fix ChromaDB (1.1 above)
2. Restart backend service
3. Test chatbot endpoint

---

### 1.3 Expose Monitoring Endpoints

**Problem**: `/metrics`, `/docs`, `/api/v1/cache/stats` return 404

**Root Cause**: Next.js frontend catches all routes; nginx not proxying to backend

**Required Actions**:

Edit nginx config to proxy monitoring routes to backend:
```nginx
# /etc/nginx/sites-available/tria-aibpo.conf

# Add before the catch-all location
location /metrics {
    proxy_pass http://127.0.0.1:8001/metrics;
    proxy_set_header Host $host;
}

location /docs {
    proxy_pass http://127.0.0.1:8001/docs;
    proxy_set_header Host $host;
}

location /openapi.json {
    proxy_pass http://127.0.0.1:8001/openapi.json;
    proxy_set_header Host $host;
}
```

**Validation**:
```bash
sudo nginx -t && sudo systemctl reload nginx
curl https://tria.himeet.ai/docs  # Should show Swagger UI
curl https://tria.himeet.ai/metrics  # Should show Prometheus metrics
```

---

### 1.4 Add Auto-Restart and Health Alerting

**Problem**: Server went down and stayed down until manual restart

**Required Actions**:

1. **Ensure systemd auto-restart**:
```ini
# /etc/systemd/system/tria-aibpo.service
[Service]
Restart=always
RestartSec=10
```

2. **Add healthcheck script**:
```bash
# /opt/tria/scripts/healthcheck.sh
#!/bin/bash
response=$(curl -s -o /dev/null -w "%{http_code}" https://tria.himeet.ai/health)
if [ "$response" != "200" ]; then
    echo "Health check failed: $response"
    systemctl restart tria-aibpo
    # Send alert (Slack/PagerDuty)
fi
```

3. **Add cron for health monitoring**:
```bash
# crontab -e
*/5 * * * * /opt/tria/scripts/healthcheck.sh >> /var/log/tria-healthcheck.log 2>&1
```

---

## Phase 2: Data Consistency (P1)

### 2.1 Verify Data Integrity

**Check Product Data**:
```sql
-- On production PostgreSQL
SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL;
SELECT COUNT(*) FROM products WHERE embedding IS NULL;
-- All products should have embeddings for semantic search
```

**Check Outlet Data**:
```sql
SELECT id, name, city FROM outlets ORDER BY id;
-- Verify outlets match frontend dropdown
```

**Existing Scripts**:
- `scripts/load_products_from_excel.py` - Load products from Excel
- `scripts/load_outlets_from_excel.py` - Load outlets from Excel
- `scripts/generate_product_embeddings.py` - Generate OpenAI embeddings

---

### 2.2 Verify ChromaDB Collections

**Expected Collections** (from `scripts/build_knowledge_base.py`):
- `policies_en` - TRIA Rules and Policies
- `faqs_en` - Product FAQ Handbook
- `escalation_rules` - Escalation Routing Guide
- `tone_personality` - Tone and Personality Guidelines

**Verification Script**:
```python
from src.rag.chroma_client import get_chroma_client, list_collections

client = get_chroma_client()
collections = list_collections(client)
print(f"Collections: {collections}")

for name in collections:
    coll = client.get_collection(name)
    print(f"  {name}: {coll.count()} documents")
```

---

### 2.3 Verify Configuration Consistency

**Check Environment Variables**:
```bash
# On production server
cat .env | grep -v PASSWORD | grep -v SECRET | grep -v KEY
```

**Required Variables** (from `src/config.py`):
- `DATABASE_URL` - PostgreSQL connection
- `OPENAI_API_KEY` - OpenAI API key
- `TAX_RATE` - Tax rate for orders
- `XERO_SALES_ACCOUNT_CODE` - Xero sales account
- `XERO_TAX_TYPE` - Xero tax type
- `REDIS_HOST`, `REDIS_PORT` - Redis connection

---

## Phase 3: Monitoring & Alerting (P1)

### 3.1 Deploy Monitoring Stack

**Existing Configuration**:
- `monitoring/docker-compose.monitoring.yml`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/alerts.yml`
- `monitoring/alertmanager/config.yml`

**Deployment**:
```bash
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# Verify
curl http://localhost:9090  # Prometheus
curl http://localhost:3001  # Grafana (admin/admin)
curl http://localhost:9093  # Alertmanager
```

---

### 3.2 Configure Alert Channels

**Edit `monitoring/alertmanager/config.yml`**:
- Add PagerDuty API key
- Add Slack webhook URL
- Configure email recipients

---

## Phase 4: Testing & Validation (P1)

### 4.1 Run Existing Test Scripts

**Smoke Tests**:
```bash
python scripts/smoke_test.py
python scripts/test_core_system.py
```

**Integration Tests**:
```bash
python scripts/test_chatbot_endpoint.py
python scripts/test_rag_retrieval.py
python scripts/test_cache_integration.py
```

**Load Tests** (in staging only):
```bash
python scripts/load_test_1_sustained.py  # 10 users, 1 hour
python scripts/load_test_2_burst.py      # 50 users, 5 min
```

---

### 4.2 End-to-End Validation Checklist

- [ ] Health endpoint returns all services healthy
- [ ] ChromaDB shows collections with documents
- [ ] Chatbot responds to "hello" message
- [ ] Chatbot responds to product inquiry
- [ ] Chatbot handles order request
- [ ] Order creates Xero invoice
- [ ] Conversation history is saved
- [ ] Cache is working (second request faster)

---

## Phase 5: Documentation & Standards (P2)

### 5.1 Create Data Dictionary

**File**: `docs/DATA_DICTIONARY.md`

Contents:
- Database table definitions
- API request/response schemas
- Environment variable catalog
- ChromaDB collection schemas

### 5.2 Update CLAUDE.md

Add enforcement rules for:
- Naming convention adherence
- Data dictionary reference requirement
- Duplicate check before creation
- File path consistency rules

### 5.3 Scripts Inventory

**File**: `scripts/README.md`

Document all 66 scripts with:
- Purpose
- Usage
- Dependencies
- Example commands

---

## Existing Resources (DO NOT DUPLICATE)

### Scripts Available
| Script | Purpose | Usage |
|--------|---------|-------|
| `build_knowledge_base.py` | Build RAG from .docx | `python scripts/build_knowledge_base.py` |
| `build_knowledge_base_from_markdown.py` | Build RAG from .md | Same |
| `load_products_from_excel.py` | Load product catalog | `python scripts/load_products_from_excel.py` |
| `load_outlets_from_excel.py` | Load outlet data | `python scripts/load_outlets_from_excel.py` |
| `generate_product_embeddings.py` | Generate embeddings | `python scripts/generate_product_embeddings.py` |
| `validate_production_config.py` | Validate config | `python scripts/validate_production_config.py` |
| `verify_production_readiness.py` | Check readiness | `python scripts/verify_production_readiness.py` |
| `smoke_test.py` | Basic functionality test | `python scripts/smoke_test.py` |
| `test_chromadb_connection.py` | Test ChromaDB | `python scripts/test_chromadb_connection.py` |

### Configuration Files
| File | Purpose |
|------|---------|
| `src/config.py` | Centralized configuration |
| `src/config_validator.py` | Config validation functions |
| `src/database.py` | Database connection pooling |
| `.env.example` | Environment template |

### Monitoring Files
| File | Purpose |
|------|---------|
| `monitoring/prometheus.yml` | Prometheus config |
| `monitoring/alerts.yml` | Alert rules |
| `monitoring/alertmanager/config.yml` | Alert routing |
| `monitoring/docker-compose.monitoring.yml` | Monitoring stack |

---

## Success Criteria

### P0 Complete When:
- [ ] `curl https://tria.himeet.ai/health` shows ChromaDB "connected"
- [ ] Chatbot API returns valid responses
- [ ] No 404 on `/metrics` endpoint
- [ ] Auto-restart configured and tested

### P1 Complete When:
- [ ] All products have embeddings
- [ ] All ChromaDB collections populated
- [ ] Monitoring stack deployed
- [ ] All test scripts pass

### P2 Complete When:
- [ ] Data dictionary created
- [ ] CLAUDE.md updated with enforcement
- [ ] Scripts README complete
- [ ] Documentation audit complete

---

## Appendix: Production Server Details

**Server**: AWS EC2
**IP**: 13.214.14.130
**Domain**: tria.himeet.ai
**OS**: Ubuntu 22.04
**Services**:
- FastAPI backend (port 8001)
- Next.js frontend (port 3000)
- PostgreSQL (port 5432)
- Redis (port 6379)
- Nginx (ports 80, 443)

---

**Last Updated**: 2025-12-08
**Owner**: Development Team
