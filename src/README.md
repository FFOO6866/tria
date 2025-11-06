# Tria AIBPO Source Code

This directory contains all source code for the Tria AI-BPO order processing system.

---

## 📁 Directory Structure

```
src/
├── agents/                          # AI Agent implementations
│   ├── enhanced_customer_service_agent.py  # Customer service with RAG
│   └── intent_classifier.py                # Intent classification
│
├── memory/                          # Conversation memory system
│   ├── context_builder.py                  # Context construction
│   └── session_manager.py                  # Session management
│
├── models/                          # Data models
│   ├── conversation_models.py              # Conversation/message models
│   └── dataflow_models.py                  # DataFlow database models
│
├── privacy/                         # Privacy & compliance
│   ├── data_retention.py                   # Data retention policies
│   └── pii_scrubber.py                     # PII scrubbing (PDPA)
│
├── prompts/                         # System prompts
│   └── system_prompts.py                   # Prompt templates
│
├── rag/                             # RAG (Retrieval Augmented Generation)
│   ├── chroma_client.py                    # ChromaDB client
│   ├── document_processor.py               # Document processing
│   ├── knowledge_base.py                   # Knowledge base wrapper
│   ├── knowledge_indexer.py                # Embedding indexing
│   └── retrieval.py                        # Semantic search
│
├── config.py                        # Centralized configuration
├── config_validator.py              # Configuration validation
├── database.py                      # Database connection pooling ⚠️ CRITICAL
├── enhanced_api.py                  # Main FastAPI server
├── process_order_with_catalog.py    # Order processing logic
└── semantic_search.py               # Product semantic search
```

---

## 🔑 Core Modules

### Entry Points

**`enhanced_api.py`** - Main API Server
- FastAPI application
- Multi-agent order processing
- Chatbot endpoints with RAG
- Real-time agent timeline visualization

**Start Server**:
```bash
python src/enhanced_api.py
# Runs on http://localhost:8001
# API Docs: http://localhost:8001/docs
```

### Configuration Management ⚠️ CRITICAL

**`config.py`** - Centralized Configuration
- Single source of truth for all config
- Validates at startup (NO FALLBACKS)
- Uses existing `config_validator.py` functions

**`config_validator.py`** - Validation Utilities
- Environment variable validation
- Database URL format checking
- API key validation

**`database.py`** - Database Connection Pooling ⚠️ MANDATORY
- Global SQLAlchemy engine (singleton pattern)
- Connection pooling (10 base, 20 overflow)
- Used by ALL database operations

**Critical Pattern**:
```python
from database import get_db_engine

engine = get_db_engine()  # Global engine, reused
with engine.connect() as conn:
    result = conn.execute(text("SELECT ..."))
# NO engine.dispose() - pool stays alive!
```

### Order Processing

**`process_order_with_catalog.py`** - Catalog-Based Order Processing
- Loads product catalog from database (NO HARDCODING)
- GPT-4 order parsing with catalog context
- Dynamic pricing from database

**`semantic_search.py`** - Product Semantic Search
- OpenAI embeddings for products
- Cosine similarity matching
- Handles typos and variations

### AI Agents

**`agents/enhanced_customer_service_agent.py`** - Customer Service Agent
- RAG-powered responses
- Escalation handling
- Multi-turn conversation support

**`agents/intent_classifier.py`** - Intent Classification
- 7 intent types (greeting, order, status, inquiry, policy, complaint, general)
- GPT-4 powered classification
- Conversation context aware

### Memory & Privacy

**`memory/session_manager.py`** - Session Management
- Persistent conversation sessions
- Session lifecycle management
- Integration with DataFlow

**`memory/context_builder.py`** - Context Construction
- Conversation history retrieval
- Context window management
- User profile integration

**`privacy/pii_scrubber.py`** - PII Scrubbing (PDPA Compliance)
- Redacts sensitive data (phone, email, NRIC, addresses)
- Singapore-specific patterns
- Preserves conversation utility

### RAG System

**`rag/knowledge_base.py`** - Knowledge Base Wrapper
- High-level RAG interface
- Multi-collection search
- Document indexing

**`rag/chroma_client.py`** - ChromaDB Client
- Vector store management
- Collection management
- Health checking

---

## 🎯 Key Design Patterns

### 1. Global Database Engine (CRITICAL)
```python
# ✅ CORRECT: Use global engine
from database import get_db_engine

def load_data():
    engine = get_db_engine()  # Reuses global engine
    with engine.connect() as conn:
        ...
    # NO dispose() - pool stays alive!

# ❌ WRONG: Create new engine
def load_data():
    engine = create_engine(...)  # New pool!
    ...
    engine.dispose()  # Destroys pool!
```

### 2. Centralized Configuration
```python
# ✅ CORRECT: Use centralized config
from config import config

api_key = config.OPENAI_API_KEY
db_url = config.get_database_url()

# ❌ WRONG: Scattered os.getenv()
api_key = os.getenv('OPENAI_API_KEY')
```

### 3. No Fallbacks
```python
# ✅ CORRECT: Fail explicitly
if not product_id:
    raise HTTPException(404, "Product not found")

# ❌ WRONG: Hidden fallback
product_id = product_id or "default_product"
```

---

## 🚨 Critical Rules

1. **Database Connections**
   - ALWAYS use `from database import get_db_engine`
   - NEVER create new engines in functions
   - NEVER call `engine.dispose()` except in tests

2. **Configuration**
   - ALWAYS use `from config import config`
   - NEVER use `os.getenv()` directly
   - NO FALLBACK VALUES

3. **No Hardcoding**
   - Credentials → Environment variables
   - Pricing → Database catalog
   - Business rules → Database tables

4. **No Mocking** (Production Code)
   - Use real APIs (OpenAI, Xero)
   - Use real databases (PostgreSQL)
   - Mock only in Tier 1 unit tests

---

## 📚 Documentation

- **Architecture**: See [docs/architecture/](../docs/architecture/)
- **Setup**: See [docs/setup/](../docs/setup/)
- **Development Guidelines**: See [CLAUDE.md](../CLAUDE.md)
- **Production Status**: See [docs/reports/production-readiness/](../docs/reports/production-readiness/)

---

## 🔧 Development

### Running Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your values

# Run API server
python src/enhanced_api.py
```

### Testing
```bash
# Run connection pool test
python tests/test_connection_pool.py

# Run all tests
pytest tests/
```

---

**Last Updated**: 2025-11-07
**See Also**: [CLAUDE.md](../CLAUDE.md) for production patterns
