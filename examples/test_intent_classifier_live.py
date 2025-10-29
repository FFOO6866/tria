"""
Live Test - Intent Classification System
==========================================

Quick manual test of the intent classification system with real GPT-4.
Run this to validate the implementation before full integration testing.

Usage:
    python examples/test_intent_classifier_live.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

from src.agents.intent_classifier import IntentClassifier, classify_intent
from src.agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent


def test_intent_classifier():
    """Test intent classifier with sample messages"""
    print("=" * 80)
    print("TESTING INTENT CLASSIFIER")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in environment")
        return False

    # Create classifier
    print("\n1. Initializing Intent Classifier...")
    classifier = IntentClassifier(api_key=api_key)
    print("   [OK] Classifier initialized")

    # Test messages
    test_messages = [
        ("Hello", "greeting"),
        ("I need 500 meal trays", "order_placement"),
        ("Where's my order #12345?", "order_status"),
        ("What's your refund policy?", "policy_question"),
        ("My order arrived damaged!", "complaint"),
        ("Do you have 10 inch boxes?", "product_inquiry"),
    ]

    print("\n2. Testing Intent Classification...")
    print("-" * 80)

    all_passed = True
    for message, expected_intent in test_messages:
        try:
            result = classifier.classify_intent(message)
            passed = result.intent == expected_intent

            status = "[PASS]" if passed else "[FAIL]"
            print(f"\n   Message: '{message}'")
            print(f"   Expected: {expected_intent}")
            print(f"   Got: {result.intent} (confidence: {result.confidence:.2f})")
            print(f"   Reasoning: {result.reasoning[:100]}...")
            print(f"   {status}")

            if not passed:
                all_passed = False

        except Exception as e:
            print(f"\n   Message: '{message}'")
            print(f"   [ERROR]: {str(e)}")
            all_passed = False

    print("-" * 80)
    return all_passed


def test_customer_service_agent():
    """Test enhanced customer service agent"""
    print("\n" + "=" * 80)
    print("TESTING ENHANCED CUSTOMER SERVICE AGENT")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in environment")
        return False

    # Create agent
    print("\n1. Initializing Enhanced Customer Service Agent...")
    # Note: RAG may fail if ChromaDB not populated, but that's okay for this test
    agent = EnhancedCustomerServiceAgent(api_key=api_key, enable_rag=True)
    print("   [OK] Agent initialized")

    # Test messages
    test_messages = [
        "Hello!",
        "I need to order 500 meal trays",
        "What's your refund policy?",
        "My order was damaged!"
    ]

    print("\n2. Testing Customer Service Responses...")
    print("-" * 80)

    all_passed = True
    for message in test_messages:
        try:
            response = agent.handle_message(message)

            print(f"\n   User: '{message}'")
            print(f"   Intent: {response.intent} (confidence: {response.confidence:.2f})")
            print(f"   Action: {response.action_taken}")
            print(f"   Escalation: {response.requires_escalation}")
            print(f"   Response: {response.response_text[:200]}...")
            print(f"   [SUCCESS]")

        except Exception as e:
            print(f"\n   User: '{message}'")
            print(f"   [ERROR]: {str(e)}")
            all_passed = False

    print("-" * 80)
    return all_passed


def test_conversation_with_history():
    """Test conversation with context"""
    print("\n" + "=" * 80)
    print("TESTING CONVERSATION WITH HISTORY")
    print("=" * 80)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in environment")
        return False

    agent = EnhancedCustomerServiceAgent(api_key=api_key)

    conversation_history = []

    messages = [
        "Hi",
        "I'm from Pacific Pizza",
        "I need some supplies"
    ]

    print("\n1. Simulating Multi-Turn Conversation...")
    print("-" * 80)

    for message in messages:
        try:
            response = agent.handle_message(
                message=message,
                conversation_history=conversation_history
            )

            print(f"\n   User: {message}")
            print(f"   Intent: {response.intent}")
            print(f"   Assistant: {response.response_text[:150]}...")

            # Add to history
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append({"role": "assistant", "content": response.response_text})

        except Exception as e:
            print(f"\n   [ERROR]: {str(e)}")
            return False

    print("-" * 80)
    print("   [SUCCESS] Conversation flow successful")
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("TRIA INTENT CLASSIFICATION SYSTEM - LIVE TEST")
    print("=" * 80)

    results = []

    # Test 1: Intent Classifier
    try:
        result = test_intent_classifier()
        results.append(("Intent Classifier", result))
    except Exception as e:
        print(f"\nFATAL ERROR in Intent Classifier: {str(e)}")
        results.append(("Intent Classifier", False))

    # Test 2: Customer Service Agent
    try:
        result = test_customer_service_agent()
        results.append(("Customer Service Agent", result))
    except Exception as e:
        print(f"\nFATAL ERROR in Customer Service Agent: {str(e)}")
        results.append(("Customer Service Agent", False))

    # Test 3: Conversation with History
    try:
        result = test_conversation_with_history()
        results.append(("Conversation with History", result))
    except Exception as e:
        print(f"\nFATAL ERROR in Conversation with History: {str(e)}")
        results.append(("Conversation with History", False))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\nALL TESTS PASSED! Intent classification system is working correctly.")
        return 0
    else:
        print("\nSOME TESTS FAILED. Review the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
