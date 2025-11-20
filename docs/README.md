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
2. [Technology Stack](03-technology-stack.md)
3. [Directory Structure](07-directory-structure.md)
4. [Data Models](05-data-models.md)

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
