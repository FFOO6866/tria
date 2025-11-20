#!/usr/bin/env python3
"""
Clear Redis Cache and Re-run Comprehensive Chat Test
=====================================================

This script:
1. Clears the Redis chat cache
2. Re-runs the comprehensive chat test to verify fixes work

Use this when you've made fixes and want to test with fresh responses
(not cached responses from before the fix).
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from cache.chat_response_cache import reset_chat_cache

if __name__ == "__main__":
    print("=" * 70)
    print("CLEARING REDIS CACHE")
    print("=" * 70)
    print("\nThis will clear all cached chat responses...")
    print("Use this after making fixes to test with fresh responses.\n")

    try:
        reset_chat_cache()
        print("[OK] Redis chat cache cleared successfully!")
        print("\nNow run: python scripts/test_comprehensive_chat.py")
        print("This will generate fresh responses with your fixes applied.\n")
    except Exception as e:
        print(f"[ERROR] Failed to clear cache: {e}")
        sys.exit(1)
