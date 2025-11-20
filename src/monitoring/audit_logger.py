"""
Audit Logging for Compliance (GDPR, SOC2)
==========================================

Tracks all sensitive operations for compliance and security auditing:
- User data access
- Order creation/modification
- Xero invoice creation
- Configuration changes
- Authentication events

NO PII in logs - all sensitive data is hashed or scrubbed.

Usage:
    from monitoring.audit_logger import audit_log, AuditEvent

    # Log user data access
    audit_log(
        event_type=AuditEvent.DATA_ACCESS,
        user_id="user123",
        resource="customer_data",
        action="read",
        details={"customer_id": 456}
    )

    # Log order creation
    audit_log(
        event_type=AuditEvent.ORDER_CREATED,
        user_id="user123",
        resource="order",
        action="create",
        details={"order_id": 789, "total_amount": 150.00}
    )
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from hashlib import sha256
import os


class AuditEvent(str, Enum):
    """Audit event types"""

    # Data Access Events
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETE = "data_delete"

    # Order Events
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    ORDER_CANCELLED = "order_cancelled"

    # Xero Events
    XERO_INVOICE_CREATED = "xero_invoice_created"
    XERO_INVOICE_FAILED = "xero_invoice_failed"

    # Authentication Events
    AUTH_LOGIN = "auth_login"
    AUTH_LOGOUT = "auth_logout"
    AUTH_FAILED = "auth_failed"

    # Configuration Events
    CONFIG_CHANGED = "config_changed"
    PROMPT_UPDATED = "prompt_updated"

    # Security Events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNAUTHORIZED_ACCESS = "unauthorized_access"

    # Admin Events
    ADMIN_ACTION = "admin_action"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"


class AuditLogger:
    """Structured audit logger with PII scrubbing"""

    def __init__(self, log_file: str = "logs/audit.log"):
        """
        Initialize audit logger

        Args:
            log_file: Path to audit log file
        """
        self.log_file = log_file

        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Configure structured logging
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # File handler for audit logs (separate from application logs)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # JSON formatter for structured logs
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        self.logger.addHandler(file_handler)

        # Don't propagate to root logger (keeps audit logs separate)
        self.logger.propagate = False

    def log(
        self,
        event_type: AuditEvent,
        user_id: str,
        resource: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        ip_address: Optional[str] = None
    ):
        """
        Log an audit event

        Args:
            event_type: Type of event (from AuditEvent enum)
            user_id: User who performed the action (hashed if PII)
            resource: Resource affected (e.g., "order", "customer_data")
            action: Action performed (e.g., "create", "read", "update", "delete")
            details: Additional details (PII will be scrubbed)
            success: Whether the action succeeded
            ip_address: IP address of request (optional)
        """

        # Scrub PII from details
        scrubbed_details = self._scrub_pii(details) if details else {}

        # Hash user_id if it looks like an email
        scrubbed_user_id = self._hash_if_email(user_id)

        # Hash IP address for privacy
        scrubbed_ip = self._hash_value(ip_address) if ip_address else None

        # Build audit record
        audit_record = {
            "event_type": event_type.value,
            "user_id": scrubbed_user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "details": scrubbed_details,
            "ip_address_hash": scrubbed_ip,
            "timestamp_utc": datetime.utcnow().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "development")
        }

        # Log as JSON
        self.logger.info(json.dumps(audit_record))

    def _scrub_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrub PII from data

        Removes or hashes sensitive fields:
        - email → hashed
        - phone → hashed
        - address → removed
        - credit_card → removed
        - password → removed
        """

        if not isinstance(data, dict):
            return data

        scrubbed = {}
        pii_fields = {"email", "phone", "address", "credit_card", "password", "ssn", "tax_id"}
        hash_fields = {"email", "phone"}

        for key, value in data.items():
            lower_key = key.lower()

            # Remove highly sensitive fields entirely
            if lower_key in {"password", "credit_card", "ssn", "tax_id"}:
                scrubbed[key] = "[REDACTED]"

            # Hash PII fields
            elif lower_key in hash_fields:
                scrubbed[key] = self._hash_value(str(value))

            # Remove address-like fields
            elif "address" in lower_key or "street" in lower_key:
                scrubbed[key] = "[REDACTED]"

            # Recursively scrub nested dicts
            elif isinstance(value, dict):
                scrubbed[key] = self._scrub_pii(value)

            # Keep other fields
            else:
                scrubbed[key] = value

        return scrubbed

    def _hash_value(self, value: str) -> str:
        """Hash a value using SHA-256"""
        if not value:
            return ""
        return sha256(value.encode()).hexdigest()[:16]  # First 16 chars

    def _hash_if_email(self, value: str) -> str:
        """Hash value if it looks like an email, otherwise return as-is"""
        if "@" in value:
            return self._hash_value(value)
        return value


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def audit_log(
    event_type: AuditEvent,
    user_id: str,
    resource: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    ip_address: Optional[str] = None
):
    """
    Convenience function for audit logging

    Example:
        from monitoring.audit_logger import audit_log, AuditEvent

        audit_log(
            event_type=AuditEvent.ORDER_CREATED,
            user_id="user123",
            resource="order",
            action="create",
            details={"order_id": 789, "total": 150.00},
            ip_address=request.client.host
        )
    """
    logger = get_audit_logger()
    logger.log(
        event_type=event_type,
        user_id=user_id,
        resource=resource,
        action=action,
        details=details,
        success=success,
        ip_address=ip_address
    )


# FastAPI middleware for automatic audit logging
class AuditMiddleware:
    """
    FastAPI middleware for automatic audit logging of sensitive endpoints

    Usage:
        from monitoring.audit_logger import AuditMiddleware

        app.add_middleware(AuditMiddleware)
    """

    def __init__(self, app, audit_paths: Optional[list] = None):
        """
        Initialize audit middleware

        Args:
            app: FastAPI app
            audit_paths: List of paths to audit (default: all POST/PUT/DELETE)
        """
        self.app = app
        self.audit_paths = audit_paths or [
            "/api/chatbot",
            "/api/order",
            "/api/post_to_xero",
            "/admin/",
            "/auth/"
        ]

    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation"""

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        path = scope.get("path", "")
        method = scope.get("method", "")

        # Check if path should be audited
        should_audit = any(path.startswith(audit_path) for audit_path in self.audit_paths)

        if should_audit and method in {"POST", "PUT", "DELETE", "PATCH"}:
            # Extract user_id and IP from scope
            user_id = scope.get("user", {}).get("id", "anonymous")
            ip_address = scope.get("client", ["unknown"])[0]

            # Map HTTP method to audit action
            action_map = {
                "POST": "create",
                "PUT": "update",
                "DELETE": "delete",
                "PATCH": "update"
            }
            action = action_map.get(method, method.lower())

            # Determine event type
            if "/order" in path or "/chatbot" in path:
                event_type = AuditEvent.ORDER_CREATED if method == "POST" else AuditEvent.ORDER_UPDATED
            elif "/xero" in path:
                event_type = AuditEvent.XERO_INVOICE_CREATED
            elif "/admin" in path:
                event_type = AuditEvent.ADMIN_ACTION
            else:
                event_type = AuditEvent.DATA_ACCESS

            # Log audit event
            audit_log(
                event_type=event_type,
                user_id=user_id,
                resource=path,
                action=action,
                details={"method": method, "path": path},
                ip_address=ip_address
            )

        # Continue processing request
        await self.app(scope, receive, send)


def query_audit_logs(
    event_type: Optional[AuditEvent] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> list:
    """
    Query audit logs

    Args:
        event_type: Filter by event type
        user_id: Filter by user ID
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Maximum number of records to return

    Returns:
        List of audit records

    Example:
        from datetime import datetime, timedelta
        from monitoring.audit_logger import query_audit_logs, AuditEvent

        # Get all order creation events in last 24 hours
        records = query_audit_logs(
            event_type=AuditEvent.ORDER_CREATED,
            start_date=datetime.now() - timedelta(days=1)
        )
    """
    records = []

    log_file = "logs/audit.log"
    if not os.path.exists(log_file):
        return records

    with open(log_file, 'r') as f:
        for line in f:
            try:
                # Parse JSON log line
                log_entry = json.loads(line)
                record = json.loads(log_entry.get("message", "{}"))

                # Apply filters
                if event_type and record.get("event_type") != event_type.value:
                    continue

                if user_id and record.get("user_id") != user_id:
                    continue

                if start_date:
                    record_time = datetime.fromisoformat(record.get("timestamp_utc", ""))
                    if record_time < start_date:
                        continue

                if end_date:
                    record_time = datetime.fromisoformat(record.get("timestamp_utc", ""))
                    if record_time > end_date:
                        continue

                records.append(record)

                if len(records) >= limit:
                    break

            except (json.JSONDecodeError, ValueError):
                continue

    return records
