"""
Xero Webhook Endpoint Handler
==============================

Handles webhook notifications from Xero when invoices are created, updated, or deleted.

Security:
- Verifies Xero HMAC-SHA256 signature
- Rejects unsigned or tampered requests
- Logs all webhook events for audit

Events handled:
- Invoice CREATE: New invoice created in Xero
- Invoice UPDATE: Invoice updated (includes payment status changes)
- Invoice DELETE: Invoice deleted

Usage:
    POST https://tria.himeet.ai/api/xero/webhook
    Header: x-xero-signature: <HMAC-SHA256 signature>
    Body: JSON webhook payload
"""

import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, List
from datetime import datetime
from fastapi import Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class XeroWebhookEvent(BaseModel):
    """Single webhook event from Xero"""
    resourceUrl: str
    resourceId: str
    eventDateUtc: str
    eventType: str  # CREATE, UPDATE, DELETE
    eventCategory: str  # INVOICE, CONTACT, etc.
    tenantId: str
    tenantType: str


class XeroWebhookPayload(BaseModel):
    """Complete webhook payload from Xero"""
    events: List[XeroWebhookEvent]
    firstEventSequence: int
    lastEventSequence: int
    entropy: str


def verify_xero_signature(
    payload: bytes,
    signature: str,
    webhook_key: str
) -> bool:
    """
    Verify Xero webhook signature using HMAC-SHA256.

    Args:
        payload: Raw request body bytes
        signature: x-xero-signature header value (base64 encoded)
        webhook_key: Webhook key from Xero app (base64 encoded)

    Returns:
        True if signature is valid, False otherwise

    Security:
        Uses constant-time comparison to prevent timing attacks
    """
    try:
        # Decode the webhook key from base64
        webhook_key_bytes = base64.b64decode(webhook_key)

        # Calculate expected signature
        expected_signature = base64.b64encode(
            hmac.new(
                webhook_key_bytes,
                payload,
                hashlib.sha256
            ).digest()
        ).decode()

        # Constant-time comparison (prevents timing attacks)
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning(
                "Webhook signature verification failed",
                extra={
                    "expected": expected_signature[:20] + "...",
                    "received": signature[:20] + "...",
                    "payload_size": len(payload)
                }
            )

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}")
        return False


async def handle_xero_webhook(request: Request, webhook_key: str) -> Dict[str, Any]:
    """
    Handle incoming Xero webhook request.

    Args:
        request: FastAPI request object
        webhook_key: Webhook key from Xero app configuration

    Returns:
        Response dict with status

    Raises:
        HTTPException: If signature verification fails
    """
    # Get raw body for signature verification
    body = await request.body()

    # Get signature from header
    signature = request.headers.get("x-xero-signature")

    if not signature:
        logger.error("Webhook request missing x-xero-signature header")
        raise HTTPException(
            status_code=401,
            detail="Missing x-xero-signature header"
        )

    # Verify signature
    if not verify_xero_signature(body, signature, webhook_key):
        logger.error("Webhook signature verification failed - possible tampering")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )

    # Parse payload
    try:
        payload = XeroWebhookPayload.parse_raw(body)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid webhook payload: {str(e)}"
        )

    # Log webhook receipt
    logger.info(
        f"Received verified Xero webhook with {len(payload.events)} events",
        extra={
            "event_count": len(payload.events),
            "first_sequence": payload.firstEventSequence,
            "last_sequence": payload.lastEventSequence,
            "entropy": payload.entropy
        }
    )

    # Process each event
    for event in payload.events:
        await process_webhook_event(event)

    return {
        "status": "success",
        "events_processed": len(payload.events),
        "timestamp": datetime.now().isoformat()
    }


async def process_webhook_event(event: XeroWebhookEvent):
    """
    Process a single webhook event from Xero.

    Args:
        event: Webhook event to process

    Note:
        Currently logs events for monitoring. Can be extended to:
        - Update local database when invoices change in Xero
        - Send notifications when payments are received
        - Sync inventory when stock levels change
        - Trigger workflows based on Xero events
    """
    event_time = datetime.fromisoformat(event.eventDateUtc.replace('Z', '+00:00'))

    logger.info(
        f"Processing Xero webhook event: {event.eventCategory} {event.eventType}",
        extra={
            "event_category": event.eventCategory,
            "event_type": event.eventType,
            "resource_id": event.resourceId,
            "tenant_id": event.tenantId,
            "event_time": event_time.isoformat(),
            "resource_url": event.resourceUrl
        }
    )

    # Handle different event types
    if event.eventCategory == "INVOICE":
        await handle_invoice_event(event)
    elif event.eventCategory == "CONTACT":
        await handle_contact_event(event)
    else:
        logger.info(f"Unhandled event category: {event.eventCategory}")


async def handle_invoice_event(event: XeroWebhookEvent):
    """
    Handle invoice-related webhook events.

    Events:
        CREATE: New invoice created in Xero
        UPDATE: Invoice updated (status change, payment received, etc.)
        DELETE: Invoice deleted

    Potential actions:
        - Update local database invoice status
        - Send payment confirmation emails
        - Update analytics/reporting
        - Trigger fulfillment workflows
    """
    if event.eventType == "CREATE":
        logger.info(
            f"Invoice created in Xero: {event.resourceId}",
            extra={"invoice_id": event.resourceId, "resource_url": event.resourceUrl}
        )
        # TODO: Fetch invoice details from Xero and update local database

    elif event.eventType == "UPDATE":
        logger.info(
            f"Invoice updated in Xero: {event.resourceId}",
            extra={"invoice_id": event.resourceId, "resource_url": event.resourceUrl}
        )
        # TODO: Fetch updated invoice (may include payment status change)
        # If status changed to PAID, trigger payment confirmation workflow

    elif event.eventType == "DELETE":
        logger.info(
            f"Invoice deleted in Xero: {event.resourceId}",
            extra={"invoice_id": event.resourceId}
        )
        # TODO: Mark invoice as deleted in local database


async def handle_contact_event(event: XeroWebhookEvent):
    """
    Handle contact-related webhook events.

    Events:
        CREATE: New contact created
        UPDATE: Contact details updated
        DELETE: Contact deleted

    Note:
        Currently logs for monitoring. Implement if customer sync needed.
    """
    logger.info(
        f"Contact {event.eventType.lower()} in Xero: {event.resourceId}",
        extra={
            "contact_id": event.resourceId,
            "event_type": event.eventType,
            "resource_url": event.resourceUrl
        }
    )
    # TODO: Implement contact sync if needed
