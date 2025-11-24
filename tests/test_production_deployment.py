#!/usr/bin/env python3
"""
Production Deployment Tests
============================

Comprehensive test suite for validating production deployment.

Tests:
- Environment configuration
- Database connectivity and schema
- Redis connectivity
- API endpoint functionality
- Health checks
- Error handling
- Performance baselines
"""

import os
import sys
import time
import pytest
import asyncio
import requests
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestEnvironmentConfiguration:
    """Test environment configuration validation"""

    def test_required_variables_set(self):
        """Verify all required environment variables are set"""
        required_vars = [
            'DATABASE_URL',
            'OPENAI_API_KEY',
            'SECRET_KEY',
            'REDIS_HOST',
            'REDIS_PORT',
            'TAX_RATE'
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        assert not missing, f"Missing required variables: {missing}"

    def test_database_url_format(self):
        """Verify DATABASE_URL has correct format"""
        db_url = os.getenv('DATABASE_URL')
        assert db_url, "DATABASE_URL not set"
        assert db_url.startswith('postgresql://'), "DATABASE_URL must start with postgresql://"
        assert '@' in db_url, "DATABASE_URL must contain @ for credentials"
        assert '/' in db_url.split('@')[1], "DATABASE_URL must contain database name"

    def test_openai_key_format(self):
        """Verify OPENAI_API_KEY has correct format"""
        api_key = os.getenv('OPENAI_API_KEY')
        assert api_key, "OPENAI_API_KEY not set"
        assert api_key.startswith('sk-'), "OPENAI_API_KEY must start with sk-"
        assert len(api_key) > 20, "OPENAI_API_KEY seems too short"

    def test_secret_key_strength(self):
        """Verify SECRET_KEY meets minimum strength"""
        secret_key = os.getenv('SECRET_KEY')
        assert secret_key, "SECRET_KEY not set"
        assert len(secret_key) >= 32, "SECRET_KEY must be at least 32 characters"

    def test_redis_configuration(self):
        """Verify Redis configuration"""
        redis_host = os.getenv('REDIS_HOST')
        redis_port = os.getenv('REDIS_PORT')

        assert redis_host, "REDIS_HOST not set"
        assert redis_port, "REDIS_PORT not set"
        assert redis_port.isdigit(), "REDIS_PORT must be numeric"


class TestDatabaseConnectivity:
    """Test database connectivity and schema"""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test database connection"""
        from database import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_required_tables_exist(self):
        """Verify all required tables exist"""
        from database import get_db_engine
        from sqlalchemy import inspect

        engine = get_db_engine()
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        required_tables = [
            'products',
            'outlets',
            'orders',
            'delivery_orders',
            'invoices',
            'conversation_sessions',
            'conversation_messages',
            'user_interaction_summaries'
        ]

        missing = [t for t in required_tables if t not in existing_tables]
        assert not missing, f"Missing required tables: {missing}"

    @pytest.mark.asyncio
    async def test_connection_pool(self):
        """Test database connection pooling"""
        from database import get_db_engine

        engine = get_db_engine()
        pool = engine.pool

        # Verify pool is configured
        assert pool.size() > 0, "Connection pool not configured"
        assert pool._max_overflow >= 0, "Pool max overflow not set"


class TestRedisConnectivity:
    """Test Redis connectivity"""

    def test_redis_connection(self):
        """Test Redis connection"""
        from cache.redis_cache import RedisCache

        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_password = os.getenv('REDIS_PASSWORD')

        redis_cache = RedisCache(
            host=redis_host,
            port=redis_port,
            password=redis_password
        )

        assert not redis_cache.using_fallback, "Redis connection failed (using fallback)"

    def test_redis_read_write(self):
        """Test Redis read/write operations"""
        from cache.redis_cache import RedisCache
        import time

        redis_cache = RedisCache()
        test_key = f"test_key_{time.time()}"
        test_value = f"test_value_{time.time()}"

        # Write
        redis_cache.set(test_key, test_value, ttl_seconds=60)

        # Read
        retrieved = redis_cache.get(test_key)
        assert retrieved == test_value, "Redis read/write test failed"

        # Cleanup
        redis_cache.delete(test_key)


class TestAPIEndpoints:
    """Test API endpoint functionality"""

    BASE_URL = "http://localhost:8003"  # Backend direct

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200, "Health endpoint returned non-200 status"

        data = response.json()
        assert data.get('status') in ['healthy', 'degraded'], "Invalid health status"

    def test_health_endpoint_details(self):
        """Test health endpoint returns service details"""
        response = requests.get(f"{self.BASE_URL}/health")
        data = response.json()

        assert 'services' in data, "Health response missing services info"
        assert 'database' in data['services'], "Health response missing database info"
        assert 'redis' in data['services'], "Health response missing Redis info"

    def test_chatbot_endpoint(self):
        """Test chatbot endpoint"""
        payload = {
            "message": "test",
            "user_id": "pytest_user"
        }
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": f"pytest_{int(time.time() * 1000)}"
        }

        response = requests.post(
            f"{self.BASE_URL}/api/chatbot",
            json=payload,
            headers=headers
        )

        assert response.status_code == 200, f"Chatbot endpoint returned {response.status_code}"

        data = response.json()
        assert data.get('success') is not None, "Chatbot response missing success field"
        assert 'message' in data, "Chatbot response missing message field"


class TestStartupOrchestrator:
    """Test startup orchestrator"""

    @pytest.mark.asyncio
    async def test_environment_validation(self):
        """Test environment validation"""
        from production.startup_orchestrator import StartupOrchestrator

        orchestrator = StartupOrchestrator()
        health = await orchestrator.validate_environment()

        assert health.status.value in ['healthy', 'degraded'], f"Environment validation failed: {health.message}"

    @pytest.mark.asyncio
    async def test_database_initialization(self):
        """Test database initialization"""
        from production.startup_orchestrator import StartupOrchestrator

        orchestrator = StartupOrchestrator()
        health = await orchestrator.initialize_database()

        assert health.status.value == 'healthy', f"Database initialization failed: {health.message}"


class TestHealthMonitor:
    """Test health monitoring"""

    @pytest.mark.asyncio
    async def test_liveness_probe(self):
        """Test liveness probe"""
        from production.health_monitor import get_health_monitor

        monitor = get_health_monitor()
        health = await monitor.liveness()

        assert health['status'] == 'alive'
        assert 'uptime_seconds' in health

    @pytest.mark.asyncio
    async def test_readiness_probe(self):
        """Test readiness probe"""
        from production.health_monitor import get_health_monitor

        monitor = get_health_monitor()
        health = await monitor.readiness()

        assert 'status' in health
        assert 'services' in health
        assert 'metrics' in health


class TestPerformance:
    """Performance baseline tests"""

    BASE_URL = "http://localhost:8003"

    def test_health_endpoint_response_time(self):
        """Test health endpoint responds within acceptable time"""
        import time

        start = time.time()
        response = requests.get(f"{self.BASE_URL}/health")
        duration = (time.time() - start) * 1000  # ms

        assert response.status_code == 200
        assert duration < 1000, f"Health endpoint took {duration}ms (should be < 1000ms)"

    def test_database_query_performance(self):
        """Test database queries are performant"""
        from database import get_db_engine
        from sqlalchemy import text
        import time

        engine = get_db_engine()

        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT COUNT(*) FROM products"))
        duration = (time.time() - start) * 1000  # ms

        assert duration < 500, f"Database query took {duration}ms (should be < 500ms)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
