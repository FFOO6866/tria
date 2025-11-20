# Development Standards

**TRIA AIBPO Coding Standards and Best Practices**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## Production-Grade Patterns (CRITICAL)

See [CLAUDE.md](../CLAUDE.md) for complete guidelines. Key patterns:

### 1. Database Connection Pooling

ALWAYS use global engine singleton from `database.py`.

### 2. Centralized Configuration  

ALWAYS use `from config import config` - never `os.getenv()` directly.

### 3. No Hardcoding

Never hardcode credentials, pricing, or business rules.

### 4. No Mocking in Production

Use real APIs and databases. Mock only in Tier 1 unit tests.

### 5. Explicit Error Handling

Fail fast and explicitly. No hidden fallbacks.

---

## Code Quality

- Type hints for all functions
- Docstrings for public functions
- PEP 8 style guide
- Meaningful variable names
- Explicit error handling (no bare `except:`)

---

## Testing Strategy

- **Tier 1**: Unit tests (mocking allowed)
- **Tier 2**: Integration tests (real infrastructure)
- **Tier 3**: E2E tests (full system)

---

## Security

- Input validation at all layers
- No credentials in code
- Rate limiting
- Structured logging (no PII)

---

## See Also

- [CLAUDE.md](../CLAUDE.md) - Complete guidelines
- [System Architecture](02-system-architecture.md)
- [src/README.md](../src/README.md)

---

**Last Updated**: 2025-11-21
