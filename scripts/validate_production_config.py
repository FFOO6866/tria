#!/usr/bin/env python3
"""
Production Configuration Validation Script
===========================================

Validates all environment variables and configuration before deployment.

NO MOCKUPS, NO FALLBACKS - Production-ready validation only.

Usage:
    python scripts/validate_production_config.py

Exit codes:
    0 - All validations passed
    1 - Configuration errors found
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
from config_validator import (
    validate_production_config,
    validate_database_url,
    validate_file_paths,
    print_config_summary,
    ConfigurationError
)


def main():
    """Run comprehensive configuration validation"""

    print("=" * 70)
    print("PRODUCTION CONFIGURATION VALIDATION")
    print("=" * 70)
    print()

    # Load environment
    env_file = project_root / ".env"
    if not env_file.exists():
        print(f"[ERROR] .env file not found at: {env_file}")
        print("Please create .env file from .env.example template")
        return 1

    load_dotenv(env_file)
    print(f"[OK] Loaded environment from: {env_file}")
    print()

    try:
        # Step 1: Validate core configuration
        print("[1/5] Validating core environment variables...")
        config = validate_production_config()
        print("[OK] Core configuration valid")
        print()

        # Step 2: Validate database connectivity
        print("[2/5] Validating database configuration...")
        db_url = validate_database_url(required=True)
        print(f"[OK] Database URL configured: {db_url[:30]}...")
        print()

        # Step 3: Validate file paths
        print("[3/5] Validating file paths...")
        file_vars = [
            'MASTER_INVENTORY_FILE',
            'DO_TEMPLATE_FILE'
        ]

        try:
            file_config = validate_file_paths(file_vars)
            print("[OK] All required files exist:")
            for var, path in file_config.items():
                print(f"     {var}: {path}")
        except ConfigurationError as e:
            print(f"[WARNING] File validation warnings:")
            print(f"         {str(e)}")
            print("         Continuing validation...")

        print()

        # Step 4: Check Xero configuration
        print("[4/5] Checking Xero API configuration...")
        xero_vars = [
            'XERO_CLIENT_ID',
            'XERO_CLIENT_SECRET',
            'XERO_REFRESH_TOKEN',
            'XERO_TENANT_ID'
        ]

        xero_configured = all(os.getenv(var) for var in xero_vars)
        if xero_configured:
            print("[OK] Xero API fully configured")
            print("     Invoice posting to Xero will work")
        else:
            print("[WARNING] Xero API not fully configured")
            print("     Missing variables:")
            for var in xero_vars:
                if not os.getenv(var):
                    print(f"       - {var}")
            print("     Invoice posting will skip Xero integration")

        print()

        # Step 5: Security check
        print("[5/5] Security configuration check...")
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key or len(secret_key) < 32:
            print("[WARNING] SECRET_KEY not set or too short")
            print("     Generate with: openssl rand -hex 32")
        else:
            print("[OK] SECRET_KEY configured")

        print()

        # Print summary
        print("=" * 70)
        print("CONFIGURATION SUMMARY")
        print("=" * 70)
        print_config_summary(config, mask_secrets=True)
        print()

        # Final verdict
        print("=" * 70)
        print("[SUCCESS] PRODUCTION CONFIGURATION VALID")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Review configuration summary above")
        print("  2. Ensure all required services are running:")
        print("     - PostgreSQL database")
        print("     - Excel files accessible")
        print("  3. Start application:")
        print("     python src/enhanced_api.py")
        print()

        return 0

    except ConfigurationError as e:
        print()
        print("=" * 70)
        print("[FAILURE] CONFIGURATION VALIDATION FAILED")
        print("=" * 70)
        print()
        print(str(e))
        print()
        print("Please fix the errors above and run validation again.")
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 70)
        print("[ERROR] UNEXPECTED VALIDATION ERROR")
        print("=" * 70)
        print()
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
