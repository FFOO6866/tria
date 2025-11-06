# Tria AIBPO Tests

Test suite for the Tria AI-BPO order processing system.

---

## 🧪 Testing Strategy

### 3-Tier Testing Approach

**Tier 1: Unit Tests** - Fast, isolated tests
- Mock external dependencies
- Test individual functions/classes
- Located in: `tier1_unit/`

**Tier 2: Integration Tests** - Component integration
- Real database (test database)
- Real APIs (when possible)
- Test multiple components together
- Located in: `tier2_integration/`

**Tier 3: End-to-End Tests** - Full system tests
- Production-like environment
- Real databases, APIs, services
- Complete user workflows
- Located in: `tier3_e2e/`

---

## 📁 Directory Structure

```
tests/
├── README.md                        # This file
├── tier1_unit/                      # Unit tests (with mocks)
├── tier2_integration/               # Integration tests (real DB)
├── tier3_e2e/                       # End-to-end tests (full system)
├── fixtures/                        # Test data and fixtures
└── test_connection_pool.py          # Connection pooling verification
```

---

## 🔍 Current Tests

### Connection Pooling Test ⚠️ CRITICAL
**File**: `test_connection_pool.py`

Verifies database connection pooling works correctly:
- ✅ Singleton pattern (same engine instance)
- ✅ Connection reuse (returned to pool)
- ✅ No dispose between calls (engine persists)
- ✅ Load products pattern (actual usage)

**Run**:
```bash
python tests/test_connection_pool.py
```

**Expected Output**:
```
[TEST 1] Testing singleton pattern...
✅ PASS: Same engine instance returned

[TEST 2] Testing connection reuse...
✅ PASS: All connections returned to pool

[TEST 3] Testing engine persistence...
✅ PASS: Engine persisted between calls

[TEST 4] Testing load products pattern...
✅ PASS: Load products pattern works correctly

Results: 4/4 tests passed
```

---

## 🎯 Testing Guidelines

### NO MOCKING Policy (Tiers 2-3)

**Tier 2 & 3 tests MUST use real infrastructure**:
- ✅ Real PostgreSQL database (test database)
- ✅ Real OpenAI API (or staging)
- ✅ Real ChromaDB instance
- ❌ NO database mocks
- ❌ NO API response mocks

**Only Tier 1 tests can mock external dependencies**

### Test Data Management

**Use fixtures/** for:
- Sample orders
- Test product catalogs
- Expected responses
- Test conversation histories

**Separate test database**:
```bash
# .env.test
DATABASE_URL=postgresql://user:pass@localhost:5432/tria_aibpo_test
```

### Test File Naming

- Unit tests: `test_unit_<module>.py`
- Integration tests: `test_integration_<feature>.py`
- E2E tests: `test_e2e_<workflow>.py`

---

## 🚀 Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Tier
```bash
# Unit tests only (fast)
pytest tests/tier1_unit/

# Integration tests (slower)
pytest tests/tier2_integration/

# E2E tests (slowest)
pytest tests/tier3_e2e/
```

### Run Single Test
```bash
python tests/test_connection_pool.py
```

### Run with Coverage
```bash
pytest --cov=src tests/
```

---

## 📝 Writing New Tests

### 1. Choose Tier
- **Tier 1**: Testing single function with mocks
- **Tier 2**: Testing database operations, API integrations
- **Tier 3**: Testing complete user workflows

### 2. Create Test File
```python
# tests/tier2_integration/test_integration_semantic_search.py
import pytest
from src.database import get_db_engine, dispose_engine
from src.semantic_search import semantic_product_search

def test_semantic_search_with_real_db():
    """Test semantic search with real database"""
    # Uses real PostgreSQL
    # Uses real OpenAI API
    results = semantic_product_search(
        message="pizza boxes for 10 inch",
        database_url=os.getenv('DATABASE_URL'),
        api_key=os.getenv('OPENAI_API_KEY')
    )

    assert len(results) > 0
    assert 'pizza' in results[0]['description'].lower()

@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """Cleanup after all tests"""
    yield
    dispose_engine()  # Clean up engine after tests
```

### 3. Run & Verify
```bash
pytest tests/tier2_integration/test_integration_semantic_search.py -v
```

---

## 🔧 Test Configuration

### Environment Variables
Create `.env.test` for test-specific configuration:
```bash
# Test database (separate from dev/prod)
DATABASE_URL=postgresql://user:pass@localhost:5432/tria_test

# Test API keys (can be same as dev)
OPENAI_API_KEY=your_test_key

# Test-specific settings
LOG_LEVEL=DEBUG
```

### Fixtures Location
```
tests/fixtures/
├── sample_orders.json           # Test orders
├── sample_products.json         # Test products
├── sample_conversations.json    # Test conversations
└── expected_responses.json      # Expected outputs
```

---

## 📊 Test Coverage Goals

**Current Coverage**: TBD
**Target Coverage**: 80%+

**Priority Areas**:
1. ✅ Database connection pooling (VERIFIED)
2. ⚠️ Order processing logic (NEEDS TESTS)
3. ⚠️ Semantic search (NEEDS TESTS)
4. ⚠️ Agent responses (NEEDS TESTS)
5. ⚠️ Memory system (NEEDS TESTS)

---

## 🚨 Critical Tests Required

Before production deployment:
- [ ] Load test connection pooling (100+ concurrent requests)
- [ ] Test semantic search with various inputs
- [ ] Test order processing end-to-end
- [ ] Test conversation memory across sessions
- [ ] Test PII scrubbing effectiveness
- [ ] Test ChromaDB knowledge retrieval

---

## 📚 See Also

- **Testing Strategy**: [CLAUDE.md](../CLAUDE.md#testing--validation)
- **Development Guidelines**: [CLAUDE.md](../CLAUDE.md)
- **Production Status**: [docs/reports/production-readiness/](../docs/reports/production-readiness/)

---

**Last Updated**: 2025-11-07
**Test Coverage**: Connection pooling verified, others pending
