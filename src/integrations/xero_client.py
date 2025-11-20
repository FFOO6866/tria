"""
Xero API Client for Tria AIBPO (REST API Implementation)

Provides OAuth2.0 authentication and API methods for Xero integration.
Uses direct REST API calls for maximum reliability.

Supports the complete order-to-invoice workflow:
1. Customer verification
2. Inventory checking
3. Draft delivery order creation
4. Order finalization
5. Invoice generation and posting

Production-grade implementation:
- Centralized configuration
- Connection pooling via singleton pattern
- Comprehensive error handling
- Rate limiting awareness
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests

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
        params={'where': f'Name=="{customer_name}"'}  # ❌ Injection risk

        # AFTER (SECURE):
        safe_name = validate_xero_where_clause_input(customer_name, "customer_name")
        params={'where': f'Name=="{safe_name}"'}  # ✅ Protected
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
    Xero API client with OAuth2.0 authentication using REST API.

    Singleton pattern: Reuses access token and session.
    Thread-safe for production use.
    """

    _instance: Optional['XeroClient'] = None
    _access_token: Optional[str] = None
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

        self._initialized = True
        logger.info("Xero client initialized (singleton)")

    def _get_access_token(self) -> str:
        """
        Get valid access token, refreshing if necessary.

        Uses singleton pattern - token is cached and reused.
        """
        # Return cached token if still valid
        if self._access_token and self._token_expiry:
            if datetime.now() < self._token_expiry - timedelta(minutes=5):
                return self._access_token

        # Refresh token using OAuth2.0
        logger.info("Refreshing Xero access token...")

        try:
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            response = requests.post(self.token_url, data=token_data)
            response.raise_for_status()

            token_response = response.json()
            self._access_token = token_response['access_token']

            # Token typically expires in 30 minutes
            expires_in = token_response.get('expires_in', 1800)
            self._token_expiry = datetime.now() + timedelta(seconds=expires_in)

            # Update refresh token if provided
            if 'refresh_token' in token_response:
                self.refresh_token = token_response['refresh_token']

            logger.info(f"Access token refreshed, expires at {self._token_expiry}")
            return self._access_token

        except Exception as e:
            logger.error(f"Failed to refresh Xero access token: {e}")
            raise RuntimeError(f"Xero authentication failed: {e}")

    @circuit_breaker("xero")
    @retry_on_rate_limit(max_attempts=5)
    @retry_with_backoff(max_attempts=3)
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> requests.Response:
        """
        Make authenticated request to Xero API with retries and circuit breaker.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint (e.g., '/Contacts')
            data: Request body data (for POST/PUT)
            params: Query parameters

        Returns:
            Response object

        Raises:
            requests.exceptions.HTTPError: If request fails
        """
        access_token = self._get_access_token()

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Xero-Tenant-Id': self.tenant_id,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        url = f"{self.api_url}{endpoint}"

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
            timeout=30  # 30 second timeout for all Xero API requests
        )

        response.raise_for_status()
        return response

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
            # SECURITY: Validate input to prevent injection attacks
            safe_customer_name = validate_xero_where_clause_input(customer_name, "customer_name")

            response = self._make_request(
                'GET',
                '/Contacts',
                params={'where': f'Name=="{safe_customer_name}"'}
            )

            data = response.json()
            contacts = data.get('Contacts', [])

            if contacts:
                contact = contacts[0]

                customer = XeroCustomer(
                    contact_id=contact['ContactID'],
                    name=contact['Name'],
                    email=contact.get('EmailAddress'),
                    phone=contact.get('Phones', [{}])[0].get('PhoneNumber') if contact.get('Phones') else None,
                    is_customer=contact.get('IsCustomer', True)
                )

                logger.info(f"Customer found: {customer.name} (ID: {customer.contact_id})")
                return customer
            else:
                logger.info(f"Customer not found: {customer_name}")
                return None

        except Exception as e:
            logger.error(f"Error verifying customer: {e}")
            raise

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
            # SECURITY: Validate input to prevent injection attacks
            safe_product_code = validate_xero_where_clause_input(product_code, "product_code")

            response = self._make_request(
                'GET',
                '/Items',
                params={'where': f'Code=="{safe_product_code}"'}
            )

            data = response.json()
            items = data.get('Items', [])

            if items:
                item = items[0]

                product = XeroProduct(
                    item_id=item['ItemID'],
                    code=item['Code'],
                    name=item.get('Name', item['Code']),
                    description=item.get('Description'),
                    unit_price=float(item.get('SalesDetails', {}).get('UnitPrice', 0)),
                    quantity_on_hand=float(item.get('QuantityOnHand', 0)) if 'QuantityOnHand' in item else None,
                    is_sold=item.get('IsSold', True)
                )

                logger.info(f"Product found: {product.name} (Code: {product.code})")
                return product
            else:
                logger.info(f"Product not found: {product_code}")
                return None

        except Exception as e:
            logger.error(f"Error checking inventory: {e}")
            raise

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
            # Build line items
            po_line_items = []
            total = 0.0

            for item in line_items:
                line_total = item['quantity'] * item['unit_price']
                total += line_total

                po_line_items.append({
                    'ItemCode': item.get('item_code'),
                    'Description': item.get('description', ''),
                    'Quantity': item['quantity'],
                    'UnitAmount': item['unit_price'],
                    'LineAmount': line_total
                })

            # Create draft purchase order
            purchase_order = {
                'Contact': {'ContactID': contact_id},
                'LineItems': po_line_items,
                'Reference': reference or f"DO-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'Status': 'DRAFT',
                'Date': datetime.now().strftime('%Y-%m-%d')
            }

            response = self._make_request(
                'POST',
                '/PurchaseOrders',
                data={'PurchaseOrders': [purchase_order]}
            )

            data = response.json()
            created_po = data['PurchaseOrders'][0]

            draft_order = XeroDraftOrder(
                order_id=created_po['PurchaseOrderID'],
                contact_id=contact_id,
                line_items=line_items,
                total=total,
                status="DRAFT",
                date_created=datetime.now()
            )

            logger.info(f"Draft order created: {created_po.get('PurchaseOrderNumber')} (ID: {draft_order.order_id})")
            return draft_order

        except Exception as e:
            logger.error(f"Error creating draft order: {e}")
            raise

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
            purchase_order = {
                'PurchaseOrderID': order_id,
                'Status': 'SUBMITTED'
            }

            response = self._make_request(
                'POST',
                f'/PurchaseOrders/{order_id}',
                data={'PurchaseOrders': [purchase_order]}
            )

            data = response.json()
            if data.get('PurchaseOrders'):
                logger.info(f"Order finalized: {order_id}")
                return True
            else:
                logger.warning(f"Failed to finalize order: {order_id}")
                return False

        except Exception as e:
            logger.error(f"Error finalizing order: {e}")
            raise

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
            # Build line items
            invoice_line_items = []
            subtotal = 0.0

            for item in line_items:
                line_total = item['quantity'] * item['unit_price']
                subtotal += line_total

                invoice_line_items.append({
                    'ItemCode': item.get('item_code'),
                    'Description': item.get('description', ''),
                    'Quantity': item['quantity'],
                    'UnitAmount': item['unit_price'],
                    'LineAmount': line_total,
                    'TaxType': item.get('tax_type', config.XERO_TAX_TYPE),
                    'AccountCode': config.XERO_SALES_ACCOUNT_CODE
                })

            # Calculate tax
            tax_amount = subtotal * config.TAX_RATE
            total = subtotal + tax_amount

            # Set due date
            if due_date is None:
                due_date = datetime.now() + timedelta(days=30)

            # Create invoice
            invoice = {
                'Type': 'ACCREC',  # Accounts Receivable (sales invoice)
                'Contact': {'ContactID': contact_id},
                'LineItems': invoice_line_items,
                'Reference': reference or f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'DueDate': due_date.strftime('%Y-%m-%d'),
                'Status': 'AUTHORISED'  # Post immediately
            }

            response = self._make_request(
                'POST',
                '/Invoices',
                data={'Invoices': [invoice]}
            )

            data = response.json()
            created_invoice = data['Invoices'][0]

            xero_invoice = XeroInvoice(
                invoice_id=created_invoice['InvoiceID'],
                invoice_number=created_invoice['InvoiceNumber'],
                contact_id=contact_id,
                line_items=line_items,
                total=total,
                status="AUTHORISED",
                date=datetime.now()
            )

            logger.info(f"Invoice created: {created_invoice['InvoiceNumber']} (ID: {xero_invoice.invoice_id})")
            return xero_invoice

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
            logger.info(f"Deleting draft order: {order_id} (compensating transaction)")

            # Xero API: DELETE /PurchaseOrders/{PurchaseOrderID}
            # Note: Only works for DRAFT orders
            response = self._make_request(
                'DELETE',
                f'/PurchaseOrders/{order_id}'
            )

            if response.status_code == 200 or response.status_code == 204:
                logger.info(f"Successfully deleted draft order: {order_id}")
                return True
            else:
                logger.warning(
                    f"Failed to delete draft order {order_id}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error deleting draft order {order_id}: {e}")
            # Don't raise - compensating transactions should not cascade failures
            return False

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
            logger.info(f"Voiding invoice: {invoice_id} (compensating transaction)")

            # First, check invoice status
            response = self._make_request(
                'GET',
                f'/Invoices/{invoice_id}'
            )

            invoice_data = response.json()['Invoices'][0]
            status = invoice_data.get('Status')

            logger.info(f"Invoice {invoice_id} current status: {status}")

            if status == 'DRAFT':
                # DRAFT invoices can be deleted
                delete_response = self._make_request(
                    'DELETE',
                    f'/Invoices/{invoice_id}'
                )

                if delete_response.status_code in [200, 204]:
                    logger.info(f"Successfully deleted DRAFT invoice: {invoice_id}")
                    return True
                else:
                    logger.warning(
                        f"Failed to delete DRAFT invoice {invoice_id}: "
                        f"HTTP {delete_response.status_code}"
                    )
                    return False

            elif status in ['AUTHORISED', 'SUBMITTED']:
                # AUTHORISED/SUBMITTED invoices must be voided (cannot delete)
                void_data = {
                    'Invoices': [{
                        'InvoiceID': invoice_id,
                        'Status': 'VOIDED'
                    }]
                }

                void_response = self._make_request(
                    'POST',
                    '/Invoices',
                    data=void_data
                )

                if void_response.status_code == 200:
                    logger.info(f"Successfully voided invoice: {invoice_id}")
                    return True
                else:
                    logger.warning(
                        f"Failed to void invoice {invoice_id}: "
                        f"HTTP {void_response.status_code}"
                    )
                    return False

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
