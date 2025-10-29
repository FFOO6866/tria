#!/usr/bin/env python3
"""
Test Chatbot Endpoint
=====================

Quick test script to verify the /api/chatbot endpoint is working.

Usage:
    python scripts/test_chatbot_endpoint.py
"""

import requests
import json
import sys
from typing import Dict, Any


API_BASE_URL = "http://localhost:8001"


def test_health_check() -> bool:
    """Test if server is running and chatbot components are initialized"""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE_URL}/health")

        if response.status_code != 200:
            print(f"❌ FAILED: Health check returned {response.status_code}")
            return False

        data = response.json()
        print(f"✅ Server Status: {data['status']}")
        print(f"✅ Database: {data['database']}")
        print(f"✅ Runtime: {data['runtime']}")
        print(f"✅ Session Manager: {data['session_manager']}")
        print("\nChatbot Components:")
        print(f"  - Intent Classifier: {data['chatbot']['intent_classifier']}")
        print(f"  - Customer Service Agent: {data['chatbot']['customer_service_agent']}")
        print(f"  - Knowledge Base: {data['chatbot']['knowledge_base']}")

        # Check if all chatbot components are initialized
        chatbot = data['chatbot']
        if all(v == "initialized" for v in chatbot.values()):
            print("\n✅ All chatbot components initialized!")
            return True
        else:
            print("\n⚠️  WARNING: Some chatbot components not initialized")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Cannot connect to server. Is it running?")
        print(f"   Start server with: python src/enhanced_api.py")
        return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def test_greeting() -> bool:
    """Test greeting intent"""
    print("\n" + "=" * 60)
    print("TEST 2: Greeting Intent")
    print("=" * 60)

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chatbot",
            json={
                "message": "Hello!",
                "user_id": "test_user_123",
                "language": "en"
            }
        )

        if response.status_code != 200:
            print(f"❌ FAILED: Endpoint returned {response.status_code}")
            print(f"   Error: {response.text}")
            return False

        data = response.json()

        print(f"✅ Session ID: {data['session_id'][:20]}...")
        print(f"✅ Intent: {data['intent']}")
        print(f"✅ Confidence: {data['confidence']:.2f}")
        print(f"✅ Language: {data['language']}")
        print(f"\nResponse:")
        print(f"  {data['message'][:200]}...")

        if data['intent'] == 'greeting':
            print("\n✅ Greeting intent correctly detected!")
            return True
        else:
            print(f"\n⚠️  WARNING: Expected 'greeting', got '{data['intent']}'")
            return False

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def test_policy_question() -> bool:
    """Test policy question with RAG"""
    print("\n" + "=" * 60)
    print("TEST 3: Policy Question (RAG)")
    print("=" * 60)

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chatbot",
            json={
                "message": "What is your refund policy?",
                "user_id": "test_user_123",
                "language": "en"
            }
        )

        if response.status_code != 200:
            print(f"❌ FAILED: Endpoint returned {response.status_code}")
            print(f"   Error: {response.text}")
            return False

        data = response.json()

        print(f"✅ Session ID: {data['session_id'][:20]}...")
        print(f"✅ Intent: {data['intent']}")
        print(f"✅ Confidence: {data['confidence']:.2f}")
        print(f"✅ Citations: {len(data['citations'])}")

        if data['citations']:
            print("\nCitations:")
            for i, citation in enumerate(data['citations'][:3], 1):
                print(f"  [{i}] {citation.get('source', 'Unknown')}")
                print(f"      Similarity: {citation.get('similarity', 0):.2f}")

        print(f"\nResponse:")
        print(f"  {data['message'][:200]}...")

        if data['intent'] == 'policy_question':
            print("\n✅ Policy question intent correctly detected!")
            if data['citations']:
                print("✅ RAG retrieval working (citations found)!")
            else:
                print("⚠️  WARNING: No citations found (RAG may not be working)")
            return True
        else:
            print(f"\n⚠️  WARNING: Expected 'policy_question', got '{data['intent']}'")
            return False

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def test_multi_turn_conversation() -> bool:
    """Test multi-turn conversation with session resumption"""
    print("\n" + "=" * 60)
    print("TEST 4: Multi-Turn Conversation")
    print("=" * 60)

    try:
        # First message
        print("\n[Turn 1] User: What products do you offer?")
        response1 = requests.post(
            f"{API_BASE_URL}/api/chatbot",
            json={
                "message": "What products do you offer?",
                "user_id": "test_user_456",
                "language": "en"
            }
        )

        if response1.status_code != 200:
            print(f"❌ FAILED: Turn 1 returned {response1.status_code}")
            return False

        data1 = response1.json()
        session_id = data1['session_id']

        print(f"✅ Session created: {session_id[:20]}...")
        print(f"✅ Intent: {data1['intent']}")
        print(f"   Response: {data1['message'][:150]}...")

        # Second message (resume session)
        print("\n[Turn 2] User: What about delivery times?")
        response2 = requests.post(
            f"{API_BASE_URL}/api/chatbot",
            json={
                "message": "What about delivery times?",
                "user_id": "test_user_456",
                "session_id": session_id,  # Resume session
                "language": "en"
            }
        )

        if response2.status_code != 200:
            print(f"❌ FAILED: Turn 2 returned {response2.status_code}")
            return False

        data2 = response2.json()

        print(f"✅ Session resumed: {data2['session_id'][:20]}...")
        print(f"✅ Intent: {data2['intent']}")
        print(f"   Response: {data2['message'][:150]}...")

        # Verify same session
        if data1['session_id'] == data2['session_id']:
            print("\n✅ Multi-turn conversation working (same session ID)!")
            return True
        else:
            print("\n⚠️  WARNING: Session IDs don't match")
            return False

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def test_metadata() -> bool:
    """Test response metadata"""
    print("\n" + "=" * 60)
    print("TEST 5: Response Metadata")
    print("=" * 60)

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/chatbot",
            json={
                "message": "Tell me about your company",
                "user_id": "test_user_789",
                "language": "en"
            }
        )

        if response.status_code != 200:
            print(f"❌ FAILED: Endpoint returned {response.status_code}")
            return False

        data = response.json()
        metadata = data.get('metadata', {})

        print(f"✅ Processing Time: {metadata.get('processing_time', 'N/A')}")
        print(f"✅ Conversation Turns: {metadata.get('conversation_turns', 0)}")
        print(f"✅ Action: {metadata.get('action', 'N/A')}")

        print("\nComponents Used:")
        for component in metadata.get('components_used', []):
            if component:
                print(f"  - {component}")

        print("\n✅ Metadata present in response!")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


def print_summary(results: Dict[str, bool]):
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✅ ALL TESTS PASSED!")
        print("\nChatbot endpoint is fully operational.")
        print("\nNext steps:")
        print("  1. Build knowledge base: python scripts/build_knowledge_base.py")
        print("  2. Test with frontend: Open http://localhost:3000")
        print("  3. Try various intents in Swagger UI: http://localhost:8001/docs")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nCheck server logs for errors:")
        print("  - Verify OPENAI_API_KEY is set")
        print("  - Ensure knowledge base is built")
        print("  - Check database connection")

    print("=" * 60 + "\n")

    return passed == total


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TRIA AI Chatbot Endpoint Test Suite")
    print("=" * 60)
    print("\nTesting endpoint: POST /api/chatbot")
    print("Server: http://localhost:8001")

    results = {}

    # Run tests in sequence
    results["Health Check"] = test_health_check()

    if not results["Health Check"]:
        print("\n❌ Server not ready. Stopping tests.")
        print_summary(results)
        sys.exit(1)

    results["Greeting Intent"] = test_greeting()
    results["Policy Question (RAG)"] = test_policy_question()
    results["Multi-Turn Conversation"] = test_multi_turn_conversation()
    results["Response Metadata"] = test_metadata()

    # Print summary
    all_passed = print_summary(results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
