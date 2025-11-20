"""
DSPy Module Definitions
=======================

DSPy signature definitions for automatic prompt optimization.

NO MOCKING - Uses real OpenAI API through DSPy.
"""

import dspy
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


# ============================================================================
# DSPY SIGNATURES
# ============================================================================

class IntentClassifierSignature(dspy.Signature):
    """
    Intent classification signature for DSPy optimization

    Classifies customer service messages into predefined intents:
    - order_placement: User wants to place order
    - order_status: Checking existing order
    - product_inquiry: Questions about products
    - policy_question: Asking about policies, refunds, delivery
    - complaint: Issue with order/service
    - greeting: Hi, hello, etc.
    - general_query: Other questions
    """

    # Input fields
    message = dspy.InputField(
        desc="Customer message to classify"
    )
    conversation_history = dspy.InputField(
        desc="Previous conversation context as JSON string"
    )

    # Output fields
    intent = dspy.OutputField(
        desc="Primary intent: order_placement, order_status, product_inquiry, "
             "policy_question, complaint, greeting, or general_query"
    )
    confidence = dspy.OutputField(
        desc="Confidence score between 0.0 and 1.0"
    )
    reasoning = dspy.OutputField(
        desc="Brief explanation of why this intent was chosen"
    )


class RAGQASignature(dspy.Signature):
    """
    RAG-based QA signature for DSPy optimization

    Answers customer questions using retrieved knowledge base context.
    Optimizes for:
    - Groundedness (answers based on context)
    - Conciseness (no hallucination)
    - Helpfulness (actually answers the question)
    """

    # Input fields
    question = dspy.InputField(
        desc="Customer question to answer"
    )
    context = dspy.InputField(
        desc="Retrieved knowledge base articles and context"
    )

    # Output fields
    answer = dspy.OutputField(
        desc="Concise answer based strictly on the provided context. "
             "If context doesn't contain answer, say so explicitly."
    )
    confidence = dspy.OutputField(
        desc="Confidence score between 0.0 and 1.0 based on context quality"
    )
    sources = dspy.OutputField(
        desc="Comma-separated list of source document IDs used"
    )


# ============================================================================
# DSPY MODULES (Chain of Thought)
# ============================================================================

class IntentClassifier(dspy.Module):
    """
    DSPy module for intent classification with Chain of Thought reasoning

    Usage:
        classifier = IntentClassifier()
        result = classifier(
            message="I need 500 meal trays",
            conversation_history="[]"
        )
        print(result.intent)  # "order_placement"
        print(result.confidence)  # 0.95
    """

    def __init__(self):
        super().__init__()
        # Use ChainOfThought for better reasoning
        self.classify = dspy.ChainOfThought(IntentClassifierSignature)

    def forward(self, message: str, conversation_history: str = "[]"):
        """
        Classify intent with reasoning

        Args:
            message: Customer message
            conversation_history: JSON string of conversation history

        Returns:
            dspy.Prediction with intent, confidence, reasoning
        """
        return self.classify(
            message=message,
            conversation_history=conversation_history
        )


class RAGQA(dspy.Module):
    """
    DSPy module for RAG-based QA with Chain of Thought reasoning

    Usage:
        qa = RAGQA()
        result = qa(
            question="What's the return policy?",
            context="Article 1: Returns accepted within 30 days..."
        )
        print(result.answer)
        print(result.sources)
    """

    def __init__(self):
        super().__init__()
        # Use ChainOfThought for grounded reasoning
        self.answer = dspy.ChainOfThought(RAGQASignature)

    def forward(self, question: str, context: str):
        """
        Answer question using retrieved context

        Args:
            question: Customer question
            context: Retrieved knowledge base context

        Returns:
            dspy.Prediction with answer, confidence, sources
        """
        return self.answer(
            question=question,
            context=context
        )


# ============================================================================
# MULTI-STAGE MODULES (Optional - Advanced)
# ============================================================================

class MultiStageRAGQA(dspy.Module):
    """
    Advanced RAG module with retrieve → rerank → answer pipeline

    This is an optional advanced version that can be optimized later.
    For now, we use the simpler RAGQA module.
    """

    def __init__(self):
        super().__init__()
        self.retrieve = dspy.Retrieve(k=5)
        self.answer = dspy.ChainOfThought(RAGQASignature)

    def forward(self, question: str):
        """
        Retrieve context and answer question

        Args:
            question: Customer question

        Returns:
            dspy.Prediction with answer, confidence, sources
        """
        # Retrieve relevant passages
        retrieval = self.retrieve(question)
        context = "\n\n".join([p.text for p in retrieval.passages])

        # Generate answer
        return self.answer(question=question, context=context)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_intent(intent: str) -> bool:
    """
    Validate that intent is one of the supported types

    Args:
        intent: Intent string to validate

    Returns:
        True if valid, False otherwise
    """
    valid_intents = {
        "order_placement",
        "order_status",
        "product_inquiry",
        "policy_question",
        "complaint",
        "greeting",
        "general_query"
    }
    return intent in valid_intents


def validate_confidence(confidence: Any) -> bool:
    """
    Validate confidence score is between 0 and 1

    Args:
        confidence: Confidence value to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        conf = float(confidence)
        return 0.0 <= conf <= 1.0
    except (ValueError, TypeError):
        return False


def parse_conversation_history(history: List[Dict[str, str]]) -> str:
    """
    Convert conversation history to string format for DSPy

    Args:
        history: List of message dicts with 'role' and 'content'

    Returns:
        JSON string representation
    """
    import json
    return json.dumps(history)
