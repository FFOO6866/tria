"""
Xero OAuth2.0 Token Helper
==========================

This script helps you get the REFRESH_TOKEN and TENANT_ID for Xero integration.

It will:
1. Generate an authorization URL
2. Wait for you to authorize in your browser
3. Exchange the authorization code for tokens
4. Get your Xero organization (tenant) ID
5. Display the values to add to your .env file

Requirements:
- pip install authlib requests
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import webbrowser
from urllib.parse import parse_qs, urlparse
import requests

# Your Xero app credentials (from .env)
CLIENT_ID = "9F2E814559754862AB4B0F57CCE85452"
CLIENT_SECRET = "qviHe5YO0oRiVEdkmfnL4TmB4KRan2W5nXfXqpjL4USTGFf8"

# Common redirect URIs - you may need to adjust based on your Xero app settings
POSSIBLE_REDIRECT_URIS = [
    "http://localhost:8080/callback",
    "http://localhost:8000/callback",
    "https://oauth.pstmn.io/v1/callback"  # Postman redirect URI
]

print("=" * 70)
print("XERO OAUTH2.0 TOKEN HELPER")
print("=" * 70)
print("\nThis script will help you get your Xero REFRESH_TOKEN and TENANT_ID")
print("\nStep 1: Choose your redirect URI")
print("-" * 70)

for i, uri in enumerate(POSSIBLE_REDIRECT_URIS, 1):
    print(f"{i}. {uri}")

print("\nWhich redirect URI did you configure in your Xero app?")
print("(Check at: https://developer.xero.com/app/manage)")

choice = input("\nEnter number (1-3) or paste custom URI: ").strip()

if choice.isdigit() and 1 <= int(choice) <= len(POSSIBLE_REDIRECT_URIS):
    REDIRECT_URI = POSSIBLE_REDIRECT_URIS[int(choice) - 1]
else:
    REDIRECT_URI = choice

print(f"\nUsing redirect URI: {REDIRECT_URI}")

# Build authorization URL
auth_params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": "offline_access accounting.transactions accounting.contacts accounting.settings accounting.attachments",
    "state": "xero_oauth_state_123"
}

auth_url = "https://login.xero.com/identity/connect/authorize?" + "&".join([f"{k}={v}" for k, v in auth_params.items()])

print("\n" + "=" * 70)
print("Step 2: Authorize the Xero app")
print("=" * 70)
print("\nI will now open your browser to this URL:")
print(auth_url)
print("\nIf the browser doesn't open automatically, copy and paste the URL above.")
print("\nIn your browser:")
print("  1. Log in to your Xero account (if not already logged in)")
print("  2. Select your Xero organization")
print("  3. Click 'Authorize' to grant access")
print("  4. You will be redirected to a URL starting with your redirect URI")
print(f"     Example: {REDIRECT_URI}?code=...")

input("\nPress ENTER to open browser...")

# Try to open browser
try:
    webbrowser.open(auth_url)
    print("\n✓ Browser opened")
except:
    print("\n✗ Could not open browser automatically")
    print("Please copy the URL above and paste it in your browser")

print("\n" + "=" * 70)
print("Step 3: Copy the redirect URL")
print("=" * 70)
print("\nAfter authorizing, you will be redirected to a URL that looks like:")
print(f"{REDIRECT_URI}?code=LONG_CODE_HERE&scope=...&state=...")
print("\nThe page may show an error (if localhost is not running) - that's OK!")
print("We only need the URL from the address bar.")

redirect_response = input("\nPaste the ENTIRE redirect URL here: ").strip()

# Extract authorization code
parsed = urlparse(redirect_response)
query_params = parse_qs(parsed.query)

if 'code' not in query_params:
    print("\n✗ ERROR: No authorization code found in URL")
    print("Make sure you copied the entire URL from the browser address bar")
    sys.exit(1)

auth_code = query_params['code'][0]
print(f"\n✓ Authorization code extracted: {auth_code[:20]}...")

# Exchange code for tokens
print("\n" + "=" * 70)
print("Step 4: Exchange code for tokens")
print("=" * 70)

token_url = "https://identity.xero.com/connect/token"
token_data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": auth_code,
    "redirect_uri": REDIRECT_URI
}

print("\nRequesting tokens from Xero...")

try:
    response = requests.post(token_url, data=token_data)
    response.raise_for_status()
    tokens = response.json()

    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']

    print("✓ Tokens received successfully!")

except requests.exceptions.RequestException as e:
    print(f"\n✗ ERROR: Failed to get tokens")
    print(f"Response: {e.response.text if hasattr(e, 'response') else str(e)}")
    sys.exit(1)

# Get tenant ID
print("\n" + "=" * 70)
print("Step 5: Get your Xero organization (tenant) ID")
print("=" * 70)

connections_url = "https://api.xero.com/connections"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

print("\nRequesting organization details...")

try:
    response = requests.get(connections_url, headers=headers)
    response.raise_for_status()
    connections = response.json()

    if not connections:
        print("\n✗ ERROR: No Xero organizations found")
        print("Make sure you selected an organization during authorization")
        sys.exit(1)

    tenant_id = connections[0]['tenantId']
    tenant_name = connections[0]['tenantName']
    tenant_type = connections[0]['tenantType']

    print(f"✓ Organization found: {tenant_name}")
    print(f"  Type: {tenant_type}")
    print(f"  Tenant ID: {tenant_id}")

except requests.exceptions.RequestException as e:
    print(f"\n✗ ERROR: Failed to get organization details")
    print(f"Response: {e.response.text if hasattr(e, 'response') else str(e)}")
    sys.exit(1)

# Display results
print("\n" + "=" * 70)
print("SUCCESS! HERE ARE YOUR XERO CREDENTIALS")
print("=" * 70)

print("\nAdd these lines to your .env file (replace lines 23-24):")
print("-" * 70)
print(f"XERO_REFRESH_TOKEN={refresh_token}")
print(f"XERO_TENANT_ID={tenant_id}")
print("-" * 70)

print(f"\nYour Xero organization: {tenant_name}")
print(f"Organization type: {tenant_type}")

print("\n" + "=" * 70)
print("NEXT STEPS")
print("=" * 70)
print("\n1. Copy the two lines above into your .env file")
print("2. Uncomment lines 23-24 (remove the # at the beginning)")
print("3. Replace the placeholder values with the actual tokens")
print("\n4. Test the configuration:")
print("   python -c \"from src.config import config; print(f'Xero configured: {config.xero_configured}')\"")
print("\n5. Load demo data to Xero:")
print("   python scripts/load_xero_demo_data.py --dry-run")
print("\n6. Start the backend and test the workflow!")

print("\n" + "=" * 70)
print("IMPORTANT NOTES")
print("=" * 70)
print("\n- Refresh token expires after 60 days of non-use")
print("- Access token expires after 30 minutes (auto-refreshed by the integration)")
print("- Keep your tokens secure - never commit them to git")
print("- If you need to re-authorize, just run this script again")

print("\n" + "=" * 70)
