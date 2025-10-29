"""
TRIA AI-BPO Intelligent Agents
================================

GPT-4 powered agents for customer service automation.
"""

from .intent_classifier import (
    IntentClassifier,
    IntentResult,
    classify_intent,
    is_high_confidence,
    requires_human_escalation,
    get_intent_category,
)

from .enhanced_customer_service_agent import (
    EnhancedCustomerServiceAgent,
    CustomerServiceResponse,
    handle_customer_message,
)

__all__ = [
    "IntentClassifier",
    "IntentResult",
    "classify_intent",
    "is_high_confidence",
    "requires_human_escalation",
    "get_intent_category",
    "EnhancedCustomerServiceAgent",
    "CustomerServiceResponse",
    "handle_customer_message",
]
