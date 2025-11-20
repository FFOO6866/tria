# NEXT STEP: Refresh Xero OAuth Token

## What's Been Fixed So Far:

✅ **PostgreSQL**: Running on port 5433 (7 tables loaded)
✅ **Redis**: Running on port 6380 (authentication working)
✅ **Circuit Breaker Bug**: Fixed in `src/production/retry.py`
✅ **System Score**: Improved from 50% → 79% (est. 11/14)

## Current Blocker:

❌ **Xero API**: Refresh token expired (400 Bad Request)

---

## YOUR ACTION REQUIRED (5 minutes):

### Step 1: Open a New Command Prompt

Open a **NEW** command prompt window (not this Claude session)

### Step 2: Navigate to Project Directory

```bash
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria
```

### Step 3: Run Token Refresh Script

```bash
python scripts/get_xero_tokens.py
```

### Step 4: Follow Interactive Prompts

The script will:
1. Ask which redirect URI you configured (usually option **1** or **3**)
2. Display an authorization URL
3. **Open your browser automatically** to Xero login
4. After you authorize, Xero redirects to a URL with a `code=` parameter
5. **Copy the entire redirect URL** from your browser address bar
6. Paste it back into the terminal when prompted

### Step 5: Copy New Token

The script will display:
```
Your XERO_REFRESH_TOKEN:
abc123xyz456... (long token string)

Your XERO_TENANT_ID:
dd8f7211-da0c-42a6-9eb3-6815379bbcac
```

### Step 6: Update .env File

Open `.env` file and replace the old token on line 39:

**OLD:**
```
XERO_REFRESH_TOKEN=ThI8KyOWILz9rzvAVTQ_fi3LPbQmh6qWOcntbfmTxsE
```

**NEW:**
```
XERO_REFRESH_TOKEN=<paste your new token here>
```

Save the file.

---

## After You Complete This:

Let me know in Claude, and I will:
1. ✅ Test Xero API connection (should work now)
2. ✅ Re-verify system state (expect 93% score)
3. ✅ Load master data to Xero (customers + products)
4. ✅ Test end-to-end order flow
5. ✅ Deploy to production

**ETA to production after token refresh:** ~60 minutes

---

## Troubleshooting:

**If browser doesn't open automatically:**
- Manually copy the authorization URL shown in terminal
- Paste into your browser
- Login and authorize

**If you get "redirect URI mismatch" error:**
- Check your Xero app configuration at: https://developer.xero.com/app/manage
- Make sure the redirect URI matches what you selected in Step 4 (option 1, 2, or 3)

**If script fails:**
- Make sure you have internet connection
- Check that XERO_CLIENT_ID and XERO_CLIENT_SECRET in `.env` are correct
