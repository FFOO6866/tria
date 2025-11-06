# Tria AIBPO Documentation

Welcome to the Tria AI-BPO documentation. This directory contains all project documentation organized by category.

---

## 📚 Documentation Structure

### **[setup/](setup/)** - Installation & Configuration
Complete guides for setting up the development environment and production deployment:

- **[uv-setup.md](setup/uv-setup.md)** - Python environment setup with UV package manager
- **[docker-deployment.md](setup/docker-deployment.md)** - Docker containerization and deployment
- **[database-configuration.md](setup/database-configuration.md)** - PostgreSQL database setup
- **[production-secrets-setup.md](setup/production-secrets-setup.md)** - Environment variables and secrets
- **[github-setup-guide.md](setup/github-setup-guide.md)** - GitHub repository configuration

### **[architecture/](architecture/)** - System Architecture
Technical architecture documentation and design decisions:

- **[chatbot-architecture-proposal.md](architecture/CHATBOT_ARCHITECTURE_PROPOSAL.md)** - Chatbot system design
- **[conversation-memory-architecture.md](architecture/conversation_memory_architecture.md)** - Memory system design
- **[conversation-memory-system.md](architecture/conversation_memory_system.md)** - Memory implementation details
- **[existing-a2a-framework-analysis.md](architecture/EXISTING_A2A_FRAMEWORK_ANALYSIS.md)** - Agent-to-agent framework analysis
- **[pdpa-compliance-guide.md](architecture/PDPA_COMPLIANCE_GUIDE.md)** - Privacy and data protection compliance

### **[guides/](guides/)** - User & Developer Guides
Quick-start guides and how-to documentation:

- **[conversation-memory-quick-reference.md](guides/conversation_memory_quick_reference.md)** - Memory system quick reference
- **[intent-classifier-quickstart.md](guides/INTENT_CLASSIFIER_QUICKSTART.md)** - Intent classification guide

### **[reports/](reports/)** - Status Reports & Audits

#### **[production-readiness/](reports/production-readiness/)** - Current Production Status
- **[FINAL_PROGRESS_REPORT.md](reports/production-readiness/FINAL_PROGRESS_REPORT.md)** - Latest honest progress assessment
- **[CODEBASE_AUDIT.md](reports/production-readiness/CODEBASE_AUDIT.md)** - Duplication and quality audit
- **[PRODUCTION_HARDENING_FIXES.md](reports/production-readiness/PRODUCTION_HARDENING_FIXES.md)** - Production fixes summary
- **[CLEANUP_PLAN.md](reports/production-readiness/CLEANUP_PLAN.md)** - Directory organization plan

#### **[archive/](reports/archive/)** - Historical Reports
Archived status reports and implementation summaries organized by date:
- `2024-10-17/` - Initial production audits
- `2024-10-18/` - Feature implementation reports
- `2024-10-23/` - Status updates and fixes

---

## 🔍 Quick Navigation

### Getting Started
1. [Project README](../README.md) - Project overview
2. [Setup Guide](setup/uv-setup.md) - Start here for installation
3. [Docker Deployment](setup/docker-deployment.md) - For containerized deployment

### Development
1. [CLAUDE.md](../CLAUDE.md) - Development guidelines and patterns
2. [Architecture Docs](architecture/) - System design documentation
3. [Source Code](../src/README.md) - Source code structure

### Production Deployment
1. [Production Secrets Setup](setup/production-secrets-setup.md)
2. [Database Configuration](setup/database-configuration.md)
3. [Final Progress Report](reports/production-readiness/FINAL_PROGRESS_REPORT.md)

---

## 📝 Documentation Standards

### File Naming
- Use lowercase with hyphens: `my-document.md`
- Be descriptive: `chatbot-architecture.md` not `arch.md`
- Date archives: `2024-10-18/`

### Organization
- **Current** docs in main categories (setup/, architecture/, guides/)
- **Historical** reports in archive/ by date
- **Active** reports in reports/production-readiness/

### Maintenance
- Archive outdated reports regularly
- Update this index when adding new documentation
- Keep CLAUDE.md updated with doc structure

---

## 🚀 Contributing

When adding documentation:
1. Place in appropriate category directory
2. Update this README with link
3. Follow naming conventions
4. Archive superseded documents

---

**Last Updated**: 2025-11-07
**Maintainer**: Development Team
