# Directory Structure

**TRIA AIBPO Project Organization**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## Project Layout

```
tria/
├── src/                        # Source code
│   ├── agents/                 # AI agents
│   ├── cache/                  # 4-tier caching
│   ├── integrations/           # External APIs
│   ├── memory/                 # Conversation memory
│   ├── models/                 # Data models
│   ├── rag/                    # RAG knowledge base
│   ├── config.py               # Centralized config
│   ├── database.py             # DB connection pooling
│   └── enhanced_api.py         # Main FastAPI server
│
├── tests/                      # Test suite
│   ├── tier1_unit/             # Unit tests
│   ├── tier2_integration/      # Integration tests
│   └── tier3_e2e/              # End-to-end tests
│
├── docs/                       # Documentation
│   ├── 01-platform-overview.md
│   ├── 02-system-architecture.md
│   ├── 03-technology-stack.md
│   ├── 04-development-standards.md
│   ├── 05-data-models.md
│   ├── 06-naming-conventions.md
│   ├── 07-directory-structure.md
│   ├── setup/                  # Setup guides
│   ├── architecture/           # Architecture docs
│   ├── guides/                 # User guides
│   └── reports/                # Status reports
│
├── data/                       # Data files
│   ├── inventory/              # Product catalogs
│   ├── templates/              # Excel templates
│   ├── generated/              # Generated files
│   └── chromadb/               # Vector store
│
├── scripts/                    # Utility scripts
│   ├── deploy_agent.py         # Deployment
│   └── test_*.py               # Test scripts
│
├── docker-compose.yml          # Docker orchestration
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── CLAUDE.md                   # AI coding guidelines
└── README.md                   # Project overview
```

---

## Key Directories

### src/
All production source code. Entry point: `src/enhanced_api.py`

### docs/
All documentation. Numbered core docs (01-07) in root.

### tests/
3-tier testing strategy (unit, integration, e2e).

### data/
Data files only - no source code.

### scripts/
Utilities and automation - not production code.

---

## Organization Rules

1. Production code → `src/`
2. Tests → `tests/` (mirror `src/` structure)
3. Documentation → `docs/`
4. Data files → `data/`
5. Utilities → `scripts/`

---

## See Also

- [Development Standards](04-development-standards.md)
- [Naming Conventions](06-naming-conventions.md)
- [src/README.md](../src/README.md)

---

**Last Updated**: 2025-11-21
