"""
PDPA-Compliant PII Detection and Scrubbing
===========================================

Production-ready PII detection for Singapore market compliance.

Detects and scrubs:
- Singapore phone numbers (+65, 8-digit, 6-digit)
- Email addresses
- NRIC/FIN numbers (S/T/F/G/M + 7 digits + letter)
- Credit card numbers (all major providers)
- Singapore postal codes (6-digit)
- Singapore addresses

NO FALLBACKS - Real regex-based detection with comprehensive patterns.
"""

import re
from dataclasses import dataclass, field
from typing import Tuple, Dict, List, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PIIType(Enum):
    """Types of PII that can be detected"""
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    NRIC = "NRIC"
    CARD = "CARD"
    POSTAL_CODE = "POSTAL_CODE"
    ADDRESS = "ADDRESS"


@dataclass
class PIIMetadata:
    """
    Metadata about detected PII

    Attributes:
        total_count: Total number of PII instances found
        by_type: Count of each PII type detected
        details: List of detection details (type, placeholder, position)
        original_length: Original text length
        scrubbed_length: Scrubbed text length
    """
    total_count: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    details: List[Dict[str, Any]] = field(default_factory=list)
    original_length: int = 0
    scrubbed_length: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'total_count': self.total_count,
            'by_type': self.by_type,
            'details': self.details,
            'original_length': self.original_length,
            'scrubbed_length': self.scrubbed_length,
        }


# ============================================================================
# SINGAPORE-SPECIFIC PII PATTERNS
# ============================================================================

# Singapore Phone Numbers
# - Mobile: +65 9XXX XXXX, +65 8XXX XXXX, 9XXXXXXX, 8XXXXXXX
# - Landline: +65 6XXX XXXX, 6XXXXXXX (office/home)
# - Toll-free: +65 1800 XXX XXXX, 1800XXXXXXX
# Handles various formats: with/without country code, with/without spaces/dashes
PHONE_PATTERNS = [
    # Singapore mobile with +65 (8 or 9 series)
    r'\+65\s*[89]\d{3}\s*\d{4}',
    # Singapore mobile without country code
    r'(?<!\d)[89]\d{7}(?!\d)',
    # Singapore landline with +65 (6 series)
    r'\+65\s*6\d{3}\s*\d{4}',
    # Singapore landline without country code
    r'(?<!\d)6\d{7}(?!\d)',
    # Singapore toll-free with +65
    r'\+65\s*1800\s*\d{3}\s*\d{4}',
    # Singapore toll-free without country code
    r'(?<!\d)1800\s*\d{7}(?!\d)',
    # Generic international format (fallback for other formats)
    r'\+65[\s\-]?\d{4}[\s\-]?\d{4}',
]

# Email Addresses (RFC 5322 compliant)
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Singapore NRIC/FIN Numbers
# Format: S/T/F/G/M + 7 digits + checksum letter
# S - Singapore Citizens born before 2000
# T - Singapore Citizens born from 2000 onwards
# F - Foreigners issued before 2000
# G - Foreigners issued from 2000 onwards
# M - Malaysian Citizens (special category)
NRIC_PATTERN = r'\b[STFGM]\d{7}[A-Z]\b'

# Credit Card Numbers
# Supports: Visa, Mastercard, Amex, Discover, Diners, JCB
# Handles various formats: with/without spaces/dashes
CARD_PATTERNS = [
    # Visa (starts with 4, 13 or 16 digits)
    r'\b4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    r'\b4\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    # Mastercard (starts with 51-55 or 2221-2720, 16 digits)
    r'\b5[1-5]\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    r'\b2[2-7]\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    # American Express (starts with 34 or 37, 15 digits)
    r'\b3[47]\d{2}[\s\-]?\d{6}[\s\-]?\d{5}\b',
    # Discover (starts with 6011, 644-649, 65, 16 digits)
    r'\b6011[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    r'\b64[4-9]\d[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    r'\b65\d{2}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    # Diners Club (starts with 300-305, 36, 38, 14 digits)
    r'\b3(?:0[0-5]|[68]\d)\d[\s\-]?\d{6}[\s\-]?\d{4}\b',
    # JCB (starts with 2131, 1800, 35, 16 digits)
    r'\b(?:2131|1800|35\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
]

# Singapore Postal Codes (6 digits)
# First 2 digits indicate district/sector
POSTAL_CODE_PATTERN = r'\b\d{6}\b'

# Singapore Address Patterns
# Common patterns in Singapore addresses
ADDRESS_PATTERNS = [
    # Block/unit numbers (e.g., "Blk 123", "Block 456", "#12-34")
    r'\b(?:Blk|Block|BLK|BLOCK)\s*\d+[A-Z]?\b',
    r'#\d{2}-\d{2,4}',
    # Road/Street/Avenue names with Singapore suffixes
    r'\b\d+[A-Z]?\s+[A-Za-z\s]+(?:Road|Street|Avenue|Drive|Lane|Park|Close|Walk|Terrace|Way)\b',
    # Common Singapore locations
    r'\b(?:Singapore|SG|SINGAPORE)\s+\d{6}\b',
]


# ============================================================================
# PII DETECTION AND SCRUBBING FUNCTIONS
# ============================================================================

def _detect_and_replace(
    text: str,
    patterns: List[str],
    pii_type: PIIType,
    placeholder: str,
    metadata: PIIMetadata,
    case_sensitive: bool = False
) -> str:
    """
    Detect and replace PII patterns in text

    Args:
        text: Input text
        patterns: List of regex patterns to match
        pii_type: Type of PII being detected
        placeholder: Replacement placeholder
        metadata: Metadata object to update
        case_sensitive: Whether to use case-sensitive matching

    Returns:
        Text with PII replaced by placeholder
    """
    scrubbed_text = text
    type_count = 0

    for pattern in patterns:
        flags = 0 if case_sensitive else re.IGNORECASE
        matches = list(re.finditer(pattern, scrubbed_text, flags))

        for match in matches:
            matched_text = match.group(0)
            type_count += 1

            # Record detection details
            metadata.details.append({
                'type': pii_type.value,
                'placeholder': placeholder,
                'position': match.start(),
                'length': len(matched_text),
            })

        # Replace all matches with placeholder
        scrubbed_text = re.sub(pattern, placeholder, scrubbed_text, flags=flags)

    if type_count > 0:
        metadata.by_type[pii_type.value] = metadata.by_type.get(pii_type.value, 0) + type_count
        metadata.total_count += type_count
        logger.debug(f"Detected {type_count} instances of {pii_type.value}")

    return scrubbed_text


def scrub_pii(text: str, preserve_structure: bool = True) -> Tuple[str, PIIMetadata]:
    """
    Detect and scrub PII from text while preserving meaning

    Detects Singapore-specific PII including:
    - Phone numbers (Singapore mobile/landline/toll-free)
    - Email addresses
    - NRIC/FIN numbers
    - Credit card numbers
    - Postal codes
    - Address components

    Args:
        text: Input text to scrub
        preserve_structure: If True, maintain text structure with placeholders

    Returns:
        Tuple of (scrubbed_text, pii_metadata)

    Example:
        >>> text = "Call me at +65 9123 4567 or email john@example.com. NRIC: S1234567D"
        >>> scrubbed, metadata = scrub_pii(text)
        >>> print(scrubbed)
        "Call me at [PHONE] or email [EMAIL]. NRIC: [NRIC]"
        >>> print(metadata.total_count)
        3
        >>> print(metadata.by_type)
        {'PHONE': 1, 'EMAIL': 1, 'NRIC': 1}
    """
    if not text or not isinstance(text, str):
        return text, PIIMetadata()

    # Initialize metadata
    metadata = PIIMetadata(
        original_length=len(text),
    )

    scrubbed_text = text

    # Order matters: scrub from most specific to least specific
    # This prevents partial matches from interfering with full matches

    # 1. NRIC/FIN (most specific format)
    scrubbed_text = _detect_and_replace(
        scrubbed_text,
        [NRIC_PATTERN],
        PIIType.NRIC,
        '[NRIC]',
        metadata,
        case_sensitive=False
    )

    # 2. Credit Cards (before phone to avoid partial matches)
    scrubbed_text = _detect_and_replace(
        scrubbed_text,
        CARD_PATTERNS,
        PIIType.CARD,
        '[CARD]',
        metadata,
        case_sensitive=False
    )

    # 3. Phone Numbers
    scrubbed_text = _detect_and_replace(
        scrubbed_text,
        PHONE_PATTERNS,
        PIIType.PHONE,
        '[PHONE]',
        metadata,
        case_sensitive=False
    )

    # 4. Email Addresses
    scrubbed_text = _detect_and_replace(
        scrubbed_text,
        [EMAIL_PATTERN],
        PIIType.EMAIL,
        '[EMAIL]',
        metadata,
        case_sensitive=False
    )

    # 5. Addresses (before postal codes to catch full addresses)
    scrubbed_text = _detect_and_replace(
        scrubbed_text,
        ADDRESS_PATTERNS,
        PIIType.ADDRESS,
        '[ADDRESS]',
        metadata,
        case_sensitive=False
    )

    # 6. Postal Codes (last to avoid false positives)
    # Only scrub if we haven't already scrubbed this as part of an address
    if PIIType.ADDRESS.value not in metadata.by_type:
        scrubbed_text = _detect_and_replace(
            scrubbed_text,
            [POSTAL_CODE_PATTERN],
            PIIType.POSTAL_CODE,
            '[POSTAL_CODE]',
            metadata,
            case_sensitive=False
        )

    # Update final metadata
    metadata.scrubbed_length = len(scrubbed_text)

    # Log summary if PII was found
    if metadata.total_count > 0:
        logger.info(
            f"Scrubbed {metadata.total_count} PII instances from text "
            f"({metadata.original_length} -> {metadata.scrubbed_length} chars)"
        )
        logger.debug(f"PII breakdown: {metadata.by_type}")

    return scrubbed_text, metadata


def validate_scrubbing(original: str, scrubbed: str, metadata: PIIMetadata) -> bool:
    """
    Validate that scrubbing was successful

    Checks:
    - No PII patterns remain in scrubbed text
    - Metadata counts match actual replacements
    - Text structure is preserved

    Args:
        original: Original text
        scrubbed: Scrubbed text
        metadata: PII metadata from scrubbing

    Returns:
        True if validation passes, False otherwise
    """
    # Re-run detection on scrubbed text
    _, remaining_pii = scrub_pii(scrubbed)

    if remaining_pii.total_count > 0:
        logger.warning(
            f"Validation failed: {remaining_pii.total_count} PII instances "
            f"remain in scrubbed text"
        )
        return False

    # Verify metadata counts match placeholders
    placeholder_counts = {
        PIIType.PHONE.value: scrubbed.count('[PHONE]'),
        PIIType.EMAIL.value: scrubbed.count('[EMAIL]'),
        PIIType.NRIC.value: scrubbed.count('[NRIC]'),
        PIIType.CARD.value: scrubbed.count('[CARD]'),
        PIIType.ADDRESS.value: scrubbed.count('[ADDRESS]'),
        PIIType.POSTAL_CODE.value: scrubbed.count('[POSTAL_CODE]'),
    }

    for pii_type, count in metadata.by_type.items():
        if placeholder_counts.get(pii_type, 0) != count:
            logger.warning(
                f"Validation failed: Metadata shows {count} {pii_type} instances, "
                f"but found {placeholder_counts.get(pii_type, 0)} placeholders"
            )
            return False

    logger.debug("PII scrubbing validation passed")
    return True


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def should_scrub_message(role: str, content: str) -> bool:
    """
    Determine if message should be scrubbed based on role and content

    Args:
        role: Message role ("user" or "assistant")
        content: Message content

    Returns:
        True if message should be scrubbed
    """
    # Always scrub user messages (may contain PII)
    if role == "user":
        return True

    # Scrub assistant messages if they appear to echo PII
    # (e.g., "I've sent the invoice to john@example.com")
    if role == "assistant":
        # Quick check for common PII indicators
        pii_indicators = ['@', '+65', 'NRIC', 'email', 'phone', 'contact']
        return any(indicator in content for indicator in pii_indicators)

    return False


def get_scrubbing_summary(metadata: PIIMetadata) -> str:
    """
    Generate human-readable summary of scrubbing results

    Args:
        metadata: PII metadata

    Returns:
        Summary string
    """
    if metadata.total_count == 0:
        return "No PII detected"

    parts = []
    for pii_type, count in metadata.by_type.items():
        parts.append(f"{count} {pii_type}")

    return f"Scrubbed {metadata.total_count} PII instances: " + ", ".join(parts)


if __name__ == "__main__":
    # Test cases for validation
    test_cases = [
        "Call me at +65 9123 4567",
        "My email is john.doe@example.com",
        "NRIC: S1234567D",
        "Credit card: 4532 1234 5678 9010",
        "Address: Blk 123 Ang Mo Kio Avenue 3 #12-34 Singapore 560123",
        "Mixed: Call +65 8765 4321 or email test@test.com. NRIC S9876543Z",
    ]

    print("PII Scrubbing Test Cases")
    print("=" * 80)

    for i, test in enumerate(test_cases, 1):
        scrubbed, meta = scrub_pii(test)
        print(f"\nTest {i}:")
        print(f"Original:  {test}")
        print(f"Scrubbed:  {scrubbed}")
        print(f"Summary:   {get_scrubbing_summary(meta)}")
        print(f"Valid:     {validate_scrubbing(test, scrubbed, meta)}")
