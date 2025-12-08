# Kailash SDK

## 🏗️ Architecture Overview

### Core SDK (`sdk-users/`)
**Foundational building blocks** for workflow automation:
- **Purpose**: Custom workflows, fine-grained control, integrations
- **Components**: WorkflowBuilder, LocalRuntime, 110+ nodes, MCP integration
- **Usage**: Direct workflow construction with full programmatic control
- **Install**: `pip install kailash`

### DataFlow (`sdk-users/apps/dataflow/`)
**Zero-config database framework** built on Core SDK:
- **Purpose**: Database operations with automatic model-to-node generation
- **Features**: @db.model decorator generates 9 nodes per model automatically. DataFlow IS NOT AN ORM!
- **Usage**: Database-first applications with enterprise features
- **Install**: `pip install kailash[dataflow]` or `pip install kailash-dataflow`

### Nexus (`sdk-users/apps/nexus/`)
**Multi-channel platform** built on Core SDK:
- **Purpose**: Deploy workflows as API + CLI + MCP simultaneously
- **Features**: Unified sessions, zero-config platform deployment
- **Usage**: Platform applications requiring multiple access methods
- **Install**: `pip install kailash[nexus]` or `pip install kailash-nexus`

### Critical Relationships
- **DataFlow and Nexus are built ON Core SDK** - they don't replace it
- **Framework choice affects development patterns** - different approaches for each
- **All use the same underlying workflow execution** - `runtime.execute(workflow.build())`

## 🎯 Specialized Subagents

### Analysis & Planning
- **ultrathink-analyst** → Deep failure analysis, complexity assessment
- **requirements-analyst** → Requirements breakdown, ADR creation
- **sdk-navigator** → Find patterns before coding, resolve errors during development
- **framework-advisor** → Choose Core SDK, DataFlow, or Nexus; coordinates with specialists

### Framework Implementation
- **nexus-specialist** → Multi-channel platform implementation (API/CLI/MCP)
- **dataflow-specialist** → Database operations with auto-generated nodes (PostgreSQL-only alpha)

### Core Implementation  
- **pattern-expert** → Workflow patterns, nodes, parameters
- **tdd-implementer** → Test-first development
- **intermediate-reviewer** → Review after todos and implementation
- **gold-standards-validator** → Compliance checking

### Testing & Validation
- **testing-specialist** → 3-tier strategy with real infrastructure
- **documentation-validator** → Test code examples, ensure accuracy

### Release & Operations
- **todo-manager** → Task management and project tracking
- **mcp-specialist** → MCP server implementation and integration
- **git-release-specialist** → Git workflows, CI validation, releases

## ⚡ Essential Pattern (All Frameworks)
```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime.local import LocalRuntime

workflow = WorkflowBuilder()
workflow.add_node("NodeName", "id", {"param": "value"})  # String-based
runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())  # ALWAYS .build()
```

## 🚨 Emergency Fixes
- **"Missing required inputs"** → Use sdk-navigator for common-mistakes.md solutions
- **Parameter issues** → Use pattern-expert for 3-method parameter guide
- **Test failures** → Use testing-specialist for real infrastructure setup
- **DataFlow errors** → Use dataflow-specialist for PostgreSQL-specific debugging
- **Nexus platform issues** → Use nexus-specialist for multi-channel troubleshooting
- **Framework selection** → Use framework-advisor to coordinate appropriate specialists

## ⚠️ Critical Rules
- ALWAYS: `runtime.execute(workflow.build())`
- NEVER: `workflow.execute(runtime)`
- String-based nodes: `workflow.add_node("NodeName", "id", {})`
- Real infrastructure: NO MOCKING in Tiers 2-3 tests

## 🔒 Strict Development Guidelines

### Absolutely Required
1. **NO MOCKUPS** - All functionality must use real integrations and services
   - Use actual APIs (Xero, Twilio, SendGrid, etc.)
   - Use real databases (PostgreSQL, MongoDB, Redis)
   - Use actual file systems (Excel, CSV, cloud storage)
   - Mock only in Tier 1 unit tests; Tiers 2-3 use real infrastructure

2. **NO HARDCODING** - All configuration must be externalized
   - Use environment variables for credentials, API keys, endpoints
   - Use configuration files (config.yaml, .env) for settings
   - Use database tables for business rules and dynamic data
   - Never embed URLs, passwords, API keys in source code

3. **NO SIMULATED OR FALLBACK DATA** - Production-grade data handling only
   - Connect to real data sources (databases, APIs, files)
   - Use proper error handling instead of fallback values
   - Fail fast with meaningful errors rather than returning fake data
   - Test data should be in separate test databases, not simulated

4. **ALWAYS CHECK FOR EXISTING CODE** - Enhance, don't duplicate

   **MANDATORY Pre-Creation Checklist:**
   - [ ] Search for similar files: `Glob` pattern matching (e.g., `**/*_agent.py`, `**/semantic*.py`)
   - [ ] Search for existing functions: `Grep` for function names (e.g., `^def load_products`)
   - [ ] Search for duplicate patterns: `Grep` for common patterns (e.g., `create_engine`, `OpenAI\(`)
   - [ ] Check existing modules: Review imports in similar files to find utilities
   - [ ] Review documentation: Check `src/README.md`, `docs/architecture/` for existing components
   - [ ] Consult CODEBASE_AUDIT.md: Check for previously identified duplications

   **Search Examples:**
   ```bash
   # Before creating database helper:
   grep -r "create_engine" src/ --include="*.py"

   # Before creating config loader:
   grep -r "os.getenv" src/ --include="*.py"

   # Before creating new agent:
   find src/agents -name "*.py" -type f

   # Before adding validation:
   grep -r "def validate_" src/ --include="*.py"
   ```

   **Decision Tree:**
   1. **Found exact match?** → Use it, don't create new
   2. **Found similar code?** → Refactor to shared utility, then use
   3. **Found partial match?** → Extend existing with new functionality
   4. **Nothing found?** → Create new, document in relevant README

   **Anti-Patterns to Avoid:**
   - ❌ Creating `utils2.py` because `utils.py` exists → Enhance `utils.py` instead
   - ❌ Copying function to new file → Import and reuse
   - ❌ Creating new validation when `config_validator.py` exists → Use existing
   - ❌ Creating new engine when `database.py` exists → Use `get_db_engine()`

5. **PROPER HOUSEKEEPING AT ALL TIMES** - Maintain directory structure
   - Follow project structure conventions:
     ```
     project_root/
     ├── src/                    # Source code
     │   ├── agents/             # Agent workflows
     │   ├── workflows/          # Reusable workflows
     │   ├── nodes/              # Custom nodes
     │   └── integrations/       # External API integrations
     ├── tests/                  # Test files (mirror src/ structure)
     │   ├── tier1_unit/
     │   ├── tier2_integration/
     │   └── tier3_e2e/
     ├── config/                 # Configuration files
     ├── data/                   # Data files (templates, samples)
     ├── docs/                   # Documentation
     │   └── adr/                # Architecture Decision Records
     └── scripts/                # Utility scripts
     ```
   - Delete obsolete files immediately (no commented-out code files)
   - Keep related files together (workflow + tests in corresponding directories)
   - Use consistent naming: `{component}_agent.py`, `{component}_workflow.py`, `test_{component}.py`
   - Update imports when moving/renaming files
   - Maintain README.md in each major directory explaining contents

### Code Quality Standards
- Use type hints for all function signatures
- Write docstrings for all public functions/classes
- Follow PEP 8 style guidelines
- Use meaningful variable/function names (no `temp`, `data`, `x`)
- Handle errors explicitly (no bare `except:` blocks)
- Log important operations (use proper logging, not print statements)

## 📋 Project-Specific Guidelines

### Tria AIBPO POV Project
**ALWAYS refer to POV documentation before implementing:**
- `TRIA_AIBPO_POV_SCOPE.md` - Complete requirements and scope (if exists)
- `adr/` directory - All Architecture Decision Records
- `REQUIREMENTS_ANALYSIS.md` - Functional/non-functional requirements

### Anti-Pattern: DO NOT OVER-ENGINEER
**Keep it simple for POV/Demo:**
- ❌ Don't build frameworks when functions suffice
- ❌ Don't add features not in requirements
- ❌ Don't create abstractions "for future use"
- ❌ Don't optimize prematurely
- ❌ Don't add unnecessary layers/middleware
- ✅ Build exactly what's documented in POV scope
- ✅ Implement only specified requirements
- ✅ Focus on demo success criteria
- ✅ Prioritize working functionality over perfect architecture

**When in doubt, ask:**
1. Is this requirement in the POV documentation?
2. Is this needed for the 5-minute demo?
3. Can I solve this with existing Kailash nodes?
4. Am I adding complexity that wasn't asked for?

---

## 🔧 Production-Grade Patterns (CRITICAL)

### Database Connection Pooling ⚠️ MANDATORY

**WRONG Pattern** (Creates/destroys pool on every call):
```python
def load_data(database_url: str):
    engine = create_engine(database_url, pool_size=5)  # ❌ New engine!
    with engine.connect() as conn:
        result = conn.execute(text("SELECT ..."))
    engine.dispose()  # ❌ Destroys the pool!
    return result
```

**CORRECT Pattern** (Global engine with singleton):
```python
# src/database.py
_engine = None

def get_db_engine(database_url: Optional[str] = None):
    """Get or create global engine (singleton pattern)"""
    global _engine
    if _engine is None:
        from config import config
        url = database_url or config.get_database_url()
        _engine = create_engine(url, pool_size=10, max_overflow=20, pool_pre_ping=True)
    return _engine

# In your functions
def load_data(database_url: str):
    engine = get_db_engine(database_url)  # ✅ Reuses global engine
    with engine.connect() as conn:
        result = conn.execute(text("SELECT ..."))
    # NO dispose() - pool stays alive! ✅
    return result
```

**Why This Matters**:
- Wrong pattern: Creates new 10-connection pool on EVERY function call, then destroys it
- Correct pattern: Creates pool once, reuses connections across all calls
- Performance: 10-100x better under load
- **This is non-negotiable for production**

### Centralized Configuration ⚠️ MANDATORY

**WRONG Pattern** (Scattered env access):
```python
# scattered across 10+ files
database_url = os.getenv('DATABASE_URL')
api_key = os.getenv('OPENAI_API_KEY')
tax_rate = os.getenv('TAX_RATE', '0.08')  # ❌ Hidden fallback!
```

**CORRECT Pattern** (Centralized with validation):
```python
# src/config.py (uses existing config_validator.py)
from config_validator import validate_required_env, validate_database_url

class ProductionConfig:
    def __init__(self):
        required_vars = ['OPENAI_API_KEY', 'TAX_RATE', 'XERO_SALES_ACCOUNT_CODE']
        validated = validate_required_env(required_vars)

        self.OPENAI_API_KEY = validated['OPENAI_API_KEY']
        self.TAX_RATE = float(validated['TAX_RATE'])  # NO FALLBACK
        self.DATABASE_URL = validate_database_url(required=True)

config = ProductionConfig()  # Validates at import time

# In your code
from config import config
api_key = config.OPENAI_API_KEY  # ✅ Validated, no fallbacks
```

**Why This Matters**:
- Fails fast at startup if config missing (not during customer transaction!)
- NO HIDDEN FALLBACKS that mask misconfiguration
- Single source of truth
- **Test your claims**: Start server without .env → should fail immediately

### Check for Duplicates BEFORE Creating ⚠️ MANDATORY

**ALWAYS run this audit before creating new functions**:
```bash
# Search for similar functions
grep -rn "def.*load_product" src/
grep -rn "def.*create_engine" src/
grep -rn "def.*validate.*config" src/

# Search for existing patterns
grep -rn "get_db_engine\|database.*pool" src/
```

**Common Duplicates to Watch For**:
1. Database connection functions
2. Configuration validation functions
3. Product/data loading functions
4. API client initialization

**Rule**: If function exists, USE IT. If broken, FIX IT. Don't create duplicate.

### Honest Testing & Verification ⚠️ MANDATORY

**WRONG Approach**:
```python
# I claimed: "Connection pooling implemented ✅"
# Reality: Never tested, had critical bug (engine.dispose())
```

**CORRECT Approach**:
```python
# 1. Create test file
tests/test_connection_pool.py

# 2. Test actual behavior
def test_singleton_pattern():
    engine1 = get_db_engine()
    engine2 = get_db_engine()
    assert engine1 is engine2  # Verify same instance

# 3. Run test BEFORE claiming completion
python tests/test_connection_pool.py

# 4. Only claim "✅ VERIFIED" if tests pass
```

**Why This Matters**:
- Untested claims lead to production bugs
- "It should work" ≠ "I verified it works"
- Tests catch bugs before customers do
- **Never claim completion without verification**

---

## 📝 Self-Review Checklist (Use Before Every Commit)

Before marking ANY task as complete, verify:

### 1. Duplication Check
- [ ] Searched for existing functions with `grep`/`Glob`
- [ ] Reused existing utilities (not reimplemented)
- [ ] If duplicates found: Enhanced existing code instead of creating new

### 2. Production Standards
- [ ] Database connections use global engine (no create/dispose per call)
- [ ] Configuration uses centralized config module (no scattered `os.getenv()`)
- [ ] No hardcoded values (credentials, URLs, rates)
- [ ] No fallbacks (fail explicitly if data missing)
- [ ] No mocks (except Tier 1 unit tests)

### 3. Testing
- [ ] Created test file for new functionality
- [ ] Ran tests and verified they pass
- [ ] Tested failure scenarios (missing config, DB down, etc.)
- [ ] Can demonstrate it works (not just "it should work")

### 4. Honest Reporting
- [ ] Task status reflects reality (not aspirational)
- [ ] Claims are verified (not assumed)
- [ ] Known issues documented (not hidden)
- [ ] Completion percentage is accurate

---

## 🚨 Anti-Patterns to AVOID

### ❌ "Fake It Till You Make It" Reporting
```
WRONG:
- "Implemented connection pooling ✅" (without testing)
- "Migrated all config ✅" (only did 1 of 8 files)
- "Production ready ✅" (has critical bugs)

RIGHT:
- "Implemented connection pooling ⚠️ NEEDS TESTING"
- "Migrated config in enhanced_api.py ⚠️ 7 more files to do"
- "Core fixes complete ⚠️ Testing required before production"
```

### ❌ Create Now, Optimize Later
```python
WRONG:
def load_data():
    engine = create_engine(...)  # "I'll optimize this later"
    # ... this becomes permanent

RIGHT:
# Use correct pattern from the start
from database import get_db_engine  # Reuse global engine
```

### ❌ Reinventing the Wheel
```python
WRONG:
# Create new validation function
def my_validate_config(): ...

RIGHT:
# Search first: grep -rn "def.*validate.*config" src/
# Found config_validator.py with validate_required_env()
from config_validator import validate_required_env  # Reuse!
```

---

## 📚 Required Reading Before Coding

1. **Check existing code**: `grep`/`Glob` for similar functions
2. **Check project docs**: See `docs/README.md` for all documentation
   - Current status: `docs/reports/production-readiness/`
   - Architecture: `docs/architecture/`
   - Setup guides: `docs/setup/`
3. **Check this file**: Patterns above
4. **When stuck**: Use specialized subagents (sdk-navigator, pattern-expert, etc.)
5. **Before claiming done**: Run tests, verify claims

**Documentation Structure**:
```
docs/
├── README.md                              # Documentation index
├── setup/                                 # Setup guides
├── architecture/                          # System architecture
├── guides/                                # User guides
└── reports/
    ├── production-readiness/             # Current status
    └── archive/                          # Historical reports
```

**Remember**:
- Production code lives for years
- Quick hacks become permanent patterns
- Other developers copy your patterns
- **Do it right the first time**
- **Keep docs organized** - Archive old reports, update indexes

---

## 📊 Codebase Audit Status (Last Updated: 2025-11-07)

### ✅ Verified Clean - No Issues Found

**1. Function Duplication**: NONE
- Searched all Python files for duplicate function names: 0 duplicates
- All function names are unique across the codebase
- Each function has single responsibility

**2. Database Engine Creation**: CLEAN
- Only 1 occurrence: `database.py:81` (global singleton) ✅ CORRECT
- No scattered `create_engine()` calls in other files
- All files use `from database import get_db_engine`

**3. Hardcoded Credentials**: NONE
- No API keys in source code (verified with pattern search)
- No passwords in code (verified)
- Xero API URLs are legitimate API endpoints (not hardcoded credentials)

**4. Mock/Simulated Data**: NONE
- All "mock" occurrences are in comments stating "NO MOCKING"
- No fake data or simulated responses in production code
- Tests use real infrastructure (PostgreSQL, OpenAI, ChromaDB)

### ⚠️ Minor Issues - Not Critical

**5. Environment Variable Access**:
- `config.py` and `config_validator.py`: ✅ APPROPRIATE (centralized config)
- 2 agent files: Use `os.getenv()` with explicit validation (acceptable pattern)
- 1 process file: Direct `os.getenv('TAX_RATE')` with validation (acceptable)
- 10 script files: Use `os.getenv()` directly (acceptable for scripts)
- **Decision**: Not a problem, patterns are appropriate for context

**6. Defensive Programming**:
- 3 occurrences of `conversation_history or []` pattern
- **Decision**: Legitimate default for optional parameters (not problematic fallback)

### 📋 Audit Verification Commands

```bash
# Check for function duplicates:
grep -r "^def " src/ --include="*.py" | sed 's/.*def \([^(]*\).*/\1/' | sort | uniq -d

# Check database engine creation:
grep -r "create_engine(" src/ --include="*.py"

# Check for hardcoded credentials:
grep -rE "sk-[a-zA-Z0-9]{20,}|password.*=.*[\"'][^\"']+[\"']" src/ --include="*.py"

# Check for mock data:
grep -riE "mock|fake|dummy" src/ --include="*.py"

# Check fallback patterns:
grep -r "or \[" src/ --include="*.py"
```

### 🎯 Audit Conclusion

**Status**: ✅ PRODUCTION-READY (Code Quality)

- Zero function duplication
- No hardcoded credentials or API keys
- No mock or simulated data
- Proper database connection pooling
- Appropriate use of environment variables
- No problematic fallback patterns

**Next Audit**: After major feature additions or when new files are created

---

## 📚 Professional Documentation Structure

TRIA AIBPO documentation follows a professional, structured organization. **ALWAYS consult these documents before coding.**

### Core Documentation (MANDATORY READING)

Located in docs/ with numbered files (01-07):

1. **Platform Overview** (docs/01-platform-overview.md) - Business overview, features, use cases, performance metrics
2. **System Architecture** (docs/02-system-architecture.md) - Multi-agent architecture, caching, RAG, integrations
3. **Technology Stack** (docs/03-technology-stack.md) - Technologies, frameworks, dependencies, infrastructure
4. **Development Standards** (docs/04-development-standards.md) - **READ THIS FIRST** - Production patterns, code quality, testing
5. **Data Models** (docs/05-data-models.md) - PostgreSQL schema, DataFlow models, API contracts
6. **Naming Conventions** (docs/06-naming-conventions.md) - File, function, variable, database naming standards
7. **Directory Structure** (docs/07-directory-structure.md) - Project organization, file locations

**Documentation Index**: docs/README.md

### When to Use Each Document

**Before Starting Development:**
1. Read Development Standards - Understand production patterns
2. Review Technology Stack - Know available tools
3. Study Directory Structure - Understand where code goes
4. Check Data Models - Understand database schema

**During Development:**
- Production patterns → Development Standards (docs/04-development-standards.md)
- Architecture questions → System Architecture (docs/02-system-architecture.md)
- Naming questions → Naming Conventions (docs/06-naming-conventions.md)
- Database questions → Data Models (docs/05-data-models.md)

**For Setup/Deployment:**
- Installation → docs/setup/ guides
- Deployment → DEPLOYMENT.md
- Operations → OPERATIONAL_RUNBOOK.md

### Documentation Enforcement

**Before Creating ANY New Code:**
1. Check Development Standards for patterns
2. Check Data Models for existing models
3. Check Directory Structure for file placement
4. Check Naming Conventions for naming

**Before Committing Code:**
1. Verify compliance with Development Standards
2. Confirm naming follows Naming Conventions
3. Ensure files are in correct locations per Directory Structure

### Quick Reference

**Most Critical Documents for Developers:**
1. Development Standards (docs/04-development-standards.md) - **MANDATORY FIRST READ**
2. Technology Stack (docs/03-technology-stack.md)
3. Directory Structure (docs/07-directory-structure.md)
4. Data Models (docs/05-data-models.md)

**Complete Documentation Index**: docs/README.md

---

## 📖 Data Dictionary & Naming Enforcement (MANDATORY)

### Data Dictionary Reference

**ALWAYS consult the Data Dictionary before:**
- Creating new database tables or columns
- Adding new API endpoints or request/response schemas
- Creating new environment variables
- Adding new ChromaDB collections

**File Location**: `docs/DATA_DICTIONARY.md`

**Contents**:
1. **Database Schema** - All table definitions with column types and descriptions
2. **API Data Contracts** - Request/response schemas for all endpoints
3. **ChromaDB Collections** - RAG collection schemas and purposes
4. **Environment Variables** - Complete catalog of required/optional variables
5. **Intent Types** - Classification intents and their meanings
6. **File Path Standards** - Standard locations for data files
7. **Naming Standards Reference** - Quick lookup for naming patterns

### Pre-Creation Checklist (MANDATORY)

Before creating ANY new data structure, verify against Data Dictionary:

```
[ ] Check DATA_DICTIONARY.md for existing similar definition
[ ] Verify column/field naming follows conventions (snake_case, prefixes)
[ ] Confirm data types match existing patterns
[ ] Check for existing environment variables before adding new ones
[ ] Verify API endpoint follows existing patterns (/api/v1/resource)
[ ] Update DATA_DICTIONARY.md if adding new definitions
```

### Naming Convention Enforcement

**Files** (see docs/06-naming-conventions.md):
```python
# Python modules: snake_case
enhanced_api.py          # ✅ Correct
EnhancedApi.py           # ❌ Wrong

# Test files: test_{component}.py
test_chatbot.py          # ✅ Correct
chatbot_test.py          # ❌ Wrong
```

**Database** (see DATA_DICTIONARY.md):
```sql
-- Tables: snake_case, singular preferred
CREATE TABLE product (...)      -- ✅ Correct
CREATE TABLE Products (...)     -- ❌ Wrong (plural, PascalCase)

-- Columns: snake_case with standard prefixes
is_active BOOLEAN              -- ✅ Correct (is_ for booleans)
active BOOLEAN                 -- ❌ Wrong (no prefix)
created_at TIMESTAMP           -- ✅ Correct (_at for timestamps)
creation_date TIMESTAMP        -- ❌ Wrong (inconsistent suffix)
```

**Environment Variables**:
```bash
# SCREAMING_SNAKE_CASE
DATABASE_URL=...               # ✅ Correct
databaseUrl=...                # ❌ Wrong
```

**API Endpoints**:
```
POST /api/chatbot             # ✅ Correct
POST /chatbot                  # ❌ Wrong (no /api prefix)
POST /api/process_order        # ❌ Wrong (use kebab-case: /process-order)
```

### Cross-Reference Requirements

When creating new code, cross-reference these documents:

| Creating | Check These Documents |
|----------|----------------------|
| New table | DATA_DICTIONARY.md, docs/05-data-models.md |
| New API endpoint | DATA_DICTIONARY.md (API section) |
| New environment var | DATA_DICTIONARY.md (Env section), src/config.py |
| New file | docs/06-naming-conventions.md, docs/07-directory-structure.md |
| New function | docs/06-naming-conventions.md (function naming) |
| New ChromaDB collection | DATA_DICTIONARY.md (ChromaDB section) |

### Violation Examples

**DO NOT DO THIS**:
```python
# Creating redundant environment variable
OPENAI_KEY = os.getenv('OPENAI_KEY')  # ❌ Already exists as OPENAI_API_KEY

# Creating table without checking Data Dictionary
CREATE TABLE user_orders (...)         # ❌ Check if 'orders' table exists

# Creating API endpoint without prefix
@app.post("/create-order")             # ❌ Should be /api/create-order
```

**DO THIS INSTEAD**:
```python
# Check Data Dictionary first
from config import config
api_key = config.OPENAI_API_KEY        # ✅ Use existing

# Check existing tables in DATA_DICTIONARY.md
# Found: 'orders' table already exists
# Use existing table with proper relationships

# Follow API naming convention
@app.post("/api/create-order")         # ✅ Correct prefix
```

---

## 🔄 Existing Scripts Reference (DO NOT DUPLICATE)

Before creating a new script, check if it already exists:

### Data Loading Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/load_products_from_excel.py` | Load product catalog | `python scripts/load_products_from_excel.py` |
| `scripts/load_outlets_from_excel.py` | Load outlet data | `python scripts/load_outlets_from_excel.py` |
| `scripts/generate_product_embeddings.py` | Generate OpenAI embeddings | `python scripts/generate_product_embeddings.py` |
| `scripts/build_knowledge_base.py` | Build RAG knowledge base | `python scripts/build_knowledge_base.py` |

### Testing Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/smoke_test.py` | Basic functionality | `python scripts/smoke_test.py` |
| `scripts/test_chromadb_connection.py` | Test ChromaDB | `python scripts/test_chromadb_connection.py` |
| `scripts/test_rag_retrieval.py` | Test RAG search | `python scripts/test_rag_retrieval.py` |

### Validation Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/validate_production_config.py` | Validate config | `python scripts/validate_production_config.py` |
| `scripts/verify_production_readiness.py` | Check readiness | `python scripts/verify_production_readiness.py` |

### Load Testing Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/load_test_1_sustained.py` | 10 users, 1 hour | Staging only |
| `scripts/load_test_2_burst.py` | 50 users, 5 min | Staging only |
| `scripts/run_all_load_tests.py` | Run all load tests | Staging only |

**Rule**: If a script exists for your task, USE IT. Don't create a duplicate.

---

