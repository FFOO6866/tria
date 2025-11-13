"""
TRIA Intent Classification Agent
==================================

GPT-4 based intent classifier for customer messages.
Uses structured output (JSON mode) for reliable intent detection.

NO MOCKING - Uses real OpenAI API calls.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from openai import OpenAI

from prompts.system_prompts import build_intent_classification_prompt


# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class IntentResult:
    """
    Result of intent classification

    Attributes:
        intent: Primary intent (order_placement, order_status, product_inquiry, etc.)
        confidence: Confidence score 0.0-1.0
        reasoning: Explanation of why this intent was chosen
        secondary_intent: Optional secondary intent
        extracted_entities: Dictionary of extracted entities (order_id, product_names, etc.)
        raw_response: Raw GPT-4 response for debugging
        timestamp: When classification was performed
    """
    intent: str
    confidence: float
    reasoning: str
    secondary_intent: Optional[str] = None
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    raw_response: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "secondary_intent": self.secondary_intent,
            "extracted_entities": self.extracted_entities,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# ============================================================================
# INTENT CLASSIFIER
# ============================================================================

class IntentClassifier:
    """
    GPT-4 based intent classification for customer messages

    Supported intents:
    - order_placement: User wants to place order
    - order_status: Checking existing order
    - product_inquiry: Questions about products
    - policy_question: Asking about policies, refunds, delivery
    - complaint: Issue with order/service
    - greeting: Hi, hello, etc.
    - general_query: Other questions

    Usage:
        classifier = IntentClassifier(api_key="...")
        result = classifier.classify_intent(
            message="I need 500 meal trays",
            conversation_history=[...]
        )
        print(f"Intent: {result.intent}, Confidence: {result.confidence}")
    """

    SUPPORTED_INTENTS = [
        "order_placement",
        "order_status",
        "product_inquiry",
        "policy_question",
        "complaint",
        "greeting",
        "general_query"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.3,
        timeout: int = 30
    ):
        """
        Initialize intent classifier

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-3.5-turbo for speed/cost optimization)
                   Intent classification is simple enough for GPT-3.5
            temperature: Temperature for model (0.0-1.0, lower = more deterministic)
            timeout: API timeout in seconds

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

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key, timeout=self.timeout)

        logger.info(
            f"IntentClassifier initialized with model={model}, "
            f"temperature={temperature}, timeout={timeout}s"
        )

    def classify_intent(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_json_mode: bool = True
    ) -> IntentResult:
        """
        Classify user message intent using GPT-4

        Args:
            message: User message to classify
            conversation_history: Optional list of previous messages for context
                                 Format: [{"role": "user", "content": "..."}, ...]
            use_json_mode: Use GPT-4 JSON mode for structured output

        Returns:
            IntentResult with intent, confidence, and metadata

        Raises:
            ValueError: If message is empty or invalid
            RuntimeError: If GPT-4 API call fails
        """
        # Validate input
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        # Build prompt
        prompt = build_intent_classification_prompt(
            user_message=message,
            conversation_history=conversation_history or []
        )

        logger.info(f"Classifying intent for message: {message[:100]}...")

        try:
            # Call GPT-4 with JSON mode
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"} if use_json_mode else None,
                max_tokens=500
            )

            # Extract response content
            raw_content = response.choices[0].message.content
            logger.debug(f"GPT-4 raw response: {raw_content}")

            # Parse JSON response
            result_dict = self._parse_gpt4_response(raw_content)

            # Validate intent
            intent = result_dict.get("intent", "general_query")
            if intent not in self.SUPPORTED_INTENTS:
                logger.warning(
                    f"GPT-4 returned unsupported intent '{intent}', "
                    f"defaulting to 'general_query'"
                )
                intent = "general_query"
                result_dict["confidence"] = max(0.5, result_dict.get("confidence", 0.5) - 0.2)

            # Create IntentResult
            return IntentResult(
                intent=intent,
                confidence=result_dict.get("confidence", 0.0),
                reasoning=result_dict.get("reasoning", ""),
                secondary_intent=result_dict.get("secondary_intent"),
                extracted_entities=result_dict.get("extracted_entities", {}),
                raw_response=raw_content
            )

        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}", exc_info=True)
            raise RuntimeError(
                f"Failed to classify intent using GPT-4. Error: {str(e)}"
            ) from e

    def _parse_gpt4_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse GPT-4 JSON response with fallback handling

        Args:
            response_content: Raw GPT-4 response content

        Returns:
            Parsed dictionary

        Raises:
            ValueError: If response cannot be parsed as JSON
        """
        # Try direct JSON parse
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON object from text
        start_idx = response_content.find('{')
        end_idx = response_content.rfind('}')

        if start_idx != -1 and end_idx != -1:
            json_str = response_content[start_idx:end_idx+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # NO FALLBACK - Fail explicitly with meaningful error
        raise ValueError(
            f"Failed to parse GPT-4 response as JSON. "
            f"Response (first 500 chars): {response_content[:500]}"
        )

    def classify_batch(
        self,
        messages: List[str],
        conversation_histories: Optional[List[List[Dict[str, str]]]] = None
    ) -> List[IntentResult]:
        """
        Classify multiple messages in batch

        Args:
            messages: List of user messages to classify
            conversation_histories: Optional list of conversation histories,
                                   one per message (must match length)

        Returns:
            List of IntentResult objects

        Raises:
            ValueError: If messages is empty or histories length doesn't match
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        if conversation_histories and len(conversation_histories) != len(messages):
            raise ValueError(
                f"Conversation histories length ({len(conversation_histories)}) "
                f"must match messages length ({len(messages)})"
            )

        results = []
        for idx, message in enumerate(messages):
            history = conversation_histories[idx] if conversation_histories else None
            try:
                result = self.classify_intent(message, history)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to classify message {idx}: {str(e)}")
                # Create fallback result
                results.append(IntentResult(
                    intent="general_query",
                    confidence=0.0,
                    reasoning=f"Classification failed: {str(e)}",
                    raw_response=""
                ))

        return results


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def classify_intent(
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    api_key: Optional[str] = None
) -> IntentResult:
    """
    Convenience function to classify a single message

    Args:
        message: User message to classify
        conversation_history: Optional conversation context
        api_key: Optional OpenAI API key (uses env var if not provided)

    Returns:
        IntentResult with classification

    Example:
        result = classify_intent("I need 500 meal trays")
        print(f"Intent: {result.intent}")  # "order_placement"
        print(f"Confidence: {result.confidence}")  # 0.95
    """
    classifier = IntentClassifier(api_key=api_key)
    return classifier.classify_intent(message, conversation_history)


def is_high_confidence(result: IntentResult, threshold: float = 0.8) -> bool:
    """
    Check if intent classification is high confidence

    Args:
        result: IntentResult to check
        threshold: Confidence threshold (default: 0.8)

    Returns:
        True if confidence >= threshold
    """
    return result.confidence >= threshold


def requires_human_escalation(result: IntentResult) -> bool:
    """
    Determine if intent requires human escalation

    Args:
        result: IntentResult to check

    Returns:
        True if intent indicates need for human intervention
    """
    # Low confidence should escalate
    if result.confidence < 0.6:
        return True

    # Complaints should escalate
    if result.intent == "complaint":
        return True

    return False


def get_intent_category(intent: str) -> str:
    """
    Get high-level category for intent

    Args:
        intent: Intent string

    Returns:
        Category string (order, inquiry, support, other)
    """
    intent_categories = {
        "order_placement": "order",
        "order_status": "order",
        "product_inquiry": "inquiry",
        "policy_question": "inquiry",
        "complaint": "support",
        "greeting": "other",
        "general_query": "other"
    }
    return intent_categories.get(intent, "other")
