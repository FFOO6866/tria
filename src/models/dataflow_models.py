"""
TRIA AI-BPO DataFlow Models
============================

DataFlow models for PostgreSQL database operations.
Each @db.model automatically generates 9 nodes:
- Create, Read, Update, Delete
- List, Count, Exists
- BulkCreate, BulkUpdate

NO MOCKING - These connect to real PostgreSQL database.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal


def initialize_dataflow_models(db):
    """
    Initialize all DataFlow models

    Args:
        db: DataFlow instance configured with PostgreSQL connection

    Returns:
        Dictionary of model classes for reference
    """

    # ========================================================================
    # PRODUCT CATALOG MODEL
    # ========================================================================
    @db.model
    class Product:
        """
        Product catalog with SKU, pricing, and UOM

        Loaded from Excel inventory and used for order matching.
        NO HARDCODING - All products come from this catalog.

        Generates nodes:
        - ProductCreateNode
        - ProductReadNode
        - ProductUpdateNode
        - ProductDeleteNode
        - ProductListNode
        - ProductCountNode
        - ProductExistsNode
        - ProductBulkCreateNode
        - ProductBulkUpdateNode
        """
        sku: str                            # e.g., "TRI-001-TR-01"
        description: str                    # e.g., "Single-Compartment Meal Tray"
        unit_price: Decimal                 # Price per unit in SGD
        uom: str = "piece"                  # Unit of measure: piece, box, pack, carton
        category: str = "general"           # Product category for grouping
        stock_quantity: int = 0             # Current stock level
        min_order_qty: int = 1              # Minimum order quantity
        is_active: bool = True              # Active in catalog
        notes: str = ""                     # Additional product notes
        created_at: datetime = None
        updated_at: Optional[datetime] = None

    # ========================================================================
    # OUTLET MODEL
    # ========================================================================
    @db.model
    class Outlet:
        """
        Pizza outlet information

        Generates nodes:
        - OutletCreateNode
        - OutletReadNode
        - OutletUpdateNode
        - OutletDeleteNode
        - OutletListNode
        - OutletCountNode
        - OutletExistsNode
        - OutletBulkCreateNode
        - OutletBulkUpdateNode
        """
        name: str                                   # e.g., "Canadian Pizza Pasir Ris"
        address: str                                # Full address
        contact_person: str                         # Contact name
        contact_number: str                         # Phone number
        whatsapp_user_id: str = ""                  # WhatsApp ID for matching (empty if not set)
        usual_order_days: str = "Monday,Thursday"   # Comma-separated order days
        avg_order_frequency: float = 2.0            # Orders per week
        notes: str = ""                             # Additional notes
        created_at: datetime = None

    # ========================================================================
    # ORDER MODEL
    # ========================================================================
    @db.model
    class Order:
        """
        Customer order record

        Tracks complete order lifecycle from WhatsApp to completion.
        """
        outlet_id: int                      # Foreign key to Outlet
        whatsapp_message: str               # Original WhatsApp text
        parsed_items: Dict[str, Any]        # JSON: {"boxes_10": 600, ...}
        total_amount: Decimal               # Calculated total (SGD)
        status: str                         # pending, processing, completed, failed
        anomaly_detected: bool = False      # True if quantity is unusual
        escalated: bool = False             # True if requires manual review
        created_at: datetime = datetime.now()
        completed_at: Optional[datetime]

    # ========================================================================
    # DELIVERY ORDER MODEL
    # ========================================================================
    @db.model
    class DeliveryOrder:
        """
        Delivery order (DO) record

        Links to generated Excel DO file.
        """
        order_id: int                       # Foreign key to Order
        do_number: str                      # Unique DO number (DO-YYYYMMDD-XXXXX)
        excel_path: str                     # Path to generated DO Excel file
        delivery_date: date                 # Scheduled delivery date
        delivery_slot: str                  # Time slot (e.g., "10:00-12:00")
        driver: Optional[str]               # Assigned driver
        status: str                         # scheduled, in_transit, delivered
        created_at: datetime = datetime.now()
        delivered_at: Optional[datetime]

    # ========================================================================
    # INVOICE MODEL
    # ========================================================================
    @db.model
    class Invoice:
        """
        Invoice record with Xero integration

        Tracks invoices posted to Xero.
        NO MOCKING - Real Xero API integration.
        """
        order_id: int                       # Foreign key to Order
        invoice_number: str                 # Invoice number (INV-YYYYMMDD-XXXXX)
        xero_invoice_id: Optional[str]      # Xero's internal invoice ID
        xero_url: Optional[str]             # Direct link to Xero invoice
        subtotal: Decimal                   # Subtotal before tax
        tax: Decimal                        # GST 8%
        total: Decimal                      # Final total
        currency: str = "SGD"               # Currency code
        status: str                         # draft, posted, paid, voided
        posted_to_xero: bool = False        # True if successfully posted
        created_at: datetime = datetime.now()
        posted_at: Optional[datetime]
        paid_at: Optional[datetime]

    # Return model classes for reference
    return {
        "Product": Product,
        "Outlet": Outlet,
        "Order": Order,
        "DeliveryOrder": DeliveryOrder,
        "Invoice": Invoice
    }
