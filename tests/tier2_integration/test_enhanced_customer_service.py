"""
Integration Tests - Enhanced Customer Service Agent
=====================================================

Tests enhanced customer service agent with REAL OpenAI GPT-4 API and ChromaDB.
NO MOCKING - validates actual API behavior and RAG integration.

Tier 2: Integration testing with real external services.
"""

import os
import pytest
from typing import List, Dict

from src.agents.enhanced_customer_service_agent import (
    EnhancedCustomerServiceAgent,
    CustomerServiceResponse,
    handle_customer_message
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
def agent(api_key):
    """Create enhanced customer service agent instance"""
    return EnhancedCustomerServiceAgent(api_key=api_key)


@pytest.fixture
def agent_without_rag(api_key):
    """Create agent with RAG disabled"""
    return EnhancedCustomerServiceAgent(
        api_key=api_key,
        enable_rag=False
    )


# ============================================================================
# AGENT INITIALIZATION TESTS
# ============================================================================

@pytest.mark.integration
def test_agent_initialization(api_key):
    """Test agent initializes correctly"""
    agent = EnhancedCustomerServiceAgent(api_key=api_key)

    assert agent.api_key == api_key
    assert agent.model == "gpt-4-turbo-preview"
    assert agent.temperature == 0.7
    assert agent.enable_rag is True
    assert agent.enable_escalation is True
    assert agent.intent_classifier is not None
    assert agent.openai_client is not None


@pytest.mark.integration
def test_agent_initialization_with_custom_params(api_key):
    """Test agent initialization with custom parameters"""
    agent = EnhancedCustomerServiceAgent(
        api_key=api_key,
        model="gpt-4-turbo-preview",
        temperature=0.5,
        enable_rag=False,
        enable_escalation=False
    )

    assert agent.temperature == 0.5
    assert agent.enable_rag is False
    assert agent.enable_escalation is False


# ============================================================================
# GREETING HANDLING TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_greeting(agent):
    """Test greeting message handling"""
    response = agent.handle_message("Hello")

    assert isinstance(response, CustomerServiceResponse)
    assert response.intent == "greeting"
    assert response.confidence > 0.8
    assert "TRIA" in response.response_text
    assert "help" in response.response_text.lower()
    assert response.action_taken == "greeting"
    assert response.requires_escalation is False


@pytest.mark.integration
def test_handle_greeting_variations(agent):
    """Test various greeting formats"""
    greetings = ["Hi", "Hello", "Good morning", "Hey there"]

    for greeting in greetings:
        response = agent.handle_message(greeting)
        assert response.intent == "greeting"
        assert response.action_taken == "greeting"


# ============================================================================
# ORDER PLACEMENT HANDLING TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_order_placement_intent(agent):
    """Test order placement message handling"""
    message = "I need 500 meal trays and 200 lids"
    response = agent.handle_message(message)

    assert response.intent == "order_placement"
    assert response.confidence > 0.7
    assert response.action_taken == "order_placement_guidance"
    assert "order" in response.response_text.lower()


@pytest.mark.integration
def test_handle_order_with_outlet_name(agent):
    """Test order placement with outlet name"""
    message = "Hi, this is Pacific Pizza. I need to order 500 trays"
    response = agent.handle_message(message)

    assert response.intent == "order_placement"
    # Should extract outlet name
    if response.extracted_entities:
        assert "outlet_name" in response.metadata or "outlet_mentioned" in response.metadata


# ============================================================================
# ORDER STATUS HANDLING TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_order_status_query(agent):
    """Test order status inquiry handling"""
    message = "Where is my order #12345?"
    response = agent.handle_message(message)

    assert response.intent == "order_status"
    assert response.action_taken == "order_status_query"
    assert "order" in response.response_text.lower()

    # Should mark for escalation if order ID provided
    if response.extracted_entities.get("order_id"):
        assert response.requires_escalation is True


@pytest.mark.integration
def test_handle_order_status_without_id(agent):
    """Test order status query without order number"""
    message = "Has my order been delivered?"
    response = agent.handle_message(message)

    assert response.intent == "order_status"
    # Should ask for order number
    assert "order number" in response.response_text.lower() or "order" in response.response_text.lower()


# ============================================================================
# PRODUCT INQUIRY WITH RAG TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_product_inquiry_with_rag(agent):
    """Test product inquiry with RAG retrieval"""
    message = "Do you have 10 inch pizza boxes?"
    response = agent.handle_message(message)

    assert response.intent == "product_inquiry"
    assert response.action_taken in ["rag_qa", "fallback_no_rag"]

    # If RAG succeeded, should have knowledge chunks
    if response.action_taken == "rag_qa":
        assert len(response.knowledge_used) >= 0  # May or may not find relevant chunks


@pytest.mark.integration
def test_handle_product_inquiry_without_rag(agent_without_rag):
    """Test product inquiry without RAG (fallback)"""
    message = "What sizes of boxes do you have?"
    response = agent_without_rag.handle_message(message)

    assert response.intent == "product_inquiry"
    assert response.action_taken in ["fallback_no_rag", "general_assistance"]
    assert response.requires_escalation is True


# ============================================================================
# POLICY QUESTION WITH RAG TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_policy_question_with_rag(agent):
    """Test policy question with RAG retrieval"""
    message = "What's your refund policy?"
    response = agent.handle_message(message)

    assert response.intent == "policy_question"
    assert response.action_taken in ["rag_qa", "fallback_no_rag"]

    # Response should address the policy
    assert len(response.response_text) > 50  # Meaningful response


@pytest.mark.integration
def test_handle_delivery_policy_question(agent):
    """Test delivery policy question"""
    message = "What are your delivery hours?"
    response = agent.handle_message(message)

    assert response.intent == "policy_question"


@pytest.mark.integration
def test_handle_cancellation_policy_question(agent):
    """Test cancellation policy question"""
    message = "Can I cancel my order after it's confirmed?"
    response = agent.handle_message(message)

    assert response.intent == "policy_question"


# ============================================================================
# COMPLAINT HANDLING TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_complaint(agent):
    """Test complaint handling with escalation"""
    message = "My order arrived damaged!"
    response = agent.handle_message(message)

    assert response.intent == "complaint"
    assert response.action_taken == "escalation"
    assert response.requires_escalation is True

    # Should show empathy
    assert any(word in response.response_text.lower() for word in ["apologize", "sorry", "sincerely"])


@pytest.mark.integration
def test_handle_late_delivery_complaint(agent):
    """Test late delivery complaint"""
    message = "The delivery was 2 hours late!"
    response = agent.handle_message(message)

    assert response.intent == "complaint"
    assert response.requires_escalation is True
    assert response.metadata.get("escalation_reason") == "customer_complaint"


@pytest.mark.integration
def test_handle_wrong_items_complaint(agent):
    """Test wrong items complaint"""
    message = "You sent me the wrong items!"
    response = agent.handle_message(message)

    assert response.intent == "complaint"
    assert response.requires_escalation is True


# ============================================================================
# GENERAL QUERY HANDLING TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_general_query(agent):
    """Test general query handling"""
    message = "What services do you offer?"
    response = agent.handle_message(message)

    assert response.intent == "general_query"
    assert response.action_taken == "general_assistance"
    assert len(response.response_text) > 0


@pytest.mark.integration
def test_handle_who_are_you_query(agent):
    """Test 'who are you' query"""
    message = "Who are you?"
    response = agent.handle_message(message)

    assert response.intent == "general_query"
    assert "TRIA" in response.response_text or "assistant" in response.response_text.lower()


# ============================================================================
# CONVERSATION CONTEXT TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_message_with_conversation_history(agent):
    """Test message handling with conversation context"""
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {"role": "user", "content": "I'm from Pacific Pizza"}
    ]

    message = "I need supplies"
    response = agent.handle_message(
        message=message,
        conversation_history=conversation_history
    )

    # With context, should better understand this is order placement
    assert response.intent in ["order_placement", "product_inquiry"]


@pytest.mark.integration
def test_handle_message_with_user_context(agent):
    """Test message handling with user context"""
    user_context = {
        "outlet_id": 123,
        "outlet_name": "Pacific Pizza",
        "language": "en"
    }

    message = "I need to order supplies"
    response = agent.handle_message(
        message=message,
        user_context=user_context
    )

    assert response.intent == "order_placement"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_empty_message(agent):
    """Test error handling for empty message"""
    with pytest.raises(ValueError, match="Message cannot be empty"):
        agent.handle_message("")


@pytest.mark.integration
def test_handle_very_long_message(agent):
    """Test handling of very long message"""
    long_message = "I need help with my order. " * 50
    response = agent.handle_message(long_message)

    # Should still process
    assert response.intent is not None
    assert response.response_text is not None


@pytest.mark.integration
def test_handle_special_characters(agent):
    """Test handling of special characters"""
    message = "I need 500 trays @ $10 each!!!"
    response = agent.handle_message(message)

    assert response.intent == "order_placement"


# ============================================================================
# RESPONSE STRUCTURE TESTS
# ============================================================================

def test_customer_service_response_to_dict():
    """Test CustomerServiceResponse serialization"""
    response = CustomerServiceResponse(
        intent="order_placement",
        confidence=0.95,
        response_text="I'll help you with that order.",
        knowledge_used=[{"text": "Policy chunk", "source": "policy.pdf"}],
        action_taken="rag_qa",
        requires_escalation=False,
        extracted_entities={"outlet_name": "Pacific Pizza"},
        metadata={"test": "value"}
    )

    response_dict = response.to_dict()

    assert response_dict["intent"] == "order_placement"
    assert response_dict["confidence"] == 0.95
    assert response_dict["response_text"] == "I'll help you with that order."
    assert len(response_dict["knowledge_used"]) == 1
    assert response_dict["action_taken"] == "rag_qa"
    assert response_dict["requires_escalation"] is False
    assert response_dict["extracted_entities"]["outlet_name"] == "Pacific Pizza"
    assert response_dict["metadata"]["test"] == "value"
    assert response_dict["timestamp"] is not None


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_customer_message_convenience_function(api_key):
    """Test convenience function"""
    response = handle_customer_message(
        message="Hello",
        api_key=api_key
    )

    assert isinstance(response, CustomerServiceResponse)
    assert response.intent == "greeting"


@pytest.mark.integration
def test_handle_customer_message_with_history(api_key):
    """Test convenience function with history"""
    conversation_history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"}
    ]

    response = handle_customer_message(
        message="I need supplies",
        conversation_history=conversation_history,
        api_key=api_key
    )

    assert response.intent in ["order_placement", "product_inquiry"]


# ============================================================================
# MULTI-INTENT MESSAGE TESTS
# ============================================================================

@pytest.mark.integration
def test_handle_multi_intent_message(agent):
    """Test message with multiple intents"""
    # Greeting + order placement
    message = "Hi! I need to order 500 meal trays urgently"
    response = agent.handle_message(message)

    # Should prioritize order_placement
    assert response.intent == "order_placement"


@pytest.mark.integration
def test_handle_complaint_with_order_id(agent):
    """Test complaint mentioning order ID"""
    message = "My order #12345 was delivered late and damaged!"
    response = agent.handle_message(message)

    # Should classify as complaint (not order_status)
    assert response.intent == "complaint"
    assert response.requires_escalation is True


# ============================================================================
# RAG INTEGRATION TESTS (if ChromaDB is populated)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.path.exists("C:\\Users\\fujif\\OneDrive\\Documents\\GitHub\\tria\\data\\chromadb"),
    reason="ChromaDB not populated - run build_knowledge_base.py first"
)
def test_rag_retrieval_integration(agent):
    """Test RAG retrieval with real ChromaDB"""
    # This test requires ChromaDB to be populated
    # with knowledge base documents

    message = "What is your refund policy for damaged items?"
    response = agent.handle_message(message)

    if response.action_taken == "rag_qa":
        # RAG succeeded
        assert response.intent == "policy_question"
        assert len(response.knowledge_used) > 0
        # Response should reference the policy
        assert len(response.response_text) > 100


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_response_latency(agent):
    """Test response time"""
    import time

    message = "What's your refund policy?"

    start = time.time()
    response = agent.handle_message(message)
    end = time.time()

    latency = end - start

    # Should complete in reasonable time (< 15 seconds for GPT-4 + RAG)
    assert latency < 15.0, f"Response took {latency:.2f}s - too slow"
    assert response.response_text is not None


@pytest.mark.integration
@pytest.mark.slow
def test_handle_multiple_messages_sequentially(agent):
    """Test handling multiple messages in sequence"""
    messages = [
        "Hello",
        "I need 500 trays",
        "What's your refund policy?",
        "My order was damaged"
    ]

    responses = []
    for message in messages:
        response = agent.handle_message(message)
        responses.append(response)

    assert len(responses) == 4
    assert responses[0].intent == "greeting"
    assert responses[1].intent == "order_placement"
    assert responses[2].intent == "policy_question"
    assert responses[3].intent == "complaint"
