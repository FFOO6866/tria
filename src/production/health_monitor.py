#!/usr/bin/env python3
"""
Production Health Monitoring System
====================================

Comprehensive health monitoring with:
- Deep health checks for all services
- Performance metrics
- Resource monitoring
- Dependency status
- Readiness vs Liveness probes
"""

import os
import time
import psutil
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class HealthMetrics:
    """System health metrics"""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_percent: float
    disk_available_gb: float
    uptime_seconds: float
    timestamp: str


class HealthMonitor:
    """
    Comprehensive health monitoring system for production.

    Provides two types of health checks:
    - Liveness: Is the service running? (basic health)
    - Readiness: Can the service handle requests? (deep health)
    """

    def __init__(self):
        self.startup_time = datetime.utcnow()
        self.last_check: Optional[datetime] = None
        self.check_count = 0

    # ========================================================================
    # LIVENESS PROBE - Is the service alive?
    # ========================================================================

    async def liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - basic health check.

        Returns 200 if service is running, regardless of dependency status.
        Used by load balancers to determine if container should be restarted.
        """
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds()
        }

    # ========================================================================
    # READINESS PROBE - Can service handle requests?
    # ========================================================================

    async def readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - comprehensive health check.

        Returns 200 only if ALL critical dependencies are healthy.
        Used by load balancers to determine if traffic should be routed.
        """
        self.check_count += 1
        self.last_check = datetime.utcnow()

        health_status = {
            "status": "unknown",
            "timestamp": self.last_check.isoformat(),
            "check_number": self.check_count,
            "services": {},
            "metrics": {},
            "overall_healthy": True
        }

        # Check all critical services
        services_to_check = [
            ("database", self._check_database),
            ("redis", self._check_redis),
            ("openai", self._check_openai),
            ("chromadb", self._check_chromadb),
        ]

        for service_name, check_func in services_to_check:
            try:
                service_health = await check_func()
                health_status["services"][service_name] = service_health

                # Critical services must be healthy
                if service_health.get("critical", True) and not service_health.get("healthy", False):
                    health_status["overall_healthy"] = False

            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status["services"][service_name] = {
                    "healthy": False,
                    "error": str(e),
                    "critical": True
                }
                health_status["overall_healthy"] = False

        # Add system metrics
        try:
            metrics = self._get_system_metrics()
            health_status["metrics"] = asdict(metrics)
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            health_status["metrics"] = {"error": str(e)}

        # Set overall status
        health_status["status"] = "healthy" if health_status["overall_healthy"] else "unhealthy"

        return health_status

    # ========================================================================
    # DEEP HEALTH CHECKS - Individual services
    # ========================================================================

    async def _check_database(self) -> Dict[str, Any]:
        """Deep health check for PostgreSQL database"""
        try:
            from database import get_db_engine
            from sqlalchemy import text

            start_time = time.time()
            engine = get_db_engine()

            with engine.connect() as conn:
                # Test query
                result = conn.execute(text("SELECT 1"))
                result.scalar()

                # Get connection pool stats
                pool = engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow()
                }

                # Get database stats
                db_stats = conn.execute(text("""
                    SELECT
                        pg_database_size(current_database()) as db_size,
                        (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()) as connections
                """)).fetchone()

                response_time = (time.time() - start_time) * 1000  # ms

                return {
                    "healthy": True,
                    "response_time_ms": round(response_time, 2),
                    "pool": pool_status,
                    "database_size_mb": round(db_stats[0] / (1024 * 1024), 2),
                    "active_connections": db_stats[1],
                    "critical": True
                }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "critical": True
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """Deep health check for Redis cache"""
        try:
            from cache.redis_cache import RedisCache

            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_password = os.getenv('REDIS_PASSWORD')

            start_time = time.time()
            redis_cache = RedisCache(
                host=redis_host,
                port=redis_port,
                password=redis_password
            )

            if redis_cache.using_fallback:
                return {
                    "healthy": False,
                    "error": "Using in-memory fallback (Redis not available)",
                    "fallback": True,
                    "critical": True,
                    "warning": "PRODUCTION NOT SAFE - Idempotency disabled"
                }

            # Test read/write
            test_key = "health_check_test"
            test_value = f"test_{time.time()}"
            redis_cache.set(test_key, test_value, ttl_seconds=10)
            retrieved = redis_cache.get(test_key)
            redis_cache.delete(test_key)

            if retrieved != test_value:
                raise ValueError("Redis read/write test failed")

            response_time = (time.time() - start_time) * 1000  # ms

            # Get Redis info (if available)
            info = {}
            try:
                if hasattr(redis_cache, 'client'):
                    redis_info = redis_cache.client.info()
                    info = {
                        "used_memory_mb": round(redis_info.get('used_memory', 0) / (1024 * 1024), 2),
                        "connected_clients": redis_info.get('connected_clients', 0),
                        "uptime_seconds": redis_info.get('uptime_in_seconds', 0)
                    }
            except:
                pass

            return {
                "healthy": True,
                "response_time_ms": round(response_time, 2),
                "host": redis_host,
                "port": redis_port,
                "info": info,
                "critical": True
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "critical": True
            }

    async def _check_openai(self) -> Dict[str, Any]:
        """Check OpenAI API availability"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {
                    "healthy": False,
                    "error": "API key not configured",
                    "critical": True
                }

            # Don't make actual API call on every health check (costs money)
            # Just verify key is set and has correct format
            if not api_key.startswith('sk-'):
                return {
                    "healthy": False,
                    "error": "Invalid API key format",
                    "critical": True
                }

            return {
                "healthy": True,
                "api_key_set": True,
                "model": os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview'),
                "critical": True,
                "note": "API key validated (not tested to avoid costs)"
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "critical": True
            }

    async def _check_chromadb(self) -> Dict[str, Any]:
        """Check ChromaDB availability"""
        try:
            from rag.chroma_client import health_check

            health = health_check()

            return {
                "healthy": health['status'] == 'healthy',
                "collections": health.get('collections', []),
                "collections_count": health.get('collections_count', 0),
                "critical": False,  # Non-critical, can degrade gracefully
                "error": health.get('error') if health['status'] != 'healthy' else None
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "critical": False
            }

    # ========================================================================
    # SYSTEM METRICS
    # ========================================================================

    def _get_system_metrics(self) -> HealthMetrics:
        """Get system resource metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_mb = memory.available / (1024 * 1024)

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_available_gb = disk.free / (1024 * 1024 * 1024)

        # Uptime
        uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()

        return HealthMetrics(
            cpu_percent=round(cpu_percent, 2),
            memory_percent=round(memory_percent, 2),
            memory_available_mb=round(memory_available_mb, 2),
            disk_percent=round(disk_percent, 2),
            disk_available_gb=round(disk_available_gb, 2),
            uptime_seconds=round(uptime_seconds, 2),
            timestamp=datetime.utcnow().isoformat()
        )

    # ========================================================================
    # DETAILED DIAGNOSTICS
    # ========================================================================

    async def detailed_diagnostics(self) -> Dict[str, Any]:
        """
        Comprehensive diagnostic information for troubleshooting.

        Includes:
        - All service health checks
        - System metrics
        - Environment validation
        - Performance statistics
        - Resource usage
        """
        diagnostics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            "health_checks_performed": self.check_count,
            "last_check": self.last_check.isoformat() if self.last_check else None,
        }

        # Get readiness status (includes all service checks)
        readiness_status = await self.readiness()
        diagnostics.update(readiness_status)

        # Add environment information
        diagnostics["environment"] = {
            "python_version": os.sys.version,
            "env_mode": os.getenv('ENVIRONMENT', 'unknown'),
            "api_port": os.getenv('API_PORT', '8003'),
            "database_configured": bool(os.getenv('DATABASE_URL')),
            "redis_configured": bool(os.getenv('REDIS_HOST')),
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "sentry_configured": bool(os.getenv('SENTRY_DSN')),
        }

        # Add process information
        process = psutil.Process()
        diagnostics["process"] = {
            "pid": process.pid,
            "threads": process.num_threads(),
            "cpu_percent": process.cpu_percent(),
            "memory_mb": round(process.memory_info().rss / (1024 * 1024), 2),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }

        return diagnostics


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor
