# TRIA AIBPO Documentation

**AI-Powered Business Process Outsourcing Platform**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## Quick Start

New to TRIA? Start here:

1. [Platform Overview](01-platform-overview.md) - What is TRIA and what does it do?
2. [Technology Stack](03-technology-stack.md) - Technologies and dependencies
3. [Development Standards](04-development-standards.md) - Coding standards and best practices
4. [Directory Structure](07-directory-structure.md) - Project organization

---

## Core Documentation

### 1. [Platform Overview](01-platform-overview.md)
**Purpose and capabilities of the TRIA AIBPO platform**
- Business overview
- Key features and capabilities
- Use cases and scenarios
- Performance metrics

### 2. [System Architecture](02-system-architecture.md)
**Technical architecture and design decisions**
- Multi-agent architecture
- Component interactions
- Integration points
- Caching strategy (4-tier system)
- RAG implementation
- Security architecture

### 3. [Technology Stack](03-technology-stack.md)
**Technologies, frameworks, and dependencies**
- Runtime environment
- Core frameworks and libraries
- Database systems
- External integrations
- Development tools

### 4. [Development Standards](04-development-standards.md)
**Coding standards and best practices**
- Production-grade patterns (CRITICAL)
- Code quality standards
- Testing requirements
- Security standards
- Error handling
- Logging and monitoring

### 5. [Data Models](05-data-models.md)
**Database schema and data structures**
- PostgreSQL models
- DataFlow model definitions
- Conversation models
- API data contracts

### 6. [Naming Conventions](06-naming-conventions.md)
**File, function, and variable naming standards**
- File naming conventions
- Function and class naming
- Variable naming patterns
- Database naming
- API endpoint naming

### 7. [Directory Structure](07-directory-structure.md)
**Project organization and file structure**
- Source code organization
- Documentation structure
- Test organization
- Configuration management

### 8. [Data Dictionary](DATA_DICTIONARY.md)
**Single source of truth for all data definitions (NEW)**
- Database schema definitions
- API request/response contracts
- Environment variable catalog
- ChromaDB collection schemas
- Intent classification types
- File path standards
- Naming standards quick reference

---

## Production Readiness

### Current Status
- [Production Readiness Plan](../PRODUCTION_READINESS_PLAN.md) - Active tasks and fixes

### Historical Reports
Located in [reports/production-readiness/](reports/production-readiness/):
- Assessment reports
- Codebase audits
- Performance analyses

---

## Integration Guides

### MCP (Model Context Protocol)
- [MCP Setup Guide](MCP_SETUP.md) - Claude Desktop integration overview
- [Xero OAuth2 Setup](setup/XERO_OAUTH2_SETUP.md) - Detailed OAuth2 configuration
- [MCP Troubleshooting](setup/MCP_TROUBLESHOOTING.md) - Common issues and solutions
- [MCP Usage Examples](guides/MCP_USAGE_EXAMPLES.md) - Real-world usage scenarios

---

## Setup Guides

### Installation & Configuration
Located in [setup/](setup/):

- [UV Setup Guide](setup/UV_SETUP.md) - Python environment with UV package manager
- [Docker Deployment](setup/DOCKER_DEPLOYMENT.md) - Containerized deployment
- [Database Configuration](setup/DATABASE_CONFIGURATION.md) - PostgreSQL setup
- [Production Secrets Setup](setup/PRODUCTION_SECRETS_SETUP.md) - Environment variables
- [GitHub Setup Guide](setup/GITHUB_SETUP_GUIDE.md) - Repository configuration
- [AWS Deployment Guide](setup/aws-deployment-guide.md) - Cloud deployment

---

## Quick Reference

### Most Important Documents

**For Developers:**
1. [Development Standards](04-development-standards.md) - READ THIS FIRST
2. [Data Dictionary](DATA_DICTIONARY.md) - Data definitions and naming
3. [Technology Stack](03-technology-stack.md)
4. [Directory Structure](07-directory-structure.md)
5. [Data Models](05-data-models.md)

**For Deployment:**
1. [DEPLOYMENT.md](../DEPLOYMENT.md)
2. [Production Secrets Setup](setup/PRODUCTION_SECRETS_SETUP.md)
3. [AWS Deployment Guide](setup/aws-deployment-guide.md)

**For Architecture:**
1. [System Architecture](02-system-architecture.md)
2. [Chatbot Architecture](architecture/CHATBOT_ARCHITECTURE_PROPOSAL.md)

---

**Maintained by**: Development Team
**Last Review**: 2025-11-21
