#!/usr/bin/env python3
"""
Exchange Xero Authorization Code for Tokens
============================================
Exchanges the authorization code from OAuth callback for refresh token and tenant ID
"""

import sys
import json
import base64
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import config

def extract_code_from_url(callback_url: str) -> str:
    """Extract authorization code from callback URL"""
    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)

    if 'code' not in params:
        raise ValueError("No authorization code found in URL")

    return params['code'][0]

def exchange_code_for_tokens(auth_code: str) -> dict:
    """Exchange authorization code for access token, refresh token, and tenant ID"""

    client_id = config.XERO_CLIENT_ID
    client_secret = config.XERO_CLIENT_SECRET
    redirect_uri = config.XERO_REDIRECT_URI or "https://tria.himeet.ai/api/xero/callback"

    # Prepare token request
    token_url = "https://identity.xero.com/connect/token"

    # Create Basic Auth header
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }

    print("Exchanging authorization code for tokens...")
    response = requests.post(token_url, headers=headers, data=data)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        raise Exception(f"Token exchange failed: {response.text}")

    return response.json()

def get_tenant_id(access_token: str) -> str:
    """Get Xero tenant ID using access token"""

    connections_url = "https://api.xero.com/connections"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print("Fetching tenant ID...")
    response = requests.get(connections_url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to get tenant ID: {response.text}")

    connections = response.json()

    if not connections:
        raise Exception("No Xero organizations connected")

    # Use the first organization
    return connections[0]['tenantId'], connections[0]['tenantName']

def main():
    print("=" * 70)
    print("XERO TOKEN EXCHANGE")
    print("=" * 70)
    print()

    # Get authorization code from command line argument or prompt
    if len(sys.argv) > 1:
        callback_url = sys.argv[1]
    else:
        print("Paste the callback URL here:")
        callback_url = input().strip()

    try:
        # Extract code from URL
        auth_code = extract_code_from_url(callback_url)
        print(f"✓ Authorization code extracted")
        print()

        # Exchange code for tokens
        token_response = exchange_code_for_tokens(auth_code)
        print(f"✓ Tokens received")
        print()

        access_token = token_response['access_token']
        refresh_token = token_response['refresh_token']

        # Get tenant ID
        tenant_id, tenant_name = get_tenant_id(access_token)
        print(f"✓ Tenant ID retrieved")
        print()

        # Display results
        print("=" * 70)
        print("SUCCESS! Add these to your .env file:")
        print("=" * 70)
        print()
        print(f"XERO_REFRESH_TOKEN={refresh_token}")
        print(f"XERO_TENANT_ID={tenant_id}")
        print()
        print(f"Organization: {tenant_name}")
        print()
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print()
        print("1. Add the above variables to your .env file")
        print("2. Restart your application: docker-compose restart")
        print("3. Test the Xero integration")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
