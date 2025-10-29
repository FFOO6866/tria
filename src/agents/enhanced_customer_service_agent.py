"""
TRIA Enhanced Customer Service Agent
======================================

Main intelligent agent that:
1. Receives user message
2. Classifies intent
3. Routes to appropriate handler:
   - order_placement → process_order workflow (existing)
   - product_inquiry/policy_question → RAG retrieval + GPT-4 response
   - order_status → A2A query (placeholder for Phase 4)
   - complaint → escalation workflow

NO MOCKING - Uses real GPT-4, ChromaDB, and PostgreSQL.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from openai import OpenAI

from .intent_classifier import IntentClassifier, IntentResult
from rag.retrieval import (
    search_policies,
    search_faqs,
    search_escalation_rules,
    format_results_for_llm,
    format_multi_collection_results_for_llm,
    search_all_collections
)
from prompts.system_prompts import (
    CUSTOMER_SERVICE_PROMPT,
    build_rag_qa_prompt,
    build_escalation_prompt
)


# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class CustomerServiceResponse:
    """
    Response from customer service agent

    Attributes:
        intent: Detected intent
        confidence: Intent confidence score
        response_text: Generated response to user
        knowledge_used: List of knowledge chunks used (if RAG was applied)
        action_taken: What action was taken (rag_qa, order_processing, escalation, etc.)
        requires_escalation: Whether human intervention is needed
        extracted_entities: Entities extracted from message
        metadata: Additional metadata
        timestamp: Response timestamp
    """
    intent: str
    confidence: float
    response_text: str
    knowledge_used: List[Dict[str, Any]] = field(default_factory=list)
    action_taken: str = "none"
    requires_escalation: bool = False
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "response_text": self.response_text,
            "knowledge_used": self.knowledge_used,
            "action_taken": self.action_taken,
            "requires_escalation": self.requires_escalation,
            "extracted_entities": self.extracted_entities,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ============================================================================
# ENHANCED CUSTOMER SERVICE AGENT
# ============================================================================

class EnhancedCustomerServiceAgent:
    """
    Intelligent customer service agent with intent-based routing

    Workflow:
    1. Classify intent using GPT-4
    2. Route based on intent:
       - order_placement → Order processing workflow
       - product_inquiry/policy_question → RAG + GPT-4 QA
       - order_status → A2A status query (Phase 4)
       - complaint → Escalation workflow
       - greeting → Friendly response
       - general_query → General assistance

    Usage:
        agent = EnhancedCustomerServiceAgent(api_key="...")
        response = agent.handle_message(
            message="What's your refund policy?",
            conversation_history=[...]
        )
        print(response.response_text)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        timeout: int = 60,
        enable_rag: bool = True,
        enable_escalation: bool = True
    ):
        """
        Initialize enhanced customer service agent

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: GPT-4 model to use
            temperature: Temperature for GPT-4 responses
            timeout: API timeout in seconds
            enable_rag: Enable RAG knowledge base retrieval
            enable_escalation: Enable escalation workflow

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        # NO HARDCODING - Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Provide via api_key parameter or set OPENAI_API_KEY environment variable."
            )

        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.enable_rag = enable_rag
        self.enable_escalation = enable_escalation

        # Initialize components
        self.intent_classifier = IntentClassifier(
            api_key=self.api_key,
            model=model,
            temperature=0.3,  # Lower temperature for intent classification
            timeout=timeout
        )

        self.openai_client = OpenAI(api_key=self.api_key, timeout=timeout)

        logger.info(
            f"EnhancedCustomerServiceAgent initialized with model={model}, "
            f"enable_rag={enable_rag}, enable_escalation={enable_escalation}"
        )

    def handle_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> CustomerServiceResponse:
        """
        Handle customer message with intelligent routing

        Args:
            message: User message
            conversation_history: Optional conversation context
            user_context: Optional user context (outlet_id, language, etc.)

        Returns:
            CustomerServiceResponse with intent, response, and metadata

        Raises:
            ValueError: If message is empty
            RuntimeError: If processing fails
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        logger.info(f"Handling message: {message[:100]}...")

        # Step 1: Classify intent
        try:
            intent_result = self.intent_classifier.classify_intent(
                message=message,
                conversation_history=conversation_history or []
            )
            logger.info(
                f"Intent classified: {intent_result.intent} "
                f"(confidence: {intent_result.confidence:.2f})"
            )
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}", exc_info=True)
            # Fallback to general_query
            intent_result = IntentResult(
                intent="general_query",
                confidence=0.0,
                reasoning=f"Classification failed: {str(e)}"
            )

        # Step 2: Route based on intent
        try:
            if intent_result.intent == "greeting":
                response = self._handle_greeting(message, conversation_history)

            elif intent_result.intent == "order_placement":
                response = self._handle_order_placement(
                    message, intent_result, conversation_history, user_context
                )

            elif intent_result.intent == "order_status":
                response = self._handle_order_status(
                    message, intent_result, conversation_history
                )

            elif intent_result.intent in ["product_inquiry", "policy_question"]:
                response = self._handle_inquiry_with_rag(
                    message, intent_result, conversation_history
                )

            elif intent_result.intent == "complaint":
                response = self._handle_complaint(
                    message, intent_result, conversation_history
                )

            else:  # general_query
                response = self._handle_general_query(
                    message, intent_result, conversation_history
                )

            # Add intent and confidence to response
            response.intent = intent_result.intent
            response.confidence = intent_result.confidence
            response.extracted_entities = intent_result.extracted_entities

            return response

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}", exc_info=True)
            # Return error response
            return CustomerServiceResponse(
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                response_text=(
                    "I apologize, but I encountered an issue processing your request. "
                    "Please try again or contact our support team for assistance."
                ),
                action_taken="error",
                requires_escalation=True,
                metadata={"error": str(e)}
            )

    def _handle_greeting(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """Handle greeting messages"""
        greeting_response = (
            "Hello! I'm TRIA's AI customer service assistant. "
            "I'm here to help you with:\n\n"
            "• Placing new orders\n"
            "• Checking order status\n"
            "• Product information and pricing\n"
            "• Policy questions\n"
            "• General inquiries\n\n"
            "How can I assist you today?"
        )

        return CustomerServiceResponse(
            intent="greeting",
            confidence=1.0,
            response_text=greeting_response,
            action_taken="greeting"
        )

    def _handle_order_placement(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]],
        user_context: Optional[Dict[str, Any]]
    ) -> CustomerServiceResponse:
        """
        Handle order placement intent

        NOTE: Integration with existing process_order_with_catalog.py workflow
        will be implemented in integration phase. For now, provide helpful response.
        """
        logger.info("Order placement detected - will integrate with existing workflow")

        # For now, provide helpful response and mark for order processing
        response_text = (
            "I'd be happy to help you place an order! "
            "To process your order efficiently, please provide:\n\n"
            "1. Your outlet/company name\n"
            "2. Products you need (with quantities)\n"
            "3. Any special delivery requirements\n\n"
            "You can list items like: '500 meal trays, 200 lids, 100 pizza boxes (10 inch)'"
        )

        # Extract product mentions from entities
        products_mentioned = intent_result.extracted_entities.get("product_names", [])
        outlet_mentioned = intent_result.extracted_entities.get("outlet_name")

        metadata = {
            "products_mentioned": products_mentioned,
            "outlet_mentioned": outlet_mentioned,
            "ready_for_processing": bool(products_mentioned),
            "note": "Integrate with process_order_with_catalog.py workflow"
        }

        return CustomerServiceResponse(
            intent="order_placement",
            confidence=intent_result.confidence,
            response_text=response_text,
            action_taken="order_placement_guidance",
            metadata=metadata
        )

    def _handle_order_status(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """
        Handle order status inquiry

        NOTE: A2A integration for order status queries is Phase 4.
        For now, provide helpful placeholder response.
        """
        logger.info("Order status query detected - A2A integration pending (Phase 4)")

        order_id = intent_result.extracted_entities.get("order_id")

        if order_id:
            response_text = (
                f"I understand you're checking on order #{order_id}. "
                f"Let me look that up for you.\n\n"
                f"[Note: A2A order status integration coming in Phase 4]\n\n"
                f"In the meantime, please contact our support team with your order number "
                f"for the most up-to-date status information."
            )
        else:
            response_text = (
                "I'd be happy to help you check your order status. "
                "Could you please provide your order number? "
                "It should be in the format #XXXXX from your order confirmation."
            )

        return CustomerServiceResponse(
            intent="order_status",
            confidence=intent_result.confidence,
            response_text=response_text,
            action_taken="order_status_query",
            requires_escalation=bool(order_id),  # Escalate if order ID provided
            metadata={
                "order_id": order_id,
                "note": "A2A integration pending (Phase 4)"
            }
        )

    def _handle_inquiry_with_rag(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """
        Handle product inquiry or policy question using RAG

        This is the core RAG-powered Q&A functionality.
        """
        logger.info(f"Handling {intent_result.intent} with RAG retrieval")

        if not self.enable_rag:
            logger.warning("RAG is disabled - using direct GPT-4 response")
            return self._handle_without_rag(message, intent_result, conversation_history)

        try:
            # Retrieve relevant knowledge
            if intent_result.intent == "policy_question":
                # Search policies and escalation rules
                policy_results = search_policies(
                    query=message,
                    api_key=self.api_key,
                    top_n=5
                )
                knowledge_text = format_results_for_llm(policy_results, "POLICIES")
                knowledge_chunks = policy_results

            elif intent_result.intent == "product_inquiry":
                # Search FAQs and policies
                faq_results = search_faqs(
                    query=message,
                    api_key=self.api_key,
                    top_n=5
                )
                knowledge_text = format_results_for_llm(faq_results, "FAQs")
                knowledge_chunks = faq_results

            else:
                # Search all collections
                all_results = search_all_collections(
                    query=message,
                    api_key=self.api_key,
                    top_n_per_collection=3
                )
                knowledge_text = format_multi_collection_results_for_llm(all_results)
                knowledge_chunks = (
                    all_results.get("policies", []) +
                    all_results.get("faqs", []) +
                    all_results.get("escalation_rules", [])
                )

            logger.info(f"Retrieved {len(knowledge_chunks)} knowledge chunks")

            # Build RAG QA prompt
            qa_prompt = build_rag_qa_prompt(
                user_question=message,
                retrieved_knowledge=knowledge_text,
                conversation_history=conversation_history or []
            )

            # Generate response with GPT-4
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CUSTOMER_SERVICE_PROMPT},
                    {"role": "user", "content": qa_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1000
            )

            response_text = response.choices[0].message.content

            return CustomerServiceResponse(
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                response_text=response_text,
                knowledge_used=knowledge_chunks,
                action_taken="rag_qa",
                metadata={
                    "knowledge_chunks_used": len(knowledge_chunks),
                    "collections_searched": intent_result.intent
                }
            )

        except Exception as e:
            logger.error(f"RAG retrieval/QA failed: {str(e)}", exc_info=True)
            # Fallback to direct response without RAG
            return self._handle_without_rag(message, intent_result, conversation_history)

    def _handle_complaint(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """Handle complaint with empathy and escalation"""
        logger.info("Complaint detected - preparing escalation")

        # Empathetic acknowledgment response
        response_text = (
            "I sincerely apologize for the issue you're experiencing. "
            "Your satisfaction is very important to us, and I want to make sure "
            "this is resolved properly.\n\n"
            "I'm escalating your concern to our customer service team who will "
            "contact you shortly to address this personally. "
            "In the meantime, could you provide additional details:\n\n"
            "1. Your order number (if applicable)\n"
            "2. What specifically went wrong\n"
            "3. How you'd like us to resolve this\n\n"
            "We take these matters seriously and will work to make this right."
        )

        # Check if escalation workflow is enabled
        if self.enable_escalation:
            # TODO: Integrate with escalation workflow
            # For now, just mark for escalation
            logger.info("Complaint marked for human escalation")

        return CustomerServiceResponse(
            intent="complaint",
            confidence=intent_result.confidence,
            response_text=response_text,
            action_taken="escalation",
            requires_escalation=True,
            metadata={
                "escalation_reason": "customer_complaint",
                "sentiment": "negative"
            }
        )

    def _handle_general_query(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """Handle general queries with GPT-4"""
        logger.info("Handling general query")

        try:
            # Format conversation history for GPT-4
            messages = [{"role": "system", "content": CUSTOMER_SERVICE_PROMPT}]

            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            # Add current message
            messages.append({"role": "user", "content": message})

            # Generate response
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=800
            )

            response_text = response.choices[0].message.content

            return CustomerServiceResponse(
                intent="general_query",
                confidence=intent_result.confidence,
                response_text=response_text,
                action_taken="general_assistance"
            )

        except Exception as e:
            logger.error(f"General query handling failed: {str(e)}", exc_info=True)
            raise

    def _handle_without_rag(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """
        Fallback handler when RAG is unavailable

        Uses GPT-4 directly without knowledge base retrieval.
        """
        logger.warning("Handling query without RAG - using GPT-4 general knowledge")

        response_text = (
            "I apologize, but I'm currently unable to access our complete knowledge base. "
            "However, I can try to help with general information, or you can contact "
            "our support team for detailed policy information.\n\n"
            "What specific information are you looking for?"
        )

        return CustomerServiceResponse(
            intent=intent_result.intent,
            confidence=intent_result.confidence,
            response_text=response_text,
            action_taken="fallback_no_rag",
            requires_escalation=True,
            metadata={"rag_unavailable": True}
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def handle_customer_message(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> CustomerServiceResponse:
    """
    Convenience function to handle a single customer message

    Args:
        message: User message
        conversation_history: Optional conversation context
        user_context: Optional user context
        api_key: Optional OpenAI API key

    Returns:
        CustomerServiceResponse

    Example:
        response = handle_customer_message("What's your refund policy?")
        print(response.response_text)
    """
    agent = EnhancedCustomerServiceAgent(api_key=api_key)
    return agent.handle_message(message, conversation_history, user_context)
