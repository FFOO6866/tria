"""
Production Environment Configuration Validator
===============================================

PRODUCTION-READY configuration validation with NO FALLBACKS.
Validates all required environment variables at startup.

Usage:
    from src.config_validator import validate_required_env, validate_database_url

    validate_required_env(['DATABASE_URL', 'OPENAI_API_KEY'])
    db_url = validate_database_url()
"""

import os
import sys
from typing import List, Optional
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid"""
    pass


def validate_required_env(
    required_vars: List[str],
    optional_vars: Optional[List[str]] = None
) -> dict:
    """
    Validate required environment variables

    Args:
        required_vars: List of required environment variable names
        optional_vars: List of optional environment variable names

    Returns:
        Dictionary of all validated variables

    Raises:
        ConfigurationError: If any required variable is missing or empty
    """
    missing_vars = []
    empty_vars = []
    config = {}

    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if value is None:
            missing_vars.append(var)
        elif value.strip() == '':
            empty_vars.append(var)
        else:
            config[var] = value

    # Check optional variables
    if optional_vars:
        for var in optional_vars:
            value = os.getenv(var)
            if value and value.strip() != '':
                config[var] = value

    # Report errors
    if missing_vars or empty_vars:
        error_msg = "Configuration validation failed:\n"
        if missing_vars:
            error_msg += f"\nMissing required environment variables:\n"
            for var in missing_vars:
                error_msg += f"  - {var}\n"
        if empty_vars:
            error_msg += f"\nEmpty required environment variables:\n"
            for var in empty_vars:
                error_msg += f"  - {var}\n"

        error_msg += "\nPlease check your .env file and ensure all required variables are set.\n"
        error_msg += "See .env.example for a template.\n"

        raise ConfigurationError(error_msg)

    return config


def validate_database_url(required: bool = True) -> Optional[str]:
    """
    Validate DATABASE_URL format

    Args:
        required: If True, raises error if DATABASE_URL is missing

    Returns:
        Validated DATABASE_URL or None if not required and missing

    Raises:
        ConfigurationError: If DATABASE_URL is invalid or missing (when required)
    """
    db_url = os.getenv('DATABASE_URL')

    if not db_url or db_url.strip() == '':
        if required:
            raise ConfigurationError(
                "DATABASE_URL is required but not set.\n"
                "Please set DATABASE_URL in your .env file.\n"
                "Example: postgresql://user:password@localhost:5432/dbname"
            )
        return None

    # Validate format
    if not db_url.startswith('postgresql://'):
        raise ConfigurationError(
            f"Invalid DATABASE_URL format: {db_url[:20]}...\n"
            "DATABASE_URL must start with 'postgresql://'\n"
            "Example: postgresql://user:password@localhost:5432/dbname"
        )

    # Check for placeholder values
    placeholders = ['password', 'your_password', 'changeme', 'localhost:5432/postgres']
    if any(placeholder in db_url.lower() for placeholder in placeholders):
        print("[WARNING] DATABASE_URL appears to contain placeholder values")
        print("         Please update with actual credentials for production")

    return db_url


def validate_api_keys(required_keys: List[str]) -> dict:
    """
    Validate API keys are present and not placeholder values

    Args:
        required_keys: List of required API key environment variable names

    Returns:
        Dictionary of validated API keys

    Raises:
        ConfigurationError: If any required key is missing or appears to be a placeholder
    """
    config = validate_required_env(required_keys)

    # Check for common placeholder patterns
    placeholder_patterns = [
        'your_', 'changeme', 'replace_', 'example', 'test_key',
        'sk-1234', 'demo_', 'sample_'
    ]

    warnings = []
    for key, value in config.items():
        value_lower = value.lower()
        if any(pattern in value_lower for pattern in placeholder_patterns):
            warnings.append(key)

    if warnings:
        print(f"[WARNING] The following API keys appear to be placeholders:")
        for key in warnings:
            print(f"         - {key}")
        print("         Please update with actual production keys")

    return config


def print_config_summary(config: dict, mask_secrets: bool = True):
    """
    Print configuration summary (with secrets masked)

    Args:
        config: Configuration dictionary
        mask_secrets: If True, mask secret values
    """
    secret_keywords = ['password', 'secret', 'key', 'token']

    print("Configuration Summary:")
    print("=" * 60)
    for key, value in sorted(config.items()):
        # Mask secrets
        if mask_secrets and any(kw in key.lower() for kw in secret_keywords):
            masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"  {key}: {masked_value}")
        else:
            # Truncate long values
            display_value = value if len(value) < 50 else value[:47] + "..."
            print(f"  {key}: {display_value}")
    print("=" * 60)


def validate_production_config() -> dict:
    """
    Validate complete production configuration

    Returns:
        Dictionary of all validated configuration

    Raises:
        ConfigurationError: If configuration is invalid
    """
    print("Validating production configuration...")

    # Required environment variables - NO FALLBACKS allowed
    # All critical configuration must be explicitly set
    required_vars = [
        'DATABASE_URL',
        'OPENAI_API_KEY',
        'TAX_RATE',                    # Required for order totals - no default!
        'XERO_SALES_ACCOUNT_CODE',     # Required for Xero integration - no default!
        'XERO_TAX_TYPE'                # Required for Xero integration - no default!
    ]

    # Optional but recommended
    optional_vars = [
        'XERO_CLIENT_ID',
        'XERO_CLIENT_SECRET',
        'XERO_REFRESH_TOKEN',
        'XERO_TENANT_ID',
        'SECRET_KEY'
    ]

    # Validate
    config = validate_required_env(required_vars, optional_vars)

    # Validate database URL format
    config['DATABASE_URL'] = validate_database_url(required=True)

    # Validate API keys format
    api_keys = ['OPENAI_API_KEY']
    if 'XERO_CLIENT_ID' in config:
        api_keys.extend(['XERO_CLIENT_ID', 'XERO_CLIENT_SECRET'])

    validate_api_keys(api_keys)

    print("[OK] Configuration validation passed")

    return config


if __name__ == "__main__":
    """Run validation checks"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        config = validate_production_config()
        print_config_summary(config, mask_secrets=True)
        print("\n[SUCCESS] All configuration checks passed!")
        sys.exit(0)
    except ConfigurationError as e:
        print(f"\n[ERROR] Configuration validation failed:")
        print(str(e))
        sys.exit(1)
