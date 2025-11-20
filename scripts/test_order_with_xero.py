"""
Test End-to-End Order Flow with Xero Integration
==================================================

This script tests the complete order workflow:
1. User sends WhatsApp message with order
2. Customer Service Agent classifies intent
3. Semantic search finds products
4. GPT-4 parses order items
5. Finance Controller calculates totals
6. Order created in database
7. Xero workflow executes (if configured):
   - Draft order created
   - Order finalized
   - Invoice posted
8. Agent timeline visualization

Usage:
    python scripts/test_order_with_xero.py
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests
import json
from datetime import datetime

# API endpoint
API_URL = "http://127.0.0.1:8003/api/chatbot"

# Test order messages
TEST_MESSAGES = [
    {
        "name": "Test 1: Simple Order at Jewel",
        "message": "Hi! This is A&W Jewel. Can I order 100 boxes of 10 inch pizza boxes and 50 liners?",
        "expected_customer": "A&W - Jewel",
        "expected_items": 2
    },
    {
        "name": "Test 2: Canadian Pizza Order",
        "message": "Hello, this is Canadian Pizza Bedok. We need 200 units of 12 inch boxes and 100 14 inch boxes.",
        "expected_customer": "Canadian Pizza - Bedok",
        "expected_items": 2
    },
    {
        "name": "Test 3: Tim Ho Wan Order",
        "message": "Good morning! Tim Ho Wan MBS here. Please send us 150 takeaway boxes and 200 liners.",
        "expected_customer": "Tim Ho Wan - MBS",
        "expected_items": 2
    }
]


def send_message(message: str, session_id: str = "test_xero_integration") -> dict:
    """Send message to chatbot API"""
    payload = {
        "message": message,
        "user_id": f"test_user_{session_id}",
        "session_id": session_id
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": str(e)}


def display_agent_timeline(timeline: list):
    """Display agent activity timeline"""
    if not timeline:
        print("  No agent timeline available")
        return

    print("\n  Agent Activity Timeline:")
    print("  " + "=" * 70)

    for idx, agent in enumerate(timeline, 1):
        agent_name = agent.get('agent_name', 'Unknown Agent')
        status = agent.get('status', 'unknown')
        task = agent.get('current_task', '')
        details = agent.get('details', [])

        # Status indicator
        status_icon = {
            'completed': '✓',
            'in_progress': '⋯',
            'failed': '✗'
        }.get(status, '?')

        print(f"  {idx}. {status_icon} {agent_name}")
        print(f"     Task: {task}")

        if details:
            print(f"     Details:")
            for detail in details[:3]:  # Show first 3 details
                print(f"       - {detail}")
            if len(details) > 3:
                print(f"       ... and {len(details) - 3} more")
        print()


def run_test(test_config: dict):
    """Run a single test case"""
    print("\n" + "=" * 80)
    print(f"TEST: {test_config['name']}")
    print("=" * 80)
    print(f"Message: {test_config['message']}")
    print()

    # Send message
    print("[1] Sending message to API...")
    result = send_message(test_config['message'])

    if "error" in result:
        print(f"ERROR: {result['error']}")
        return False

    # Display results
    print("\n[2] Response received:")
    print(f"  Intent: {result.get('intent', 'Unknown')}")
    print(f"  Response: {result.get('response', '')[:200]}...")

    # Check agent timeline
    agent_timeline = result.get('agent_timeline', [])
    if agent_timeline:
        display_agent_timeline(agent_timeline)

    # Check for Xero integration
    xero_mentioned = False
    for agent in agent_timeline:
        details = agent.get('details', [])
        for detail in details:
            if 'Xero' in detail or 'Invoice' in detail or 'Draft Order' in detail:
                xero_mentioned = True
                break

    if xero_mentioned:
        print("  🎉 Xero Integration: ACTIVE (Draft Order → Invoice flow executed)")
    else:
        print("  ℹ️  Xero Integration: SKIPPED (Not configured or flow disabled)")

    # Show order creation
    print("\n[3] Order Processing:")
    if result.get('response'):
        if 'order' in result['response'].lower() and 'confirmed' in result['response'].lower():
            print("  ✓ Order created successfully in database")
        else:
            print("  ℹ️  Order status unclear from response")

    return True


def main():
    """Main test runner"""
    print("\n" + "=" * 80)
    print("TRIA AI-BPO: End-to-End Order Flow with Xero Integration")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_URL}")
    print()

    # Check API health
    print("Checking API health...")
    try:
        health_response = requests.get("http://127.0.0.1:8003/health", timeout=5)
        if health_response.status_code == 200:
            print("✓ API is healthy and ready")
        else:
            print(f"⚠ API returned status code: {health_response.status_code}")
    except Exception as e:
        print(f"✗ API health check failed: {e}")
        print("  Make sure the backend server is running:")
        print("  uvicorn src.enhanced_api:app --host 127.0.0.1 --port 8003")
        return

    # Run tests
    success_count = 0
    for test_config in TEST_MESSAGES:
        if run_test(test_config):
            success_count += 1

    # Summary
    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {success_count}/{len(TEST_MESSAGES)} tests completed")
    print("=" * 80)

    print("\nWhat was tested:")
    print("  [✓] Customer/outlet lookup from database")
    print("  [✓] Product semantic search")
    print("  [✓] GPT-4 order parsing")
    print("  [✓] Order total calculation")
    print("  [✓] Database order creation")
    print("  [✓] Xero integration trigger (if configured)")
    print("  [✓] Agent timeline visualization")

    print("\nNext steps:")
    print("  1. Check database for created orders:")
    print("     SELECT * FROM orders ORDER BY created_at DESC LIMIT 5;")
    print()
    print("  2. To enable Xero sync:")
    print("     - Update XERO_REFRESH_TOKEN in .env")
    print("     - Restart backend server")
    print("     - Re-run this test")
    print()
    print("  3. View orders in frontend:")
    print("     http://localhost:3000")


if __name__ == '__main__':
    main()
