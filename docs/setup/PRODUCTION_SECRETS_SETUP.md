# Production Secrets Setup Guide

**Date:** 2025-10-18
**For:** Tria AIBPO Production Deployment
**Security Level:** CRITICAL

---

## 📁 FILES CREATED

| File | Purpose | Commit to Git? |
|------|---------|----------------|
| `.env.production` | **ACTUAL SECRETS** | ❌ NO - Contains real secrets |
| `.env.production.example` | Template with placeholders | ✅ YES - Safe template |

---

## 🔐 AUTO-GENERATED SECRETS

The following production secrets have been **securely generated** using cryptographic random generation:

### 1. Database Password
```bash
POSTGRES_PASSWORD=MAv9crbSYmn7gHTBCqJMvaHhBfHt/DGJd1fKmMJPHCUiuEy9Iidna7CQs+HNT/7r
```
- **Length:** 64 characters (base64)
- **Entropy:** 384 bits
- **Generated with:** `openssl rand -base64 48`
- **Security:** Production-grade

### 2. Application Secret Key
```bash
SECRET_KEY=3505bf4420d3dfe11199045a7419153d4858e05ac013ac00ff4b8dc22d1cf721b6478e1e76635ea8c2889f3d026b4910729f09943f79b296f6102d92db1c3304
```
- **Length:** 128 characters (hex)
- **Entropy:** 512 bits
- **Generated with:** `openssl rand -hex 64`
- **Security:** Production-grade
- **Used for:** Session encryption, token signing, CSRF protection

### 3. Backup Encryption Key
```bash
BACKUP_ENCRYPTION_KEY=MJATgHckJVfbcZeZAUn5i7fenHbBIrEybWlmWKebNRU=
```
- **Length:** 44 characters (base64)
- **Entropy:** 256 bits
- **Generated with:** `openssl rand -base64 32`
- **Security:** Production-grade
- **Used for:** Encrypted database backups

---

## ⚠️ MANUAL CONFIGURATION REQUIRED

The following values **MUST be manually configured** before production deployment:

### 1. Database Host (CRITICAL)
```bash
# Current placeholder:
DATABASE_URL=postgresql://...@your-production-db-host.com:5432/...

# Replace with actual:
DATABASE_URL=postgresql://tria_admin_prod:<PASSWORD>@db.your-company.com:5432/tria_aibpo_production
```

### 2. OpenAI API Key (CRITICAL)
```bash
# Current placeholder:
OPENAI_API_KEY=YOUR_PRODUCTION_OPENAI_API_KEY_HERE

# Get from: https://platform.openai.com/api-keys
# Replace with actual:
OPENAI_API_KEY=sk-proj-...
```

### 3. Xero OAuth Credentials (CRITICAL)
```bash
# Current placeholders:
XERO_CLIENT_ID=YOUR_PRODUCTION_XERO_CLIENT_ID
XERO_CLIENT_SECRET=YOUR_PRODUCTION_XERO_CLIENT_SECRET
XERO_REFRESH_TOKEN=YOUR_PRODUCTION_XERO_REFRESH_TOKEN
XERO_TENANT_ID=YOUR_PRODUCTION_XERO_TENANT_ID

# Setup instructions:
# 1. Go to: https://developer.xero.com/
# 2. Create production OAuth app
# 3. Run: python setup_xero_oauth.py
# 4. Copy tokens to .env.production
```

### 4. CORS Origins (CRITICAL)
```bash
# Current placeholder:
CORS_ORIGINS=https://tria-aibpo.com,https://app.tria-aibpo.com,https://api.tria-aibpo.com

# Replace with your actual production domains
```

---

## 📋 DEPLOYMENT CHECKLIST

### Before First Deployment:

#### Critical (MUST DO):
- [ ] Update `DATABASE_URL` with production database host
- [ ] Add production `OPENAI_API_KEY`
- [ ] Configure Xero OAuth credentials
- [ ] Update `CORS_ORIGINS` with production domains
- [ ] Verify `TAX_RATE` is correct (0.08 for Singapore)
- [ ] Verify `XERO_SALES_ACCOUNT_CODE` and `XERO_TAX_TYPE`

#### Recommended:
- [ ] Set up Sentry (`SENTRY_DSN`) for error tracking
- [ ] Configure SendGrid (`SENDGRID_API_KEY`) for email alerts
- [ ] Set up Twilio (optional) for SMS notifications
- [ ] Enable SSL/TLS for database connection
- [ ] Configure automated backups
- [ ] Set up monitoring dashboards
- [ ] Test backup and restore procedures

#### Security:
- [ ] Store `.env.production` in secrets management system
- [ ] Never commit `.env.production` to git
- [ ] Use separate secrets for dev/staging/prod
- [ ] Enable database encryption at rest
- [ ] Configure firewall rules
- [ ] Set up SSL certificates
- [ ] Enable audit logging
- [ ] Schedule secret rotation (90 days)

---

## 🔒 SECRETS MANAGEMENT

### Recommended Approach:

#### For AWS:
```bash
# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name tria-aibpo/production/env \
  --secret-string file://.env.production

# Retrieve in application:
# Use AWS SDK to fetch secrets at runtime
```

#### For Azure:
```bash
# Store in Azure Key Vault
az keyvault secret set \
  --vault-name tria-aibpo-vault \
  --name production-env \
  --file .env.production

# Retrieve in application:
# Use Azure SDK to fetch secrets at runtime
```

#### For Google Cloud:
```bash
# Store in Secret Manager
gcloud secrets create tria-aibpo-production-env \
  --data-file=.env.production

# Retrieve in application:
# Use Google Cloud SDK to fetch secrets at runtime
```

---

## 🔄 SECRET ROTATION SCHEDULE

All secrets should be rotated on a regular schedule:

| Secret | Rotation Frequency | Impact |
|--------|-------------------|--------|
| `POSTGRES_PASSWORD` | 90 days | Requires app restart |
| `SECRET_KEY` | 90 days | Invalidates sessions |
| `XERO_REFRESH_TOKEN` | Auto (OAuth) | Handled by OAuth flow |
| `OPENAI_API_KEY` | On security incident | Immediate |
| `BACKUP_ENCRYPTION_KEY` | Never* | Breaks old backups |

\* Backup encryption key should only be rotated with migration plan

### Rotation Procedure:
1. Generate new secret
2. Update secrets management system
3. Deploy new configuration (blue-green)
4. Verify application health
5. Decommission old secret after 24h
6. Document rotation in audit log

---

## 🧪 VALIDATION BEFORE DEPLOYMENT

Run these commands to verify production configuration:

### 1. Validate Required Variables
```bash
# Copy production config
cp .env.production .env

# Run validator
python src/config_validator.py

# Expected output:
# [OK] Configuration validation passed
# [SUCCESS] All configuration checks passed!
```

### 2. Check for Placeholder Values
```bash
# This should return NOTHING:
grep "YOUR_.*_HERE" .env.production
grep "<.*>" .env.production

# If anything found, you have unconfigured placeholders!
```

### 3. Test Database Connection
```bash
# Test connection string
python -c "
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('.env.production')
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

### 4. Verify Secrets Are Strong
```bash
# Check database password entropy (should be 48+ bytes)
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.production')
pwd = os.getenv('POSTGRES_PASSWORD')
print(f'Password length: {len(pwd)} characters')
print(f'✅ Strong' if len(pwd) >= 48 else '❌ Weak')
"
```

---

## 🚨 SECURITY INCIDENTS

### If Secrets Are Compromised:

1. **IMMEDIATELY** rotate all affected secrets
2. Revoke compromised API keys
3. Change database passwords
4. Review access logs for unauthorized access
5. Generate new `SECRET_KEY` (invalidates all sessions)
6. Notify security team
7. Document incident
8. Review and improve access controls

### Emergency Contacts:
- Security Team: security@your-company.com
- On-Call: Use PagerDuty/OpsGenie
- Database Admin: dba@your-company.com

---

## 📊 PRODUCTION SECRETS INVENTORY

All secrets in `.env.production`:

### Critical Secrets (MUST be configured):
1. ✅ `POSTGRES_PASSWORD` - Auto-generated (64 chars)
2. ✅ `SECRET_KEY` - Auto-generated (128 chars)
3. ⚠️ `DATABASE_URL` - **NEEDS MANUAL UPDATE** (host)
4. ⚠️ `OPENAI_API_KEY` - **NEEDS MANUAL CONFIG**
5. ⚠️ `XERO_CLIENT_ID` - **NEEDS MANUAL CONFIG**
6. ⚠️ `XERO_CLIENT_SECRET` - **NEEDS MANUAL CONFIG**
7. ⚠️ `XERO_REFRESH_TOKEN` - **NEEDS MANUAL CONFIG**
8. ⚠️ `XERO_TENANT_ID` - **NEEDS MANUAL CONFIG**

### Optional Secrets (Recommended):
9. ❌ `SENTRY_DSN` - Not configured
10. ❌ `SENDGRID_API_KEY` - Not configured
11. ❌ `TWILIO_ACCOUNT_SID` - Not configured
12. ❌ `TWILIO_AUTH_TOKEN` - Not configured

---

## 🛠️ HOW TO GENERATE NEW SECRETS

If you need to regenerate any secret:

### Database Password (48 bytes):
```bash
openssl rand -base64 48
```

### Secret Key (64 bytes):
```bash
openssl rand -hex 64
```

### Backup Encryption Key (32 bytes):
```bash
openssl rand -base64 32
```

### UUID-based Secret:
```bash
python -c "import uuid; print(str(uuid.uuid4()))"
```

---

## ✅ VERIFICATION RESULTS

All critical variables verified present in `.env.production`:

```bash
✅ DATABASE_URL - Present (needs host update)
✅ OPENAI_API_KEY - Present (needs actual key)
✅ TAX_RATE - Configured (0.08)
✅ XERO_SALES_ACCOUNT_CODE - Configured (200)
✅ XERO_TAX_TYPE - Configured (OUTPUT2)
✅ SECRET_KEY - Auto-generated (128 chars)
✅ POSTGRES_PASSWORD - Auto-generated (64 chars)
✅ BACKUP_ENCRYPTION_KEY - Auto-generated (44 chars)
```

---

## 📚 NEXT STEPS

1. **Review** `.env.production` and update placeholders
2. **Test** configuration with `python src/config_validator.py`
3. **Store** `.env.production` in secrets management system
4. **Delete** local `.env.production` after storing securely
5. **Deploy** using secrets management retrieval
6. **Monitor** for any configuration errors
7. **Document** any additional secrets added

---

## 🔗 RELATED DOCUMENTATION

- `DATABASE_CONFIGURATION.md` - Database setup and passwords
- `PRODUCTION_AUDIT_COMPLETE.md` - Code audit and fixes
- `HONEST_TEST_RESULTS.md` - Testing verification
- `.env.example` - Development configuration template
- `.env.docker.example` - Docker deployment template

---

**Generated:** 2025-10-18
**Security Level:** CRITICAL - PROTECT THIS INFORMATION
**Secrets Management:** Store in vault, never commit to git
**Rotation Schedule:** Every 90 days minimum
