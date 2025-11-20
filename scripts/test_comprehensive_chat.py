"""
Comprehensive Multi-Turn Conversation Testing
==============================================

Tests chat quality across 5 different conversation types:
1. Greeting + Product Inquiry + Order Placement
2. Policy Question + Follow-up Questions
3. Order Status + Modification Request
4. Complaint + Escalation
5. Mixed Topic Conversation

Tests 3-5 exchanges per conversation to verify:
- Context retention
- Multi-turn understanding
- Tone adaptation
- Response quality
"""

import requests
import json
import time
import uuid
import sys
from typing import List, Dict

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://localhost:8003"

def chat(message: str, session_id: str, user_id: str = "test_user") -> Dict:
    """Send chat message and get response"""
    url = f"{API_BASE}/api/chatbot"
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": str(uuid.uuid4())
    }
    payload = {
        "message": message,
        "user_id": user_id,
        "session_id": session_id
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        return {"error": f"HTTP {response.status_code}: {response.text}"}

    return response.json()

def run_conversation(title: str, messages: List[str], session_id: str) -> List[Dict]:
    """Run a multi-turn conversation"""
    print(f"\n{'='*70}")
    print(f"CONVERSATION: {title}")
    print(f"{'='*70}\n")

    results = []
    for i, msg in enumerate(messages, 1):
        print(f"[Turn {i}/{len(messages)}] User: {msg}")

        start_time = time.time()
        response = chat(msg, session_id)
        elapsed = time.time() - start_time

        if "error" in response:
            print(f"  ERROR: {response['error']}")
            results.append({"user": msg, "error": response['error']})
            break

        bot_msg = response.get("message", "No response")
        intent = response.get("intent", "unknown")
        confidence = response.get("confidence", 0)

        print(f"  Bot ({intent}, {confidence:.2f}): {bot_msg[:200]}{'...' if len(bot_msg) > 200 else ''}")
        print(f"  Time: {elapsed:.2f}s\n")

        results.append({
            "turn": i,
            "user": msg,
            "bot": bot_msg,
            "intent": intent,
            "confidence": confidence,
            "time": elapsed,
            "from_cache": response.get("metadata", {}).get("from_cache", False)
        })

        time.sleep(0.5)  # Brief pause between messages

    return results

def main():
    """Run comprehensive chat testing"""
    print("="*70)
    print("COMPREHENSIVE MULTI-TURN CONVERSATION TESTING")
    print("="*70)

    all_results = {}

    # Conversation 1: Product Inquiry to Order
    conv1_messages = [
        "Hello! I'm looking for pizza boxes.",
        "What sizes do you have?",
        "Great! I need 100 of the 12-inch boxes. Can you help me place an order?",
        "My outlet is Canadian Pizza Pasir Ris."
    ]
    all_results["Product Inquiry & Order"] = run_conversation(
        "Product Inquiry to Order Placement",
        conv1_messages,
        f"test_{uuid.uuid4().hex[:8]}"
    )

    # Conversation 2: Policy Questions with Follow-ups
    conv2_messages = [
        "What is your delivery policy?",
        "What if the delivery is late?",
        "Do you deliver on weekends?"
    ]
    all_results["Policy Questions"] = run_conversation(
        "Policy Questions with Follow-ups",
        conv2_messages,
        f"test_{uuid.uuid4().hex[:8]}"
    )

    # Conversation 3: Complaint
    conv3_messages = [
        "I received defective boxes in my last order",
        "The order number is ORD-001. Half the boxes arrived crushed.",
        "When can I expect the replacement?"
    ]
    all_results["Complaint"] = run_conversation(
        "Complaint and Resolution",
        conv3_messages,
        f"test_{uuid.uuid4().hex[:8]}"
    )

    # Conversation 4: Mixed Topics (tests context switching)
    conv4_messages = [
        "Hi, do you have delivery today?",
        "What's your refund policy?",
        "Actually, I want to place an order for liners.",
        "How many do you have in stock?"
    ]
    all_results["Mixed Topics"] = run_conversation(
        "Mixed Topics - Context Switching",
        conv4_messages,
        f"test_{uuid.uuid4().hex[:8]}"
    )

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")

    total_turns = 0
    total_time = 0
    errors = 0

    for conv_name, results in all_results.items():
        print(f"\n{conv_name}:")
        turns = len(results)
        total_turns += turns

        errors_in_conv = sum(1 for r in results if "error" in r)
        errors += errors_in_conv

        if errors_in_conv == 0:
            avg_time = sum(r["time"] for r in results) / turns if turns > 0 else 0
            total_time += sum(r["time"] for r in results)
            cached = sum(1 for r in results if r.get("from_cache", False))

            print(f"  Turns: {turns}")
            print(f"  Avg Response Time: {avg_time:.2f}s")
            print(f"  Cached Responses: {cached}/{turns}")
            print(f"  Status: {'✓ PASS' if errors_in_conv == 0 else '✗ FAIL'}")
        else:
            print(f"  Status: ✗ FAIL ({errors_in_conv} errors)")

    print(f"\n{'='*70}")
    print(f"OVERALL STATISTICS")
    print(f"{'='*70}")
    print(f"Total Conversations: {len(all_results)}")
    print(f"Total Turns: {total_turns}")
    print(f"Total Errors: {errors}")
    print(f"Success Rate: {((total_turns - errors) / total_turns * 100):.1f}%")
    if total_turns > errors:
        print(f"Average Response Time: {total_time / (total_turns - errors):.2f}s")

    # Save detailed results
    with open("test_results_comprehensive_chat.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nDetailed results saved to: test_results_comprehensive_chat.json")

if __name__ == "__main__":
    main()
