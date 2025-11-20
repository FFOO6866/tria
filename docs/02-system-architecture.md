# System Architecture

**TRIA AIBPO Technical Architecture**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## Architecture Overview

TRIA AIBPO follows a multi-layered architecture with:
- Multi-agent AI system (5 specialized agents)
- 4-tier caching system (12.2x performance improvement)
- RAG knowledge base integration
- Real-time WebSocket communication
- Production-grade error handling and monitoring

---

## Component Layers

### 1. API Layer
**File**: src/enhanced_api.py
- FastAPI REST endpoints
- WebSocket real-time broadcasting
- Request validation
- Health monitoring

### 2. Multi-Agent System
**5 Specialized AI Agents:**
- Customer Service Agent (primary router)
- Operations Orchestrator (A2A coordination)
- Inventory Agent (product catalog)
- Delivery Agent (DO generation)
- Finance Agent (Xero integration)

### 3. 4-Tier Caching
**L1**: Exact Match (Redis) - 20-30% hit rate
**L2**: Semantic (ChromaDB) - 15-25% hit rate  
**L3**: Product (Redis) - 90%+ hit rate
**L4**: RAG (Redis) - 40-50% hit rate

**Total Performance**: 12.2x improvement (26.6s to 2.2s)

### 4. RAG System
**Vector Store**: ChromaDB
**Embeddings**: OpenAI text-embedding-3-large
**Knowledge Base**: 4 policy documents embedded

### 5. Data Layer
**PostgreSQL**: Orders, products, outlets, conversations
**Redis**: Sessions, caching
**ChromaDB**: Vector embeddings for RAG and semantic cache

---

## Integration Points

### OpenAI
- GPT-4 for agent reasoning
- text-embedding-3-large for embeddings

### Xero API
- Real-time invoice posting
- OAuth2 authentication

### Excel
- DO generation with openpyxl
- Template-based formatting

---

## Security

- Centralized configuration (no hardcoded credentials)
- Input validation at all layers
- Rate limiting (100 req/min)
- Circuit breakers for external APIs
- PII scrubbing (PDPA compliance)

---

## Deployment

**Development**: Docker Compose (local services)
**Production**: AWS EC2 / DigitalOcean with managed databases

See [DEPLOYMENT.md](../DEPLOYMENT.md) for details.

---

## See Also

- [Technology Stack](03-technology-stack.md)
- [Development Standards](04-development-standards.md)
- [Data Models](05-data-models.md)

---

**Last Updated**: 2025-11-21
