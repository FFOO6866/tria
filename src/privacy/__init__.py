"""
TRIA AI-BPO Privacy Module
===========================

PDPA-compliant PII detection, scrubbing, and data retention.

NO MOCKING - Production-ready privacy controls.
"""

from .pii_scrubber import scrub_pii, PIIType, PIIMetadata
from .data_retention import cleanup_old_conversations, anonymize_old_summaries

__all__ = [
    'scrub_pii',
    'PIIType',
    'PIIMetadata',
    'cleanup_old_conversations',
    'anonymize_old_summaries',
]
