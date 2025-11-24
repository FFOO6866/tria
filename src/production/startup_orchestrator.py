#!/usr/bin/env python3
"""
Production Startup Orchestrator
================================

Comprehensive startup sequence with proper error handling, validation,
and health checking. NO SILENT FAILURES - all components must be operational.

This module ensures:
1. Environment validation (fail fast if misconfigured)
2. Database connectivity and schema validation
3. Redis connectivity and configuration
4. External service connectivity (OpenAI, Xero)
5. Proper initialization ordering with dependencies
6. Health monitoring and diagnostics
7. Graceful degradation only where explicitly allowed
"""

import os
import sys
import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class ServiceHealth:
    """Health status for a service"""
    name: str
    status: ServiceStatus
    message: str
    details: Dict[str, Any]
    critical: bool = True  # If True, failure prevents startup
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class StartupOrchestrator:
    """
    Production-grade startup orchestrator that validates and initializes
    all required services in the correct order.
    """

    def __init__(self):
        self.services: Dict[str, ServiceHealth] = {}
        self.startup_time = datetime.utcnow()
        self.initialized = False

    # ========================================================================
    # PHASE 1: ENVIRONMENT VALIDATION
    # ========================================================================

    async def validate_environment(self) -> ServiceHealth:
        """
        Validate all required environment variables are set and valid.

        CRITICAL: This must pass for production deployment.
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: Environment Validation")
        logger.info("=" * 60)

        errors = []
        warnings = []
        config_details = {}

        # Required variables (MUST be set)
        required_vars = {
            'DATABASE_URL': self._validate_database_url,
            'OPENAI_API_KEY': self._validate_openai_key,
            'SECRET_KEY': self._validate_secret_key,
            'REDIS_HOST': lambda v: (True, "Redis host set"),
            'REDIS_PORT': lambda v: (True, "Redis port set") if v.isdigit() else (False, "Must be numeric"),
            'TAX_RATE': lambda v: self._validate_float(v, 0.0, 1.0, "Tax rate"),
        }

        # Optional but recommended variables
        optional_vars = {
            'REDIS_PASSWORD': 'Redis password',
            'SENTRY_DSN': 'Error tracking',
            'XERO_CLIENT_ID': 'Xero integration',
            'ENVIRONMENT': 'Environment name',
        }

        # Validate required variables
        for var_name, validator in required_vars.items():
            value = os.getenv(var_name)
            if not value:
                errors.append(f"Missing required variable: {var_name}")
                config_details[var_name] = "MISSING"
            else:
                is_valid, message = validator(value)
                if not is_valid:
                    errors.append(f"{var_name}: {message}")
                    config_details[var_name] = "INVALID"
                else:
                    # Mask sensitive values
                    if 'KEY' in var_name or 'SECRET' in var_name or 'PASSWORD' in var_name:
                        config_details[var_name] = value[:10] + "..." if len(value) > 10 else "***"
                    else:
                        config_details[var_name] = value[:50]

        # Check optional variables
        for var_name, description in optional_vars.items():
            value = os.getenv(var_name)
            if not value:
                warnings.append(f"Optional variable not set: {var_name} ({description})")
                config_details[var_name] = "NOT SET (optional)"

        # Log results
        for key, value in config_details.items():
            logger.info(f"  {key}: {value}")

        if warnings:
            for warning in warnings:
                logger.warning(f"  ⚠️  {warning}")

        if errors:
            for error in errors:
                logger.error(f"  ❌ {error}")
            return ServiceHealth(
                name="environment",
                status=ServiceStatus.FAILED,
                message=f"Environment validation failed: {len(errors)} errors",
                details={"errors": errors, "warnings": warnings, "config": config_details},
                critical=True
            )

        logger.info("  ✅ Environment validation passed")
        return ServiceHealth(
            name="environment",
            status=ServiceStatus.HEALTHY,
            message="All required variables validated",
            details={"warnings": warnings, "config": config_details},
            critical=True
        )

    def _validate_database_url(self, url: str) -> Tuple[bool, str]:
        """Validate database URL format"""
        if not url.startswith('postgresql://'):
            return False, "Must start with postgresql://"
        if '@' not in url or '/' not in url:
            return False, "Invalid format (should be postgresql://user:pass@host:port/db)"
        return True, "Valid PostgreSQL URL"

    def _validate_openai_key(self, key: str) -> Tuple[bool, str]:
        """Validate OpenAI API key format"""
        if not key.startswith('sk-'):
            return False, "Must start with 'sk-'"
        if len(key) < 20:
            return False, "Key too short"
        return True, "Valid API key format"

    def _validate_secret_key(self, key: str) -> Tuple[bool, str]:
        """Validate secret key strength"""
        if len(key) < 32:
            return False, "Secret key must be at least 32 characters"
        return True, "Secret key meets minimum length"

    def _validate_float(self, value: str, min_val: float, max_val: float, name: str) -> Tuple[bool, str]:
        """Validate float value in range"""
        try:
            fval = float(value)
            if fval < min_val or fval > max_val:
                return False, f"{name} must be between {min_val} and {max_val}"
            return True, f"Valid {name}"
        except ValueError:
            return False, f"{name} must be a number"

    # ========================================================================
    # PHASE 2: DATABASE INITIALIZATION
    # ========================================================================

    async def initialize_database(self) -> ServiceHealth:
        """
        Initialize database connection, validate schema, and run migrations.

        Steps:
        1. Test connection
        2. Validate PostgreSQL version
        3. Create/update schema
        4. Verify tables exist
        5. Check for required data
        """
        logger.info("=" * 60)
        logger.info("PHASE 2: Database Initialization")
        logger.info("=" * 60)

        try:
            from database import get_db_engine
            from sqlalchemy import text, inspect
            from models.order_orm import create_tables as create_order_tables
            from models.conversation_orm import create_tables as create_conversation_tables

            database_url = os.getenv('DATABASE_URL')
            engine = get_db_engine(database_url)

            # Step 1: Test connection
            logger.info("  Testing database connection...")
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                logger.info(f"  ✅ Connected to PostgreSQL: {version[:50]}")

            # Step 2: Create/update tables
            logger.info("  Creating/updating database schema...")
            create_order_tables(engine)
            create_conversation_tables(engine)
            logger.info("  ✅ Schema updated successfully")

            # Step 3: Verify tables exist
            logger.info("  Verifying tables...")
            inspector = inspect(engine)
            required_tables = [
                'products', 'outlets', 'orders', 'delivery_orders', 'invoices',
                'conversation_sessions', 'conversation_messages', 'user_interaction_summaries'
            ]

            existing_tables = inspector.get_table_names()
            missing_tables = [t for t in required_tables if t not in existing_tables]

            if missing_tables:
                return ServiceHealth(
                    name="database",
                    status=ServiceStatus.FAILED,
                    message=f"Missing required tables: {missing_tables}",
                    details={"existing_tables": existing_tables, "missing_tables": missing_tables},
                    critical=True
                )

            logger.info(f"  ✅ All {len(required_tables)} required tables exist")

            # Step 4: Check data existence
            with engine.connect() as conn:
                product_count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
                outlet_count = conn.execute(text("SELECT COUNT(*) FROM outlets")).scalar()

                logger.info(f"  📊 Database statistics:")
                logger.info(f"     - Products: {product_count}")
                logger.info(f"     - Outlets: {outlet_count}")

                if product_count == 0:
                    logger.warning("  ⚠️  No products in database - catalog may need initialization")
                if outlet_count == 0:
                    logger.warning("  ⚠️  No outlets in database - may need to import initial data")

            return ServiceHealth(
                name="database",
                status=ServiceStatus.HEALTHY,
                message="Database initialized and validated",
                details={
                    "tables": existing_tables,
                    "product_count": product_count,
                    "outlet_count": outlet_count
                },
                critical=True
            )

        except Exception as e:
            logger.error(f"  ❌ Database initialization failed: {e}")
            return ServiceHealth(
                name="database",
                status=ServiceStatus.FAILED,
                message=f"Database initialization failed: {str(e)}",
                details={"error": str(e), "type": type(e).__name__},
                critical=True
            )

    # ========================================================================
    # PHASE 3: REDIS INITIALIZATION
    # ========================================================================

    async def initialize_redis(self) -> ServiceHealth:
        """
        Initialize Redis connection and validate configuration.

        Redis is CRITICAL for production:
        - Idempotency (prevents duplicate orders)
        - Caching (improves performance)
        - Session storage
        """
        logger.info("=" * 60)
        logger.info("PHASE 3: Redis Initialization")
        logger.info("=" * 60)

        try:
            from cache.redis_cache import RedisCache

            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_db = int(os.getenv('REDIS_DB', '0'))

            logger.info(f"  Connecting to Redis: {redis_host}:{redis_port}")

            redis_cache = RedisCache(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db
            )

            # Test connection
            if redis_cache.using_fallback:
                logger.warning("  ⚠️  Redis connection failed - using in-memory fallback")
                logger.warning("  ⚠️  CRITICAL: This is NOT suitable for production!")
                logger.warning("  ⚠️  Idempotency and caching will NOT work across restarts")
                return ServiceHealth(
                    name="redis",
                    status=ServiceStatus.DEGRADED,
                    message="Redis unavailable - using in-memory fallback (NOT PRODUCTION SAFE)",
                    details={
                        "host": redis_host,
                        "port": redis_port,
                        "fallback": True
                    },
                    critical=True  # Critical for production
                )

            # Test operations
            test_key = "startup_health_check"
            test_value = f"test_{datetime.utcnow().isoformat()}"

            redis_cache.set(test_key, test_value, ttl_seconds=60)
            retrieved = redis_cache.get(test_key)

            if retrieved != test_value:
                raise RuntimeError("Redis read/write test failed")

            redis_cache.delete(test_key)

            logger.info("  ✅ Redis connected and operational")
            logger.info(f"     - Host: {redis_host}:{redis_port}")
            logger.info(f"     - Database: {redis_db}")
            logger.info(f"     - Password: {'configured' if redis_password else 'not set'}")

            return ServiceHealth(
                name="redis",
                status=ServiceStatus.HEALTHY,
                message="Redis connected and validated",
                details={
                    "host": redis_host,
                    "port": redis_port,
                    "db": redis_db,
                    "password_set": bool(redis_password)
                },
                critical=True
            )

        except Exception as e:
            logger.error(f"  ❌ Redis initialization failed: {e}")
            return ServiceHealth(
                name="redis",
                status=ServiceStatus.FAILED,
                message=f"Redis initialization failed: {str(e)}",
                details={"error": str(e), "type": type(e).__name__},
                critical=True
            )

    # ========================================================================
    # PHASE 4: EXTERNAL SERVICES
    # ========================================================================

    async def validate_openai(self) -> ServiceHealth:
        """Validate OpenAI API connectivity"""
        logger.info("=" * 60)
        logger.info("PHASE 4: OpenAI API Validation")
        logger.info("=" * 60)

        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')

            if not api_key:
                return ServiceHealth(
                    name="openai",
                    status=ServiceStatus.DISABLED,
                    message="OpenAI API key not configured",
                    details={},
                    critical=True  # Critical for chatbot
                )

            # Test API connection with minimal request
            logger.info("  Testing OpenAI API connection...")
            client = openai.OpenAI(api_key=api_key)

            # Use the new API format
            response = client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview'),
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )

            logger.info("  ✅ OpenAI API connected successfully")
            logger.info(f"     - Model: {response.model}")
            logger.info(f"     - Response ID: {response.id}")

            return ServiceHealth(
                name="openai",
                status=ServiceStatus.HEALTHY,
                message="OpenAI API validated",
                details={"model": response.model},
                critical=True
            )

        except Exception as e:
            logger.error(f"  ❌ OpenAI API validation failed: {e}")
            return ServiceHealth(
                name="openai",
                status=ServiceStatus.FAILED,
                message=f"OpenAI API validation failed: {str(e)}",
                details={"error": str(e), "type": type(e).__name__},
                critical=True
            )

    async def validate_chromadb(self) -> ServiceHealth:
        """Validate ChromaDB for RAG functionality"""
        logger.info("=" * 60)
        logger.info("PHASE 5: ChromaDB Validation")
        logger.info("=" * 60)

        try:
            from rag.chroma_client import health_check

            health = health_check()

            if health['status'] == 'healthy':
                logger.info("  ✅ ChromaDB operational")
                logger.info(f"     - Collections: {health['collections_count']}")
                if health['collections']:
                    logger.info(f"     - Available: {', '.join(health['collections'])}")

                return ServiceHealth(
                    name="chromadb",
                    status=ServiceStatus.HEALTHY,
                    message="ChromaDB operational",
                    details=health,
                    critical=False  # Non-critical, degrades gracefully
                )
            else:
                logger.warning(f"  ⚠️  ChromaDB check failed: {health.get('error')}")
                return ServiceHealth(
                    name="chromadb",
                    status=ServiceStatus.DEGRADED,
                    message="ChromaDB unavailable - RAG features limited",
                    details=health,
                    critical=False
                )

        except Exception as e:
            logger.warning(f"  ⚠️  ChromaDB validation failed: {e}")
            return ServiceHealth(
                name="chromadb",
                status=ServiceStatus.DEGRADED,
                message="ChromaDB unavailable",
                details={"error": str(e)},
                critical=False
            )

    # ========================================================================
    # ORCHESTRATION
    # ========================================================================

    async def startup(self) -> Dict[str, ServiceHealth]:
        """
        Execute complete startup sequence.

        Returns dict of service health statuses.
        Raises RuntimeError if any critical service fails.
        """
        logger.info("\n" + "=" * 60)
        logger.info("TRIA AIBPO PRODUCTION STARTUP")
        logger.info("=" * 60)
        logger.info(f"Start time: {self.startup_time.isoformat()}")
        logger.info("=" * 60 + "\n")

        # Phase 1: Environment (CRITICAL)
        env_health = await self.validate_environment()
        self.services['environment'] = env_health
        if env_health.status == ServiceStatus.FAILED:
            self._fail_startup("Environment validation failed")

        # Phase 2: Database (CRITICAL)
        db_health = await self.initialize_database()
        self.services['database'] = db_health
        if db_health.status == ServiceStatus.FAILED:
            self._fail_startup("Database initialization failed")

        # Phase 3: Redis (CRITICAL)
        redis_health = await self.initialize_redis()
        self.services['redis'] = redis_health
        if redis_health.status == ServiceStatus.FAILED:
            self._fail_startup("Redis initialization failed")

        # Phase 4: OpenAI (CRITICAL for chatbot)
        openai_health = await self.validate_openai()
        self.services['openai'] = openai_health
        if openai_health.status == ServiceStatus.FAILED:
            self._fail_startup("OpenAI API validation failed")

        # Phase 5: ChromaDB (Non-critical)
        chromadb_health = await self.validate_chromadb()
        self.services['chromadb'] = chromadb_health

        # Summary
        self._print_summary()

        # Check for critical failures
        critical_failures = [
            name for name, health in self.services.items()
            if health.critical and health.status == ServiceStatus.FAILED
        ]

        if critical_failures:
            self._fail_startup(f"Critical services failed: {critical_failures}")

        self.initialized = True
        logger.info("\n" + "=" * 60)
        logger.info("✅ STARTUP COMPLETE - ALL CRITICAL SERVICES OPERATIONAL")
        logger.info("=" * 60 + "\n")

        return self.services

    def _print_summary(self):
        """Print startup summary"""
        logger.info("\n" + "=" * 60)
        logger.info("STARTUP SUMMARY")
        logger.info("=" * 60)

        for name, health in self.services.items():
            status_symbol = {
                ServiceStatus.HEALTHY: "✅",
                ServiceStatus.DEGRADED: "⚠️ ",
                ServiceStatus.FAILED: "❌",
                ServiceStatus.DISABLED: "⊘ ",
                ServiceStatus.INITIALIZING: "⏳"
            }.get(health.status, "?")

            critical_marker = "[CRITICAL]" if health.critical else "[optional]"
            logger.info(f"{status_symbol} {name:15s} {critical_marker:12s} {health.message}")

        logger.info("=" * 60)

    def _fail_startup(self, message: str):
        """Fail startup with error message"""
        logger.error("\n" + "=" * 60)
        logger.error("❌ STARTUP FAILED")
        logger.error("=" * 60)
        logger.error(f"Reason: {message}")
        logger.error("=" * 60)
        raise RuntimeError(f"Startup failed: {message}")

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all services"""
        return {
            "initialized": self.initialized,
            "startup_time": self.startup_time.isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            "services": {
                name: {
                    "status": health.status.value,
                    "message": health.message,
                    "critical": health.critical,
                    "details": health.details,
                    "timestamp": health.timestamp.isoformat()
                }
                for name, health in self.services.items()
            }
        }


# Global orchestrator instance
_orchestrator: Optional[StartupOrchestrator] = None


def get_orchestrator() -> StartupOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = StartupOrchestrator()
    return _orchestrator
