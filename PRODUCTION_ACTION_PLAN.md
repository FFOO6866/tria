# Production Readiness: Detailed Action Plan
## Based on Phase 1 Verification Results (2025-11-19)

**Current Score: 7/14 (50%) - NEEDS WORK**

---

## ✅ What's Already Working

1. **OpenAI API**: Configured with GPT-4 Turbo
2. **Xero Credentials**: Properly configured in .env
3. **ChromaDB**: Connected and populated
   - 9 policy documents
   - 14 FAQ documents
4. **Environment Configuration**: All keys present

---

## ❌ Critical Blockers (Must Fix)

### BLOCKER 1: PostgreSQL Not Running
**Error**: Connection to localhost:5433 refused

**Root Cause**: PostgreSQL service not started

**Fix Options**:
```bash
# Option A: Start via Docker Compose (Recommended)
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria
docker-compose up -d postgres

# Option B: Start local PostgreSQL service
# (If installed locally on Windows)
# Services -> PostgreSQL -> Start

# Verify it's running:
docker-compose ps
# Should show: tria_aibpo_postgres Up (healthy)
```

**Impact**: Cannot test order processing, customer data, or product catalog without database

---

### BLOCKER 2: Redis Authentication Failing
**Error**: Invalid username-password pair or user is disabled

**Root Cause**: Redis password mismatch between .env and actual Redis config

**Fix Options**:
```bash
# Option A: Start Redis via Docker Compose (Recommended)
docker-compose up -d redis

# Option B: Remove Redis password requirement
# Edit .env:
# REDIS_PASSWORD=  (leave empty if Redis has no password)

# Option C: Check Docker Compose redis configuration
# File: docker-compose.yml
# Ensure REDIS_PASSWORD matches between .env and docker-compose.yml

# Verify:
docker exec -it tria_aibpo_redis redis-cli
# If password required: AUTH <password>
# Test: PING (should return PONG)
```

**Impact**: Caching disabled, slower response times, higher OpenAI costs

---

### BLOCKER 3: Xero API Connection Error
**Error**: 'function' object has no attribute 'before_call'

**Root Cause**: Likely OAuth authentication issue or library incompatibility

**Fix**:
```bash
# Check if refresh token is expired
# Xero refresh tokens expire after 60 days

# Option A: Refresh the Xero token
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria
python scripts/get_xero_tokens.py

# Follow prompts to re-authenticate
# This will generate new XERO_REFRESH_TOKEN

# Update .env with new token

# Option B: Check xero_client.py for API changes
# The error suggests a library version mismatch
# May need to update xero-python library:
pip install --upgrade xero-python
```

**Impact**: Cannot create invoices, verify customers, or check inventory in Xero

---

## ⚠️ Warnings (Should Fix)

### WARNING 1: Escalation Rules Collection Empty
**Impact**: Complaint handling will use fallback logic instead of RAG-based escalation

**Fix**:
```bash
# Check if markdown files exist
ls data/policies/escalation_rules.md

# If exists, rebuild knowledge base:
python scripts/build_knowledge_base_from_markdown.py

# If doesn't exist, create sample escalation rules or proceed without
```

---

### WARNING 2: Tone Guidelines Collection Empty
**Impact**: Responses use default tone instead of context-aware tone adaptation

**Fix**:
```bash
# Check if markdown files exist
ls data/policies/tone_guidelines.md

# If exists, rebuild knowledge base:
python scripts/build_knowledge_base_from_markdown.py

# If doesn't exist, system will work but without tone adaptation
```

---

## 📋 Step-by-Step Execution Plan

### Step 1: Start Docker Services (10 minutes)
```bash
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be healthy (30 seconds)
timeout /t 30

# Verify services
docker-compose ps

# Expected output:
# tria_aibpo_postgres    Up (healthy)
# tria_aibpo_redis       Up (healthy)
```

---

### Step 2: Fix Xero API Connection (15 minutes)
```bash
# Re-authenticate with Xero to get fresh token
python scripts/get_xero_tokens.py

# Follow the prompts:
# 1. Opens browser to Xero login
# 2. Authorize the application
# 3. Copy the code from redirect URL
# 4. Paste into terminal
# 5. New XERO_REFRESH_TOKEN is displayed

# Update .env file with new XERO_REFRESH_TOKEN

# Test connection:
python -c "
from integrations.xero_client import get_xero_client
client = get_xero_client()
response = client._make_request('GET', '/Organisation')
print(f'Xero Status: {response.status_code}')
print(f'Organization: {response.json()['Organisations'][0]['Name']}')
"
```

---

### Step 3: Verify System State Again (5 minutes)
```bash
# Re-run verification to confirm fixes
python scripts/phase1_verify_system_state.py

# Expected score: 10-12/14 (71-86%)
# Remaining issues should be warnings only
```

---

### Step 4: Load Xero Master Data (20 minutes)
**Only proceed if database and Xero are both connected**

```bash
# First verify database has products and customers
python -c "
from database import get_db_engine
from config import config
from sqlalchemy import text

engine = get_db_engine()
with engine.connect() as conn:
    products = conn.execute(text('SELECT COUNT(*) FROM products WHERE is_active=true')).fetchone()[0]
    outlets = conn.execute(text('SELECT COUNT(*) FROM outlets')).fetchone()[0]
    print(f'Database has {products} products and {outlets} outlets')
"

# Load to Xero (dry-run first to preview)
python scripts/load_xero_demo_data.py --dry-run

# If output looks good, load for real
python scripts/load_xero_demo_data.py

# Expected:
# - Creates customers in Xero from outlets table
# - Creates products in Xero from products table
# - Skips duplicates automatically
```

---

### Step 5: Test End-to-End Order Flow (15 minutes)
```bash
# Start the API server in one terminal
python src/enhanced_api.py

# In another terminal, test order processing
python scripts/test_order_with_xero.py

# This will:
# 1. Send WhatsApp-style order messages
# 2. Process through chatbot
# 3. Create orders in database
# 4. Create invoices in Xero
# 5. Show agent timeline
```

---

### Step 6: Run Full Verification (10 minutes)
```bash
# Run the production verification script
python scripts/verify_production_readiness.py

# This checks:
# - Server health
# - Cache integration
# - Streaming endpoint
# - Basic performance
# - All components initialized

# Expected: All checks pass
```

---

### Step 7: Test Chat Quality (20 minutes)
```bash
# Start server (if not already running)
python src/enhanced_api.py

# In another terminal, test various conversation types
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello!",
    "user_id": "test_user",
    "session_id": "test_001"
  }'

# Test policy question
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is your refund policy?",
    "user_id": "test_user",
    "session_id": "test_001"
  }'

# Test product inquiry
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Do you have pizza boxes?",
    "user_id": "test_user",
    "session_id": "test_001"
  }'

# Test order placement (if you have products loaded)
curl -X POST http://localhost:8003/api/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi, this is A&W Jewel. I need 100 pizza boxes and 50 liners.",
    "user_id": "test_user",
    "session_id": "test_001"
  }'
```

---

### Step 8: Performance Testing (30 minutes)
```bash
# Follow the comprehensive testing guide
# File: docs/TESTING_GUIDE.md

# Key phases:
# - Phase 2: Cache verification (10 min)
# - Phase 3: Performance benchmarks (30 min)
# - Phase 4: Load testing (30 min)
```

---

### Step 9: Document Final Results (15 minutes)
```bash
# Collect all test results
mkdir -p test_results
cp phase1_verification_results.json test_results/
cp verification_results.json test_results/

# Create final report
# Use template in docs/TESTING_GUIDE.md (Phase 9)

# Update production readiness status based on actual results
```

---

## ⏱️ Time Estimates

| Phase | Task | Time | Priority |
|-------|------|------|----------|
| 1 | Start Docker services | 10 min | P0 |
| 2 | Fix Xero connection | 15 min | P0 |
| 3 | Re-verify system | 5 min | P0 |
| 4 | Load Xero master data | 20 min | P0 |
| 5 | Test end-to-end flow | 15 min | P0 |
| 6 | Run verification | 10 min | P1 |
| 7 | Test chat quality | 20 min | P1 |
| 8 | Performance testing | 30 min | P1 |
| 9 | Document results | 15 min | P1 |
| **TOTAL** | **Complete verification** | **140 min** | **(2h 20min)** |

**P0 Tasks**: 65 minutes (Must complete to claim "working")
**P1 Tasks**: 75 minutes (Should complete to claim "production ready")

---

## 🎯 Success Criteria

### Minimum Viable (50% Production Ready)
- ✅ Database connected
- ✅ Redis connected (or gracefully disabled)
- ✅ Xero API connected
- ✅ One successful end-to-end order test
- ✅ Server starts without errors

### Production Ready (85% Production Ready)
- Everything in Minimum Viable, plus:
- ✅ Xero master data loaded (customers + products)
- ✅ Cache hit rate > 30% after warm-up
- ✅ P95 latency < 5 seconds
- ✅ 10 concurrent users handled successfully
- ✅ All security tests pass
- ✅ Monitoring collecting metrics

### Production Excellent (95%+ Production Ready)
- Everything in Production Ready, plus:
- ✅ Performance benchmarks pass all targets
- ✅ Load tests pass (50+ concurrent users)
- ✅ Comprehensive test documentation
- ✅ All knowledge base collections populated
- ✅ Audit logging verified working

---

## 📊 Current Status Summary

**Phase 1 Verification Results:**
- Configuration: 5/6 checks passed (83%)
- Database: 0/3 checks passed (0%) ← **BLOCKER**
- Redis: 0/2 checks passed (0%) ← **BLOCKER**
- ChromaDB: 2/4 checks passed (50%)
- Xero: 0/3 checks passed (0%) ← **BLOCKER**

**Overall: 7/14 (50%)**

**Status**: System has excellent code but is NOT RUNNING
**Action**: Follow Steps 1-3 above to get to 70%+ readiness

---

## 🚀 Quick Start (If You Just Want It Working)

```bash
# 1. Start services
docker-compose up -d postgres redis

# 2. Wait for startup
timeout /t 30

# 3. Fix Xero token
python scripts/get_xero_tokens.py

# 4. Load master data
python scripts/load_xero_demo_data.py

# 5. Test it works
python src/enhanced_api.py &
python scripts/test_order_with_xero.py

# 6. If all pass: System is working!
```

---

**Next**: Execute Step 1 (Start Docker Services)
