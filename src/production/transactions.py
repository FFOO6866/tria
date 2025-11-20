"""
Transaction Management for Production Data Integrity
=====================================================

Provides database transaction management with proper commit/rollback handling
to prevent data corruption and orphaned records.

Usage:
    from production.transactions import TransactionManager, transactional

    # Context manager approach:
    tx_manager = TransactionManager(engine)
    with tx_manager.transaction() as conn:
        # All operations succeed or all rollback
        conn.execute(...)

    # Decorator approach:
    @transactional
    def create_order(order_data, conn=None):
        # conn is injected automatically
        result = conn.execute(...)
        return result
"""

from contextlib import contextmanager
from typing import Generator, Callable, Any
from sqlalchemy.engine import Engine, Connection
import logging
import functools

logger = logging.getLogger(__name__)


class TransactionManager:
    """Manages database transactions with proper rollback handling"""

    def __init__(self, engine: Engine):
        self.engine = engine

    @contextmanager
    def transaction(self) -> Generator[Connection, None, None]:
        """
        Context manager for transactional database operations.

        All operations within the context succeed together or all rollback.
        Automatically handles commit on success and rollback on any exception.

        Usage:
            with tx_manager.transaction() as conn:
                result = conn.execute(query)
                # More operations...
                # Auto-commits if no exceptions

        Yields:
            Connection: Database connection with active transaction

        Raises:
            Exception: Any exception from operations (after rollback)
        """
        connection = self.engine.connect()
        transaction = connection.begin()

        try:
            yield connection
            transaction.commit()
            logger.info("Transaction committed successfully")

        except Exception as e:
            transaction.rollback()
            logger.error(f"Transaction rolled back due to: {str(e)}")
            raise

        finally:
            connection.close()


def transactional(func: Callable) -> Callable:
    """
    Decorator to wrap function in database transaction.

    Automatically injects database connection with active transaction.
    Function must accept 'conn' as a keyword argument.

    Usage:
        @transactional
        def create_order(order_data, conn=None):
            result = conn.execute(text("INSERT INTO orders ..."))
            return result.fetchone()[0]

    Args:
        func: Function to wrap in transaction

    Returns:
        Wrapped function with transaction management
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from database import get_db_engine

        engine = get_db_engine()
        tx_manager = TransactionManager(engine)

        with tx_manager.transaction() as conn:
            # Inject connection into function
            kwargs['conn'] = conn
            return func(*args, **kwargs)

    return wrapper


# Example usage for order creation
@transactional
def create_order_with_external_sync(
    order_data: dict,
    sync_to_xero: bool = False,
    conn: Connection = None
) -> int:
    """
    Example: Create order in database with optional Xero sync.

    Both operations happen in same transaction - if Xero fails,
    database insert is rolled back.

    Args:
        order_data: Order information
        sync_to_xero: Whether to sync to Xero
        conn: Database connection (injected by @transactional)

    Returns:
        order_id: Created order ID

    Raises:
        Exception: If order creation or Xero sync fails
    """
    from sqlalchemy import text

    # Insert order
    result = conn.execute(
        text("""
            INSERT INTO orders (outlet_id, total_amount, status)
            VALUES (:outlet_id, :total_amount, :status)
            RETURNING id
        """),
        order_data
    )
    order_id = result.fetchone()[0]
    logger.info(f"Order {order_id} inserted in database")

    # Optional: Sync to Xero within same transaction
    if sync_to_xero:
        try:
            # Xero sync logic here
            # If this fails, entire transaction rolls back
            logger.info(f"Order {order_id} synced to Xero")
        except Exception as e:
            logger.error(f"Xero sync failed: {e}")
            raise  # Triggers rollback of entire transaction

    return order_id
