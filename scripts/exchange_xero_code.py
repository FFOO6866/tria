"""
Exchange Xero Authorization Code for Tokens
============================================

Run this script after visiting the authorization URL.
Paste the redirect URL when prompted, and it will get your tokens.
"""

import sys
import requests
from urllib.parse import parse_qs, urlparse

# Your Xero credentials
CLIENT_ID = "9F2E814559754862AB4B0F57CCE85452"
CLIENT_SECRET = "qviHe5YO0oRiVEdkmfnL4TmB4KRan2W5nXfXqpjL4USTGFf8"
REDIRECT_URI = "http://localhost:8080/callback"

print("=" * 70)
print("XERO TOKEN EXCHANGE")
print("=" * 70)
print("\nPaste the redirect URL from your browser:")
print("(It should start with: http://localhost:8080/callback?code=...)")
print()

redirect_url = input("Redirect URL: ").strip()

# Extract authorization code
try:
    parsed = urlparse(redirect_url)
    query_params = parse_qs(parsed.query)

    if 'code' not in query_params:
        print("\n✗ ERROR: No authorization code found in URL")
        print("Make sure you copied the entire URL from the browser")
        sys.exit(1)

    auth_code = query_params['code'][0]
    print(f"\n✓ Authorization code found: {auth_code[:30]}...")

except Exception as e:
    print(f"\n✗ ERROR: Could not parse URL: {e}")
    sys.exit(1)

# Exchange code for tokens
print("\nExchanging code for tokens...")

token_url = "https://identity.xero.com/connect/token"
token_data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": auth_code,
    "redirect_uri": REDIRECT_URI
}

try:
    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    tokens = response.json()

    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']

    print("✓ Tokens received!")

except Exception as e:
    print(f"\n✗ ERROR: Failed to exchange code for tokens")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
    else:
        print(f"Error: {e}")
    sys.exit(1)

# Get tenant ID
print("\nGetting your Xero organization ID...")

connections_url = "https://api.xero.com/connections"
headers = {"Authorization": f"Bearer {access_token}"}

try:
    response = requests.get(connections_url, headers=headers)
    response.raise_for_status()
    connections = response.json()

    if not connections:
        print("\n✗ ERROR: No Xero organizations found")
        sys.exit(1)

    tenant_id = connections[0]['tenantId']
    tenant_name = connections[0]['tenantName']

    print(f"✓ Organization: {tenant_name}")
    print(f"  Tenant ID: {tenant_id}")

except Exception as e:
    print(f"\n✗ ERROR: Failed to get organization details")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text}")
    else:
        print(f"Error: {e}")
    sys.exit(1)

# Display results
print("\n" + "=" * 70)
print("SUCCESS! ADD THESE TO YOUR .ENV FILE")
print("=" * 70)
print("\nReplace lines 23-24 in .env with:")
print("-" * 70)
print(f"XERO_REFRESH_TOKEN={refresh_token}")
print(f"XERO_TENANT_ID={tenant_id}")
print("-" * 70)
print(f"\nOrganization: {tenant_name}")
print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("\n1. Update .env file with the tokens above")
print("2. Test configuration:")
print('   python -c "from src.config import config; print(config.xero_configured)"')
print("\n3. Load demo data:")
print("   python scripts/load_xero_demo_data.py --dry-run")
print("\n" + "=" * 70)
