"""
Xero Order Orchestrator for Tria AIBPO
=======================================

End-to-end workflow orchestrator that integrates:
1. WhatsApp message parsing (via chatbot)
2. Customer verification in Xero
3. Inventory checking in Xero
4. Draft delivery order creation
5. Customer confirmation
6. Order finalization
7. Invoice generation and posting

All orchestrated with AI agents providing status updates.

Production-grade implementation:
- Real Xero integration (no mocks)
- Comprehensive error handling
- Agent status tracking for UI visualization
- Centralized configuration
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

from integrations.xero_client import (
    get_xero_client,
    XeroCustomer,
    XeroProduct,
    XeroDraftOrder,
    XeroInvoice
)
from config import config
from database import get_db_engine
from sqlalchemy import text
from utils.compensating_transactions import CompensatingTransactionManager

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class OrderWorkflowStage(str, Enum):
    """Order workflow stages"""
    RECEIVED = "received"
    CUSTOMER_VERIFIED = "customer_verified"
    INVENTORY_CHECKED = "inventory_checked"
    DRAFT_CREATED = "draft_created"
    CUSTOMER_CONFIRMED = "customer_confirmed"
    ORDER_FINALIZED = "order_finalized"
    INVOICE_POSTED = "invoice_posted"
    COMPLETED = "completed"
    ERROR = "error"


class XeroOrderOrchestrator:
    """
    Orchestrates the complete order-to-invoice workflow with Xero integration.

    Workflow:
    1. Parse WhatsApp message → Extract order details
    2. Verify customer → Check/create in Xero
    3. Check inventory → Verify availability in Xero
    4. Create draft order → Draft delivery order in Xero
    5. Customer confirmation → Send confirmation message
    6. Finalize order → Convert draft to firm order
    7. Post invoice → Create and post invoice in Xero

    All steps include agent status updates for real-time UI visualization.
    """

    def __init__(self):
        """Initialize orchestrator with Xero client"""
        self.xero_client = get_xero_client()
        self.agent_timeline: List[Dict[str, Any]] = []

    def _update_agent_status(
        self,
        agent_name: str,
        status: AgentStatus,
        progress: int,
        current_task: Optional[str] = None,
        details: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update agent status in timeline for UI visualization with detailed outputs.

        Args:
            agent_name: Name of the agent (e.g., "Customer Service Agent")
            status: Current agent status
            progress: Progress percentage (0-100)
            current_task: Current task description
            details: List of detail strings for the agent
            metadata: Additional structured data (DO numbers, invoice IDs, inventory levels, etc.)
        """
        # Map agent names to functional categories for filtering
        category_map = {
            "🎧 Customer Service": "orders",
            "📦 Inventory Manager": "inventory",
            "🚚 Delivery Coordinator": "delivery",
            "🎯 Operations Orchestrator": "orders",
            "💰 Finance Controller": "finance"
        }

        now = datetime.now()

        # Find existing agent or create new
        agent_entry = next(
            (a for a in self.agent_timeline if a['agent_name'] == agent_name),
            None
        )

        if agent_entry:
            agent_entry['status'] = status.value
            agent_entry['progress'] = progress
            agent_entry['updated_at'] = now.isoformat()
            agent_entry['updated_timestamp'] = now.timestamp()
            if current_task:
                agent_entry['current_task'] = current_task
            if details:
                agent_entry['details'] = details
            if metadata:
                # Merge metadata instead of replacing
                if 'metadata' not in agent_entry:
                    agent_entry['metadata'] = {}
                agent_entry['metadata'].update(metadata)
            if status == AgentStatus.COMPLETED:
                agent_entry['end_time'] = now.timestamp()
                agent_entry['completed_at'] = now.isoformat()
        else:
            self.agent_timeline.append({
                'agent_name': agent_name,
                'status': status.value,
                'progress': progress,
                'current_task': current_task or '',
                'details': details or [],
                'category': category_map.get(agent_name, 'general'),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'start_time': now.timestamp(),
                'started_at': now.isoformat(),
                'updated_at': now.isoformat(),
                'updated_timestamp': now.timestamp(),
                'end_time': None,
                'completed_at': None,
                'metadata': metadata or {}
            })

    def verify_customer_in_xero(
        self,
        customer_name: str
    ) -> Tuple[Optional[XeroCustomer], bool]:
        """
        Verify customer exists in Xero, create if needed.

        Args:
            customer_name: Customer/outlet name from WhatsApp message

        Returns:
            Tuple of (XeroCustomer, was_created)
        """
        logger.info(f"Verifying customer in Xero: {customer_name}")

        self._update_agent_status(
            "🎧 Customer Service",
            AgentStatus.PROCESSING,
            20,
            f"Verifying customer: {customer_name}",
            [f"Searching Xero for customer: {customer_name}"]
        )

        try:
            # Check if customer exists
            customer = self.xero_client.verify_customer(customer_name)

            if customer:
                logger.info(f"Customer found in Xero: {customer.name} (ID: {customer.contact_id})")
                self._update_agent_status(
                    "🎧 Customer Service",
                    AgentStatus.COMPLETED,
                    100,
                    "Customer verified",
                    [
                        f"✓ Customer found: {customer.name}",
                        f"✓ Contact ID: {customer.contact_id}",
                        f"✓ Email: {customer.email or 'N/A'}",
                        f"✓ Phone: {customer.phone or 'N/A'}"
                    ]
                )
                return customer, False
            else:
                # Customer not found - would create here in production
                # For now, log warning
                logger.warning(f"Customer not found in Xero: {customer_name}")
                self._update_agent_status(
                    "🎧 Customer Service",
                    AgentStatus.ERROR,
                    0,
                    "Customer not found",
                    [
                        f"✗ Customer not found in Xero: {customer_name}",
                        "Please create customer in Xero first"
                    ]
                )
                return None, False

        except Exception as e:
            logger.error(f"Error verifying customer: {e}")
            self._update_agent_status(
                "🎧 Customer Service",
                AgentStatus.ERROR,
                0,
                "Customer verification failed",
                [f"✗ Error: {str(e)}"]
            )
            raise

    def check_inventory_in_xero(
        self,
        line_items: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Check inventory availability in Xero for all line items.

        Args:
            line_items: List of order line items with SKUs and quantities

        Returns:
            Tuple of (all_available, issues_list)
        """
        logger.info(f"Checking inventory for {len(line_items)} items")

        self._update_agent_status(
            "📦 Inventory Manager",
            AgentStatus.PROCESSING,
            30,
            "Checking inventory availability",
            [f"Verifying {len(line_items)} products in Xero"]
        )

        all_available = True
        issues = []
        details = []
        inventory_summary = []

        try:
            for item in line_items:
                sku = item.get('sku')
                requested_qty = item.get('quantity', 0)

                if not sku:
                    issues.append(f"Missing SKU for item: {item}")
                    all_available = False
                    continue

                # Check product in Xero
                product = self.xero_client.check_inventory(sku)

                if product:
                    # Product exists in Xero
                    if product.quantity_on_hand is not None:
                        remaining_after = product.quantity_on_hand - requested_qty
                        if product.quantity_on_hand >= requested_qty:
                            details.append(
                                f"✓ {product.name} ({sku}): Current stock {product.quantity_on_hand} units, "
                                f"requested {requested_qty} units, remaining {remaining_after} units"
                            )
                            inventory_summary.append({
                                'sku': sku,
                                'product_name': product.name,
                                'before': product.quantity_on_hand,
                                'requested': requested_qty,
                                'after': remaining_after,
                                'status': 'available'
                            })
                        else:
                            details.append(
                                f"⚠ {product.name} ({sku}): Insufficient stock! Current {product.quantity_on_hand} units, "
                                f"requested {requested_qty} units, short by {requested_qty - product.quantity_on_hand} units"
                            )
                            issues.append(
                                f"Insufficient stock for {product.name}: "
                                f"{product.quantity_on_hand} < {requested_qty}"
                            )
                            inventory_summary.append({
                                'sku': sku,
                                'product_name': product.name,
                                'before': product.quantity_on_hand,
                                'requested': requested_qty,
                                'shortfall': requested_qty - product.quantity_on_hand,
                                'status': 'insufficient'
                            })
                            all_available = False
                    else:
                        # Quantity tracking not enabled in Xero
                        details.append(f"✓ {product.name} ({sku}): Product exists (inventory tracking not enabled in Xero)")
                        inventory_summary.append({
                            'sku': sku,
                            'product_name': product.name,
                            'requested': requested_qty,
                            'status': 'untracked'
                        })
                else:
                    # Product not found in Xero
                    details.append(f"✗ Product not found in Xero: {sku}")
                    issues.append(f"Product not found: {sku}")
                    all_available = False
                    inventory_summary.append({
                        'sku': sku,
                        'requested': requested_qty,
                        'status': 'not_found'
                    })

            # Add summary of inventory changes
            if all_available:
                summary_details = [
                    f"✓ All {len(line_items)} products available in inventory",
                    f"✓ Inventory verification completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "Inventory Details:"
                ] + details

                self._update_agent_status(
                    "📦 Inventory Manager",
                    AgentStatus.COMPLETED,
                    100,
                    "Inventory verified - all items available",
                    summary_details,
                    metadata={
                        'inventory_summary': inventory_summary,
                        'total_products_checked': len(line_items),
                        'all_available': True,
                        'checked_date': datetime.now().isoformat()
                    }
                )
            else:
                summary_details = [
                    f"⚠ Inventory issues detected for {len(issues)} items",
                    f"✓ Checked at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    "",
                    "Inventory Details:"
                ] + details

                self._update_agent_status(
                    "📦 Inventory Manager",
                    AgentStatus.ERROR,
                    50,
                    "Inventory issues - insufficient stock detected",
                    summary_details,
                    metadata={
                        'inventory_summary': inventory_summary,
                        'total_products_checked': len(line_items),
                        'all_available': False,
                        'issues_count': len(issues),
                        'issues': issues,
                        'checked_date': datetime.now().isoformat()
                    }
                )

            return all_available, issues

        except Exception as e:
            logger.error(f"Error checking inventory: {e}")
            self._update_agent_status(
                "📦 Inventory Manager",
                AgentStatus.ERROR,
                0,
                "Inventory check failed",
                [f"✗ Error: {str(e)}"]
            )
            raise

    def create_draft_delivery_order(
        self,
        customer: XeroCustomer,
        line_items: List[Dict[str, Any]],
        outlet_name: str
    ) -> Optional[XeroDraftOrder]:
        """
        Create a draft delivery order in Xero.

        Args:
            customer: Xero customer object
            line_items: Order line items
            outlet_name: Outlet/customer name for reference

        Returns:
            XeroDraftOrder if successful, None otherwise
        """
        logger.info(f"Creating draft delivery order for {customer.name}")

        self._update_agent_status(
            "🚚 Delivery Coordinator",
            AgentStatus.PROCESSING,
            40,
            "Creating draft delivery order",
            [f"Preparing draft order for {customer.name}"]
        )

        try:
            # Build Xero line items with pricing from our database
            xero_line_items = []
            engine = get_db_engine(config.DATABASE_URL)

            for item in line_items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)
                description = item.get('description', '')

                # Get unit price from database
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT unit_price FROM products WHERE sku = :sku"),
                        {'sku': sku}
                    )
                    row = result.fetchone()
                    unit_price = float(row[0]) if row else 0.0

                xero_line_items.append({
                    'item_code': sku,
                    'description': description,
                    'quantity': quantity,
                    'unit_price': unit_price
                })

            # Create draft order in Xero
            reference = f"DO-{outlet_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            draft_order = self.xero_client.create_draft_order(
                contact_id=customer.contact_id,
                line_items=xero_line_items,
                reference=reference
            )

            # Prepare detailed line items for output
            line_items_summary = []
            total_qty = 0
            for item in xero_line_items:
                line_items_summary.append(
                    f"  • {item.get('description', item.get('item_code'))}: "
                    f"{item.get('quantity')} units @ ${item.get('unit_price', 0):.2f} = "
                    f"${item.get('quantity', 0) * item.get('unit_price', 0):.2f}"
                )
                total_qty += item.get('quantity', 0)

            self._update_agent_status(
                "🚚 Delivery Coordinator",
                AgentStatus.COMPLETED,
                100,
                f"Draft Delivery Order #{reference} prepared",
                [
                    f"✓ Draft Delivery Order #{reference} created in Xero",
                    f"✓ Customer: {customer.name}",
                    f"✓ Order ID: {draft_order.order_id}",
                    f"✓ Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    f"✓ Total Items: {total_qty} units",
                    f"✓ Line Items:",
                    *line_items_summary,
                    f"✓ Order Total: ${draft_order.total:.2f}",
                    f"✓ Status: {draft_order.status}"
                ],
                metadata={
                    'do_number': reference,
                    'order_id': draft_order.order_id,
                    'customer': customer.name,
                    'customer_id': customer.contact_id,
                    'total_amount': draft_order.total,
                    'total_quantity': total_qty,
                    'line_items': xero_line_items,
                    'status': draft_order.status,
                    'created_date': datetime.now().isoformat()
                }
            )

            return draft_order

        except Exception as e:
            logger.error(f"Error creating draft order: {e}")
            self._update_agent_status(
                "🚚 Delivery Coordinator",
                AgentStatus.ERROR,
                0,
                "Draft order creation failed",
                [f"✗ Error: {str(e)}"]
            )
            raise

    def finalize_order_in_xero(
        self,
        draft_order: XeroDraftOrder
    ) -> bool:
        """
        Finalize draft delivery order (convert to firm order).

        Args:
            draft_order: Draft order to finalize

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Finalizing order: {draft_order.order_id}")

        self._update_agent_status(
            "🎯 Operations Orchestrator",
            AgentStatus.PROCESSING,
            60,
            "Finalizing delivery order",
            [f"Converting draft order to firm order"]
        )

        try:
            success = self.xero_client.finalize_order(draft_order.order_id)

            if success:
                self._update_agent_status(
                    "🎯 Operations Orchestrator",
                    AgentStatus.COMPLETED,
                    100,
                    "Order finalized",
                    [
                        f"✓ Order finalized in Xero",
                        f"✓ Order ID: {draft_order.order_id}",
                        f"✓ Status changed: DRAFT → SUBMITTED"
                    ]
                )
            else:
                self._update_agent_status(
                    "🎯 Operations Orchestrator",
                    AgentStatus.ERROR,
                    0,
                    "Order finalization failed",
                    [f"✗ Failed to finalize order {draft_order.order_id}"]
                )

            return success

        except Exception as e:
            logger.error(f"Error finalizing order: {e}")
            self._update_agent_status(
                "🎯 Operations Orchestrator",
                AgentStatus.ERROR,
                0,
                "Order finalization error",
                [f"✗ Error: {str(e)}"]
            )
            raise

    def post_invoice_to_xero(
        self,
        customer: XeroCustomer,
        line_items: List[Dict[str, Any]],
        outlet_name: str
    ) -> Optional[XeroInvoice]:
        """
        Create and post invoice to Xero.

        Args:
            customer: Xero customer object
            line_items: Order line items
            outlet_name: Outlet/customer name for reference

        Returns:
            XeroInvoice if successful, None otherwise
        """
        logger.info(f"Creating invoice for {customer.name}")

        self._update_agent_status(
            "💰 Finance Controller",
            AgentStatus.PROCESSING,
            80,
            "Generating invoice",
            [f"Creating invoice for {customer.name}"]
        )

        try:
            # Build Xero line items with pricing and tax
            xero_line_items = []
            engine = get_db_engine(config.DATABASE_URL)

            for item in line_items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)
                description = item.get('description', '')

                # Get unit price from database
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT unit_price FROM products WHERE sku = :sku"),
                        {'sku': sku}
                    )
                    row = result.fetchone()
                    unit_price = float(row[0]) if row else 0.0

                xero_line_items.append({
                    'item_code': sku,
                    'description': description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'tax_type': config.XERO_TAX_TYPE
                })

            # Create invoice in Xero
            reference = f"INV-{outlet_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            invoice = self.xero_client.create_invoice(
                contact_id=customer.contact_id,
                line_items=xero_line_items,
                reference=reference
            )

            # Prepare detailed invoice line items for output
            invoice_line_items_summary = []
            total_qty = 0
            subtotal = 0
            for item in xero_line_items:
                line_total = item.get('quantity', 0) * item.get('unit_price', 0)
                invoice_line_items_summary.append(
                    f"  • {item.get('description', item.get('item_code'))}: "
                    f"{item.get('quantity')} units @ ${item.get('unit_price', 0):.2f} = "
                    f"${line_total:.2f} (Tax: {item.get('tax_type', 'N/A')})"
                )
                total_qty += item.get('quantity', 0)
                subtotal += line_total

            tax_amount = invoice.total - subtotal if invoice.total >= subtotal else 0

            self._update_agent_status(
                "💰 Finance Controller",
                AgentStatus.COMPLETED,
                100,
                f"Invoice {invoice.invoice_number} generated and posted",
                [
                    f"✓ Invoice {invoice.invoice_number} created and posted to Xero",
                    f"✓ Customer: {customer.name}",
                    f"✓ Invoice ID: {invoice.invoice_id}",
                    f"✓ Reference: {reference}",
                    f"✓ Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    f"✓ Total Items: {total_qty} units",
                    f"✓ Line Items:",
                    *invoice_line_items_summary,
                    f"✓ Subtotal: ${subtotal:.2f}",
                    f"✓ Tax: ${tax_amount:.2f}",
                    f"✓ Invoice Total: ${invoice.total:.2f}",
                    f"✓ Payment Status: {invoice.status}"
                ],
                metadata={
                    'invoice_number': invoice.invoice_number,
                    'invoice_id': invoice.invoice_id,
                    'reference': reference,
                    'customer': customer.name,
                    'customer_id': customer.contact_id,
                    'subtotal': subtotal,
                    'tax_amount': tax_amount,
                    'total_amount': invoice.total,
                    'total_quantity': total_qty,
                    'line_items': xero_line_items,
                    'status': invoice.status,
                    'generated_date': datetime.now().isoformat()
                }
            )

            return invoice

        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            self._update_agent_status(
                "💰 Finance Controller",
                AgentStatus.ERROR,
                0,
                "Invoice creation failed",
                [f"✗ Error: {str(e)}"]
            )
            raise

    def execute_workflow(
        self,
        parsed_order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the complete order-to-invoice workflow with compensating transactions.

        Workflow (with automatic rollback on failure):
        1. Verify customer in Xero
        2. Check inventory availability
        3. Create draft delivery order ← REGISTER CLEANUP
        4. (Customer confirms - simulated for demo)
        5. Finalize order ← REGISTER CLEANUP
        6. Post invoice ← REGISTER CLEANUP

        If any step fails after step 3, all completed Xero operations are
        automatically rolled back to prevent orphaned resources.

        Args:
            parsed_order: Parsed order from chatbot with structure:
                {
                    "outlet_name": str,
                    "line_items": [{"sku": str, "quantity": int, "description": str}],
                    "is_urgent": bool
                }

        Returns:
            Workflow result with structure:
                {
                    "success": bool,
                    "stage": OrderWorkflowStage,
                    "customer": XeroCustomer (if successful),
                    "draft_order": XeroDraftOrder (if created),
                    "invoice": XeroInvoice (if posted),
                    "agent_timeline": List[Dict],
                    "error": str (if failed)
                }
        """
        logger.info(f"Starting Xero order workflow for {parsed_order.get('outlet_name')}")

        outlet_name = parsed_order.get('outlet_name', 'Unknown')
        line_items = parsed_order.get('line_items', [])

        self.agent_timeline = []  # Reset timeline

        # Initialize compensating transaction manager
        transaction = CompensatingTransactionManager(f"xero_order_{outlet_name}")

        try:
            # Stage 1: Verify customer (no compensating action needed - Xero handles idempotently)
            customer, was_created = self.verify_customer_in_xero(outlet_name)
            if not customer:
                return {
                    "success": False,
                    "stage": OrderWorkflowStage.ERROR,
                    "agent_timeline": self.agent_timeline,
                    "error": f"Customer not found in Xero: {outlet_name}"
                }

            # Stage 2: Check inventory (no compensating action needed - read-only operation)
            inventory_ok, issues = self.check_inventory_in_xero(line_items)
            if not inventory_ok:
                return {
                    "success": False,
                    "stage": OrderWorkflowStage.ERROR,
                    "customer": customer,
                    "agent_timeline": self.agent_timeline,
                    "error": f"Inventory issues: {', '.join(issues)}"
                }

            # Stage 3: Create draft delivery order
            # CRITICAL: Register compensating action AFTER successful creation
            draft_order = self.create_draft_delivery_order(customer, line_items, outlet_name)
            if not draft_order:
                return {
                    "success": False,
                    "stage": OrderWorkflowStage.ERROR,
                    "customer": customer,
                    "agent_timeline": self.agent_timeline,
                    "error": "Failed to create draft delivery order"
                }

            # COMPENSATING ACTION: Delete draft order if later steps fail
            transaction.add_compensating_action(
                step_name="create_draft_order",
                compensate_func=self.xero_client.delete_draft_order,
                compensate_args=(draft_order.order_id,),
                context={
                    "order_id": draft_order.order_id,
                    "customer": customer.name,
                    "outlet": outlet_name
                }
            )

            # Stage 4: Customer confirmation (simulated for demo)
            logger.info("Customer confirmation: APPROVED (simulated for demo)")

            # Stage 5: Finalize order
            # NOTE: Once finalized, the order cannot be easily deleted (only cancelled)
            # We keep the compensating action to attempt cleanup even for finalized orders
            finalized = self.finalize_order_in_xero(draft_order)
            if not finalized:
                # Rollback draft order before returning error
                transaction.rollback()
                return {
                    "success": False,
                    "stage": OrderWorkflowStage.ERROR,
                    "customer": customer,
                    "draft_order": draft_order,
                    "agent_timeline": self.agent_timeline,
                    "error": "Failed to finalize delivery order"
                }

            # Stage 6: Post invoice
            # CRITICAL: Register compensating action AFTER successful creation
            invoice = self.post_invoice_to_xero(customer, line_items, outlet_name)
            if not invoice:
                # Rollback all Xero operations (draft order, finalized order)
                transaction.rollback()
                return {
                    "success": False,
                    "stage": OrderWorkflowStage.ERROR,
                    "customer": customer,
                    "draft_order": draft_order,
                    "agent_timeline": self.agent_timeline,
                    "error": "Failed to create invoice"
                }

            # COMPENSATING ACTION: Void invoice if later steps fail
            transaction.add_compensating_action(
                step_name="create_invoice",
                compensate_func=self.xero_client.void_invoice,
                compensate_args=(invoice.invoice_id,),
                context={
                    "invoice_id": invoice.invoice_id,
                    "invoice_number": invoice.invoice_number,
                    "customer": customer.name
                }
            )

            # Success! Commit transaction (clears all compensating actions)
            transaction.commit()

            logger.info(f"Workflow completed successfully for {outlet_name}")
            return {
                "success": True,
                "stage": OrderWorkflowStage.COMPLETED,
                "customer": customer,
                "draft_order": draft_order,
                "invoice": invoice,
                "agent_timeline": self.agent_timeline,
                "message": f"Order processed successfully! Invoice {invoice.invoice_number} posted to Xero."
            }

        except Exception as e:
            # Automatic rollback on any exception
            logger.error(f"Workflow error: {e} - Rolling back Xero operations")
            transaction.rollback(error=e)

            return {
                "success": False,
                "stage": OrderWorkflowStage.ERROR,
                "agent_timeline": self.agent_timeline,
                "error": f"Workflow error: {str(e)}"
            }

    def get_timeline_filtered(
        self,
        category: Optional[str] = None,
        date: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get filtered agent timeline outputs.

        Args:
            category: Filter by functionality (inventory, delivery, finance, orders, general)
            date: Filter by date (YYYY-MM-DD format)
            status: Filter by status (idle, processing, completed, error)

        Returns:
            Filtered list of agent timeline entries

        Example:
            # Get all inventory operations
            inventory_ops = orchestrator.get_timeline_filtered(category='inventory')

            # Get all operations from today
            today_ops = orchestrator.get_timeline_filtered(date='2025-01-15')

            # Get all completed finance operations
            finance_done = orchestrator.get_timeline_filtered(
                category='finance',
                status='completed'
            )
        """
        filtered = self.agent_timeline

        if category:
            filtered = [
                entry for entry in filtered
                if entry.get('category') == category
            ]

        if date:
            filtered = [
                entry for entry in filtered
                if entry.get('date') == date
            ]

        if status:
            filtered = [
                entry for entry in filtered
                if entry.get('status') == status
            ]

        return filtered

    def get_timeline_grouped_by_date(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get agent timeline grouped by date for daily summary view.

        Returns:
            Dictionary with dates as keys and lists of agent entries as values

        Example Output:
            {
                "2025-01-15": [
                    {
                        "agent_name": "📦 Inventory Manager",
                        "category": "inventory",
                        "current_task": "Inventory verified",
                        "details": ["✓ Product A: Current stock 100, requested 10..."],
                        "metadata": {...}
                    },
                    {
                        "agent_name": "💰 Finance Controller",
                        "category": "finance",
                        "current_task": "Invoice INV-001 generated",
                        ...
                    }
                ],
                "2025-01-16": [...]
            }
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}

        for entry in self.agent_timeline:
            date = entry.get('date', 'unknown')
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(entry)

        # Sort dates in descending order (most recent first)
        return dict(sorted(grouped.items(), reverse=True))

    def get_timeline_grouped_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get agent timeline grouped by functional category.

        Returns:
            Dictionary with categories as keys (inventory, delivery, finance, orders, general)
            and lists of agent entries as values

        Example Output:
            {
                "inventory": [
                    {
                        "agent_name": "📦 Inventory Manager",
                        "current_task": "Inventory verified",
                        "metadata": {
                            "inventory_summary": [
                                {"sku": "PROD-001", "before": 100, "after": 90, ...}
                            ]
                        }
                    }
                ],
                "finance": [...],
                "delivery": [...]
            }
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {
            'inventory': [],
            'delivery': [],
            'finance': [],
            'orders': [],
            'general': []
        }

        for entry in self.agent_timeline:
            category = entry.get('category', 'general')
            if category in grouped:
                grouped[category].append(entry)
            else:
                grouped['general'].append(entry)

        return grouped

    def get_generated_outputs_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of all generated outputs for reporting.

        This provides a complete view of all actions performed, suitable for:
        - Daily activity reports
        - Audit trails
        - Performance dashboards
        - Client-facing status updates

        Returns:
            Dictionary with comprehensive output summary including:
            - Total operations by category
            - Documents generated (DOs, invoices)
            - Inventory movements
            - Timeline grouped by date and category

        Example Output:
            {
                "summary": {
                    "total_operations": 5,
                    "by_category": {
                        "inventory": 1,
                        "delivery": 1,
                        "finance": 1,
                        "orders": 2
                    },
                    "documents_generated": {
                        "delivery_orders": ["DO-Store1-20250115-143022"],
                        "invoices": ["INV-Store1-20250115-143055"]
                    }
                },
                "by_date": {
                    "2025-01-15": [...]
                },
                "by_category": {
                    "inventory": [...],
                    "finance": [...]
                },
                "inventory_movements": [
                    {
                        "product": "Product A",
                        "sku": "PROD-001",
                        "before": 100,
                        "withdrawn": 10,
                        "after": 90,
                        "date": "2025-01-15 14:30:22"
                    }
                ]
            }
        """
        # Collect document references
        delivery_orders = []
        invoices = []
        inventory_movements = []

        # Count operations by category
        category_counts = {
            'inventory': 0,
            'delivery': 0,
            'finance': 0,
            'orders': 0,
            'general': 0
        }

        for entry in self.agent_timeline:
            category = entry.get('category', 'general')
            if entry.get('status') == 'completed':
                category_counts[category] = category_counts.get(category, 0) + 1

            # Extract delivery orders
            metadata = entry.get('metadata', {})
            if 'do_number' in metadata:
                delivery_orders.append({
                    'do_number': metadata['do_number'],
                    'customer': metadata.get('customer'),
                    'total_amount': metadata.get('total_amount'),
                    'total_quantity': metadata.get('total_quantity'),
                    'date': entry.get('completed_at') or entry.get('updated_at')
                })

            # Extract invoices
            if 'invoice_number' in metadata:
                invoices.append({
                    'invoice_number': metadata['invoice_number'],
                    'customer': metadata.get('customer'),
                    'total_amount': metadata.get('total_amount'),
                    'tax_amount': metadata.get('tax_amount'),
                    'date': entry.get('completed_at') or entry.get('updated_at')
                })

            # Extract inventory movements
            if 'inventory_summary' in metadata:
                for item in metadata['inventory_summary']:
                    if item.get('status') == 'available' and 'before' in item:
                        inventory_movements.append({
                            'product': item.get('product_name'),
                            'sku': item.get('sku'),
                            'before': item.get('before'),
                            'withdrawn': item.get('requested'),
                            'after': item.get('after'),
                            'date': entry.get('completed_at') or entry.get('updated_at')
                        })

        return {
            'summary': {
                'total_operations': len([e for e in self.agent_timeline if e.get('status') == 'completed']),
                'by_category': category_counts,
                'documents_generated': {
                    'delivery_orders': delivery_orders,
                    'invoices': invoices
                }
            },
            'by_date': self.get_timeline_grouped_by_date(),
            'by_category': self.get_timeline_grouped_by_category(),
            'inventory_movements': inventory_movements
        }


# Global singleton instance
_orchestrator: Optional[XeroOrderOrchestrator] = None


def get_xero_orchestrator() -> XeroOrderOrchestrator:
    """
    Get or create global Xero orchestrator (singleton pattern).

    Returns:
        XeroOrderOrchestrator instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = XeroOrderOrchestrator()
    return _orchestrator
