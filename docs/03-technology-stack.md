# Technology Stack

**TRIA AIBPO Technical Dependencies**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## Core Technologies

### Runtime
- Python 3.10+
- FastAPI + Uvicorn (ASGI server)
- Pydantic (data validation)

### AI/ML
- **OpenAI GPT-4** - Agent reasoning and response generation
- **OpenAI text-embedding-3-large** - Semantic embeddings (3072-d)
- **DSPy** - Automatic prompt optimization framework
- **Sentence Transformers** - Embedding models

### Databases
- **PostgreSQL 16** - Structured data (orders, products, outlets, conversations)
- **Redis 7** - L1/L3/L4 caching + session management
- **ChromaDB** - Vector store for RAG + L2 semantic cache

### Integrations
- **xero-python** - Official Xero SDK for accounting/invoicing
- **openpyxl** - Excel file generation (DO templates)
- **pandas** - Data manipulation
- **python-docx** - Document processing

### Production Infrastructure
- **tenacity** - Retry logic with exponential backoff
- **pybreaker** - Circuit breakers for external services
- **sentry-sdk[fastapi]** - Error tracking and monitoring
- **ratelimit** - API rate limiting
- **python-json-logger** - Structured logging

### Configuration
- **python-dotenv** - Environment variable management

### Development
- **pytest** - Testing framework
- **black** - Code formatting
- **scikit-learn** - Metrics and evaluation

### Deployment
- **Docker** - Containerization
- **docker-compose** - Multi-container orchestration
- **Nginx** - Reverse proxy and SSL termination

---

## Infrastructure Options

### Development
- Local PostgreSQL (Docker container)
- Local Redis (Docker container)
- Local ChromaDB (Docker volume)

### Production
- **Compute**: AWS EC2 (t3.small/medium) or DigitalOcean Droplet
- **Database**: AWS RDS PostgreSQL or DigitalOcean Managed Database
- **Cache**: AWS ElastiCache Redis or DigitalOcean Managed Redis
- **Storage**: EBS or Block Storage for ChromaDB persistence

---

## Installation

```bash
# Install all dependencies
pip install -r requirements.txt
```

See [requirements.txt](../requirements.txt) for exact versions.

---

## Version Requirements

- Python 3.10+ (required)
- PostgreSQL 14+ (recommended)
- Redis 6+ (required)
- ChromaDB 0.4+ (required)
- OpenAI API access

---

## See Also

- [System Architecture](02-system-architecture.md) - How components interact
- [Development Standards](04-development-standards.md) - Usage patterns
- [Setup Guides](setup/) - Installation instructions

---

**Last Updated**: 2025-11-21
