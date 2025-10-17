# Security Guidelines

## Critical Security Requirements

### 1. Environment Variables

**NEVER commit actual credentials to git:**
- `.env` - Local development (EXCLUDED from git)
- `.env.docker` - Docker deployment (EXCLUDED from git)
- `.env.example` - Template only (safe to commit)

**Required for production:**
```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
OPENAI_API_KEY=sk-...
XERO_CLIENT_ID=...
XERO_CLIENT_SECRET=...
XERO_REFRESH_TOKEN=...
XERO_TENANT_ID=...
SECRET_KEY=... (generate with: openssl rand -hex 32)
```

### 2. Secrets Management

**Development:**
1. Copy `.env.example` to `.env`
2. Fill in actual values
3. NEVER commit .env to git

**Docker Deployment:**
1. Copy `.env.docker.example` to `.env.docker`
2. Generate strong passwords: `openssl rand -base64 32`
3. Start with: `docker-compose --env-file .env.docker up`

**Production Deployment:**
- Use secrets management (AWS Secrets Manager, Azure Key Vault, etc.)
- Never use hardcoded credentials
- Rotate secrets regularly

### 3. Database Security

**PostgreSQL:**
- Use strong, unique passwords (min 32 characters)
- Limit network access (use firewall rules)
- Enable SSL/TLS for connections
- Regular backups

**Configuration:**
```bash
# Generate secure password
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Use in DATABASE_URL
DATABASE_URL=postgresql://user:${POSTGRES_PASSWORD}@host:port/dbname
```

### 4. API Security

**OpenAI:**
- Use project-specific API keys
- Set spending limits
- Monitor usage
- Rotate keys if exposed

**Xero:**
- Use OAuth 2.0 refresh tokens
- Never share client secrets
- Implement rate limiting
- Monitor API usage

### 5. Configuration Validation

**Before deployment, run:**
```bash
python scripts/validate_production_config.py
```

This checks:
- All required environment variables
- No placeholder values
- File paths exist
- Database URL format
- API key formats

### 6. Security Checklist

**Before first deployment:**
- [ ] `.env` not tracked in git
- [ ] All API keys are production keys (not test/demo)
- [ ] Database password is strong and unique
- [ ] SECRET_KEY generated (openssl rand -hex 32)
- [ ] CORS origins configured correctly
- [ ] SSL/TLS enabled for database connections
- [ ] Firewall rules configured
- [ ] Backup strategy in place

**Regular maintenance:**
- [ ] Rotate API keys quarterly
- [ ] Update dependencies monthly
- [ ] Review access logs weekly
- [ ] Test backup restoration quarterly

### 7. Incident Response

**If credentials are exposed:**
1. Immediately revoke/regenerate all exposed keys
2. Update .env files
3. Purge git history (BFG Repo-Cleaner)
4. Force push to all remotes
5. Notify team members
6. Monitor for unauthorized access
7. Document incident

### 8. Security Contacts

For security issues, contact:
- Project Lead: [contact info]
- Security Team: [contact info]

**Do NOT open public GitHub issues for security vulnerabilities.**

---

Generated: 2025-10-17
Project: TRIA AI-BPO Order Processing System
