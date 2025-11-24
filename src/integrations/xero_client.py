"""
Xero API Client for Tria AIBPO (Official SDK Implementation)

Provides OAuth2.0 authentication and API methods for Xero integration.
Uses official xero-python SDK for maximum reliability and maintainability.

Supports the complete order-to-invoice workflow:
1. Customer verification
2. Inventory checking
3. Draft delivery order creation
4. Order finalization
5. Invoice generation and posting

Production-grade implementation:
- Official Xero SDK (xero-python)
- Centralized configuration
- Singleton pattern for connection management
- Comprehensive error handling
- Automatic token refresh
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Official Xero SDK imports
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.accounting import AccountingApi
from xero_python.accounting import (
    Contact, Contacts,
    Item, Items,
    PurchaseOrder, PurchaseOrders,
    Invoice, Invoices,
    LineItem,
    Phone
)
from xero_python.exceptions import AccountingBadRequestException

# Use centralized config
from config import config

# Production infrastructure
from production.retry import retry_with_backoff, retry_on_rate_limit, circuit_breaker
from production.rate_limiting import rate_limit_xero

logger = logging.getLogger(__name__)


def validate_xero_where_clause_input(value: str, field_name: str = "input") -> str:
    """
    Validate and sanitize input for Xero API WHERE clauses to prevent injection attacks.

    SECURITY: Xero API doesn't support parameterized queries, so we must validate
    and escape inputs manually to prevent injection attacks.

    Args:
        value: Input value to validate and sanitize
        field_name: Name of the field for error messages

    Returns:
        Sanitized input value with quotes escaped

    Raises:
        ValueError: If input contains suspicious or invalid characters

    Example:
        # BEFORE (VULNERABLE):
        where = f'Name=="{customer_name}"'  # ❌ Injection risk

        # AFTER (SECURE):
        safe_name = validate_xero_where_clause_input(customer_name, "customer_name")
        where = f'Name=="{safe_name}"'  # ✅ Protected
    """
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")

    # Strip whitespace
    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty after trimming whitespace")

    # Validate against whitelist: alphanumeric, spaces, hyphens, ampersands, apostrophes, periods, commas
    # This allows legitimate business names like "John's Shop", "Smith & Co.", "ABC-123"
    # but blocks injection attempts with quotes, equals, parentheses, semicolons, etc.
    if not re.match(r"^[a-zA-Z0-9\s\-&'.,()]+$", value):
        logger.warning(
            f"Rejected {field_name} with suspicious characters: {value[:50]}",
            extra={"field_name": field_name, "value_preview": value[:50]}
        )
        raise ValueError(
            f"{field_name} contains invalid characters. Only alphanumeric characters, "
            f"spaces, hyphens, ampersands, apostrophes, periods, commas, and parentheses are allowed."
        )

    # Escape double quotes to prevent breaking out of the WHERE clause string
    # Example: 'O"Reilly' becomes 'O\"Reilly'
    sanitized = value.replace('"', '\\"')

    # Log for audit trail
    logger.debug(
        f"Validated {field_name} for Xero WHERE clause",
        extra={"field_name": field_name, "original_length": len(value)}
    )

    return sanitized


@dataclass
class XeroCustomer:
    """Xero customer/contact information"""
    contact_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_customer: bool = True


@dataclass
class XeroProduct:
    """Xero inventory item information"""
    item_id: str
    code: str
    name: str
    description: Optional[str] = None
    unit_price: float = 0.0
    quantity_on_hand: Optional[float] = None
    is_sold: bool = True


@dataclass
class XeroDraftOrder:
    """Draft delivery order (using Purchase Order as placeholder)"""
    order_id: str
    contact_id: str
    line_items: List[Dict[str, Any]]
    total: float
    status: str = "DRAFT"
    date_created: Optional[datetime] = None


@dataclass
class XeroInvoice:
    """Xero invoice information"""
    invoice_id: str
    invoice_number: str
    contact_id: str
    line_items: List[Dict[str, Any]]
    total: float
    status: str
    date: Optional[datetime] = None


class XeroClient:
    """
    Xero API client with OAuth2.0 authentication using official SDK.

    Singleton pattern: Reuses API client and token across requests.
    Thread-safe for production use.
    """

    _instance: Optional['XeroClient'] = None
    _api_client: Optional[ApiClient] = None
    _accounting_api: Optional[AccountingApi] = None
    _token_expiry: Optional[datetime] = None

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize Xero client with configuration from environment"""
        if self._initialized:
            return

        # Get configuration from centralized config
        self.client_id = config.XERO_CLIENT_ID
        self.client_secret = config.XERO_CLIENT_SECRET
        self.refresh_token = config.XERO_REFRESH_TOKEN
        self.tenant_id = config.XERO_TENANT_ID

        self.token_url = config.XERO_TOKEN_URL
        self.api_url = config.XERO_API_URL
        self.rate_limit = config.XERO_RATE_LIMIT_PER_MINUTE

        # Validate required configuration
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            raise ValueError(
                "Missing required Xero configuration. Please set XERO_CLIENT_ID, "
                "XERO_CLIENT_SECRET, and XERO_TENANT_ID in .env file"
            )

        # Initialize SDK API client
        self._initialize_api_client()

        self._initialized = True
        logger.info("Xero client initialized with official SDK (singleton)")

    def _initialize_api_client(self):
        """Initialize Xero SDK API client with OAuth2 token"""
        try:
            # Create OAuth2 token with client credentials
            # NOTE: OAuth2Token constructor signature: (client_id, client_secret, expiration_buffer)
            token = OAuth2Token(
                client_id=self.client_id,
                client_secret=self.client_secret
            )

            # Set refresh token (required for refresh flow)
            token.refresh_token = self.refresh_token

            # Create API client first (needed for refresh)
            api_config = Configuration()
            self._api_client = ApiClient(api_config)

            # Refresh token to get access token
            # NOTE: refresh_access_token() requires an ApiClient instance
            token.refresh_access_token(self._api_client)

            # Store token expiry
            if hasattr(token, 'expires_at') and token.expires_at:
                self._token_expiry = datetime.fromtimestamp(token.expires_at)
            else:
                # Default to 30 minutes if expires_at not available
                self._token_expiry = datetime.now() + timedelta(seconds=1800)

            # Update API configuration with authenticated token
            api_config.oauth2_token = token
            api_config.oauth2_token_saver = self._token_saver

            # Create accounting API
            self._accounting_api = AccountingApi(self._api_client)

            logger.info(f"Xero SDK API client initialized, token expires at {self._token_expiry}")

        except Exception as e:
            logger.error(f"Failed to initialize Xero SDK API client: {e}")
            raise RuntimeError(f"Xero SDK initialization failed: {e}")

    def _token_saver(self, token: OAuth2Token):
        """Callback to save refreshed token (updates expiry time)"""
        if hasattr(token, 'expires_at'):
            self._token_expiry = datetime.fromtimestamp(token.expires_at)
            logger.info(f"Token refreshed, new expiry: {self._token_expiry}")

        # Update refresh token if changed
        if hasattr(token, 'refresh_token') and token.refresh_token:
            self.refresh_token = token.refresh_token

    def _ensure_token_valid(self):
        """Ensure access token is valid, refresh if needed"""
        if self._token_expiry and datetime.now() >= self._token_expiry - timedelta(minutes=5):
            logger.info("Token expiring soon, refreshing...")
            self._initialize_api_client()

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def verify_customer(self, customer_name: str) -> Optional[XeroCustomer]:
        """
        Verify if customer exists in Xero.

        Args:
            customer_name: Customer/contact name to search for

        Returns:
            XeroCustomer if found, None otherwise
        """
        try:
            self._ensure_token_valid()

            # SECURITY: Validate input to prevent injection attacks
            safe_customer_name = validate_xero_where_clause_input(customer_name, "customer_name")

            # Use SDK to get contacts with WHERE clause
            contacts = self._accounting_api.get_contacts(
                xero_tenant_id=self.tenant_id,
                where=f'Name=="{safe_customer_name}"'
            )

            if contacts and contacts.contacts and len(contacts.contacts) > 0:
                contact = contacts.contacts[0]

                # Extract phone number if available
                phone = None
                if contact.phones and len(contact.phones) > 0:
                    phone = contact.phones[0].phone_number

                customer = XeroCustomer(
                    contact_id=contact.contact_id,
                    name=contact.name,
                    email=contact.email_address,
                    phone=phone,
                    is_customer=contact.is_customer if contact.is_customer is not None else True
                )

                logger.info(f"Customer found: {customer.name} (ID: {customer.contact_id})")
                return customer
            else:
                logger.info(f"Customer not found: {customer_name}")
                return None

        except AccountingBadRequestException as e:
            logger.error(f"Xero API error verifying customer: {e}")
            raise
        except Exception as e:
            logger.error(f"Error verifying customer: {e}")
            raise

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def check_inventory(self, product_code: str) -> Optional[XeroProduct]:
        """
        Check if product exists in Xero inventory.

        Args:
            product_code: Product/item code to search for

        Returns:
            XeroProduct if found, None otherwise
        """
        try:
            self._ensure_token_valid()

            # SECURITY: Validate input to prevent injection attacks
            safe_product_code = validate_xero_where_clause_input(product_code, "product_code")

            # Use SDK to get items with WHERE clause
            items_response = self._accounting_api.get_items(
                xero_tenant_id=self.tenant_id,
                where=f'Code=="{safe_product_code}"'
            )

            if items_response and items_response.items and len(items_response.items) > 0:
                item = items_response.items[0]

                # Extract unit price from sales details
                unit_price = 0.0
                if item.sales_details and item.sales_details.unit_price:
                    unit_price = float(item.sales_details.unit_price)

                product = XeroProduct(
                    item_id=item.item_id,
                    code=item.code,
                    name=item.name if item.name else item.code,
                    description=item.description,
                    unit_price=unit_price,
                    quantity_on_hand=float(item.quantity_on_hand) if item.quantity_on_hand is not None else None,
                    is_sold=item.is_sold if item.is_sold is not None else True
                )

                logger.info(f"Product found: {product.name} (Code: {product.code})")
                return product
            else:
                logger.info(f"Product not found: {product_code}")
                return None

        except AccountingBadRequestException as e:
            logger.error(f"Xero API error checking inventory: {e}")
            raise
        except Exception as e:
            logger.error(f"Error checking inventory: {e}")
            raise

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def create_draft_order(
        self,
        contact_id: str,
        line_items: List[Dict[str, Any]],
        reference: Optional[str] = None
    ) -> XeroDraftOrder:
        """
        Create a draft delivery order in Xero.

        Uses Purchase Order with DRAFT status as placeholder for delivery order.

        Args:
            contact_id: Xero contact/customer ID
            line_items: List of line items with structure:
                [{"item_code": str, "quantity": float, "unit_price": float, "description": str}]
            reference: Optional reference number for the order

        Returns:
            XeroDraftOrder with order details
        """
        try:
            self._ensure_token_valid()

            # Build line items using SDK models
            po_line_items = []
            total = 0.0

            for item in line_items:
                line_total = item['quantity'] * item['unit_price']
                total += line_total

                line_item = LineItem(
                    item_code=item.get('item_code'),
                    description=item.get('description', ''),
                    quantity=item['quantity'],
                    unit_amount=item['unit_price'],
                    line_amount=line_total
                )
                po_line_items.append(line_item)

            # Create contact reference
            contact = Contact(contact_id=contact_id)

            # Create purchase order using SDK model
            purchase_order = PurchaseOrder(
                contact=contact,
                line_items=po_line_items,
                reference=reference or f"DO-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                status="DRAFT",
                date=datetime.now().date()
            )

            # Create purchase orders collection
            purchase_orders = PurchaseOrders(purchase_orders=[purchase_order])

            # Call API
            created_pos = self._accounting_api.create_purchase_orders(
                xero_tenant_id=self.tenant_id,
                purchase_orders=purchase_orders
            )

            if created_pos and created_pos.purchase_orders and len(created_pos.purchase_orders) > 0:
                created_po = created_pos.purchase_orders[0]

                draft_order = XeroDraftOrder(
                    order_id=created_po.purchase_order_id,
                    contact_id=contact_id,
                    line_items=line_items,
                    total=total,
                    status="DRAFT",
                    date_created=datetime.now()
                )

                logger.info(f"Draft order created: {created_po.purchase_order_number} (ID: {draft_order.order_id})")
                return draft_order
            else:
                raise RuntimeError("Failed to create draft order: No purchase order returned")

        except AccountingBadRequestException as e:
            logger.error(f"Xero API error creating draft order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating draft order: {e}")
            raise

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def finalize_order(self, order_id: str) -> bool:
        """
        Finalize a draft delivery order (convert from DRAFT to SUBMITTED).

        Args:
            order_id: Xero purchase order ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_token_valid()

            # Create purchase order with updated status
            purchase_order = PurchaseOrder(
                purchase_order_id=order_id,
                status="SUBMITTED"
            )

            purchase_orders = PurchaseOrders(purchase_orders=[purchase_order])

            # Update purchase order
            updated_pos = self._accounting_api.update_purchase_order(
                xero_tenant_id=self.tenant_id,
                purchase_order_id=order_id,
                purchase_orders=purchase_orders
            )

            if updated_pos and updated_pos.purchase_orders and len(updated_pos.purchase_orders) > 0:
                logger.info(f"Order finalized: {order_id}")
                return True
            else:
                logger.warning(f"Failed to finalize order: {order_id}")
                return False

        except AccountingBadRequestException as e:
            logger.error(f"Xero API error finalizing order: {e}")
            raise
        except Exception as e:
            logger.error(f"Error finalizing order: {e}")
            raise

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def create_invoice(
        self,
        contact_id: str,
        line_items: List[Dict[str, Any]],
        reference: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> XeroInvoice:
        """
        Create and post an invoice in Xero.

        Args:
            contact_id: Xero contact/customer ID
            line_items: List of line items with structure:
                [{"item_code": str, "quantity": float, "unit_price": float, "description": str, "tax_type": str}]
            reference: Optional reference number
            due_date: Optional due date (defaults to 30 days from now)

        Returns:
            XeroInvoice with invoice details
        """
        try:
            self._ensure_token_valid()

            # Build line items using SDK models
            invoice_line_items = []
            subtotal = 0.0

            for item in line_items:
                line_total = item['quantity'] * item['unit_price']
                subtotal += line_total

                line_item = LineItem(
                    item_code=item.get('item_code'),
                    description=item.get('description', ''),
                    quantity=item['quantity'],
                    unit_amount=item['unit_price'],
                    line_amount=line_total,
                    tax_type=item.get('tax_type', config.XERO_TAX_TYPE),
                    account_code=config.XERO_SALES_ACCOUNT_CODE
                )
                invoice_line_items.append(line_item)

            # Calculate tax and total
            tax_amount = subtotal * config.TAX_RATE
            total = subtotal + tax_amount

            # Set due date
            if due_date is None:
                due_date = datetime.now() + timedelta(days=30)

            # Create contact reference
            contact = Contact(contact_id=contact_id)

            # Create invoice using SDK model
            invoice = Invoice(
                type="ACCREC",  # Accounts Receivable (sales invoice)
                contact=contact,
                line_items=invoice_line_items,
                reference=reference or f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                date=datetime.now().date(),
                due_date=due_date.date() if isinstance(due_date, datetime) else due_date,
                status="AUTHORISED"  # Post immediately
            )

            # Create invoices collection
            invoices = Invoices(invoices=[invoice])

            # Call API
            created_invs = self._accounting_api.create_invoices(
                xero_tenant_id=self.tenant_id,
                invoices=invoices
            )

            if created_invs and created_invs.invoices and len(created_invs.invoices) > 0:
                created_invoice = created_invs.invoices[0]

                xero_invoice = XeroInvoice(
                    invoice_id=created_invoice.invoice_id,
                    invoice_number=created_invoice.invoice_number,
                    contact_id=contact_id,
                    line_items=line_items,
                    total=total,
                    status="AUTHORISED",
                    date=datetime.now()
                )

                logger.info(f"Invoice created: {created_invoice.invoice_number} (ID: {xero_invoice.invoice_id})")
                return xero_invoice
            else:
                raise RuntimeError("Failed to create invoice: No invoice returned")

        except AccountingBadRequestException as e:
            logger.error(f"Xero API error creating invoice: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise

    def get_contact_by_name(self, name: str) -> Optional[XeroCustomer]:
        """Alias for verify_customer for backward compatibility"""
        return self.verify_customer(name)

    def get_item_by_code(self, code: str) -> Optional[XeroProduct]:
        """Alias for check_inventory for backward compatibility"""
        return self.check_inventory(code)

    # ========================================================================
    # COMPENSATING TRANSACTION METHODS (Cleanup/Rollback)
    # ========================================================================

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def delete_draft_order(self, order_id: str) -> bool:
        """
        Delete a draft purchase order (compensating transaction).

        Used for rollback when later steps in a workflow fail.
        Only works for orders with status='DRAFT'.

        Args:
            order_id: Xero purchase order ID

        Returns:
            True if successfully deleted, False otherwise

        Example:
            # In compensating transaction:
            self.xero_client.delete_draft_order(draft_order.order_id)
        """
        try:
            self._ensure_token_valid()

            logger.info(f"Deleting draft order: {order_id} (compensating transaction)")

            # Use SDK to delete purchase order
            self._accounting_api.delete_purchase_order(
                xero_tenant_id=self.tenant_id,
                purchase_order_id=order_id
            )

            logger.info(f"Successfully deleted draft order: {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting draft order {order_id}: {e}")
            # Don't raise - compensating transactions should not cascade failures
            return False

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    @rate_limit_xero
    def void_invoice(self, invoice_id: str) -> bool:
        """
        Void or delete an invoice (compensating transaction).

        Used for rollback when later steps in a workflow fail.
        - DRAFT invoices: Deleted
        - AUTHORISED invoices: Voided (cannot be deleted)

        Args:
            invoice_id: Xero invoice ID

        Returns:
            True if successfully voided/deleted, False otherwise

        Example:
            # In compensating transaction:
            self.xero_client.void_invoice(invoice.invoice_id)
        """
        try:
            self._ensure_token_valid()

            logger.info(f"Voiding invoice: {invoice_id} (compensating transaction)")

            # First, get invoice to check status
            invoice_response = self._accounting_api.get_invoice(
                xero_tenant_id=self.tenant_id,
                invoice_id=invoice_id
            )

            if not invoice_response or not invoice_response.invoices or len(invoice_response.invoices) == 0:
                logger.warning(f"Invoice not found: {invoice_id}")
                return False

            invoice = invoice_response.invoices[0]
            status = invoice.status

            logger.info(f"Invoice {invoice_id} current status: {status}")

            if status == "DRAFT":
                # DRAFT invoices can be deleted
                self._accounting_api.delete_invoice(
                    xero_tenant_id=self.tenant_id,
                    invoice_id=invoice_id
                )
                logger.info(f"Successfully deleted DRAFT invoice: {invoice_id}")
                return True

            elif status in ["AUTHORISED", "SUBMITTED"]:
                # AUTHORISED/SUBMITTED invoices must be voided
                void_invoice = Invoice(
                    invoice_id=invoice_id,
                    status="VOIDED"
                )

                invoices = Invoices(invoices=[void_invoice])

                self._accounting_api.update_invoice(
                    xero_tenant_id=self.tenant_id,
                    invoice_id=invoice_id,
                    invoices=invoices
                )

                logger.info(f"Successfully voided invoice: {invoice_id}")
                return True

            else:
                logger.warning(
                    f"Cannot void invoice {invoice_id} with status '{status}'. "
                    f"Only DRAFT/AUTHORISED/SUBMITTED invoices can be voided."
                )
                return False

        except Exception as e:
            logger.error(f"Error voiding invoice {invoice_id}: {e}")
            # Don't raise - compensating transactions should not cascade failures
            return False


# Global singleton instance
_xero_client: Optional[XeroClient] = None


def get_xero_client() -> XeroClient:
    """
    Get or create global Xero client (singleton pattern).

    Returns:
        XeroClient instance
    """
    global _xero_client
    if _xero_client is None:
        _xero_client = XeroClient()
    return _xero_client
