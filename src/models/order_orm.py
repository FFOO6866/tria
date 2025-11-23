"""
TRIA AI-BPO Order Management Models
====================================

SQLAlchemy ORM models for order processing.
Replaces DataFlow auto-generated nodes with standard ORM patterns.

NO MOCKING - Real PostgreSQL with production-ready patterns.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Date, Numeric, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from decimal import Decimal

Base = declarative_base()


class Product(Base):
    """
    Product catalog with SKU, pricing, and UOM

    Loaded from Excel inventory and used for order matching.
    NO HARDCODING - All products come from this catalog.
    """
    __tablename__ = 'products'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    sku = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    uom = Column(String(20), nullable=False, default='piece')
    category = Column(String(50), nullable=False, default='general', index=True)
    stock_quantity = Column(Integer, nullable=False, default=0)
    min_order_qty = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(Text, nullable=False, default='')

    # Semantic search embedding (OpenAI text-embedding-3-small JSON array)
    embedding = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True,
                       onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_product_category_active', 'category', 'is_active'),
        Index('idx_product_sku_active', 'sku', 'is_active'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'sku': self.sku,
            'description': self.description,
            'unit_price': float(self.unit_price) if self.unit_price else 0.0,
            'uom': self.uom,
            'category': self.category,
            'stock_quantity': self.stock_quantity,
            'min_order_qty': self.min_order_qty,
            'is_active': self.is_active,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Outlet(Base):
    """
    Pizza outlet information
    """
    __tablename__ = 'outlets'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    name = Column(String(200), nullable=False, index=True)
    address = Column(Text, nullable=False)
    contact_person = Column(String(200), nullable=False)
    contact_number = Column(String(50), nullable=False)
    whatsapp_user_id = Column(String(100), nullable=False, default='', index=True)
    usual_order_days = Column(String(100), nullable=False, default='Monday,Thursday')
    avg_order_frequency = Column(Float, nullable=False, default=2.0)
    notes = Column(Text, nullable=False, default='')

    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)

    # Indexes
    __table_args__ = (
        Index('idx_outlet_name', 'name'),
        Index('idx_outlet_whatsapp', 'whatsapp_user_id'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'contact_person': self.contact_person,
            'contact_number': self.contact_number,
            'whatsapp_user_id': self.whatsapp_user_id,
            'usual_order_days': self.usual_order_days,
            'avg_order_frequency': self.avg_order_frequency,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Order(Base):
    """
    Customer order record

    Tracks complete order lifecycle from WhatsApp to completion.
    """
    __tablename__ = 'orders'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Outlet
    outlet_id = Column(Integer, nullable=False, index=True)

    # Core fields
    whatsapp_message = Column(Text, nullable=False)
    parsed_items = Column(JSONB, nullable=False)  # {"boxes_10": 600, ...}
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False, default='pending', index=True)
    anomaly_detected = Column(Boolean, nullable=False, default=False)
    escalated = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_order_outlet_created', 'outlet_id', 'created_at'),
        Index('idx_order_status', 'status'),
        Index('idx_order_escalated', 'escalated'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'outlet_id': self.outlet_id,
            'whatsapp_message': self.whatsapp_message,
            'parsed_items': self.parsed_items,
            'total_amount': float(self.total_amount) if self.total_amount else 0.0,
            'status': self.status,
            'anomaly_detected': self.anomaly_detected,
            'escalated': self.escalated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class DeliveryOrder(Base):
    """
    Delivery order (DO) record

    Links to generated Excel DO file.
    """
    __tablename__ = 'delivery_orders'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Order
    order_id = Column(Integer, nullable=False, index=True)

    # Core fields
    do_number = Column(String(100), unique=True, nullable=False, index=True)
    excel_path = Column(Text, nullable=False)
    delivery_date = Column(Date, nullable=False, index=True)
    delivery_slot = Column(String(50), nullable=False)
    driver = Column(String(200), nullable=True)
    status = Column(String(50), nullable=False, default='scheduled', index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_do_order', 'order_id'),
        Index('idx_do_delivery_date', 'delivery_date'),
        Index('idx_do_status', 'status'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'do_number': self.do_number,
            'excel_path': self.excel_path,
            'delivery_date': self.delivery_date.isoformat() if self.delivery_date else None,
            'delivery_slot': self.delivery_slot,
            'driver': self.driver,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
        }


class Invoice(Base):
    """
    Invoice record with Xero integration

    Tracks invoices posted to Xero.
    NO MOCKING - Real Xero API integration.
    """
    __tablename__ = 'invoices'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Order
    order_id = Column(Integer, nullable=False, index=True)

    # Core fields
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    xero_invoice_id = Column(String(200), nullable=True, index=True)
    xero_url = Column(Text, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    tax = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default='SGD')
    status = Column(String(50), nullable=False, default='draft', index=True)
    posted_to_xero = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index('idx_invoice_order', 'order_id'),
        Index('idx_invoice_xero_id', 'xero_invoice_id'),
        Index('idx_invoice_status', 'status'),
        Index('idx_invoice_posted', 'posted_to_xero'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'invoice_number': self.invoice_number,
            'xero_invoice_id': self.xero_invoice_id,
            'xero_url': self.xero_url,
            'subtotal': float(self.subtotal) if self.subtotal else 0.0,
            'tax': float(self.tax) if self.tax else 0.0,
            'total': float(self.total) if self.total else 0.0,
            'currency': self.currency,
            'status': self.status,
            'posted_to_xero': self.posted_to_xero,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }


def create_tables(engine):
    """
    Create all order management tables in PostgreSQL

    Args:
        engine: SQLAlchemy engine instance

    Note:
        This is idempotent - safe to call multiple times.
        Uses IF NOT EXISTS internally.
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """
    Drop all order management tables (for testing only!)

    Args:
        engine: SQLAlchemy engine instance

    Warning:
        This will DELETE ALL ORDER DATA!
        Only use in development/testing.
    """
    Base.metadata.drop_all(engine)
