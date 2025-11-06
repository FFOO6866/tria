# Directory Cleanup Plan

**Current Status**: 40+ markdown files in root directory (MESSY)
**Target**: Clean, organized structure with proper documentation hierarchy

---

## Problems Identified

### 1. Root Directory Clutter (40+ files)
```
ROOT HAS:
- 35+ status/implementation reports (should be archived)
- Multiple duplicate audits (PRODUCTION_AUDIT, HONEST_PRODUCTION_AUDIT, FINAL_PRODUCTION_AUDIT)
- Temporary files (_ul, _ul-FFOO, backend.log)
- Multiple .env files not organized
```

### 2. Multiple Documentation Directories
```
./doc/          (2 files)
./docs/         (4 files)
./examples/     (1 file)
```

### 3. Duplicate/Superseded Documentation
```
DUPLICATES:
- PRODUCTION_AUDIT_COMPLETE.md
- FINAL_PRODUCTION_AUDIT.md
- HONEST_PRODUCTION_AUDIT.md
- PRODUCTION_FIXES_COMPLETE.md
- PRODUCTION_HARDENING_FIXES.md

SUPERSEDED BY:
- FINAL_PROGRESS_REPORT.md (latest, most accurate)
- CODEBASE_AUDIT.md (latest audit)
```

---

## Target Structure

```
tria/
├── README.md                          # Main project readme
├── CLAUDE.md                          # Development guidelines (KEEP)
├── SECURITY.md                        # Security policy (KEEP)
├── LICENSE
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
│
├── .env.example                       # Example configuration
├── .env.docker.example               # Docker example
├── .env.production.example           # Production example
│
├── docs/                             # ALL DOCUMENTATION
│   ├── README.md                     # Documentation index
│   ├── setup/                        # Setup guides
│   │   ├── uv-setup.md
│   │   ├── docker-deployment.md
│   │   ├── database-configuration.md
│   │   ├── production-secrets-setup.md
│   │   └── github-setup-guide.md
│   ├── architecture/                 # Architecture documentation
│   │   ├── chatbot-architecture.md
│   │   ├── conversation-memory-architecture.md
│   │   ├── conversation-memory-system.md
│   │   └── existing-a2a-framework-analysis.md
│   ├── guides/                       # User guides
│   │   ├── conversation-memory-quick-reference.md
│   │   ├── pdpa-compliance-guide.md
│   │   └── intent-classifier-quickstart.md
│   ├── reports/                      # Current reports
│   │   ├── production-readiness/
│   │   │   ├── FINAL_PROGRESS_REPORT.md      # CURRENT
│   │   │   ├── CODEBASE_AUDIT.md             # CURRENT
│   │   │   └── PRODUCTION_HARDENING_FIXES.md # CURRENT
│   │   └── archive/                  # Historical reports (archived)
│   │       ├── 2024-10-17/
│   │       ├── 2024-10-18/
│   │       └── 2024-10-23/
│   └── adr/                          # Architecture Decision Records
│
├── src/                              # Source code
│   ├── README.md                     # Source code overview
│   ├── agents/
│   ├── memory/
│   ├── models/
│   ├── privacy/
│   ├── prompts/
│   ├── rag/
│   ├── config.py
│   ├── config_validator.py
│   ├── database.py
│   ├── enhanced_api.py
│   ├── process_order_with_catalog.py
│   └── semantic_search.py
│
├── tests/                            # Test files
│   ├── README.md
│   ├── tier1_unit/
│   ├── tier2_integration/
│   ├── tier3_e2e/
│   ├── fixtures/
│   └── test_connection_pool.py
│
├── frontend/                         # Frontend application
├── data/                             # Data files
├── scripts/                          # Utility scripts
└── migrations/                       # Database migrations
```

---

## Actions Required

### Phase 1: Create Proper Directory Structure
1. Create `docs/setup/`
2. Create `docs/architecture/`
3. Create `docs/guides/`
4. Create `docs/reports/production-readiness/`
5. Create `docs/reports/archive/`

### Phase 2: Move Current Reports (Keep Latest)
**KEEP IN docs/reports/production-readiness/**:
- FINAL_PROGRESS_REPORT.md
- CODEBASE_AUDIT.md
- PRODUCTION_HARDENING_FIXES.md

**ARCHIVE to docs/reports/archive/**:
- All other status/implementation reports (30+ files)

### Phase 3: Organize Documentation by Type
**Setup Guides → docs/setup/**:
- UV_SETUP.md
- DOCKER_DEPLOYMENT.md
- DATABASE_CONFIGURATION.md
- PRODUCTION_SECRETS_SETUP.md
- GITHUB_SETUP_GUIDE.md

**Architecture Docs → docs/architecture/**:
- doc/CHATBOT_ARCHITECTURE_PROPOSAL.md
- docs/conversation_memory_architecture.md
- docs/conversation_memory_system.md
- doc/EXISTING_A2A_FRAMEWORK_ANALYSIS.md

**User Guides → docs/guides/**:
- docs/conversation_memory_quick_reference.md
- docs/PDPA_COMPLIANCE_GUIDE.md
- examples/INTENT_CLASSIFIER_QUICKSTART.md

### Phase 4: Clean Up Root
**KEEP IN ROOT**:
- README.md
- CLAUDE.md
- SECURITY.md
- LICENSE
- .gitignore
- .env.example (3 files)
- Build files (requirements.txt, pyproject.toml, docker-compose.yml, Dockerfile)

**DELETE (Temporary Files)**:
- _ul
- _ul-FFOO
- backend.log

### Phase 5: Delete Obsolete Directories
- Remove `doc/` (merge into `docs/`)
- Remove `examples/` (merge into `docs/guides/`)
- Remove old `docs/` (restructure)

---

## Harmonization Strategy

### Consolidate Duplicate Reports

**Production Readiness** (Keep FINAL_PROGRESS_REPORT.md, archive others):
- ❌ PRODUCTION_AUDIT_COMPLETE.md
- ❌ FINAL_PRODUCTION_AUDIT.md
- ❌ HONEST_PRODUCTION_AUDIT.md
- ❌ PRODUCTION_READY.md
- ❌ FINAL_CERTIFICATION.md
- ✅ FINAL_PROGRESS_REPORT.md (CURRENT)

**Implementation Reports** (Archive all to dated folders):
- CHATBOT_*.md (5 files) → docs/reports/archive/2024-10-18/
- CONVERSATION_MEMORY_*.md (2 files) → docs/reports/archive/2024-10-18/
- INTENT_CLASSIFICATION_*.md (2 files) → docs/reports/archive/2024-10-23/
- SESSION_*.md (2 files) → docs/reports/archive/2024-10-23/
- *_STATUS.md (5 files) → docs/reports/archive/2024-10-23/

### Create Index Documentation

**docs/README.md** - Master index pointing to all documentation
**src/README.md** - Source code structure overview
**tests/README.md** - Testing strategy overview

---

## Verification Checklist

After cleanup:
- [ ] Root has <10 files (only essentials)
- [ ] All docs in `docs/` with clear hierarchy
- [ ] No duplicate documentation
- [ ] All temporary files removed
- [ ] Documentation cross-references updated
- [ ] CLAUDE.md updated with new doc locations
- [ ] README.md updated with new structure

---

**Status**: Plan Ready
**Next**: Execute cleanup
