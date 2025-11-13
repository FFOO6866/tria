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
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from openai import OpenAI

from .intent_classifier import IntentClassifier, IntentResult
from rag.retrieval import (
    search_policies,
    search_faqs,
    search_escalation_rules,
    search_tone_guidelines,
    format_results_for_llm,
    format_multi_collection_results_for_llm,
    search_all_collections
)
from prompts.system_prompts import (
    CUSTOMER_SERVICE_PROMPT,
    build_rag_qa_prompt,
    build_escalation_prompt
)
from rag.policy_analytics import get_tracker
from cache.response_cache import get_cache
from validation.input_validator import validate_and_sanitize, ValidationSeverity
from ratelimit.rate_limiter import get_rate_limiter

# Import monitoring modules
from monitoring.logger import (
    app_logger,
    request_logger,
    performance_logger,
    error_tracker
)
from monitoring.metrics import (
    metrics_collector,
    cache_metrics,
    rate_limit_metrics,
    error_metrics,
    memory_metrics
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
        enable_escalation: bool = True,
        enable_response_validation: bool = True,
        enable_cache: bool = True,
        enable_rate_limiting: bool = True
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
            enable_response_validation: Enable policy-aware response validation
            enable_cache: Enable response caching
            enable_rate_limiting: Enable rate limiting

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
        self.enable_response_validation = enable_response_validation
        self.enable_cache = enable_cache
        self.enable_rate_limiting = enable_rate_limiting

        # Initialize components
        # Use GPT-3.5-Turbo for intent classification (6x cheaper, 2-5x faster than GPT-4)
        # Intent classification is simple enough for GPT-3.5
        self.intent_classifier = IntentClassifier(
            api_key=self.api_key,
            model="gpt-3.5-turbo",  # Optimized for speed and cost
            temperature=0.3,  # Lower temperature for intent classification
            timeout=30  # Shorter timeout for faster model
        )

        self.openai_client = OpenAI(api_key=self.api_key, timeout=timeout)

        # Initialize cache
        self.cache = get_cache() if enable_cache else None
        if self.cache:
            logger.info("Response caching enabled")

        # Initialize rate limiter
        self.rate_limiter = get_rate_limiter() if enable_rate_limiting else None
        if self.rate_limiter:
            logger.info("Rate limiting enabled")

        logger.info(
            f"EnhancedCustomerServiceAgent initialized with model={model}, "
            f"enable_rag={enable_rag}, enable_escalation={enable_escalation}, "
            f"enable_response_validation={enable_response_validation}, "
            f"enable_cache={enable_cache}, enable_rate_limiting={enable_rate_limiting}"
        )

    def handle_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> CustomerServiceResponse:
        """
        Handle customer message with intelligent routing

        Args:
            message: User message
            conversation_history: Optional conversation context
            user_context: Optional user context (outlet_id, language, etc.)
            user_id: Optional user identifier for rate limiting
            ip_address: Optional IP address for rate limiting

        Returns:
            CustomerServiceResponse with intent, response, and metadata

        Raises:
            RuntimeError: If processing fails
        """
        # Start performance tracking
        start_time = time.time()
        metrics_collector.increment_counter("requests_total")
        memory_metrics.record_current()

        # Log incoming request
        request_logger.log_request(
            method="CHAT",
            endpoint="/handle_message",
            user_id=user_id,
            ip_address=ip_address,
            message_length=len(message)
        )

        try:
            # Validate and sanitize input
            validation_result = validate_and_sanitize(message, max_length=5000, strict_mode=False)

            if not validation_result.is_valid:
                # Track validation failure
                error_metrics.record_error("ValidationError", severity="warning")
                metrics_collector.increment_counter("validation_failures")

                # Log validation failure
                app_logger.error(
                    "Input validation failed",
                    user_id=user_id,
                    validation_issues=validation_result.issues,
                    message_length=len(message)
                )

                # Record response time
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_metric("response_time_ms", duration_ms)
                request_logger.log_response(
                    method="CHAT",
                    endpoint="/handle_message",
                    status_code=400,
                    latency_ms=duration_ms,
                    user_id=user_id
                )

                # Return error response
                return CustomerServiceResponse(
                intent="validation_error",
                confidence=0.0,
                response_text=(
                    "I'm sorry, but I couldn't process your message due to validation issues. "
                    "Please ensure your message is between 1-5000 characters and doesn't contain "
                    "unusual characters. If you continue to have issues, please contact our support team."
                ),
                action_taken="input_validation_failed",
                requires_escalation=True,
                metadata={
                    "validation_issues": validation_result.issues,
                    "original_message_length": len(message)
                }
            )

            # Use sanitized input for processing
            message = validation_result.sanitized_input

            # Log warnings if any (non-critical issues)
            if validation_result.has_warnings():
                app_logger.warning(
                    "Input validation warnings",
                    user_id=user_id,
                    validation_warnings=validation_result.issues
                )

            # Check rate limits
            if self.enable_rate_limiting and self.rate_limiter:
                rate_limit_result = self.rate_limiter.check_rate_limit(
                    user_id=user_id,
                    ip_address=ip_address
                )

                if not rate_limit_result.allowed:
                    # Track rate limit block
                    rate_limit_metrics.record_blocked(
                        user_id=user_id or "anonymous",
                        limit_type=rate_limit_result.limit_type.value if rate_limit_result.limit_type else "unknown"
                    )

                    # Log rate limit exceeded
                    app_logger.warning(
                        "Rate limit exceeded",
                        user_id=user_id,
                        ip_address=ip_address,
                        limit_type=rate_limit_result.limit_type.value if rate_limit_result.limit_type else "unknown",
                        retry_after=rate_limit_result.retry_after
                    )

                    # Record response time
                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_metric("response_time_ms", duration_ms)
                    request_logger.log_response(
                        method="CHAT",
                        endpoint="/handle_message",
                        status_code=429,
                        latency_ms=duration_ms,
                        user_id=user_id
                    )

                    return CustomerServiceResponse(
                    intent="rate_limit_exceeded",
                    confidence=0.0,
                    response_text=(
                        f"I apologize, but you've reached the maximum number of requests allowed. "
                        f"Please try again in {rate_limit_result.retry_after} seconds. "
                        f"If you need immediate assistance, please contact our support team directly."
                    ),
                    action_taken="rate_limit_exceeded",
                    requires_escalation=False,
                    metadata={
                        "rate_limit_type": rate_limit_result.limit_type.value if rate_limit_result.limit_type else None,
                        "retry_after": rate_limit_result.retry_after,
                        "limit": rate_limit_result.limit,
                        "remaining": rate_limit_result.remaining,
                        "reset_at": rate_limit_result.reset_at,
                        "rate_limit_headers": rate_limit_result.to_headers()
                    }
                )
                else:
                    # Track allowed request
                    rate_limit_metrics.record_allowed(user_id=user_id or "anonymous")

            app_logger.info(
                "Processing message",
                user_id=user_id,
                message_preview=message[:100]
            )

            # Step 1: Classify intent (with caching)
            try:
                # Check intent cache first
                cached_intent = None
                if self.enable_cache and self.cache:
                    cached_intent = self.cache.get_intent(message)
                    if cached_intent:
                        intent_result = IntentResult(**cached_intent)
                        cache_metrics.record_hit()  # Track cache hit
                        app_logger.info(
                            "Intent classification cache hit",
                            intent=intent_result.intent,
                            confidence=intent_result.confidence
                        )
                    else:
                        cache_metrics.record_miss()  # Track cache miss
                        app_logger.debug("Intent classification cache miss")

                # Classify intent if not cached
                if not cached_intent:
                    intent_result = self.intent_classifier.classify_intent(
                        message=message,
                        conversation_history=conversation_history or []
                    )
                    app_logger.info(
                        "Intent classified",
                        intent=intent_result.intent,
                        confidence=intent_result.confidence
                    )

                # Cache the intent result
                if self.enable_cache and self.cache:
                    from dataclasses import asdict
                    self.cache.put_intent(message, asdict(intent_result))

            except Exception as e:
                logger.error(f"Intent classification failed: {str(e)}", exc_info=True)
                # Fallback to general_query
                intent_result = IntentResult(
                    intent="general_query",
                    confidence=0.0,
                    reasoning=f"Classification failed: {str(e)}"
                )

            # Check for cached full response (after we have intent)
            if self.enable_cache and self.cache:
                cached_response = self.cache.get_response(message, intent_result.intent)
                if cached_response:
                    logger.info(
                        f"Full response CACHE HIT for intent={intent_result.intent} "
                        f"- skipping all processing"
                    )
                    return CustomerServiceResponse(
                        intent=intent_result.intent,
                        confidence=intent_result.confidence,
                        response_text=cached_response,
                        action_taken="cached_response",
                        metadata={"cache_hit": True}
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

                # Cache the complete response
                if self.enable_cache and self.cache:
                    self.cache.put_response(message, intent_result.intent, response.response_text)
                    app_logger.debug("Cached response", intent=intent_result.intent)

                # Record successful response metrics
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_metric("response_time_ms", duration_ms)
                metrics_collector.increment_counter("requests_succeeded")

                # Log successful response
                request_logger.log_response(
                    method="CHAT",
                    endpoint="/handle_message",
                    status_code=200,
                    latency_ms=duration_ms,
                    user_id=user_id
                )

                app_logger.info(
                    "Message handled successfully",
                    intent=intent_result.intent,
                    action_taken=response.action_taken,
                    duration_ms=duration_ms,
                    user_id=user_id
                )

                return response

            except Exception as e:
                # Track error
                error_metrics.record_error(type(e).__name__, severity="error", user_id=user_id)
                error_tracker.track_error(e, context={"user_id": user_id, "message_length": len(message)})

                # Log error
                app_logger.error(
                    "Message handling failed",
                    error=e,
                    user_id=user_id,
                    message_length=len(message)
                )

                # Record failed response metrics
                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_metric("response_time_ms", duration_ms)
                metrics_collector.increment_counter("requests_failed")

                request_logger.log_response(
                    method="CHAT",
                    endpoint="/handle_message",
                    status_code=500,
                    latency_ms=duration_ms,
                    user_id=user_id
                )

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

        except Exception as e:
            # Outer exception handler - catches any unhandled errors from the entire process
            error_metrics.record_error(type(e).__name__, severity="critical", user_id=user_id)
            error_tracker.track_error(e, context={"user_id": user_id, "message": message[:100]})

            # Log critical error
            app_logger.error(
                "Critical error in message handling",
                error=e,
                user_id=user_id,
                message_preview=message[:100]
            )

            # Record failed response metrics
            duration_ms = (time.time() - start_time) * 1000
            metrics_collector.record_metric("response_time_ms", duration_ms)
            metrics_collector.increment_counter("requests_failed")

            request_logger.log_response(
                method="CHAT",
                endpoint="/handle_message",
                status_code=500,
                latency_ms=duration_ms,
                user_id=user_id
            )

            # Return generic error response
            return CustomerServiceResponse(
                intent="error",
                confidence=0.0,
                response_text=(
                    "I apologize, but I encountered a technical issue. "
                    "Please try again later or contact our support team for immediate assistance."
                ),
                action_taken="critical_error",
                requires_escalation=True,
                metadata={"error": str(e), "error_type": type(e).__name__}
            )

    def _get_tone_guidelines(
        self,
        intent: str,
        message: str,
        sentiment: str = "neutral"
    ) -> str:
        """
        Retrieve appropriate tone guidelines from RAG based on context

        Args:
            intent: Detected intent (complaint, greeting, product_inquiry, etc.)
            message: User's message (for additional context)
            sentiment: Estimated sentiment (positive/neutral/negative)

        Returns:
            Formatted tone guidelines for LLM system prompt
        """
        # Build tone query based on intent and sentiment
        if intent == "complaint" or sentiment == "negative":
            tone_query = (
                "How to respond to customer complaints with empathy and professionalism. "
                "Handling frustrated or angry customers."
            )
        elif intent == "greeting":
            tone_query = "How to greet customers professionally and warmly. Initial greeting tone."
        elif intent == "order_placement":
            tone_query = (
                "How to assist customers with placing orders. "
                "Professional, efficient, and helpful tone for order processing."
            )
        elif intent == "policy_question" or intent == "product_inquiry":
            tone_query = (
                "How to explain policies and product information clearly. "
                "Professional informative tone for answering questions."
            )
        else:
            tone_query = (
                "Standard customer service tone. "
                "Professional, friendly, and helpful communication style."
            )

        try:
            # Retrieve tone guidelines from RAG
            tone_results = search_tone_guidelines(
                query=tone_query,
                api_key=self.api_key,
                top_n=2  # Just top 2 most relevant guidelines
            )

            if tone_results:
                # Format for LLM prompt
                tone_text = "\n\nTONE GUIDELINES FOR THIS INTERACTION:\n"
                tone_text += "=" * 60 + "\n"

                for idx, result in enumerate(tone_results, 1):
                    similarity_pct = result['similarity'] * 100 if result['similarity'] else 0
                    if similarity_pct >= 60:  # Only use highly relevant tone guidelines
                        tone_text += f"\n[Guideline {idx}] (Relevance: {similarity_pct:.0f}%)\n"
                        tone_text += f"{result['text']}\n"

                tone_text += "=" * 60 + "\n"

                logger.info(
                    f"Retrieved {len(tone_results)} tone guidelines for intent='{intent}', "
                    f"sentiment='{sentiment}'"
                )

                # Track tone retrieval
                try:
                    tracker = get_tracker()
                    top_similarity = tone_results[0]['similarity'] if tone_results else None
                    tracker.log_tone_retrieval(
                        intent=intent,
                        sentiment=sentiment,
                        results_count=len(tone_results),
                        metadata={"top_similarity": top_similarity}
                    )
                except Exception as e:
                    # Don't fail if tracking fails, but log the error
                    logger.warning(f"Failed to track tone retrieval: {str(e)}", exc_info=False)

                return tone_text
            else:
                logger.warning(f"No tone guidelines found for intent='{intent}'")
                return ""

        except Exception as e:
            logger.error(f"Failed to retrieve tone guidelines: {str(e)}", exc_info=True)
            return ""  # Fail gracefully, use default tone

    def _determine_escalation_tier(
        self,
        message: str,
        intent: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Determine escalation tier and routing using RAG-retrieved escalation rules

        Args:
            message: User's message
            intent: Detected intent
            conversation_history: Optional conversation context

        Returns:
            Dictionary with escalation decision:
            {
                "tier": "TIER_1_BOT"|"TIER_2_AGENT"|"TIER_3_MANAGER"|"TIER_4_URGENT",
                "urgency": "low"|"medium"|"high"|"critical",
                "category": "complaint"|"refund"|"technical"|"other",
                "summary": "Brief summary for receiving tier",
                "sentiment": "positive"|"neutral"|"negative"|"angry",
                "requires_immediate_attention": bool,
                "rules_used": list of rule chunks
            }
        """
        try:
            # Build escalation-specific query
            escalation_query = (
                f"When should I escalate this customer issue? "
                f"Intent: {intent}. Message: {message}"
            )

            # Retrieve escalation rules from RAG
            escalation_rules = search_escalation_rules(
                query=escalation_query,
                api_key=self.api_key,
                top_n=3
            )

            if not escalation_rules:
                logger.warning("No escalation rules found, using default escalation")
                return {
                    "tier": "TIER_2_AGENT",
                    "urgency": "medium",
                    "category": "complaint",
                    "summary": "Customer issue requiring human attention",
                    "sentiment": "negative",
                    "requires_immediate_attention": False,
                    "rules_used": []
                }

            # Format escalation rules for LLM
            rules_text = format_results_for_llm(escalation_rules, "ESCALATION RULES")

            # Build escalation routing prompt
            escalation_prompt = build_escalation_prompt(
                user_message=message,
                escalation_rules=rules_text,
                conversation_history=conversation_history or []
            )

            # Use GPT-4 to make escalation decision
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an escalation routing expert."},
                    {"role": "user", "content": escalation_prompt}
                ],
                temperature=0.3,  # Lower temperature for consistent routing decisions
                max_tokens=500,
                response_format={"type": "json_object"}  # JSON mode for structured output
            )

            # Parse escalation decision
            decision_text = response.choices[0].message.content
            decision = json.loads(decision_text)

            # Add rules used to metadata
            decision["rules_used"] = escalation_rules

            logger.info(
                f"Escalation decision: tier={decision.get('tier')}, "
                f"urgency={decision.get('urgency')}, "
                f"category={decision.get('category')}"
            )

            return decision

        except Exception as e:
            logger.error(f"Escalation tier determination failed: {str(e)}", exc_info=True)
            # Fallback to safe default
            return {
                "tier": "TIER_2_AGENT",
                "urgency": "medium",
                "category": "unknown",
                "summary": f"Customer issue: {message[:100]}",
                "sentiment": "neutral",
                "requires_immediate_attention": False,
                "rules_used": [],
                "error": str(e)
            }

    def _validate_response_against_policies(
        self,
        response_text: str,
        intent: str,
        knowledge_used: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Validate that response aligns with company policies

        This method checks for:
        - Pricing accuracy (if prices are mentioned)
        - Policy compliance (delivery times, refund terms, etc.)
        - Factual correctness against knowledge base

        Args:
            response_text: Generated response to validate
            intent: Intent of the conversation
            knowledge_used: Knowledge chunks used to generate response

        Returns:
            Dictionary with validation results:
            {
                "is_valid": bool,
                "confidence": float,
                "issues_found": list,
                "corrected_response": str (if corrections needed),
                "validation_details": dict
            }
        """
        try:
            # Build validation query based on response content
            validation_query = (
                f"Verify the following customer service response is factually correct "
                f"according to TRIA policies: {response_text[:500]}"
            )

            # Retrieve relevant policies for validation
            validation_policies = search_policies(
                query=validation_query,
                api_key=self.api_key,
                top_n=3
            )

            # Also check FAQs for pricing/product information
            validation_faqs = search_faqs(
                query=validation_query,
                api_key=self.api_key,
                top_n=2
            )

            # Combine validation sources
            all_validation_sources = validation_policies + validation_faqs

            if not all_validation_sources:
                # No validation sources found - cannot validate
                logger.warning("No validation sources found for response validation")
                return {
                    "is_valid": True,  # Assume valid if we can't validate
                    "confidence": 0.5,
                    "issues_found": [],
                    "validation_details": {"reason": "No validation sources available"}
                }

            # Format validation knowledge
            validation_knowledge = format_results_for_llm(
                all_validation_sources,
                "VALIDATION KNOWLEDGE"
            )

            # Use GPT-4 to validate response against policies
            validation_prompt = f"""You are a policy compliance validator for TRIA AI-BPO Solutions.

TASK: Validate that the customer service response below is factually accurate and complies with company policies.

VALIDATION KNOWLEDGE (Official Policies and FAQs):
{validation_knowledge}

RESPONSE TO VALIDATE:
{response_text}

VALIDATION CRITERIA:
1. **Pricing Accuracy**: If prices are mentioned, do they match the official pricing?
2. **Policy Compliance**: Are delivery times, refund terms, and policies stated correctly?
3. **Factual Correctness**: Are all claims supported by the validation knowledge?
4. **No Hallucinations**: Is the response making up information not in the knowledge base?

IMPORTANT:
- If the response is accurate and compliant, return is_valid: true
- If there are minor issues that don't affect core facts, return is_valid: true with warnings
- If there are factual errors or policy violations, return is_valid: false with corrections

Return ONLY a JSON object:
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "issues_found": [
    {{
      "type": "pricing_error|policy_violation|factual_error|hallucination",
      "severity": "critical|major|minor",
      "description": "what's wrong",
      "location": "relevant excerpt from response"
    }}
  ],
  "corrected_response": "corrected version if is_valid=false, otherwise null",
  "validation_summary": "brief summary of validation"
}}
"""

            # Get validation result from GPT-4
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a policy compliance validator."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.2,  # Low temperature for consistent validation
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            validation_result = json.loads(response.choices[0].message.content)

            # Add validation sources to result
            validation_result["validation_sources"] = len(all_validation_sources)
            validation_result["policies_checked"] = len(validation_policies)
            validation_result["faqs_checked"] = len(validation_faqs)

            # Log validation result
            if validation_result.get("is_valid"):
                logger.info(
                    f"Response validation PASSED (confidence: {validation_result.get('confidence', 0):.2f})"
                )
            else:
                logger.warning(
                    f"Response validation FAILED: {len(validation_result.get('issues_found', []))} issues found"
                )

            # Track validation
            try:
                tracker = get_tracker()
                tracker.log_validation(
                    intent=intent,
                    validation_passed=validation_result.get("is_valid", True),
                    confidence=validation_result.get("confidence", 0),
                    issues_count=len(validation_result.get("issues_found", [])),
                    metadata={
                        "policies_checked": validation_result.get("policies_checked", 0),
                        "faqs_checked": validation_result.get("faqs_checked", 0)
                    }
                )
            except Exception as e:
                # Don't fail if tracking fails, but log the error
                logger.warning(f"Failed to track validation result: {str(e)}", exc_info=False)

            return validation_result

        except Exception as e:
            logger.error(f"Response validation failed: {str(e)}", exc_info=True)
            # On error, assume valid (fail-open to avoid blocking user)
            return {
                "is_valid": True,
                "confidence": 0.0,
                "issues_found": [],
                "validation_details": {"error": str(e)},
                "error": str(e)
            }

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
            # Retrieve relevant knowledge (with caching)
            # Reduced from top_n=5 to top_n=3 for performance optimization
            # This reduces context tokens by ~40% while maintaining quality
            if intent_result.intent == "policy_question":
                # Check cache first
                cached_results = None
                if self.enable_cache and self.cache:
                    cached_results = self.cache.get_retrieval(message, "policies_en", 3)

                if cached_results:
                    policy_results = cached_results
                    logger.info("Policy retrieval CACHE HIT")
                else:
                    # Search policies and escalation rules
                    policy_results = search_policies(
                        query=message,
                        api_key=self.api_key,
                        top_n=3  # Optimized from 5 to 3
                    )
                    # Cache the results
                    if self.enable_cache and self.cache:
                        self.cache.put_retrieval(message, "policies_en", 3, policy_results)

                knowledge_text = format_results_for_llm(policy_results, "POLICIES")
                knowledge_chunks = policy_results

            elif intent_result.intent == "product_inquiry":
                # Check cache first
                cached_results = None
                if self.enable_cache and self.cache:
                    cached_results = self.cache.get_retrieval(message, "faqs_en", 3)

                if cached_results:
                    faq_results = cached_results
                    logger.info("FAQ retrieval CACHE HIT")
                else:
                    # Search FAQs and policies
                    faq_results = search_faqs(
                        query=message,
                        api_key=self.api_key,
                        top_n=3  # Optimized from 5 to 3
                    )
                    # Cache the results
                    if self.enable_cache and self.cache:
                        self.cache.put_retrieval(message, "faqs_en", 3, faq_results)

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

            # Track policy/FAQ retrieval
            try:
                tracker = get_tracker()
                if intent_result.intent == "policy_question" and policy_results:
                    top_sim = policy_results[0]['similarity'] if policy_results else None
                    tracker.log_retrieval(
                        intent=intent_result.intent,
                        query=message,
                        collection="policies_en",
                        results_count=len(policy_results),
                        top_similarity=top_sim
                    )
                elif intent_result.intent == "product_inquiry" and faq_results:
                    top_sim = faq_results[0]['similarity'] if faq_results else None
                    tracker.log_retrieval(
                        intent=intent_result.intent,
                        query=message,
                        collection="faqs_en",
                        results_count=len(faq_results),
                        top_similarity=top_sim
                    )
            except Exception as e:
                # Don't fail if tracking fails, but log the error
                logger.warning(f"Failed to track policy/FAQ retrieval: {str(e)}", exc_info=False)

            # Retrieve appropriate tone guidelines
            tone_guidelines = self._get_tone_guidelines(
                intent=intent_result.intent,
                message=message,
                sentiment="neutral"  # Could be enhanced with sentiment analysis
            )

            # Build enhanced system prompt with tone guidelines
            enhanced_system_prompt = CUSTOMER_SERVICE_PROMPT
            if tone_guidelines:
                enhanced_system_prompt += tone_guidelines

            # Build RAG QA prompt
            qa_prompt = build_rag_qa_prompt(
                user_question=message,
                retrieved_knowledge=knowledge_text,
                conversation_history=conversation_history or []
            )

            # Generate response with GPT-4 using tone-aware system prompt
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": qa_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1000
            )

            response_text = response.choices[0].message.content

            # Validate response against policies if enabled
            validation_result = {}
            if self.enable_response_validation:
                validation_result = self._validate_response_against_policies(
                    response_text=response_text,
                    intent=intent_result.intent,
                    knowledge_used=knowledge_chunks
                )

                # If validation failed with critical issues, use corrected response
                if not validation_result.get("is_valid", True):
                    critical_issues = [
                        issue for issue in validation_result.get("issues_found", [])
                        if issue.get("severity") == "critical"
                    ]
                    if critical_issues and validation_result.get("corrected_response"):
                        logger.warning(
                            f"Using corrected response due to {len(critical_issues)} critical issues"
                        )
                        response_text = validation_result["corrected_response"]

            return CustomerServiceResponse(
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                response_text=response_text,
                knowledge_used=knowledge_chunks,
                action_taken="rag_qa",
                metadata={
                    "knowledge_chunks_used": len(knowledge_chunks),
                    "collections_searched": intent_result.intent,
                    "response_validation": validation_result if validation_result else None,
                    "validation_passed": validation_result.get("is_valid", True) if validation_result else None,
                    "validation_confidence": validation_result.get("confidence", 0) if validation_result else None
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
        """Handle complaint with empathy and escalation using dynamic tone"""
        logger.info("Complaint detected - preparing empathetic response with escalation")

        try:
            # Retrieve complaint-specific tone guidelines (negative sentiment)
            tone_guidelines = self._get_tone_guidelines(
                intent="complaint",
                message=message,
                sentiment="negative"
            )

            # Build enhanced system prompt with tone guidelines
            complaint_system_prompt = CUSTOMER_SERVICE_PROMPT
            if tone_guidelines:
                complaint_system_prompt += tone_guidelines

            # Add specific complaint handling context
            complaint_context = (
                "\n\nCURRENT SITUATION: The customer has a complaint. "
                "Your response must be:\n"
                "1. Empathetic and sincere in acknowledging their frustration\n"
                "2. Professional and solution-focused\n"
                "3. Clear about next steps (escalation to human team)\n"
                "4. Gathering necessary information to help resolve the issue\n\n"
                "Remember: This interaction is being escalated to a human agent, "
                "so your role is to provide immediate empathetic acknowledgment "
                "and collect relevant details."
            )
            complaint_system_prompt += complaint_context

            # Format conversation history
            messages = [{"role": "system", "content": complaint_system_prompt}]
            if conversation_history:
                for msg in conversation_history[-5:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            messages.append({"role": "user", "content": message})

            # Generate empathetic response with GPT-4
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,  # Balanced for empathy and professionalism
                max_tokens=800
            )

            response_text = response.choices[0].message.content

            # Determine escalation tier using RAG-based escalation rules
            escalation_decision = {}
            if self.enable_escalation:
                escalation_decision = self._determine_escalation_tier(
                    message=message,
                    intent="complaint",
                    conversation_history=conversation_history
                )
                logger.info(
                    f"Complaint escalated to {escalation_decision.get('tier')} "
                    f"with urgency={escalation_decision.get('urgency')}"
                )

            return CustomerServiceResponse(
                intent="complaint",
                confidence=intent_result.confidence,
                response_text=response_text,
                action_taken="complaint_escalation",
                requires_escalation=True,
                metadata={
                    "escalation_reason": "customer_complaint",
                    "sentiment": "negative",
                    "tone_guidelines_used": bool(tone_guidelines),
                    "escalation_decision": escalation_decision,
                    "escalation_tier": escalation_decision.get("tier", "TIER_2_AGENT"),
                    "escalation_urgency": escalation_decision.get("urgency", "medium"),
                    "escalation_rules_used": len(escalation_decision.get("rules_used", []))
                }
            )

        except Exception as e:
            logger.error(f"Complaint handling failed: {str(e)}", exc_info=True)
            # Fallback to standard empathetic response
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

            return CustomerServiceResponse(
                intent="complaint",
                confidence=intent_result.confidence,
                response_text=response_text,
                action_taken="complaint_escalation_fallback",
                requires_escalation=True,
                metadata={
                    "escalation_reason": "customer_complaint",
                    "sentiment": "negative",
                    "error": str(e)
                }
            )

    def _handle_general_query(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> CustomerServiceResponse:
        """Handle general queries with GPT-4 and dynamic tone"""
        logger.info("Handling general query")

        try:
            # Retrieve appropriate tone guidelines
            tone_guidelines = self._get_tone_guidelines(
                intent="general_query",
                message=message,
                sentiment="neutral"
            )

            # Build enhanced system prompt with tone guidelines
            enhanced_system_prompt = CUSTOMER_SERVICE_PROMPT
            if tone_guidelines:
                enhanced_system_prompt += tone_guidelines

            # Format conversation history for GPT-4
            messages = [{"role": "system", "content": enhanced_system_prompt}]

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
