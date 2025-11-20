"""
Database Operations Module
===========================

Simple helper functions for common database operations.
Replaces Kailash WorkflowBuilder patterns with direct SQLAlchemy queries.

NO MOCKING - Real PostgreSQL operations.
"""

from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import and_, or_

from database import get_db_engine
from models.order_orm import Product, Outlet, Order, DeliveryOrder, Invoice
from models.conversation_orm import ConversationSession, ConversationMessage, UserInteractionSummary


# Global session factory
_SessionFactory = None


def get_session_factory():
    """Get or create global session factory"""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_db_engine()
        _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory


@contextmanager
def get_db_session():
    """
    Context manager for database sessions

    Usage:
        with get_db_session() as session:
            outlets = list_outlets(session)
    """
    SessionFactory = get_session_factory()
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# OUTLET OPERATIONS
# ============================================================================

def list_outlets(session: Session, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    List outlets from database

    Args:
        session: SQLAlchemy session
        limit: Maximum number of outlets to return
        filters: Optional filters (e.g., {'name': 'Canadian Pizza'})

    Returns:
        List of outlet dictionaries
    """
    query = session.query(Outlet)

    if filters:
        for key, value in filters.items():
            if hasattr(Outlet, key):
                query = query.filter(getattr(Outlet, key) == value)

    outlets = query.limit(limit).all()
    return [outlet.to_dict() for outlet in outlets]


def get_outlet_by_id(session: Session, outlet_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single outlet by ID

    Args:
        session: SQLAlchemy session
        outlet_id: Outlet ID

    Returns:
        Outlet dictionary or None if not found
    """
    outlet = session.query(Outlet).filter(Outlet.id == outlet_id).first()
    return outlet.to_dict() if outlet else None


def get_outlet_by_name(session: Session, name: str) -> Optional[Dict[str, Any]]:
    """
    Get a single outlet by name

    Args:
        session: SQLAlchemy session
        name: Outlet name

    Returns:
        Outlet dictionary or None if not found
    """
    outlet = session.query(Outlet).filter(Outlet.name == name).first()
    return outlet.to_dict() if outlet else None


# ============================================================================
# PRODUCT OPERATIONS
# ============================================================================

def list_products(session: Session, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    List products from database

    Args:
        session: SQLAlchemy session
        limit: Maximum number of products to return
        filters: Optional filters (e.g., {'category': 'boxes', 'is_active': True})

    Returns:
        List of product dictionaries
    """
    query = session.query(Product)

    if filters:
        for key, value in filters.items():
            if hasattr(Product, key):
                query = query.filter(getattr(Product, key) == value)

    products = query.limit(limit).all()
    return [product.to_dict() for product in products]


def get_product_by_sku(session: Session, sku: str) -> Optional[Dict[str, Any]]:
    """
    Get a single product by SKU

    Args:
        session: SQLAlchemy session
        sku: Product SKU

    Returns:
        Product dictionary or None if not found
    """
    product = session.query(Product).filter(Product.sku == sku).first()
    return product.to_dict() if product else None


# ============================================================================
# ORDER OPERATIONS
# ============================================================================

def create_order(session: Session, order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new order

    Args:
        session: SQLAlchemy session
        order_data: Order data dictionary

    Returns:
        Created order dictionary
    """
    from decimal import Decimal

    order = Order(
        outlet_id=order_data['outlet_id'],
        whatsapp_message=order_data['whatsapp_message'],
        parsed_items=order_data['parsed_items'],
        total_amount=Decimal(str(order_data['total_amount'])),
        status=order_data.get('status', 'pending'),
        anomaly_detected=order_data.get('anomaly_detected', False),
        escalated=order_data.get('escalated', False)
    )

    session.add(order)
    session.commit()
    session.refresh(order)

    return order.to_dict()


def get_order_by_id(session: Session, order_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single order by ID

    Args:
        session: SQLAlchemy session
        order_id: Order ID

    Returns:
        Order dictionary or None if not found
    """
    order = session.query(Order).filter(Order.id == order_id).first()
    return order.to_dict() if order else None


def list_orders(session: Session, limit: int = 100, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    List orders from database

    Args:
        session: SQLAlchemy session
        limit: Maximum number of orders to return
        filters: Optional filters (e.g., {'outlet_id': 1, 'status': 'pending'})

    Returns:
        List of order dictionaries
    """
    query = session.query(Order)

    if filters:
        for key, value in filters.items():
            if hasattr(Order, key):
                query = query.filter(getattr(Order, key) == value)

    query = query.order_by(Order.created_at.desc())
    orders = query.limit(limit).all()
    return [order.to_dict() for order in orders]


# ============================================================================
# CONVERSATION OPERATIONS
# ============================================================================

def get_conversation_session(session: Session, session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get conversation session by ID

    Args:
        session: SQLAlchemy session
        session_id: Session ID

    Returns:
        Session dictionary or None if not found
    """
    conv_session = session.query(ConversationSession).filter(
        ConversationSession.session_id == session_id
    ).first()
    return conv_session.to_dict() if conv_session else None


def get_conversation_messages(
    session: Session,
    session_id: str,
    limit: int = 10,
    role_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get conversation messages for a session

    Args:
        session: SQLAlchemy session
        session_id: Session ID
        limit: Maximum number of messages to return
        role_filter: Optional filter by role ('user' or 'assistant')

    Returns:
        List of message dictionaries (ordered by timestamp ascending)
    """
    query = session.query(ConversationMessage).filter(
        ConversationMessage.session_id == session_id
    )

    if role_filter:
        query = query.filter(ConversationMessage.role == role_filter)

    query = query.order_by(ConversationMessage.timestamp.asc())
    messages = query.limit(limit).all()
    return [msg.to_dict() for msg in messages]
