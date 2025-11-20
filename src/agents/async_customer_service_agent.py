"""
TRIA Async Customer Service Agent
==================================

Fully async agent with parallel execution and streaming support.

Features:
- Parallel task execution (intent + RAG + tone + context)
- Streaming responses for perceived latency reduction
- Correlation IDs for request tracing
- Timing logs for performance monitoring
- Graceful error handling with fallbacks
- Maintains all features from EnhancedCustomerServiceAgent

Performance targets:
- Parallel execution: max(2s, 5s, 1s, 1s) = 5s (not 9s sequential)
- First token: <1s with streaming
- Total perceived latency: <8s

NO MOCKING - Uses real OpenAI, ChromaDB, PostgreSQL.
"""

import os
import json
import logging
import time
import asyncio
import uuid
from typing import Dict, List, Optional, Any, AsyncIterator
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
class AsyncCustomerServiceResponse:
    """
    Response from async customer service agent

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
        correlation_id: Unique ID for request tracing
        timing_info: Performance timing breakdown
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
    correlation_id: str = ""
    timing_info: Dict[str, float] = field(default_factory=dict)

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
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "correlation_id": self.correlation_id,
            "timing_info": self.timing_info
        }


# ============================================================================
# ASYNC CUSTOMER SERVICE AGENT
# ============================================================================

class AsyncCustomerServiceAgent:
    """
    Fully async customer service agent with parallel execution and streaming

    Features:
    - Parallel task execution using asyncio.gather()
    - Streaming response generation (async generator)
    - Correlation IDs for distributed tracing
    - Comprehensive timing logs
    - All existing features (caching, validation, rate limiting, etc.)

    Usage:
        agent = AsyncCustomerServiceAgent(api_key="...")

        # Non-streaming
        response = await agent.handle_message(
            message="What's your refund policy?",
            conversation_history=[...]
        )

        # Streaming
        async for chunk in agent.handle_message_stream(
            message="What's your refund policy?",
            conversation_history=[...]
        ):
            print(chunk, end="", flush=True)
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
        Initialize async customer service agent

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
        self.intent_classifier = IntentClassifier(
            api_key=self.api_key,
            model="gpt-3.5-turbo",
            temperature=0.3,
            timeout=30
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
            f"AsyncCustomerServiceAgent initialized with model={model}, "
            f"enable_rag={enable_rag}, enable_escalation={enable_escalation}, "
            f"enable_response_validation={enable_response_validation}, "
            f"enable_cache={enable_cache}, enable_rate_limiting={enable_rate_limiting}"
        )

    async def handle_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AsyncCustomerServiceResponse:
        """
        Handle customer message with intelligent routing (async, non-streaming)

        Args:
            message: User message
            conversation_history: Optional conversation context
            user_context: Optional user context (outlet_id, language, etc.)
            user_id: Optional user identifier for rate limiting
            ip_address: Optional IP address for rate limiting
            correlation_id: Optional correlation ID for tracing

        Returns:
            AsyncCustomerServiceResponse with intent, response, and metadata

        Raises:
            RuntimeError: If processing fails
        """
        # Generate correlation ID if not provided
        correlation_id = correlation_id or str(uuid.uuid4())

        # Start performance tracking
        start_time = time.time()
        timing_info = {}

        metrics_collector.increment_counter("requests_total")
        memory_metrics.record_current()

        # Log incoming request with correlation ID
        request_logger.log_request(
            method="CHAT_ASYNC",
            endpoint="/handle_message",
            user_id=user_id,
            ip_address=ip_address,
            message_length=len(message)
        )

        logger.info(
            f"[{correlation_id}] Processing async message: {message[:100]}...",
            extra={"correlation_id": correlation_id}
        )

        try:
            # Validate and sanitize input
            validation_start = time.time()
            validation_result = validate_and_sanitize(message, max_length=5000, strict_mode=False)
            timing_info["validation_ms"] = (time.time() - validation_start) * 1000

            if not validation_result.is_valid:
                error_metrics.record_error("ValidationError", severity="warning")
                metrics_collector.increment_counter("validation_failures")

                app_logger.error(
                    "Input validation failed",
                    user_id=user_id,
                    validation_issues=validation_result.issues,
                    message_length=len(message),
                    correlation_id=correlation_id
                )

                duration_ms = (time.time() - start_time) * 1000
                metrics_collector.record_metric("response_time_ms", duration_ms)

                return AsyncCustomerServiceResponse(
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
                    },
                    correlation_id=correlation_id,
                    timing_info=timing_info
                )

            # Use sanitized input
            message = validation_result.sanitized_input

            # Log warnings if any
            if validation_result.has_warnings():
                app_logger.warning(
                    "Input validation warnings",
                    user_id=user_id,
                    validation_warnings=validation_result.issues,
                    correlation_id=correlation_id
                )

            # Check rate limits
            if self.enable_rate_limiting and self.rate_limiter:
                rate_limit_start = time.time()
                rate_limit_result = self.rate_limiter.check_rate_limit(
                    user_id=user_id,
                    ip_address=ip_address
                )
                timing_info["rate_limit_ms"] = (time.time() - rate_limit_start) * 1000

                if not rate_limit_result.allowed:
                    rate_limit_metrics.record_blocked(
                        user_id=user_id or "anonymous",
                        limit_type=rate_limit_result.limit_type.value if rate_limit_result.limit_type else "unknown"
                    )

                    app_logger.warning(
                        "Rate limit exceeded",
                        user_id=user_id,
                        ip_address=ip_address,
                        limit_type=rate_limit_result.limit_type.value if rate_limit_result.limit_type else "unknown",
                        retry_after=rate_limit_result.retry_after,
                        correlation_id=correlation_id
                    )

                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_metric("response_time_ms", duration_ms)

                    return AsyncCustomerServiceResponse(
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
                            "reset_at": rate_limit_result.reset_at
                        },
                        correlation_id=correlation_id,
                        timing_info=timing_info
                    )
                else:
                    rate_limit_metrics.record_allowed(user_id=user_id or "anonymous")

            app_logger.info(
                "Processing message with parallel execution",
                user_id=user_id,
                message_preview=message[:100],
                correlation_id=correlation_id
            )

            # PARALLEL EXECUTION - Intent, RAG, Tone, Context
            parallel_start = time.time()

            try:
                # Create tasks for parallel execution
                intent_task = self._classify_intent_async(message, conversation_history, correlation_id)
                rag_task = self._retrieve_knowledge_async(message, correlation_id)
                tone_task = self._get_tone_async("general_query", message, "neutral", correlation_id)
                context_task = self._get_context_async(user_id, user_context, correlation_id)

                # Execute in parallel - max(2s, 5s, 1s, 1s) = 5s (not 9s!)
                intent_result, knowledge_results, tone_guidelines, context = await asyncio.gather(
                    intent_task,
                    rag_task,
                    tone_task,
                    context_task,
                    return_exceptions=True  # Don't fail entire operation if one task fails
                )

                parallel_duration = (time.time() - parallel_start) * 1000
                timing_info["parallel_execution_ms"] = parallel_duration

                logger.info(
                    f"[{correlation_id}] Parallel execution completed in {parallel_duration:.2f}ms "
                    f"(target: 5000ms)"
                )

                # Handle exceptions from parallel tasks
                if isinstance(intent_result, Exception):
                    logger.error(f"[{correlation_id}] Intent classification failed: {intent_result}")
                    intent_result = IntentResult(
                        intent="general_query",
                        confidence=0.0,
                        reasoning=f"Classification failed: {str(intent_result)}"
                    )

                if isinstance(knowledge_results, Exception):
                    logger.error(f"[{correlation_id}] Knowledge retrieval failed: {knowledge_results}")
                    knowledge_results = []

                if isinstance(tone_guidelines, Exception):
                    logger.error(f"[{correlation_id}] Tone retrieval failed: {tone_guidelines}")
                    tone_guidelines = ""

                if isinstance(context, Exception):
                    logger.error(f"[{correlation_id}] Context retrieval failed: {context}")
                    context = {}

            except Exception as e:
                logger.error(
                    f"[{correlation_id}] Parallel execution failed: {str(e)}",
                    exc_info=True
                )
                # Fallback to sequential execution
                intent_result = await self._classify_intent_async(message, conversation_history, correlation_id)
                knowledge_results = []
                tone_guidelines = ""
                context = {}

            # Check for cached full response (after we have intent)
            if self.enable_cache and self.cache:
                cache_start = time.time()
                cached_response = self.cache.get_response(message, intent_result.intent)
                timing_info["cache_check_ms"] = (time.time() - cache_start) * 1000

                if cached_response:
                    logger.info(
                        f"[{correlation_id}] Full response CACHE HIT for intent={intent_result.intent}"
                    )
                    cache_metrics.record_hit()

                    duration_ms = (time.time() - start_time) * 1000
                    metrics_collector.record_metric("response_time_ms", duration_ms)
                    timing_info["total_ms"] = duration_ms

                    return AsyncCustomerServiceResponse(
                        intent=intent_result.intent,
                        confidence=intent_result.confidence,
                        response_text=cached_response,
                        action_taken="cached_response",
                        metadata={"cache_hit": True},
                        correlation_id=correlation_id,
                        timing_info=timing_info
                    )
                else:
                    cache_metrics.record_miss()

            # Route based on intent
            try:
                response_start = time.time()

                if intent_result.intent == "greeting":
                    response = await self._handle_greeting_async(message, conversation_history, correlation_id)

                elif intent_result.intent == "order_placement":
                    response = await self._handle_order_placement_async(
                        message, intent_result, conversation_history, user_context, correlation_id
                    )

                elif intent_result.intent == "order_status":
                    response = await self._handle_order_status_async(
                        message, intent_result, conversation_history, correlation_id
                    )

                elif intent_result.intent in ["product_inquiry", "policy_question"]:
                    response = await self._handle_inquiry_with_rag_async(
                        message, intent_result, conversation_history, knowledge_results, tone_guidelines, correlation_id
                    )

                elif intent_result.intent == "complaint":
                    response = await self._handle_complaint_async(
                        message, intent_result, conversation_history, tone_guidelines, correlation_id
                    )

                else:  # general_query
                    response = await self._handle_general_query_async(
                        message, intent_result, conversation_history, tone_guidelines, correlation_id
                    )

                timing_info["response_generation_ms"] = (time.time() - response_start) * 1000

                # Add intent and confidence to response
                response.intent = intent_result.intent
                response.confidence = intent_result.confidence
                response.extracted_entities = intent_result.extracted_entities
                response.correlation_id = correlation_id
                response.timing_info = timing_info

                # Cache the complete response
                if self.enable_cache and self.cache:
                    self.cache.put_response(message, intent_result.intent, response.response_text)
                    app_logger.debug("Cached response", intent=intent_result.intent, correlation_id=correlation_id)

                # Record successful response metrics
                duration_ms = (time.time() - start_time) * 1000
                timing_info["total_ms"] = duration_ms
                metrics_collector.record_metric("response_time_ms", duration_ms)
                metrics_collector.increment_counter("requests_succeeded")

                request_logger.log_response(
                    method="CHAT_ASYNC",
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
                    user_id=user_id,
                    correlation_id=correlation_id
                )

                return response

            except Exception as e:
                error_metrics.record_error(type(e).__name__, severity="error", user_id=user_id)
                error_tracker.track_error(e, context={
                    "user_id": user_id,
                    "message_length": len(message),
                    "correlation_id": correlation_id
                })

                app_logger.error(
                    "Message handling failed",
                    error=e,
                    user_id=user_id,
                    message_length=len(message),
                    correlation_id=correlation_id
                )

                duration_ms = (time.time() - start_time) * 1000
                timing_info["total_ms"] = duration_ms
                metrics_collector.record_metric("response_time_ms", duration_ms)
                metrics_collector.increment_counter("requests_failed")

                return AsyncCustomerServiceResponse(
                    intent=intent_result.intent,
                    confidence=intent_result.confidence,
                    response_text=(
                        "I apologize, but I encountered an issue processing your request. "
                        "Please try again or contact our support team for assistance."
                    ),
                    action_taken="error",
                    requires_escalation=True,
                    metadata={"error": str(e)},
                    correlation_id=correlation_id,
                    timing_info=timing_info
                )

        except Exception as e:
            # Outer exception handler
            error_metrics.record_error(type(e).__name__, severity="critical", user_id=user_id)
            error_tracker.track_error(e, context={
                "user_id": user_id,
                "message": message[:100],
                "correlation_id": correlation_id
            })

            app_logger.error(
                "Critical error in message handling",
                error=e,
                user_id=user_id,
                message_preview=message[:100],
                correlation_id=correlation_id
            )

            duration_ms = (time.time() - start_time) * 1000
            timing_info["total_ms"] = duration_ms
            metrics_collector.record_metric("response_time_ms", duration_ms)
            metrics_collector.increment_counter("requests_failed")

            return AsyncCustomerServiceResponse(
                intent="error",
                confidence=0.0,
                response_text=(
                    "I apologize, but I encountered a technical issue. "
                    "Please try again later or contact our support team for immediate assistance."
                ),
                action_taken="critical_error",
                requires_escalation=True,
                metadata={"error": str(e), "error_type": type(e).__name__},
                correlation_id=correlation_id,
                timing_info=timing_info
            )

    async def handle_message_stream(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Handle customer message with streaming response

        This method performs all the same logic as handle_message(), but streams
        the response text progressively for better perceived latency.

        Args:
            message: User message
            conversation_history: Optional conversation context
            user_context: Optional user context
            user_id: Optional user identifier
            ip_address: Optional IP address
            correlation_id: Optional correlation ID

        Yields:
            Response chunks as they're generated

        Example:
            async for chunk in agent.handle_message_stream("What's your return policy?"):
                print(chunk, end="", flush=True)
        """
        # Generate correlation ID if not provided
        correlation_id = correlation_id or str(uuid.uuid4())

        logger.info(
            f"[{correlation_id}] Starting streaming response",
            extra={"correlation_id": correlation_id}
        )

        start_time = time.time()
        first_token_time = None

        try:
            # Similar validation and rate limiting as handle_message
            validation_result = validate_and_sanitize(message, max_length=5000, strict_mode=False)

            if not validation_result.is_valid:
                yield json.dumps({
                    "error": "validation_failed",
                    "message": "Invalid input. Please check your message and try again."
                }) + "\n"
                return

            message = validation_result.sanitized_input

            # Check rate limits
            if self.enable_rate_limiting and self.rate_limiter:
                rate_limit_result = self.rate_limiter.check_rate_limit(
                    user_id=user_id,
                    ip_address=ip_address
                )

                if not rate_limit_result.allowed:
                    yield json.dumps({
                        "error": "rate_limit_exceeded",
                        "retry_after": rate_limit_result.retry_after
                    }) + "\n"
                    return

            # Parallel execution
            intent_task = self._classify_intent_async(message, conversation_history, correlation_id)
            rag_task = self._retrieve_knowledge_async(message, correlation_id)
            tone_task = self._get_tone_async("general_query", message, "neutral", correlation_id)
            context_task = self._get_context_async(user_id, user_context, correlation_id)

            intent_result, knowledge_results, tone_guidelines, context = await asyncio.gather(
                intent_task,
                rag_task,
                tone_task,
                context_task,
                return_exceptions=True
            )

            # Handle exceptions from parallel tasks
            if isinstance(intent_result, Exception):
                intent_result = IntentResult(
                    intent="general_query",
                    confidence=0.0,
                    reasoning=f"Classification failed: {str(intent_result)}"
                )

            # Check cache
            if self.enable_cache and self.cache:
                cached_response = self.cache.get_response(message, intent_result.intent)
                if cached_response:
                    logger.info(f"[{correlation_id}] Streaming from cache")
                    # Stream cached response in chunks for consistent UX
                    words = cached_response.split()
                    for i in range(0, len(words), 5):
                        chunk = " ".join(words[i:i+5]) + " "
                        if not first_token_time:
                            first_token_time = time.time()
                            logger.info(
                                f"[{correlation_id}] First token delivered in "
                                f"{(first_token_time - start_time) * 1000:.2f}ms"
                            )
                        yield chunk
                        await asyncio.sleep(0.05)  # Simulate streaming
                    return

            # Generate streaming response
            if intent_result.intent in ["product_inquiry", "policy_question"]:
                # Build prompt for RAG QA
                knowledge_text = format_results_for_llm(
                    knowledge_results if isinstance(knowledge_results, list) else [],
                    "KNOWLEDGE"
                )

                enhanced_system_prompt = CUSTOMER_SERVICE_PROMPT
                if isinstance(tone_guidelines, str) and tone_guidelines:
                    enhanced_system_prompt += tone_guidelines

                qa_prompt = build_rag_qa_prompt(
                    user_question=message,
                    retrieved_knowledge=knowledge_text,
                    conversation_history=conversation_history or []
                )

                # Stream response from OpenAI
                async for chunk in self._generate_streaming_response_async(
                    system_prompt=enhanced_system_prompt,
                    user_prompt=qa_prompt,
                    correlation_id=correlation_id
                ):
                    if not first_token_time:
                        first_token_time = time.time()
                        logger.info(
                            f"[{correlation_id}] First token delivered in "
                            f"{(first_token_time - start_time) * 1000:.2f}ms (target: <1000ms)"
                        )
                    yield chunk

            else:
                # For other intents, use non-streaming for now
                response = await self.handle_message(
                    message, conversation_history, user_context,
                    user_id, ip_address, correlation_id
                )

                # Stream the response in chunks
                words = response.response_text.split()
                for i in range(0, len(words), 5):
                    chunk = " ".join(words[i:i+5]) + " "
                    if not first_token_time:
                        first_token_time = time.time()
                    yield chunk
                    await asyncio.sleep(0.05)

            total_time = time.time() - start_time
            logger.info(
                f"[{correlation_id}] Streaming completed in {total_time * 1000:.2f}ms, "
                f"first token in {(first_token_time - start_time) * 1000:.2f}ms"
            )

        except Exception as e:
            logger.error(
                f"[{correlation_id}] Streaming failed: {str(e)}",
                exc_info=True
            )
            yield json.dumps({
                "error": "streaming_failed",
                "message": "An error occurred while processing your request."
            }) + "\n"

    # ========================================================================
    # ASYNC HELPER METHODS
    # ========================================================================

    async def _classify_intent_async(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        correlation_id: str
    ) -> IntentResult:
        """Async intent classification using asyncio.to_thread()"""
        start = time.time()

        try:
            # Check cache first
            if self.enable_cache and self.cache:
                cached_intent = self.cache.get_intent(message)
                if cached_intent:
                    cache_metrics.record_hit()
                    logger.info(f"[{correlation_id}] Intent cache hit")
                    return IntentResult(**cached_intent)
                cache_metrics.record_miss()

            # Wrap sync OpenAI call with asyncio.to_thread()
            intent_result = await asyncio.to_thread(
                self.intent_classifier.classify_intent,
                message,
                conversation_history or []
            )

            duration = (time.time() - start) * 1000
            logger.info(f"[{correlation_id}] Intent classified in {duration:.2f}ms: {intent_result.intent}")

            # Cache the result
            if self.enable_cache and self.cache:
                from dataclasses import asdict
                self.cache.put_intent(message, asdict(intent_result))

            return intent_result

        except Exception as e:
            logger.error(f"[{correlation_id}] Intent classification failed: {str(e)}")
            return IntentResult(
                intent="general_query",
                confidence=0.0,
                reasoning=f"Classification failed: {str(e)}"
            )

    async def _retrieve_knowledge_async(
        self,
        message: str,
        correlation_id: str
    ) -> List[Dict[str, Any]]:
        """Async RAG retrieval using asyncio.to_thread()"""
        start = time.time()

        if not self.enable_rag:
            return []

        try:
            # Check cache first
            if self.enable_cache and self.cache:
                cached_results = self.cache.get_retrieval(message, "all", 3)
                if cached_results:
                    logger.info(f"[{correlation_id}] RAG cache hit")
                    return cached_results

            # Wrap sync RAG call with asyncio.to_thread()
            all_results = await asyncio.to_thread(
                search_all_collections,
                query=message,
                api_key=self.api_key,
                top_n_per_collection=3
            )

            knowledge_chunks = (
                all_results.get("policies", []) +
                all_results.get("faqs", []) +
                all_results.get("escalation_rules", [])
            )

            duration = (time.time() - start) * 1000
            logger.info(
                f"[{correlation_id}] RAG retrieval completed in {duration:.2f}ms: "
                f"{len(knowledge_chunks)} chunks"
            )

            # Cache the results
            if self.enable_cache and self.cache:
                self.cache.put_retrieval(message, "all", 3, knowledge_chunks)

            return knowledge_chunks

        except Exception as e:
            logger.error(f"[{correlation_id}] RAG retrieval failed: {str(e)}")
            return []

    async def _get_tone_async(
        self,
        intent: str,
        message: str,
        sentiment: str,
        correlation_id: str
    ) -> str:
        """Async tone guidelines retrieval"""
        start = time.time()

        try:
            # Build tone query
            tone_query = self._build_tone_query(intent, sentiment)

            # Wrap sync tone retrieval with asyncio.to_thread()
            tone_results = await asyncio.to_thread(
                search_tone_guidelines,
                query=tone_query,
                api_key=self.api_key,
                top_n=2
            )

            duration = (time.time() - start) * 1000
            logger.info(
                f"[{correlation_id}] Tone retrieval completed in {duration:.2f}ms: "
                f"{len(tone_results)} guidelines"
            )

            if tone_results:
                tone_text = "\n\nTONE GUIDELINES FOR THIS INTERACTION:\n"
                tone_text += "=" * 60 + "\n"

                for idx, result in enumerate(tone_results, 1):
                    similarity_pct = result['similarity'] * 100 if result['similarity'] else 0
                    if similarity_pct >= 60:
                        tone_text += f"\n[Guideline {idx}] (Relevance: {similarity_pct:.0f}%)\n"
                        tone_text += f"{result['text']}\n"

                tone_text += "=" * 60 + "\n"
                return tone_text

            return ""

        except Exception as e:
            logger.error(f"[{correlation_id}] Tone retrieval failed: {str(e)}")
            return ""

    async def _get_context_async(
        self,
        user_id: Optional[str],
        user_context: Optional[Dict[str, Any]],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Async user context retrieval (placeholder for future DB lookup)"""
        start = time.time()

        # For now, just return the provided context
        # In future, could fetch user preferences, history, etc. from DB
        context = user_context or {}

        duration = (time.time() - start) * 1000
        logger.debug(f"[{correlation_id}] Context retrieval completed in {duration:.2f}ms")

        return context

    async def _generate_streaming_response_async(
        self,
        system_prompt: str,
        user_prompt: str,
        correlation_id: str
    ) -> AsyncIterator[str]:
        """Generate streaming response from OpenAI using asyncio.to_thread()"""
        try:
            # OpenAI streaming must be wrapped in to_thread() for sync client
            def sync_stream():
                return self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=1000,
                    stream=True
                )

            stream = await asyncio.to_thread(sync_stream)

            # Stream chunks
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"[{correlation_id}] Streaming generation failed: {str(e)}")
            yield "I apologize, but I encountered an error generating the response."

    def _build_tone_query(self, intent: str, sentiment: str) -> str:
        """Build tone query based on intent and sentiment"""
        if intent == "complaint" or sentiment == "negative":
            return (
                "How to respond to customer complaints with empathy and professionalism. "
                "Handling frustrated or angry customers."
            )
        elif intent == "greeting":
            return "How to greet customers professionally and warmly. Initial greeting tone."
        elif intent == "order_placement":
            return (
                "How to assist customers with placing orders. "
                "Professional, efficient, and helpful tone for order processing."
            )
        elif intent == "policy_question" or intent == "product_inquiry":
            return (
                "How to explain policies and product information clearly. "
                "Professional informative tone for answering questions."
            )
        else:
            return (
                "Standard customer service tone. "
                "Professional, friendly, and helpful communication style."
            )

    # ========================================================================
    # ASYNC INTENT HANDLERS
    # ========================================================================

    async def _handle_greeting_async(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]],
        correlation_id: str
    ) -> AsyncCustomerServiceResponse:
        """Handle greeting messages (async)"""
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

        return AsyncCustomerServiceResponse(
            intent="greeting",
            confidence=1.0,
            response_text=greeting_response,
            action_taken="greeting",
            correlation_id=correlation_id
        )

    async def _handle_order_placement_async(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]],
        user_context: Optional[Dict[str, Any]],
        correlation_id: str
    ) -> AsyncCustomerServiceResponse:
        """Handle order placement intent (async)"""
        logger.info(f"[{correlation_id}] Order placement detected")

        response_text = (
            "I'd be happy to help you place an order! "
            "To process your order efficiently, please provide:\n\n"
            "1. Your outlet/company name\n"
            "2. Products you need (with quantities)\n"
            "3. Any special delivery requirements\n\n"
            "You can list items like: '500 meal trays, 200 lids, 100 pizza boxes (10 inch)'"
        )

        products_mentioned = intent_result.extracted_entities.get("product_names", [])
        outlet_mentioned = intent_result.extracted_entities.get("outlet_name")

        metadata = {
            "products_mentioned": products_mentioned,
            "outlet_mentioned": outlet_mentioned,
            "ready_for_processing": bool(products_mentioned),
            "note": "Integrate with process_order_with_catalog.py workflow"
        }

        return AsyncCustomerServiceResponse(
            intent="order_placement",
            confidence=intent_result.confidence,
            response_text=response_text,
            action_taken="order_placement_guidance",
            metadata=metadata,
            correlation_id=correlation_id
        )

    async def _handle_order_status_async(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]],
        correlation_id: str
    ) -> AsyncCustomerServiceResponse:
        """Handle order status inquiry (async)"""
        logger.info(f"[{correlation_id}] Order status query detected")

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

        return AsyncCustomerServiceResponse(
            intent="order_status",
            confidence=intent_result.confidence,
            response_text=response_text,
            action_taken="order_status_query",
            requires_escalation=bool(order_id),
            metadata={
                "order_id": order_id,
                "note": "A2A integration pending (Phase 4)"
            },
            correlation_id=correlation_id
        )

    async def _handle_inquiry_with_rag_async(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]],
        knowledge_results: List[Dict[str, Any]],
        tone_guidelines: str,
        correlation_id: str
    ) -> AsyncCustomerServiceResponse:
        """Handle inquiry with RAG (async)"""
        logger.info(f"[{correlation_id}] Handling {intent_result.intent} with RAG")

        try:
            # Format knowledge
            knowledge_text = format_results_for_llm(knowledge_results, "KNOWLEDGE")

            # Build enhanced system prompt
            enhanced_system_prompt = CUSTOMER_SERVICE_PROMPT
            if tone_guidelines:
                enhanced_system_prompt += tone_guidelines

            # Build RAG QA prompt
            qa_prompt = build_rag_qa_prompt(
                user_question=message,
                retrieved_knowledge=knowledge_text,
                conversation_history=conversation_history or []
            )

            # Generate response using asyncio.to_thread()
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                messages=[
                    {"role": "system", "content": enhanced_system_prompt},
                    {"role": "user", "content": qa_prompt}
                ],
                temperature=self.temperature,
                max_tokens=1000
            )

            response_text = response.choices[0].message.content

            return AsyncCustomerServiceResponse(
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                response_text=response_text,
                knowledge_used=knowledge_results,
                action_taken="rag_qa",
                metadata={
                    "knowledge_chunks_used": len(knowledge_results),
                    "collections_searched": intent_result.intent
                },
                correlation_id=correlation_id
            )

        except Exception as e:
            logger.error(f"[{correlation_id}] RAG QA failed: {str(e)}")
            return AsyncCustomerServiceResponse(
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                response_text=(
                    "I apologize, but I'm having trouble accessing our knowledge base. "
                    "Please contact our support team for assistance."
                ),
                action_taken="rag_qa_failed",
                requires_escalation=True,
                metadata={"error": str(e)},
                correlation_id=correlation_id
            )

    async def _handle_complaint_async(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]],
        tone_guidelines: str,
        correlation_id: str
    ) -> AsyncCustomerServiceResponse:
        """Handle complaint with empathy (async)"""
        logger.info(f"[{correlation_id}] Complaint detected")

        try:
            # Build complaint prompt
            complaint_system_prompt = CUSTOMER_SERVICE_PROMPT
            if tone_guidelines:
                complaint_system_prompt += tone_guidelines

            complaint_context = (
                "\n\nCURRENT SITUATION: The customer has a complaint. "
                "Your response must be:\n"
                "1. Empathetic and sincere in acknowledging their frustration\n"
                "2. Professional and solution-focused\n"
                "3. Clear about next steps (escalation to human team)\n"
                "4. Gathering necessary information to help resolve the issue\n"
            )
            complaint_system_prompt += complaint_context

            messages = [{"role": "system", "content": complaint_system_prompt}]
            if conversation_history:
                for msg in conversation_history[-5:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            messages.append({"role": "user", "content": message})

            # Generate response using asyncio.to_thread()
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )

            response_text = response.choices[0].message.content

            return AsyncCustomerServiceResponse(
                intent="complaint",
                confidence=intent_result.confidence,
                response_text=response_text,
                action_taken="complaint_escalation",
                requires_escalation=True,
                metadata={
                    "escalation_reason": "customer_complaint",
                    "sentiment": "negative"
                },
                correlation_id=correlation_id
            )

        except Exception as e:
            logger.error(f"[{correlation_id}] Complaint handling failed: {str(e)}")
            response_text = (
                "I sincerely apologize for the issue you're experiencing. "
                "Your satisfaction is very important to us. "
                "I'm escalating your concern to our customer service team who will "
                "contact you shortly to address this personally."
            )

            return AsyncCustomerServiceResponse(
                intent="complaint",
                confidence=intent_result.confidence,
                response_text=response_text,
                action_taken="complaint_escalation_fallback",
                requires_escalation=True,
                metadata={
                    "escalation_reason": "customer_complaint",
                    "sentiment": "negative",
                    "error": str(e)
                },
                correlation_id=correlation_id
            )

    async def _handle_general_query_async(
        self,
        message: str,
        intent_result: IntentResult,
        conversation_history: Optional[List[Dict[str, str]]],
        tone_guidelines: str,
        correlation_id: str
    ) -> AsyncCustomerServiceResponse:
        """Handle general queries (async)"""
        logger.info(f"[{correlation_id}] Handling general query")

        try:
            # Build enhanced system prompt
            enhanced_system_prompt = CUSTOMER_SERVICE_PROMPT
            if tone_guidelines:
                enhanced_system_prompt += tone_guidelines

            messages = [{"role": "system", "content": enhanced_system_prompt}]

            if conversation_history:
                for msg in conversation_history[-5:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            messages.append({"role": "user", "content": message})

            # Generate response using asyncio.to_thread()
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=800
            )

            response_text = response.choices[0].message.content

            return AsyncCustomerServiceResponse(
                intent="general_query",
                confidence=intent_result.confidence,
                response_text=response_text,
                action_taken="general_assistance",
                correlation_id=correlation_id
            )

        except Exception as e:
            logger.error(f"[{correlation_id}] General query handling failed: {str(e)}")
            raise


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def handle_customer_message_async(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> AsyncCustomerServiceResponse:
    """
    Convenience function to handle a single customer message (async)

    Args:
        message: User message
        conversation_history: Optional conversation context
        user_context: Optional user context
        api_key: Optional OpenAI API key

    Returns:
        AsyncCustomerServiceResponse

    Example:
        response = await handle_customer_message_async("What's your refund policy?")
        print(response.response_text)
    """
    agent = AsyncCustomerServiceAgent(api_key=api_key)
    return await agent.handle_message(message, conversation_history, user_context)
