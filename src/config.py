"""
Centralized Configuration Module
==================================

Single source of truth for all application configuration.
All environment variables are validated at import time.

Uses existing config_validator.py functions to avoid duplication.

NO FALLBACKS - All required configuration must be explicitly set.

Usage:
    from src.config import config

    database_url = config.DATABASE_URL
    openai_key = config.OPENAI_API_KEY
"""

import os
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Import existing validation functions (reuse instead of duplicate)
from config_validator import (
    validate_required_env,
    validate_database_url,
    ConfigurationError
)

# Load environment from .env file
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class ProductionConfig:
    """
    Production configuration with validation

    All required variables are validated at initialization.
    Optional variables have explicit None defaults.
    """

    def __init__(self):
        """Initialize and validate all configuration"""

        # ====================================================================
        # REQUIRED CONFIGURATION (NO FALLBACKS)
        # ====================================================================
        # Use existing validation functions from config_validator.py

        # Validate required environment variables
        required_vars = [
            'OPENAI_API_KEY',
            'TAX_RATE',
            'XERO_SALES_ACCOUNT_CODE',
            'XERO_TAX_TYPE'
        ]

        optional_vars = [
            'XERO_CLIENT_ID',
            'XERO_CLIENT_SECRET',
            'XERO_REFRESH_TOKEN',
            'XERO_TENANT_ID',
            'SECRET_KEY'
        ]

        # Validate using existing function
        validated_config = validate_required_env(required_vars, optional_vars)

        # Validate DATABASE_URL separately with format checking
        self.DATABASE_URL = validate_database_url(required=True)

        # Set required configuration
        self.OPENAI_API_KEY = validated_config['OPENAI_API_KEY']
        self.TAX_RATE = float(validated_config['TAX_RATE'])
        self.XERO_SALES_ACCOUNT_CODE = validated_config['XERO_SALES_ACCOUNT_CODE']
        self.XERO_TAX_TYPE = validated_config['XERO_TAX_TYPE']

        # Set optional Xero configuration
        self.XERO_CLIENT_ID = validated_config.get('XERO_CLIENT_ID')
        self.XERO_CLIENT_SECRET = validated_config.get('XERO_CLIENT_SECRET')
        self.XERO_REFRESH_TOKEN = validated_config.get('XERO_REFRESH_TOKEN')
        self.XERO_TENANT_ID = validated_config.get('XERO_TENANT_ID')
        self.SECRET_KEY = validated_config.get('SECRET_KEY')

        # ====================================================================
        # OPTIONAL CONFIGURATION WITH DEFAULTS
        # ====================================================================

        # OpenAI settings
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
        self.OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
        self.OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))

        # File paths with defaults
        self.MASTER_INVENTORY_FILE = Path(os.getenv(
            'MASTER_INVENTORY_FILE',
            './data/inventory/Master_Inventory_File_2025.xlsx'
        ))
        self.DO_TEMPLATE_FILE = Path(os.getenv(
            'DO_TEMPLATE_FILE',
            './data/templates/DO_Template.xlsx'
        ))

        # API server settings
        self.API_PORT = int(os.getenv('API_PORT', '8000'))
        self.ENHANCED_API_PORT = int(os.getenv('ENHANCED_API_PORT', '8001'))
        self.API_HOST = os.getenv('API_HOST', '0.0.0.0')

        # Logging
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # Validate critical file paths exist (if specified)
        self._validate_file_paths()

        logger.info("Configuration validated successfully")

    def _validate_file_paths(self):
        """Validate that critical file paths exist"""

        # Only validate if paths are explicitly set (not using defaults)
        if os.getenv('MASTER_INVENTORY_FILE'):
            if not self.MASTER_INVENTORY_FILE.exists():
                logger.warning(
                    f"MASTER_INVENTORY_FILE not found: {self.MASTER_INVENTORY_FILE}"
                )

        if os.getenv('DO_TEMPLATE_FILE'):
            if not self.DO_TEMPLATE_FILE.exists():
                logger.warning(
                    f"DO_TEMPLATE_FILE not found: {self.DO_TEMPLATE_FILE}"
                )

    @property
    def xero_configured(self) -> bool:
        """Check if Xero OAuth is fully configured"""
        return all([
            self.XERO_CLIENT_ID,
            self.XERO_CLIENT_SECRET,
            self.XERO_REFRESH_TOKEN,
            self.XERO_TENANT_ID
        ])

    def get_database_url(self) -> str:
        """Get validated database URL"""
        return self.DATABASE_URL

    def get_openai_config(self) -> dict:
        """Get OpenAI configuration as dictionary"""
        return {
            'api_key': self.OPENAI_API_KEY,
            'model': self.OPENAI_MODEL,
            'temperature': self.OPENAI_TEMPERATURE,
            'max_tokens': self.OPENAI_MAX_TOKENS
        }

    def __repr__(self) -> str:
        """String representation (masks secrets)"""
        return (
            f"ProductionConfig("
            f"DATABASE_URL={self.DATABASE_URL[:30]}..., "
            f"OPENAI_MODEL={self.OPENAI_MODEL}, "
            f"XERO_CONFIGURED={self.xero_configured}"
            f")"
        )


# ============================================================================
# GLOBAL CONFIG INSTANCE
# ============================================================================
# Initialize configuration at module import
# This ensures all configuration is validated before any code runs

try:
    config = ProductionConfig()
except (ValueError, ConfigurationError) as e:
    logger.error(f"Configuration validation failed: {e}")
    raise RuntimeError(
        "Failed to initialize application configuration. "
        "Please check your .env file and ensure all required variables are set. "
        "See .env.example for a template."
    ) from e
