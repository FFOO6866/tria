"""
Centralized Database Connection Management
==========================================

Global SQLAlchemy engine with connection pooling for all database operations.

Features:
- Single global engine instance (created once, reused forever)
- Connection pooling (10 base connections, 20 max overflow)
- Automatic connection health checks (pool_pre_ping)
- Connection recycling (prevents stale connections)
- UTF-8 encoding for all connections
- Production-ready error handling

NO MOCKUPS - Real PostgreSQL connection only.
NO FALLBACKS - Fails explicitly if database unavailable.

Usage:
    from database import get_db_engine

    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT ..."), params)
"""

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.pool import QueuePool
from typing import Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Global engine instance - created once, reused forever
_engine: Optional[Engine] = None


def get_db_engine(database_url: Optional[str] = None) -> Engine:
    """
    Get or create global database engine with connection pooling

    This function implements the singleton pattern for SQLAlchemy engine.
    The engine is created once on first call, then reused for all subsequent calls.

    Connection Pool Configuration:
    - pool_size=10: 10 persistent connections in the pool
    - max_overflow=20: Up to 20 additional temporary connections under load
    - pool_pre_ping=True: Test connection health before using
    - pool_recycle=3600: Recycle connections after 1 hour (prevents stale connections)
    - connect_timeout=10: Fail fast if database unreachable

    Args:
        database_url: Optional PostgreSQL connection string
                     If not provided, uses config.DATABASE_URL

    Returns:
        SQLAlchemy Engine instance with pooling configured

    Raises:
        RuntimeError: If engine creation fails (database unreachable, invalid URL, etc.)

    Example:
        >>> from database import get_db_engine
        >>> from sqlalchemy import text
        >>>
        >>> engine = get_db_engine()
        >>> with engine.connect() as conn:
        ...     result = conn.execute(text("SELECT COUNT(*) FROM products"))
        ...     count = result.scalar()
    """
    global _engine

    if _engine is None:
        # Import config here to avoid circular imports
        from config import config

        # Use provided URL or get from config
        url = database_url or config.get_database_url()

        try:
            _engine = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=10,                    # Base pool size
                max_overflow=20,                  # Additional connections under load
                pool_pre_ping=True,               # Test connection before using
                pool_recycle=3600,                # Recycle after 1 hour
                echo=False,                       # Set to True for SQL logging (development only)
                connect_args={
                    'connect_timeout': 10,        # Fail fast if DB unreachable
                    'options': '-c client_encoding=UTF8'  # Force UTF-8
                }
            )

            # Test the connection immediately
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info(
                "Database engine initialized successfully "
                f"(pool_size=10, max_overflow=20, recycle=3600s)"
            )

        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise RuntimeError(
                f"Failed to create database engine. "
                f"Please check DATABASE_URL and ensure PostgreSQL is accessible. "
                f"Error: {str(e)}"
            ) from e

    return _engine


def dispose_engine() -> None:
    """
    Dispose engine and close all connections

    This function is primarily for testing and cleanup scenarios.
    In production, the engine should remain alive for the lifetime of the application.

    Warning:
        This will close ALL active connections in the pool. Only use during
        application shutdown or in test teardown.

    Example:
        >>> from database import dispose_engine
        >>>
        >>> # In test teardown
        >>> dispose_engine()
    """
    global _engine

    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed and all connections closed")


def get_pool_status() -> dict:
    """
    Get current connection pool statistics

    Returns:
        Dictionary with pool statistics:
        - size: Current number of connections in pool
        - checked_in: Connections available for use
        - checked_out: Connections currently in use
        - overflow: Additional connections beyond pool_size
        - total: Total connections (checked_in + checked_out + overflow)

    Raises:
        RuntimeError: If engine not initialized

    Example:
        >>> from database import get_db_engine, get_pool_status
        >>>
        >>> engine = get_db_engine()
        >>> stats = get_pool_status()
        >>> print(f"Active connections: {stats['checked_out']}")
    """
    global _engine

    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call get_db_engine() first.")

    pool = _engine.pool

    return {
        'size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total': pool.checkedout() + pool.overflow()
    }
