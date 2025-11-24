#!/usr/bin/env python3
"""
Generate Xero Authorization URL
================================
Simple script to generate the Xero authorization URL
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import config

# Build authorization URL
redirect_uri = config.XERO_REDIRECT_URI or "https://tria.himeet.ai/api/xero/callback"
client_id = config.XERO_CLIENT_ID

auth_url = (
    f"https://login.xero.com/identity/connect/authorize"
    f"?response_type=code"
    f"&client_id={client_id}"
    f"&redirect_uri={redirect_uri}"
    f"&scope=offline_access accounting.transactions accounting.contacts accounting.settings accounting.attachments"
    f"&state=xero_oauth_state_123"
)

print("=" * 70)
print("XERO AUTHORIZATION URL")
print("=" * 70)
print()
print("Copy this URL and open it in your browser:")
print()
print(auth_url)
print()
print("=" * 70)
print("AFTER AUTHORIZATION:")
print("=" * 70)
print()
print("1. Xero will redirect you to:")
print(f"   {redirect_uri}?code=LONG_CODE_HERE")
print()
print("2. Copy that ENTIRE URL from your browser")
print()
print("3. Run: python3 scripts/exchange_xero_code.py")
print("   And paste the URL when prompted")
print()
