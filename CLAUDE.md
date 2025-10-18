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
   - Use `Glob` tool to search for similar functionality before creating new files
   - Use `Grep` tool to find existing functions/classes that can be reused
   - Extend existing workflows/agents instead of creating new ones
   - Review `sdk-users/` documentation for built-in nodes before custom implementations

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
