# Xero SDK Migration Documentation

**Status:** ⚠️ **IN TESTING** - Not yet production-ready
**Date:** 2025-11-24
**Migration Type:** REST API → Official xero-python SDK

---

## Executive Summary

**What Changed:**
- Replaced custom REST API implementation (719 lines) with official xero-python SDK
- Maintained identical interface (same methods, same dataclasses)
- Zero breaking changes to calling code (orchestrator, scripts)

**Current Status:**
- ✅ Code implemented
- ✅ Syntax validated
- ⚠️ **Needs verification** (see Testing section)
- ❌ **Not production-ready yet**

**Risk Level:** 🟡 **MEDIUM**
- High confidence in SDK quality
- Needs thorough testing before production use
- Rollback plan available (see below)

---

## Migration Details

### What Was Replaced

**File:** `src/integrations/xero_client.py`

**Before (REST API):**
```python
import requests

# Manual OAuth token refresh
response = requests.post(self.token_url, data=token_data)
self._access_token = response.json()['access_token']

# Manual API calls
response = requests.get(
    f"{self.api_url}/Contacts",
    headers={"Authorization": f"Bearer {token}", ...}
)
```

**After (Official SDK):**
```python
from xero_python.api_client import ApiClient
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.accounting import AccountingApi

# Automatic OAuth token refresh
token = OAuth2Token(client_id, client_secret)
token.refresh_token = self.refresh_token
token.refresh_access_token(api_client)

# SDK API calls
contacts = self._accounting_api.get_contacts(
    xero_tenant_id=self.tenant_id,
    where=f'Name=="{customer_name}"'
)
```

---

## Key Differences

### 1. Token Management

| Aspect | REST API (Old) | SDK (New) |
|--------|---------------|-----------|
| **Token Refresh** | Manual `requests.post()` | `token.refresh_access_token(api_client)` |
| **Token Storage** | Manual `self._access_token` | SDK manages internally |
| **Expiry Tracking** | Manual calculation | `token.expires_at` |
| **Refresh Logic** | 30 lines custom code | SDK handles automatically |

### 2. API Calls

| Operation | REST API (Old) | SDK (New) |
|-----------|---------------|-----------|
| **Get Contacts** | `requests.get("/Contacts", headers=...)` | `accounting_api.get_contacts(tenant_id, where=...)` |
| **Create PO** | `requests.post("/PurchaseOrders", json=...)` | `accounting_api.create_purchase_orders(tenant_id, purchase_orders)` |
| **Create Invoice** | `requests.post("/Invoices", json=...)` | `accounting_api.create_invoices(tenant_id, invoices)` |
| **Error Handling** | `requests.exceptions.HTTPError` | `AccountingBadRequestException` |

### 3. Data Models

| Aspect | REST API (Old) | SDK (New) |
|--------|---------------|-----------|
| **Request Body** | Plain dicts `{"Contact": {"ContactID": "..."}}` | SDK models `Contact(contact_id="...")` |
| **Response Parsing** | Manual `response.json()["Contacts"][0]` | SDK models `contacts.contacts[0]` |
| **Type Safety** | Manual typing | Built-in Pydantic models |

---

## What Stayed the Same

✅ **Public Interface (100% Compatible)**

All these still work exactly the same:

```python
from integrations.xero_client import get_xero_client

client = get_xero_client()

# Same methods
customer = client.verify_customer("Customer Name")
product = client.check_inventory("PROD-001")
order = client.create_draft_order(contact_id, line_items)
client.finalize_order(order_id)
invoice = client.create_invoice(contact_id, line_items)

# Same dataclasses
assert isinstance(customer, XeroCustomer)
assert isinstance(product, XeroProduct)
assert isinstance(order, XeroDraftOrder)
assert isinstance(invoice, XeroInvoice)
```

✅ **Production Infrastructure (Unchanged)**

- Circuit breaker: `@circuit_breaker("xero")`
- Retry logic: `@retry_with_backoff(max_attempts=3)`
- Rate limiting: `@rate_limit_xero`
- Input validation: `validate_xero_where_clause_input()`

✅ **No Changes Required To:**

- `src/integrations/xero_order_orchestrator.py`
- `scripts/load_xero_demo_data.py`
- `scripts/test_order_with_xero.py`
- Any other code that uses `get_xero_client()`

---

## Configuration Changes

### Added to `.env`:

```bash
# NEW - Required for SDK
XERO_REFRESH_TOKEN=your-refresh-token
XERO_TAX_TYPE=Tax on Purchases
```

### Existing (No Change):

```bash
XERO_CLIENT_ID=your-xero-client-id
XERO_CLIENT_SECRET=your-xero-client-secret
XERO_TENANT_ID=your-tenant-id
XERO_SALES_ACCOUNT_CODE=200
```

---

## Testing & Verification

### Phase 1: Pre-Deployment Testing (REQUIRED) ⚠️

**Run verification script:**

```bash
python scripts/verify_xero_sdk_integration.py
```

**This tests:**
1. ✅ SDK imports work
2. ✅ Configuration is valid
3. ✅ Client initializes correctly
4. ✅ OAuth token mechanism works
5. ✅ Method signatures are correct
6. ✅ Dataclasses work
7. ✅ Error handling works
8. ✅ Live API calls (customer/product lookup)

**Expected Output:**
```
🎉 ALL TESTS PASSED - SDK Integration Verified!
```

**If tests fail:**
```
⚠️  SOME TESTS FAILED - DO NOT USE IN PRODUCTION
```
→ See "Rollback Procedure" section

---

### Phase 2: Integration Testing

**Test end-to-end order flow:**

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Start backend
python -m uvicorn src.enhanced_api:app --host 127.0.0.1 --port 8003

# 3. Run integration test
python scripts/test_order_with_xero.py
```

**What to verify:**
- ✅ Customer verification works
- ✅ Inventory check works
- ✅ Draft order creation works
- ✅ Order finalization works
- ✅ Invoice creation works
- ✅ Agent timeline updates correctly
- ✅ No SDK-specific errors in logs

---

### Phase 3: Load Testing (Recommended)

**Test under production-like load:**

```bash
python scripts/load_xero_demo_data.py --dry-run
python scripts/load_xero_demo_data.py
```

**Monitor for:**
- Token refresh behavior (every 30 minutes)
- Rate limiting (60 requests/minute)
- Memory usage (SDK client singleton)
- Error rates

---

## Known Issues & Limitations

### 1. Token Refresh Untested ⚠️

**Issue:**
Token refresh mechanism (`token.refresh_access_token()`) has not been verified with real Xero credentials.

**Impact:**
Unknown if tokens will refresh correctly when they expire (every 30 minutes).

**Mitigation:**
- Test with real credentials in dev environment
- Monitor logs for token refresh events
- Keep REST API implementation as backup

---

### 2. SDK Exception Handling Incomplete ⚠️

**Issue:**
Only catching `AccountingBadRequestException`, but SDK may throw other exceptions:
- `ApiException` - General API errors
- `UnauthorizedException` - Auth failures
- `NotFoundException` - Resource not found
- Network/timeout exceptions

**Impact:**
Unexpected exceptions might not be handled gracefully.

**Mitigation:**
```python
# Consider adding:
from xero_python.exceptions import (
    AccountingBadRequestException,
    ApiException,
    UnauthorizedException
)
```

---

### 3. Decorator Conflicts Unknown ⚠️

**Issue:**
Our custom retry decorators might conflict with SDK's built-in retry logic (if any).

**Impact:**
Potential double-retries or excessive API calls.

**Mitigation:**
- Monitor API call counts
- Review SDK source for built-in retries
- Consider removing our decorators if SDK handles it

---

### 4. Performance Unverified ⚠️

**Issue:**
SDK performance vs REST API not benchmarked.

**Impact:**
Unknown if SDK introduces latency or memory overhead.

**Mitigation:**
- Benchmark both implementations side-by-side
- Monitor production metrics after deployment

---

## Rollback Procedure

### If SDK Integration Fails:

**Option 1: Git Revert (Recommended)**

```bash
# Revert to commit before SDK migration
git log --oneline | grep "xero"  # Find commit hash
git revert <commit-hash>

# Or restore specific file
git checkout HEAD~1 -- src/integrations/xero_client.py
```

**Option 2: Manual Restore (If needed)**

1. **Restore old REST API implementation:**
   - File: `src/integrations/xero_client.py`
   - Backup location: `git show HEAD~1:src/integrations/xero_client.py`

2. **Remove SDK-specific config:**
   ```bash
   # Remove from .env:
   XERO_REFRESH_TOKEN=...  # Keep only if used by REST API
   XERO_TAX_TYPE=...       # Keep (used by both)
   ```

3. **Restart services:**
   ```bash
   docker-compose restart
   python -m uvicorn src.enhanced_api:app --reload
   ```

4. **Verify REST API works:**
   ```bash
   python scripts/test_order_with_xero.py
   ```

**Recovery Time Estimate:** 10 minutes

---

## Comparison Benchmarks (To Be Completed)

### Performance Metrics (Placeholder)

| Operation | REST API (Old) | SDK (New) | Difference |
|-----------|----------------|-----------|------------|
| **Token Refresh** | TBD | TBD | TBD |
| **Get Contact** | TBD | TBD | TBD |
| **Create PO** | TBD | TBD | TBD |
| **Create Invoice** | TBD | TBD | TBD |
| **Memory Usage** | TBD | TBD | TBD |

**TODO:** Run benchmarks after verification passes.

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] All verification tests pass (`verify_xero_sdk_integration.py`)
- [ ] Integration tests pass (`test_order_with_xero.py`)
- [ ] Load testing completed successfully
- [ ] Token refresh verified with real credentials
- [ ] Performance benchmarks acceptable
- [ ] Logs reviewed for SDK-specific warnings/errors
- [ ] Rollback procedure tested and documented
- [ ] Team trained on new SDK behavior

### During Deployment

- [ ] Deploy to staging first
- [ ] Run full regression tests in staging
- [ ] Monitor logs for 24 hours
- [ ] Verify no error rate increase
- [ ] Check token refresh works in production-like environment

### Post-Deployment

- [ ] Monitor Xero API call rates
- [ ] Monitor token refresh frequency
- [ ] Track error rates vs baseline
- [ ] Monitor memory/CPU usage
- [ ] Keep REST API code available for quick rollback

---

## Support & Troubleshooting

### Common Issues

**1. Token Refresh Fails**

```
Error: Failed to initialize Xero SDK API client: ...
```

**Solution:**
- Check `XERO_REFRESH_TOKEN` in `.env`
- Verify token hasn't expired (60-day limit)
- Re-run: `python scripts/get_xero_tokens.py`

---

**2. Import Errors**

```
ImportError: cannot import name 'LineItems' from 'xero_python.accounting'
```

**Solution:**
- Check xero-python version: `pip show xero-python` (should be >=2.4.0)
- Reinstall: `pip install --upgrade xero-python`

---

**3. Method Not Found**

```
AttributeError: 'AccountingApi' object has no attribute 'get_contacts'
```

**Solution:**
- Verify SDK version: `pip show xero-python`
- Check SDK documentation: https://github.com/XeroAPI/xero-python
- May need to update SDK: `pip install --upgrade xero-python`

---

### Logging & Debugging

**Enable verbose SDK logging:**

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('xero_python').setLevel(logging.DEBUG)
```

**Check SDK version at runtime:**

```python
import xero_python
print(f"xero-python version: {xero_python.__version__}")
```

---

## References

### Official Documentation

- **xero-python SDK:** https://github.com/XeroAPI/xero-python
- **Xero API Docs:** https://developer.xero.com/documentation/api/accounting/overview
- **OAuth 2.0 Guide:** https://developer.xero.com/documentation/guides/oauth2/overview

### Internal Documentation

- **Original REST API:** `git show HEAD~1:src/integrations/xero_client.py`
- **Configuration:** `docs/setup/PRODUCTION_SECRETS_SETUP.md`
- **System Architecture:** `docs/02-system-architecture.md`

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-24 | 0.1.0 | Initial SDK migration (untested) |
| 2025-11-24 | 0.2.0 | Fixed token initialization based on SDK API research |
| TBD | 1.0.0 | Production-ready after full verification |

---

## Sign-Off

**Implemented By:** Claude Code
**Reviewed By:** _Pending_
**Tested By:** _Pending_
**Approved By:** _Pending_

**Production Deployment:** ❌ **NOT APPROVED**
**Status:** ⚠️ **REQUIRES VERIFICATION**
