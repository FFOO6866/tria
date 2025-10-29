"""
Integration Tests - Intent Classification
===========================================

Tests intent classifier with REAL OpenAI GPT-4 API.
NO MOCKING - validates actual API behavior.

Tier 2: Integration testing with real external services.
"""

import os
import pytest
from typing import List, Dict

from src.agents.intent_classifier import (
    IntentClassifier,
    IntentResult,
    classify_intent,
    is_high_confidence,
    requires_human_escalation,
    get_intent_category
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_key():
    """Get OpenAI API key from environment"""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set - skipping integration tests")
    return key


@pytest.fixture
def classifier(api_key):
    """Create intent classifier instance"""
    return IntentClassifier(api_key=api_key)


@pytest.fixture
def test_messages() -> Dict[str, List[str]]:
    """Sample messages for each intent type"""
    return {
        "order_placement": [
            "I need 500 meal trays and 200 lids",
            "Can I place an order for pizza boxes?",
            "Pacific Pizza here, need to order supplies",
            "We need 1000 pieces of 10 inch boxes urgently",
        ],
        "order_status": [
            "Where's my order #12345?",
            "Has my order been delivered yet?",
            "Can you check the status of order 98765?",
            "When will I receive my delivery?",
        ],
        "product_inquiry": [
            "Do you have 10 inch pizza boxes?",
            "What's the price of meal trays?",
            "How many trays come in a bundle?",
            "What sizes of boxes are available?",
        ],
        "policy_question": [
            "What's your refund policy?",
            "Can I cancel my order after it's confirmed?",
            "What are your delivery hours?",
            "Do you offer bulk discounts?",
        ],
        "complaint": [
            "My order arrived damaged",
            "The delivery was 2 hours late!",
            "Wrong items were delivered",
            "This is unacceptable, I want a refund!",
        ],
        "greeting": [
            "Hi",
            "Hello",
            "Good morning",
            "Hey there",
        ],
        "general_query": [
            "Who are you?",
            "What services do you offer?",
            "Can I speak to a human?",
            "Are you a robot?",
        ]
    }


# ============================================================================
# INTENT CLASSIFICATION TESTS
# ============================================================================

@pytest.mark.integration
def test_classifier_initialization(api_key):
    """Test classifier initializes correctly"""
    classifier = IntentClassifier(api_key=api_key)

    assert classifier.api_key == api_key
    assert classifier.model == "gpt-4-turbo-preview"
    assert classifier.temperature == 0.3
    assert len(classifier.SUPPORTED_INTENTS) == 7


@pytest.mark.integration
def test_classify_order_placement(classifier, test_messages):
    """Test order placement intent classification"""
    for message in test_messages["order_placement"]:
        result = classifier.classify_intent(message)

        assert isinstance(result, IntentResult)
        assert result.intent == "order_placement"
        assert result.confidence > 0.7, f"Low confidence for: {message}"
        assert result.reasoning is not None
        assert isinstance(result.extracted_entities, dict)


@pytest.mark.integration
def test_classify_order_status(classifier, test_messages):
    """Test order status intent classification"""
    for message in test_messages["order_status"]:
        result = classifier.classify_intent(message)

        assert result.intent == "order_status"
        assert result.confidence > 0.7

        # Check if order ID is extracted
        if "#" in message or "order" in message.lower():
            # Should attempt entity extraction
            assert isinstance(result.extracted_entities, dict)


@pytest.mark.integration
def test_classify_product_inquiry(classifier, test_messages):
    """Test product inquiry intent classification"""
    for message in test_messages["product_inquiry"]:
        result = classifier.classify_intent(message)

        assert result.intent == "product_inquiry"
        assert result.confidence > 0.7


@pytest.mark.integration
def test_classify_policy_question(classifier, test_messages):
    """Test policy question intent classification"""
    for message in test_messages["policy_question"]:
        result = classifier.classify_intent(message)

        assert result.intent == "policy_question"
        assert result.confidence > 0.7


@pytest.mark.integration
def test_classify_complaint(classifier, test_messages):
    """Test complaint intent classification"""
    for message in test_messages["complaint"]:
        result = classifier.classify_intent(message)

        assert result.intent == "complaint"
        assert result.confidence > 0.7


@pytest.mark.integration
def test_classify_greeting(classifier, test_messages):
    """Test greeting intent classification"""
    for message in test_messages["greeting"]:
        result = classifier.classify_intent(message)

        assert result.intent == "greeting"
        assert result.confidence > 0.8  # Greetings should be very confident


@pytest.mark.integration
def test_classify_general_query(classifier, test_messages):
    """Test general query intent classification"""
    for message in test_messages["general_query"]:
        result = classifier.classify_intent(message)

        assert result.intent == "general_query"
        assert result.confidence > 0.6  # May vary


# ============================================================================
# CONVERSATION CONTEXT TESTS
# ============================================================================

@pytest.mark.integration
def test_classify_with_conversation_history(classifier):
    """Test intent classification with conversation context"""
    conversation_history = [
        {"role": "user", "content": "Hi, I'm from Pacific Pizza"},
        {"role": "assistant", "content": "Hello! How can I help you today?"},
        {"role": "user", "content": "I need some supplies"}
    ]

    # With context, "I need some supplies" should be order_placement
    result = classifier.classify_intent(
        message="I need some supplies",
        conversation_history=conversation_history
    )

    assert result.intent == "order_placement"
    assert result.confidence > 0.6


@pytest.mark.integration
def test_classify_multi_intent_message(classifier):
    """Test message with multiple intents (should prioritize)"""
    # Greeting + order placement
    message = "Hi! I need to order 500 meal trays"
    result = classifier.classify_intent(message)

    # Primary intent should be order_placement
    assert result.intent == "order_placement"

    # May have greeting as secondary intent
    # (depends on GPT-4 response)


# ============================================================================
# ENTITY EXTRACTION TESTS
# ============================================================================

@pytest.mark.integration
def test_extract_order_id(classifier):
    """Test order ID extraction"""
    message = "Where is my order #12345?"
    result = classifier.classify_intent(message)

    assert result.intent == "order_status"

    # Check if order_id was extracted
    if "order_id" in result.extracted_entities:
        order_id = result.extracted_entities["order_id"]
        assert "12345" in str(order_id)


@pytest.mark.integration
def test_extract_product_names(classifier):
    """Test product name extraction"""
    message = "I need meal trays and pizza boxes"
    result = classifier.classify_intent(message)

    assert result.intent == "order_placement"

    # Check if products were extracted
    if "product_names" in result.extracted_entities:
        products = result.extracted_entities["product_names"]
        assert isinstance(products, list)
        # At least one product should be mentioned
        assert len(products) > 0


@pytest.mark.integration
def test_extract_outlet_name(classifier):
    """Test outlet name extraction"""
    message = "Hi, this is Pacific Pizza. I need to place an order"
    result = classifier.classify_intent(message)

    # Check if outlet name was extracted
    if "outlet_name" in result.extracted_entities:
        outlet = result.extracted_entities["outlet_name"]
        assert "Pacific Pizza" in outlet or "pizza" in outlet.lower()


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

@pytest.mark.integration
def test_classify_empty_message(classifier):
    """Test error handling for empty message"""
    with pytest.raises(ValueError, match="Message cannot be empty"):
        classifier.classify_intent("")


@pytest.mark.integration
def test_classify_very_long_message(classifier):
    """Test handling of very long message"""
    long_message = "I need supplies. " * 100  # 300+ words
    result = classifier.classify_intent(long_message)

    # Should still classify (GPT-4 can handle it)
    assert result.intent is not None
    assert result.confidence > 0


@pytest.mark.integration
def test_classify_mixed_language_message(classifier):
    """Test mixed language message (English + Chinese)"""
    message = "Hi, I need 盒子 (boxes)"
    result = classifier.classify_intent(message)

    # Should still detect intent despite mixed language
    assert result.intent in ["order_placement", "product_inquiry", "general_query"]


@pytest.mark.integration
def test_classify_ambiguous_message(classifier):
    """Test ambiguous message classification"""
    message = "boxes"  # Very minimal context
    result = classifier.classify_intent(message)

    # Should classify, but confidence may be lower
    assert result.intent is not None
    assert 0.0 <= result.confidence <= 1.0


# ============================================================================
# BATCH CLASSIFICATION TESTS
# ============================================================================

@pytest.mark.integration
def test_classify_batch(classifier):
    """Test batch classification"""
    messages = [
        "I need 500 trays",
        "Where's my order?",
        "What's your refund policy?"
    ]

    results = classifier.classify_batch(messages)

    assert len(results) == 3
    assert results[0].intent == "order_placement"
    assert results[1].intent == "order_status"
    assert results[2].intent == "policy_question"


@pytest.mark.integration
def test_classify_batch_with_histories(classifier):
    """Test batch classification with conversation histories"""
    messages = ["I need supplies", "I need help"]
    histories = [
        [{"role": "user", "content": "Hi from Pacific Pizza"}],
        [{"role": "user", "content": "My order is damaged"}]
    ]

    results = classifier.classify_batch(messages, histories)

    assert len(results) == 2
    # Context should influence classification
    assert results[0].intent in ["order_placement", "product_inquiry"]
    assert results[1].intent in ["complaint", "general_query"]


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_is_high_confidence():
    """Test high confidence helper"""
    high_conf = IntentResult(intent="greeting", confidence=0.95, reasoning="Clear greeting")
    low_conf = IntentResult(intent="general_query", confidence=0.5, reasoning="Ambiguous")

    assert is_high_confidence(high_conf)
    assert not is_high_confidence(low_conf)
    assert is_high_confidence(low_conf, threshold=0.4)


def test_requires_human_escalation():
    """Test escalation helper"""
    complaint = IntentResult(intent="complaint", confidence=0.9, reasoning="User upset")
    low_conf = IntentResult(intent="general_query", confidence=0.5, reasoning="Uncertain")
    normal = IntentResult(intent="greeting", confidence=0.9, reasoning="Clear greeting")

    assert requires_human_escalation(complaint)
    assert requires_human_escalation(low_conf)
    assert not requires_human_escalation(normal)


def test_get_intent_category():
    """Test intent category mapping"""
    assert get_intent_category("order_placement") == "order"
    assert get_intent_category("order_status") == "order"
    assert get_intent_category("product_inquiry") == "inquiry"
    assert get_intent_category("policy_question") == "inquiry"
    assert get_intent_category("complaint") == "support"
    assert get_intent_category("greeting") == "other"
    assert get_intent_category("general_query") == "other"
    assert get_intent_category("unknown") == "other"


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

@pytest.mark.integration
def test_classify_intent_convenience_function(api_key):
    """Test convenience function"""
    result = classify_intent("I need 500 trays", api_key=api_key)

    assert isinstance(result, IntentResult)
    assert result.intent == "order_placement"
    assert result.confidence > 0.7


# ============================================================================
# PERFORMANCE & RELIABILITY TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_classification_consistency(classifier):
    """Test that same message gets consistent classification"""
    message = "I need to order 500 meal trays"

    results = [classifier.classify_intent(message) for _ in range(3)]

    # Should get same intent (temperature is low, but allow for some variance)
    intents = [r.intent for r in results]
    # All should be order_placement
    assert all(intent == "order_placement" for intent in intents)


@pytest.mark.integration
@pytest.mark.slow
def test_classification_latency(classifier, test_messages):
    """Test classification response time"""
    import time

    message = test_messages["order_placement"][0]

    start = time.time()
    result = classifier.classify_intent(message)
    end = time.time()

    latency = end - start

    # Should complete in reasonable time (< 10 seconds for GPT-4)
    assert latency < 10.0, f"Classification took {latency:.2f}s - too slow"
    assert result.intent is not None


# ============================================================================
# RESULT SERIALIZATION TESTS
# ============================================================================

def test_intent_result_to_dict():
    """Test IntentResult serialization"""
    result = IntentResult(
        intent="order_placement",
        confidence=0.95,
        reasoning="Clear order request",
        secondary_intent="greeting",
        extracted_entities={"product_names": ["trays", "lids"]}
    )

    result_dict = result.to_dict()

    assert result_dict["intent"] == "order_placement"
    assert result_dict["confidence"] == 0.95
    assert result_dict["reasoning"] == "Clear order request"
    assert result_dict["secondary_intent"] == "greeting"
    assert "product_names" in result_dict["extracted_entities"]
    assert result_dict["timestamp"] is not None
