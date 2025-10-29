# TRIA AI-BPO PDPA Compliance Guide

**Version:** 1.0
**Date:** 2025-10-18
**Status:** PRODUCTION-READY

---

## Overview

This document describes TRIA's implementation of Singapore's Personal Data Protection Act (PDPA) compliance for the AI-BPO chatbot system.

### Key Features

✅ **Automatic PII Detection & Scrubbing** - Singapore-specific patterns
✅ **Data Retention Policies** - 90 days (conversations), 2 years (summaries)
✅ **Audit Logging** - Complete trail of data operations
✅ **Privacy-First Design** - Original PII never stored
✅ **Production-Ready** - No mocking, real database operations

---

## Architecture

### Privacy Layer Components

```
┌─────────────────────────────────────────────────────────────┐
│                    PRIVACY PROTECTION LAYER                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. PII Scrubber (src/privacy/pii_scrubber.py)              │
│     - Singapore phone numbers (+65, 8/9/6 series)           │
│     - Email addresses                                        │
│     - NRIC/FIN numbers (S/T/F/G/M series)                   │
│     - Credit card numbers (all major providers)             │
│     - Singapore addresses & postal codes                    │
│                                                              │
│  2. Data Retention (src/privacy/data_retention.py)          │
│     - 90-day conversation cleanup                           │
│     - 2-year summary anonymization                          │
│     - Audit logging                                         │
│                                                              │
│  3. Session Manager (src/memory/session_manager.py)         │
│     - Integrated PII scrubbing on message logging           │
│     - PII metadata stored in JSONB context                  │
│     - Automatic scrubbing for all user messages             │
│                                                              │
│  4. Cleanup Scheduler (scripts/schedule_data_cleanup.py)    │
│     - Cron-ready automation script                          │
│     - Dry-run mode for testing                              │
│     - Email notifications                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. PII Detection & Scrubbing

### Supported PII Types

| PII Type | Examples | Placeholder |
|----------|----------|-------------|
| **Singapore Phone** | +65 9123 4567, 81234567 | `[PHONE]` |
| **Email** | john@example.com | `[EMAIL]` |
| **NRIC/FIN** | S1234567D, T9876543A, F1234567N | `[NRIC]` |
| **Credit Card** | 4532 1234 5678 9010 | `[CARD]` |
| **Address** | Blk 123 Ang Mo Kio Ave 3 #12-34 | `[ADDRESS]` |
| **Postal Code** | 560123 | `[POSTAL_CODE]` |

### Usage Example

```python
from src.privacy.pii_scrubber import scrub_pii

# Original message with PII
text = "Call me at +65 9123 4567 or email john@example.com. NRIC: S1234567D"

# Scrub PII
scrubbed_text, metadata = scrub_pii(text)

print(scrubbed_text)
# Output: "Call me at [PHONE] or email [EMAIL]. NRIC: [NRIC]"

print(metadata.total_count)
# Output: 3

print(metadata.by_type)
# Output: {'PHONE': 1, 'EMAIL': 1, 'NRIC': 1}
```

### Automatic Integration

PII scrubbing is automatically applied when logging messages:

```python
from src.memory.session_manager import SessionManager

manager = SessionManager()

# Log message - PII automatically scrubbed before storage
manager.log_message(
    session_id="abc123",
    role="user",
    content="My phone is +65 9123 4567",  # Original with PII
    intent="inquiry"
)

# Database stores: "My phone is [PHONE]"
# PII metadata stored in message context for audit
```

### PII Metadata Structure

```json
{
  "total_count": 3,
  "by_type": {
    "PHONE": 1,
    "EMAIL": 1,
    "NRIC": 1
  },
  "details": [
    {
      "type": "PHONE",
      "placeholder": "[PHONE]",
      "position": 11,
      "length": 14
    },
    {
      "type": "EMAIL",
      "placeholder": "[EMAIL]",
      "position": 35,
      "length": 18
    },
    {
      "type": "NRIC",
      "placeholder": "[NRIC]",
      "position": 61,
      "length": 9
    }
  ],
  "original_length": 70,
  "scrubbed_length": 58
}
```

---

## 2. Data Retention Policies

### Retention Periods

| Data Type | Retention Period | Action After Period |
|-----------|------------------|---------------------|
| **Conversation Messages** | 90 days | Permanent deletion |
| **Conversation Sessions** | 90 days | Permanent deletion |
| **User Summaries** | 2 years | Anonymization (user_id → hash) |
| **Audit Logs** | Indefinite | Retained for compliance |

### Cleanup Operations

#### Manual Cleanup (Development)

```python
import psycopg2
from src.privacy.data_retention import run_full_cleanup

# Connect to database
conn = psycopg2.connect(os.getenv('DATABASE_URL'))

# Dry run (reports only, no changes)
results = run_full_cleanup(conn, dry_run=True)

print(f"Would delete: {results['conversations'].conversations_deleted} conversations")
print(f"Would anonymize: {results['summaries'].summaries_anonymized} summaries")

# Production run (actually deletes data)
results = run_full_cleanup(conn, dry_run=False)
```

#### Automated Cleanup (Production)

```bash
# Install as cron job (daily at 2 AM)
0 2 * * * /path/to/python /path/to/schedule_data_cleanup.py >> /var/log/tria/cleanup.log 2>&1

# Dry run for testing
python scripts/schedule_data_cleanup.py --dry-run

# Production run
python scripts/schedule_data_cleanup.py

# With email notifications
python scripts/schedule_data_cleanup.py --notify-email admin@tria.com

# Custom retention periods
python scripts/schedule_data_cleanup.py --conversation-retention 60 --summary-retention 365
```

### Anonymization Process

User summaries older than 2 years are anonymized:

**Before:**
```sql
user_id: "+6591234567"
total_conversations: 10
preferred_language: "en"
```

**After:**
```sql
user_id: "ANON_a7b3c9d8e2f1a4b6c8d9e0f1a2b3c4d5"  -- SHA-256 hash
total_conversations: 10  -- Statistics preserved
preferred_language: "en"  -- Preserved
```

**Key Points:**
- User ID replaced with deterministic hash (same user → same hash)
- Aggregate statistics preserved for analytics
- Process is irreversible (cannot recover original user_id)
- Already anonymized records not re-processed

---

## 3. Database Schema

### Conversation Messages (90-day retention)

```sql
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES conversation_sessions(session_id),
    role VARCHAR(20),              -- 'user' or 'assistant'
    content TEXT,                  -- SCRUBBED CONTENT (PII removed)
    language VARCHAR(10),
    intent VARCHAR(50),
    confidence DECIMAL(3,2),
    context JSONB,                 -- Includes PII metadata if scrubbed
    pii_scrubbed BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User Summaries (2-year retention before anonymization)

```sql
CREATE TABLE user_interaction_summaries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE,   -- Anonymized after 2 years
    outlet_id INTEGER REFERENCES outlets(id),
    total_conversations INTEGER,
    total_messages INTEGER,
    common_intents JSONB,
    preferred_language VARCHAR(10),
    avg_satisfaction DECIMAL(3,2),
    last_interaction TIMESTAMP,
    first_interaction TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Audit Log (indefinite retention)

```sql
CREATE TABLE data_retention_audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,  -- 'cleanup_old_conversations', 'anonymize_old_summaries'
    details JSONB NOT NULL,        -- Full operation details
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Testing

### Unit Tests (Tier 1)

Test PII detection without database:

```bash
# Run PII scrubber tests
pytest tests/tier1_unit/privacy/test_pii_scrubber.py -v

# Test coverage
pytest tests/tier1_unit/privacy/test_pii_scrubber.py --cov=src.privacy.pii_scrubber
```

**Test Coverage:**
- Singapore phone numbers (all formats)
- Email addresses
- NRIC/FIN numbers (all series: S, T, F, G, M)
- Credit cards (Visa, Mastercard, Amex, Discover, etc.)
- Addresses and postal codes
- Edge cases (empty text, no PII, boundary conditions)
- Real-world scenarios (orders, complaints, deliveries)

### Integration Tests (Tier 2)

Test data retention with real database:

```bash
# Set DATABASE_URL in .env
export DATABASE_URL="postgresql://user:pass@localhost:5432/tria"

# Run data retention tests
pytest tests/tier2_integration/privacy/test_data_retention.py -v

# Specific test
pytest tests/tier2_integration/privacy/test_data_retention.py::TestConversationCleanup::test_cleanup_deletes_old_conversations -v
```

**Test Coverage:**
- Conversation cleanup (90-day retention)
- User summary anonymization (2-year retention)
- Dry-run mode
- Audit logging
- Statistics reporting
- Full cleanup operation

---

## 5. Compliance Checklist

### PDPA Requirements

- [x] **Data Minimization** - Only necessary data collected
- [x] **Purpose Limitation** - Data used only for stated purpose
- [x] **Consent** - User consent obtained before data collection
- [x] **Accuracy** - Data kept accurate and up-to-date
- [x] **Retention Limitation** - Data deleted after retention period
- [x] **Security** - Data encrypted at rest and in transit
- [x] **Access Controls** - Role-based access to personal data
- [x] **Audit Trail** - Complete log of data operations
- [x] **Right to Erasure** - Data deletion mechanism implemented
- [x] **Data Breach Response** - Incident response plan in place

### Implementation Verification

```bash
# 1. Verify PII scrubbing works
python -c "
from src.privacy.pii_scrubber import scrub_pii
text = 'Call +65 9123 4567'
scrubbed, meta = scrub_pii(text)
assert scrubbed == 'Call [PHONE]'
assert meta.total_count == 1
print('✓ PII scrubbing works')
"

# 2. Verify retention statistics
python -c "
import os
import psycopg2
from src.privacy.data_retention import get_retention_statistics
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
stats = get_retention_statistics(conn)
print('✓ Retention statistics:', stats)
conn.close()
"

# 3. Verify cleanup script
python scripts/schedule_data_cleanup.py --dry-run
```

---

## 6. Production Deployment

### Environment Configuration

```bash
# .env file
DATABASE_URL=postgresql://user:pass@host:5432/tria
OPENAI_API_KEY=sk-...

# Optional: Email notifications
SENDGRID_API_KEY=SG.xxx
NOTIFICATION_EMAIL=admin@tria.com
```

### Cron Setup

```bash
# 1. Edit crontab
crontab -e

# 2. Add daily cleanup job (2 AM)
0 2 * * * /usr/bin/python3 /opt/tria/scripts/schedule_data_cleanup.py >> /var/log/tria/cleanup.log 2>&1

# 3. Verify cron job
crontab -l

# 4. Monitor logs
tail -f /var/log/tria/cleanup.log
```

### Monitoring

```bash
# Check cleanup reports
ls -lh logs/cleanup/

# View latest cleanup report
cat logs/cleanup/cleanup_20251018_020000.json | jq

# Monitor audit log
psql $DATABASE_URL -c "
SELECT action, timestamp, details->>'conversations_deleted' as deleted
FROM data_retention_audit_log
ORDER BY timestamp DESC
LIMIT 10
"
```

---

## 7. Troubleshooting

### Common Issues

#### PII Not Detected

**Symptom:** PII visible in database
**Solution:** Check regex patterns in `pii_scrubber.py`, verify pattern matches your format

```python
from src.privacy.pii_scrubber import scrub_pii

# Test specific case
text = "Your problematic PII here"
scrubbed, meta = scrub_pii(text)
print(f"Detected: {meta.by_type}")
```

#### Cleanup Not Running

**Symptom:** Old data not deleted
**Solution:**
1. Check cron job is active: `crontab -l`
2. Check script permissions: `chmod +x scripts/schedule_data_cleanup.py`
3. Check logs: `tail -f /var/log/tria/cleanup.log`
4. Test manually: `python scripts/schedule_data_cleanup.py --dry-run`

#### Database Connection Errors

**Symptom:** "DATABASE_URL not set" error
**Solution:** Verify environment variables

```bash
# Check DATABASE_URL is set
echo $DATABASE_URL

# Test connection
python -c "
import os
import psycopg2
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
print('✓ Database connection successful')
conn.close()
"
```

---

## 8. Security Best Practices

### Do's ✅

- **Always** use PII scrubbing when logging user messages
- **Always** run cleanup in dry-run mode first when testing
- **Always** check audit logs after cleanup operations
- **Always** encrypt database backups
- **Always** use HTTPS/TLS for all API communications
- **Always** hash sensitive identifiers before logging

### Don'ts ❌

- **Never** disable PII scrubbing in production
- **Never** log original PII to files or console
- **Never** share database credentials in code or docs
- **Never** extend retention periods without legal review
- **Never** manually edit anonymized user IDs
- **Never** skip backup before running cleanup

---

## 9. References

### PDPA Resources

- [PDPA Official Website](https://www.pdpc.gov.sg)
- [Guide to Data Protection](https://www.pdpc.gov.sg/Help-and-Resources/2017/10/Guide-to-Data-Protection)
- [Data Breach Notification](https://www.pdpc.gov.sg/overview-of-pdpa/data-protection/mandatory-data-breach-notification)

### Internal Documentation

- `doc/CHATBOT_ARCHITECTURE_PROPOSAL.md` - Section 7 (PDPA Compliance)
- `src/privacy/pii_scrubber.py` - PII detection implementation
- `src/privacy/data_retention.py` - Retention policy implementation
- `tests/tier1_unit/privacy/` - Unit test examples
- `tests/tier2_integration/privacy/` - Integration test examples

---

## 10. Support & Contact

**For PDPA compliance questions:**
- Technical: [Your Tech Lead]
- Legal: [Your Legal Team]
- DPO (Data Protection Officer): [DPO Contact]

**For implementation support:**
- See test files for usage examples
- Check audit logs for operation history
- Review documentation in `docs/`

---

**Last Updated:** 2025-10-18
**Next Review:** 2026-01-18 (Quarterly review)
