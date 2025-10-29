"""
TRIA AI-BPO System Prompts Module
===================================

System prompts for GPT-4 agents and intelligent routing.
"""

from .system_prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    CUSTOMER_SERVICE_PROMPT,
    RAG_QA_PROMPT,
    ORDER_PROCESSING_PROMPT,
    ESCALATION_PROMPT,
    build_intent_classification_prompt,
    build_rag_qa_prompt,
    build_order_processing_prompt,
    build_escalation_prompt,
)

__all__ = [
    "INTENT_CLASSIFICATION_PROMPT",
    "CUSTOMER_SERVICE_PROMPT",
    "RAG_QA_PROMPT",
    "ORDER_PROCESSING_PROMPT",
    "ESCALATION_PROMPT",
    "build_intent_classification_prompt",
    "build_rag_qa_prompt",
    "build_order_processing_prompt",
    "build_escalation_prompt",
]
