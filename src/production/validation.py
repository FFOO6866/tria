"""
Input Validation and Sanitization for Production Security
==========================================================

Validates order inputs to prevent:
- Excessive quantities (fraud/errors)
- Invalid totals (calculation errors)
- SQL injection (security)
- Financial precision errors (revenue loss)

Usage:
    from production.validation import OrderValidator, sanitize_for_sql

    # Validate order before saving
    OrderValidator.validate_order(line_items, total)

    # Sanitize GPT-4 outputs before SQL
    safe_name = sanitize_for_sql(gpt4_extracted_name)
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class OrderValidator:
    """Validates order inputs to prevent fraud and errors"""

    # Business rules (configurable per environment)
    MAX_QUANTITY_PER_ITEM = 10000
    MAX_ORDER_TOTAL = Decimal('100000.00')  # $100k limit
    MAX_LINE_ITEMS = 100
    MIN_ORDER_TOTAL = Decimal('0.01')  # At least 1 cent

    @classmethod
    def validate_order(
        cls,
        line_items: List[Dict[str, Any]],
        total: Decimal
    ) -> None:
        """
        Validate order data. Raises ValueError if invalid.

        Args:
            line_items: List of order line items with 'quantity' field
            total: Calculated order total (Decimal)

        Raises:
            ValueError: If validation fails with detailed error message

        Example:
            try:
                OrderValidator.validate_order(line_items, total)
            except ValueError as e:
                return {"error": str(e)}
        """
        # Check line item count
        if not line_items:
            raise ValueError("Order must have at least one line item")

        if len(line_items) > cls.MAX_LINE_ITEMS:
            raise ValueError(
                f"Order has {len(line_items)} items, "
                f"maximum is {cls.MAX_LINE_ITEMS}"
            )

        # Validate each line item
        for idx, item in enumerate(line_items, 1):
            cls._validate_line_item(item, idx)

        # Validate total
        cls._validate_total(total)

        logger.info(
            f"Order validation passed: {len(line_items)} items, "
            f"total ${total}"
        )

    @classmethod
    def _validate_line_item(cls, item: Dict[str, Any], idx: int) -> None:
        """Validate individual line item"""
        qty = item.get('quantity', 0)

        # Check quantity exists and is valid
        if not isinstance(qty, (int, float)):
            raise ValueError(
                f"Line item {idx}: Quantity must be a number, "
                f"got {type(qty).__name__}"
            )

        if qty <= 0:
            raise ValueError(
                f"Line item {idx}: Quantity must be positive, got {qty}"
            )

        if qty > cls.MAX_QUANTITY_PER_ITEM:
            raise ValueError(
                f"Line item {idx}: Quantity {qty:,} exceeds "
                f"maximum {cls.MAX_QUANTITY_PER_ITEM:,}"
            )

        # Check SKU exists
        sku = item.get('sku')
        if not sku or sku == 'unknown':
            raise ValueError(
                f"Line item {idx}: Invalid or missing product SKU"
            )

    @classmethod
    def _validate_total(cls, total: Decimal) -> None:
        """Validate order total"""
        if not isinstance(total, Decimal):
            try:
                total = Decimal(str(total))
            except (ValueError, InvalidOperation):
                raise ValueError(
                    f"Order total must be a valid number, got {total}"
                )

        if total < cls.MIN_ORDER_TOTAL:
            raise ValueError(
                f"Order total ${total} must be at least "
                f"${cls.MIN_ORDER_TOTAL}"
            )

        if total > cls.MAX_ORDER_TOTAL:
            raise ValueError(
                f"Order total ${total:,.2f} exceeds "
                f"maximum ${cls.MAX_ORDER_TOTAL:,.2f}"
            )


def sanitize_for_sql(value: str) -> str:
    """
    Sanitize string values before use in SQL queries.

    Critical for GPT-4 extracted values that might contain SQL injection.

    Args:
        value: Input string (potentially from untrusted source like GPT-4)

    Returns:
        Sanitized string safe for SQL LIKE patterns

    Security Notes:
        - Removes SQL comment markers (--)
        - Removes statement terminators (;)
        - Escapes single quotes
        - Removes control characters
        - Does NOT make value safe for direct concatenation!
          ALWAYS use parameterized queries.

    Example:
        # WRONG - still vulnerable:
        query = f"SELECT * FROM outlets WHERE name = '{sanitize_for_sql(name)}'"

        # CORRECT - use parameterization:
        safe_name = sanitize_for_sql(name)
        query = text("SELECT * FROM outlets WHERE name LIKE :name")
        conn.execute(query, {'name': f'%{safe_name}%'})
    """
    if not value:
        return ""

    if not isinstance(value, str):
        value = str(value)

    # Remove SQL-dangerous characters
    sanitized = value.replace("'", "''")  # Escape single quotes (SQL standard)
    sanitized = sanitized.replace(";", "")  # Remove statement terminators
    sanitized = sanitized.replace("--", "")  # Remove SQL comment markers
    sanitized = sanitized.replace("/*", "")  # Remove block comment start
    sanitized = sanitized.replace("*/", "")  # Remove block comment end

    # Remove control characters (ASCII 0-31 and 127-159)
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)

    # Remove excessive whitespace
    sanitized = ' '.join(sanitized.split())

    # Limit length to prevent DOS
    MAX_LENGTH = 255
    if len(sanitized) > MAX_LENGTH:
        logger.warning(f"Truncating sanitized value from {len(sanitized)} to {MAX_LENGTH} chars")
        sanitized = sanitized[:MAX_LENGTH]

    return sanitized.strip()


def validate_decimal_precision(
    value: Decimal,
    decimal_places: int = 2
) -> Decimal:
    """
    Ensure decimal has correct precision for financial calculations.

    Prevents revenue loss from rounding errors and ensures consistent
    precision across all monetary values.

    Args:
        value: Decimal value to validate
        decimal_places: Number of decimal places (default 2 for currency)

    Returns:
        Decimal with correct precision

    Example:
        # Calculate tax with proper precision
        subtotal = Decimal('1000.00')
        tax_rate = Decimal('0.08')
        tax = validate_decimal_precision(subtotal * tax_rate)  # Exactly $80.00
    """
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            raise ValueError(f"Cannot convert {value} to Decimal")

    # Create quantize template (e.g., '0.01' for 2 decimal places)
    quantize_template = Decimal('0.{}'.format('0' * decimal_places))

    # Round to correct precision
    return value.quantize(quantize_template, rounding=ROUND_HALF_UP)


def validate_phone_number(phone: str) -> bool:
    """
    Validate Singapore phone number format.

    Args:
        phone: Phone number string

    Returns:
        True if valid Singapore phone format

    Example:
        validate_phone_number("+65 9123 4567")  # True
        validate_phone_number("91234567")  # True
        validate_phone_number("1234")  # False
    """
    if not phone:
        return False

    # Remove spaces and dashes
    clean = re.sub(r'[\s\-]', '', phone)

    # Singapore mobile: +65 8XXX XXXX or 9XXX XXXX
    # Singapore landline: +65 6XXX XXXX
    patterns = [
        r'^\+65[896]\d{7}$',  # +65 8/9/6 followed by 7 digits
        r'^[896]\d{7}$',  # 8/9/6 followed by 7 digits
    ]

    return any(re.match(pattern, clean) for pattern in patterns)


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email address string

    Returns:
        True if valid email format
    """
    if not email:
        return False

    # Basic email regex (not RFC-compliant but good enough)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


class ValidationError(Exception):
    """Custom exception for validation failures"""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)

    def to_dict(self) -> Dict[str, str]:
        """Convert to API-friendly dict"""
        return {
            'error': self.message,
            'field': self.field
        } if self.field else {'error': self.message}
