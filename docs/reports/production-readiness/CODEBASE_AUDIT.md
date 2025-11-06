# Codebase Audit - Duplicate Functions & Patterns

**Date**: 2025-11-07
**Purpose**: Identify duplicates before fixing connection pooling

---

## 🔍 Audit Results

### 1. Database Connection Patterns

#### **DUPLICATE: Engine Creation (CRITICAL)**

**Location 1**: `src/semantic_search.py:112-121`
```python
engine = create_engine(
    database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={'connect_timeout': 10, 'options': '-c client_encoding=UTF8'}
)
```

**Location 2**: `src/process_order_with_catalog.py:43-51`
```python
engine = create_engine(
    database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={'connect_timeout': 10, 'options': '-c client_encoding=UTF8'}
)
```

**Status**: 🔴 **DUPLICATE** - Exact same pattern, should be centralized

**Action Required**: Create `src/database.py` with global engine management

---

### 2. Product Loading Functions

#### **NOT DUPLICATE: Different Purposes**

**Function 1**: `load_products_with_embeddings()` (semantic_search.py)
- Loads products WITH embeddings from `products.embedding` column
- Used for semantic similarity search
- Returns: Products with `embedding` field as numpy array

**Function 2**: `load_product_catalog()` (process_order_with_catalog.py)
- Loads products WITHOUT embeddings
- Used for general product catalog operations
- Returns: Products with basic fields only

**Status**: ✅ **DIFFERENT PURPOSES** - Keep both

**However**: Both should use centralized engine

---

### 3. Configuration Modules

#### **NOT DUPLICATE: Complementary Purposes**

**Module 1**: `config.py` (NEW)
- Centralized configuration class
- Validates at import time
- Single config instance

**Module 2**: `config_validator.py` (EXISTING)
- Utility functions for validation
- Used by scripts and manual validation
- Lower-level validation functions

**Status**: ✅ **COMPLEMENTARY** - Keep both

**Improvement**: `config.py` should USE `config_validator.py` functions instead of reimplementing

---

### 4. ChromaDB Client Management

**Location**: `src/rag/chroma_client.py`

**Functions**:
- `get_chroma_client()` - Global client getter
- `get_or_create_collection()` - Collection management
- `health_check()` - Health check

**Status**: ✅ **WELL STRUCTURED** - Already using singleton pattern

---

### 5. Environment Variable Access

#### **SCATTERED PATTERN: Needs Consolidation**

**Files using `os.getenv()` directly**:
1. `src/enhanced_api.py` - ✅ MIGRATED to config.py
2. `src/agents/intent_classifier.py` - ❌ NOT MIGRATED
3. `src/agents/enhanced_customer_service_agent.py` - ❌ NOT MIGRATED
4. `src/memory/session_manager.py` - ❓ UNKNOWN
5. `src/rag/knowledge_base.py` - ❓ UNKNOWN
6. `src/process_order_with_catalog.py` - ❌ Still has `os.getenv('TAX_RATE')`
7. Scripts in `scripts/` - ❓ UNKNOWN

**Action Required**: Complete migration to centralized config

---

## 📋 Required Actions (Priority Order)

### **Priority 1: Fix Engine Duplication (CRITICAL)**

**Create**: `src/database.py`
```python
"""
Centralized Database Connection Management
==========================================

Global SQLAlchemy engine with connection pooling.
All database operations should use this module.

NO MOCKUPS - Real PostgreSQL connection only.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global engine instance
_engine = None

def get_db_engine(database_url: Optional[str] = None):
    """
    Get or create global database engine with connection pooling

    Returns:
        SQLAlchemy engine with pooling configured
    """
    global _engine

    if _engine is None:
        from config import config
        url = database_url or config.get_database_url()

        _engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections after 1 hour
            connect_args={
                'connect_timeout': 10,
                'options': '-c client_encoding=UTF8'
            }
        )
        logger.info("Database engine initialized with connection pooling")

    return _engine

def dispose_engine():
    """Dispose engine and close all connections (for testing/cleanup)"""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
```

**Update**:
1. `src/semantic_search.py` - Use `get_db_engine()`
2. `src/process_order_with_catalog.py` - Use `get_db_engine()`

---

### **Priority 2: Consolidate Configuration**

**Update `config.py`** to use `config_validator.py`:
```python
from config_validator import validate_database_url, validate_api_keys

class ProductionConfig:
    def __init__(self):
        # Use existing validation functions
        self.DATABASE_URL = validate_database_url(required=True)
        # ... rest of config
```

---

### **Priority 3: Complete Config Migration**

**Files needing audit**:
- [ ] `src/agents/intent_classifier.py`
- [ ] `src/agents/enhanced_customer_service_agent.py`
- [ ] `src/memory/session_manager.py`
- [ ] `src/memory/context_builder.py`
- [ ] `src/rag/knowledge_base.py`
- [ ] `src/rag/retrieval.py`
- [ ] `src/privacy/pii_scrubber.py`
- [ ] `src/privacy/data_retention.py`
- [ ] All scripts in `scripts/`

---

## 📊 Duplication Summary

| Pattern | Locations | Status | Action |
|---------|-----------|--------|--------|
| Engine creation | 2 files | 🔴 DUPLICATE | Centralize in database.py |
| Product loading | 2 files | ✅ DIFFERENT | Keep both, share engine |
| Config modules | 2 files | ✅ COMPLEMENTARY | Integrate |
| os.getenv() calls | 8+ files | 🟡 SCATTERED | Complete migration |
| ChromaDB client | 1 file | ✅ GOOD | No action |

---

## ✅ Best Practices Moving Forward

1. **ALWAYS check for existing utilities** before creating new functions
2. **Use global singletons** for expensive resources (DB engines, API clients)
3. **Centralize configuration** - no scattered `os.getenv()` calls
4. **Document patterns** in CLAUDE.md for consistency
5. **Test before claiming completion**

---

**Next Steps**: Execute fixes in priority order
