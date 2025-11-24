#!/usr/bin/env python3
"""
Application Lifecycle Manager
==============================

Manages graceful startup, shutdown, and cleanup of application resources.

Key Features:
- Ordered startup with dependency management
- Graceful shutdown with resource cleanup
- Signal handling (SIGTERM, SIGINT)
- Connection pool cleanup
- Background task cancellation
- Proper error handling
"""

import signal
import logging
import asyncio
from typing import List, Callable, Optional, Awaitable
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class LifecycleHook:
    """Lifecycle hook callback"""
    name: str
    callback: Callable[[], Awaitable[None]]
    priority: int = 0  # Lower numbers run first


class LifecycleManager:
    """
    Manages application lifecycle with proper resource cleanup.

    Usage:
        manager = LifecycleManager()
        manager.add_startup_hook("database", init_database, priority=1)
        manager.add_shutdown_hook("database", cleanup_database, priority=99)

        await manager.startup()
        # ... application runs ...
        await manager.shutdown()
    """

    def __init__(self):
        self.startup_hooks: List[LifecycleHook] = []
        self.shutdown_hooks: List[LifecycleHook] = []
        self.started = False
        self.shutdown_initiated = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            if not self.shutdown_initiated:
                asyncio.create_task(self.shutdown())

        # Handle SIGTERM (docker stop, kubernetes)
        signal.signal(signal.SIGTERM, signal_handler)
        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, signal_handler)

    def add_startup_hook(self, name: str, callback: Callable[[], Awaitable[None]], priority: int = 0):
        """
        Add startup hook.

        Args:
            name: Hook name for logging
            callback: Async function to call during startup
            priority: Execution order (lower = earlier)
        """
        self.startup_hooks.append(LifecycleHook(name, callback, priority))
        self.startup_hooks.sort(key=lambda h: h.priority)

    def add_shutdown_hook(self, name: str, callback: Callable[[], Awaitable[None]], priority: int = 0):
        """
        Add shutdown hook.

        Args:
            name: Hook name for logging
            callback: Async function to call during shutdown
            priority: Execution order (lower = earlier, but shutdown runs in reverse)
        """
        self.shutdown_hooks.append(LifecycleHook(name, callback, priority))
        self.shutdown_hooks.sort(key=lambda h: h.priority, reverse=True)

    async def startup(self):
        """Execute all startup hooks in order"""
        if self.started:
            logger.warning("Lifecycle manager already started")
            return

        logger.info("=" * 60)
        logger.info("APPLICATION STARTUP")
        logger.info("=" * 60)

        for hook in self.startup_hooks:
            try:
                logger.info(f"Executing startup hook: {hook.name} (priority: {hook.priority})")
                await hook.callback()
                logger.info(f"✓ Startup hook completed: {hook.name}")
            except Exception as e:
                logger.error(f"✗ Startup hook failed: {hook.name}")
                logger.error(f"  Error: {e}")
                raise RuntimeError(f"Startup hook '{hook.name}' failed: {e}") from e

        self.started = True
        logger.info("=" * 60)
        logger.info("✓ APPLICATION STARTUP COMPLETE")
        logger.info("=" * 60)

    async def shutdown(self):
        """Execute all shutdown hooks in reverse order"""
        if self.shutdown_initiated:
            logger.warning("Shutdown already initiated")
            return

        self.shutdown_initiated = True

        logger.info("=" * 60)
        logger.info("APPLICATION SHUTDOWN")
        logger.info("=" * 60)

        # Run shutdown hooks in reverse order
        for hook in self.shutdown_hooks:
            try:
                logger.info(f"Executing shutdown hook: {hook.name} (priority: {hook.priority})")
                await hook.callback()
                logger.info(f"✓ Shutdown hook completed: {hook.name}")
            except Exception as e:
                logger.error(f"✗ Shutdown hook failed: {hook.name}")
                logger.error(f"  Error: {e}")
                # Continue with other shutdown hooks even if one fails

        logger.info("=" * 60)
        logger.info("✓ APPLICATION SHUTDOWN COMPLETE")
        logger.info("=" * 60)

    @asynccontextmanager
    async def lifespan(self):
        """
        Context manager for application lifespan.

        Usage with FastAPI:
            app = FastAPI(lifespan=lifecycle_manager.lifespan)
        """
        await self.startup()
        try:
            yield
        finally:
            await self.shutdown()


# Example cleanup functions for common resources

async def cleanup_database_connections():
    """Cleanup database connection pool"""
    try:
        from database import get_db_engine
        engine = get_db_engine()
        if engine:
            logger.info("Disposing database connection pool...")
            engine.dispose()
            logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Failed to cleanup database connections: {e}")


async def cleanup_redis_connections():
    """Cleanup Redis connections"""
    try:
        from cache.redis_cache import RedisCache
        # Note: RedisCache uses connection pooling, connections close automatically
        logger.info("✓ Redis connections will be closed by connection pool")
    except Exception as e:
        logger.error(f"Failed to cleanup Redis connections: {e}")


async def cleanup_openai_client():
    """Cleanup OpenAI client"""
    try:
        # OpenAI client doesn't need explicit cleanup in current version
        logger.info("✓ OpenAI client cleanup complete")
    except Exception as e:
        logger.error(f"Failed to cleanup OpenAI client: {e}")


async def cancel_background_tasks():
    """Cancel all background tasks"""
    try:
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
        if tasks:
            logger.info(f"Cancelling {len(tasks)} background tasks...")
            for task in tasks:
                task.cancel()
            # Wait for tasks to finish cancellation
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("✓ Background tasks cancelled")
    except Exception as e:
        logger.error(f"Failed to cancel background tasks: {e}")


# Global lifecycle manager instance
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get global lifecycle manager instance"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager
