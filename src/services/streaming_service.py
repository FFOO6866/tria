"""
TRIA AI-BPO Streaming Service
==============================

Core SSE (Server-Sent Events) streaming service for progressive response rendering.

Features:
- Async streaming of chat responses
- Chunk-by-chunk delivery from OpenAI
- Progress indicators (thinking, retrieving, generating)
- Error handling in streams
- Connection management

NO MOCKING - Uses real OpenAI streaming API.
"""

import asyncio
import json
import logging
import time
from typing import AsyncIterator, Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from openai import AsyncOpenAI

from agents.intent_classifier import IntentClassifier
from rag.retrieval import (
    search_policies,
    search_faqs,
    search_escalation_rules,
    format_results_for_llm
)
from prompts.system_prompts import (
    CUSTOMER_SERVICE_PROMPT,
    build_rag_qa_prompt
)


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """
    Server-Sent Event structure

    Attributes:
        event_type: Type of event (status, chunk, error, complete)
        data: Event data (dict or string)
        timestamp: Event timestamp
    """
    event_type: str
    data: Any
    timestamp: datetime

    def to_sse(self) -> str:
        """
        Convert to SSE format

        Returns:
            Formatted SSE string: "data: {json}\n\n"
        """
        payload = {
            "type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
        return f"data: {json.dumps(payload)}\n\n"


class StreamingService:
    """
    Service for streaming chat responses with SSE

    Workflow:
    1. Emit "thinking" status
    2. Classify intent (emit "classifying")
    3. Retrieve knowledge if needed (emit "retrieving")
    4. Stream GPT-4 response chunks (emit "chunk")
    5. Emit "complete" status

    Usage:
        service = StreamingService(api_key="...")
        async for event in service.stream_chat_response(message="Hello"):
            print(event)  # SSE formatted string
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        timeout: int = 60,
        enable_rag: bool = True
    ):
        """
        Initialize streaming service

        Args:
            api_key: OpenAI API key
            model: GPT-4 model to use
            temperature: Temperature for responses
            timeout: API timeout in seconds
            enable_rag: Enable RAG knowledge retrieval
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.enable_rag = enable_rag

        # Initialize async OpenAI client
        self.openai_client = AsyncOpenAI(api_key=api_key, timeout=timeout)

        # Initialize intent classifier (synchronous, will run in executor)
        self.intent_classifier = IntentClassifier(
            api_key=api_key,
            model="gpt-3.5-turbo",
            temperature=0.3,
            timeout=30
        )

        logger.info(
            f"StreamingService initialized with model={model}, "
            f"enable_rag={enable_rag}"
        )

    async def stream_chat_response(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Stream chat response with progress indicators

        Args:
            message: User message
            conversation_history: Optional conversation context
            user_context: Optional user context

        Yields:
            SSE formatted strings (data: {json}\\n\\n)

        Example:
            async for event in service.stream_chat_response("What's your refund policy?"):
                # event = "data: {\"type\": \"chunk\", \"data\": \"Our refund...\"}\n\n"
                print(event)
        """
        start_time = time.time()

        try:
            # ================================================================
            # PHASE 1: THINKING
            # ================================================================
            yield StreamEvent(
                event_type="status",
                data={"status": "thinking", "message": "Processing your message..."},
                timestamp=datetime.now()
            ).to_sse()

            # ================================================================
            # PHASE 2: INTENT CLASSIFICATION
            # ================================================================
            yield StreamEvent(
                event_type="status",
                data={"status": "classifying", "message": "Understanding your request..."},
                timestamp=datetime.now()
            ).to_sse()

            # Run synchronous intent classification in executor
            loop = asyncio.get_event_loop()
            intent_result = await loop.run_in_executor(
                None,
                self.intent_classifier.classify_intent,
                message,
                conversation_history or []
            )

            logger.info(
                f"[STREAMING] Intent: {intent_result.intent} "
                f"(confidence: {intent_result.confidence:.2f})"
            )

            # Emit intent classification result
            yield StreamEvent(
                event_type="intent",
                data={
                    "intent": intent_result.intent,
                    "confidence": intent_result.confidence,
                    "entities": intent_result.extracted_entities
                },
                timestamp=datetime.now()
            ).to_sse()

            # ================================================================
            # PHASE 3: KNOWLEDGE RETRIEVAL (if applicable)
            # ================================================================
            knowledge_chunks = []
            knowledge_text = ""

            if self.enable_rag and intent_result.intent in ["policy_question", "product_inquiry"]:
                yield StreamEvent(
                    event_type="status",
                    data={"status": "retrieving", "message": "Searching knowledge base..."},
                    timestamp=datetime.now()
                ).to_sse()

                # Retrieve knowledge asynchronously
                if intent_result.intent == "policy_question":
                    # Run synchronous search in executor
                    policy_results = await loop.run_in_executor(
                        None,
                        search_policies,
                        message,
                        self.api_key,
                        3
                    )
                    knowledge_chunks = policy_results
                    knowledge_text = format_results_for_llm(policy_results, "POLICIES")

                elif intent_result.intent == "product_inquiry":
                    # Run synchronous search in executor
                    faq_results = await loop.run_in_executor(
                        None,
                        search_faqs,
                        message,
                        self.api_key,
                        3
                    )
                    knowledge_chunks = faq_results
                    knowledge_text = format_results_for_llm(faq_results, "FAQs")

                logger.info(f"[STREAMING] Retrieved {len(knowledge_chunks)} knowledge chunks")

                # Emit retrieval result
                yield StreamEvent(
                    event_type="retrieval",
                    data={
                        "chunks_retrieved": len(knowledge_chunks),
                        "collections": [intent_result.intent]
                    },
                    timestamp=datetime.now()
                ).to_sse()

            # ================================================================
            # PHASE 4: RESPONSE GENERATION (STREAMING)
            # ================================================================
            yield StreamEvent(
                event_type="status",
                data={"status": "generating", "message": "Generating response..."},
                timestamp=datetime.now()
            ).to_sse()

            # Build system prompt and user prompt
            system_prompt = CUSTOMER_SERVICE_PROMPT

            if knowledge_text:
                # RAG-powered response
                user_prompt = build_rag_qa_prompt(
                    user_question=message,
                    retrieved_knowledge=knowledge_text,
                    conversation_history=conversation_history or []
                )
            else:
                # Direct response
                user_prompt = message

            # Stream GPT-4 response
            full_response = ""

            async for chunk_text in self._stream_openai_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                conversation_history=conversation_history
            ):
                full_response += chunk_text

                # Emit chunk
                yield StreamEvent(
                    event_type="chunk",
                    data={"chunk": chunk_text},
                    timestamp=datetime.now()
                ).to_sse()

            # ================================================================
            # PHASE 5: COMPLETE
            # ================================================================
            total_time = time.time() - start_time

            logger.info(
                f"[STREAMING] Response completed in {total_time:.2f}s "
                f"({len(full_response)} chars, {len(knowledge_chunks)} citations)"
            )

            yield StreamEvent(
                event_type="complete",
                data={
                    "status": "complete",
                    "message": "Response complete",
                    "metadata": {
                        "intent": intent_result.intent,
                        "confidence": intent_result.confidence,
                        "citations_count": len(knowledge_chunks),
                        "response_length": len(full_response),
                        "processing_time": f"{total_time:.2f}s"
                    }
                },
                timestamp=datetime.now()
            ).to_sse()

        except asyncio.CancelledError:
            # Client disconnected
            logger.info("[STREAMING] Client disconnected")
            yield StreamEvent(
                event_type="error",
                data={"error": "Connection closed by client"},
                timestamp=datetime.now()
            ).to_sse()

        except Exception as e:
            # Error during streaming
            logger.error(f"[STREAMING] Error: {str(e)}", exc_info=True)
            yield StreamEvent(
                event_type="error",
                data={
                    "error": "An error occurred while processing your request",
                    "details": str(e)
                },
                timestamp=datetime.now()
            ).to_sse()

    async def _stream_openai_response(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[str]:
        """
        Stream response from OpenAI API

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            conversation_history: Optional conversation history

        Yields:
            Text chunks from OpenAI
        """
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        # Add current message
        messages.append({"role": "user", "content": user_prompt})

        # Stream from OpenAI
        try:
            stream = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=1000,
                stream=True  # Enable streaming
            )

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {str(e)}", exc_info=True)
            raise


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def stream_chat_message(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> AsyncIterator[str]:
    """
    Convenience function to stream a single chat message

    Args:
        message: User message
        conversation_history: Optional conversation context
        user_context: Optional user context
        api_key: OpenAI API key

    Yields:
        SSE formatted strings

    Example:
        async for event in stream_chat_message("What's your refund policy?"):
            print(event)
    """
    import os
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key is required")

    service = StreamingService(api_key=api_key)
    async for event in service.stream_chat_response(message, conversation_history, user_context):
        yield event
