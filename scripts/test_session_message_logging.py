#!/usr/bin/env python3
"""
Test Session Message Logging
=============================

Verify that SessionManager can:
1. Create a session
2. Log messages to database
3. Retrieve conversation history

This tests if the ConversationMessage table is working despite migration errors.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from memory.session_manager import SessionManager
from kailash.runtime.local import LocalRuntime

if __name__ == "__main__":
    print("=" * 70)
    print("SESSION MESSAGE LOGGING TEST")
    print("=" * 70)

    try:
        # Initialize SessionManager
        runtime = LocalRuntime()
        session_manager = SessionManager(runtime=runtime)
        print("\n[OK] SessionManager initialized")

        # Create a test session
        print("\n[1/4] Creating test session...")
        session_id = session_manager.create_session(
            user_id="test_user_12345",
            outlet_id=None,
            language="en",
            initial_intent="greeting",
            intent_confidence=0.95
        )
        print(f"[OK] Session created: {session_id[:16]}...")

        # Log a user message
        print("\n[2/4] Logging user message...")
        logged_user = session_manager.log_message(
            session_id=session_id,
            role="user",
            content="Hello! I'm looking for pizza boxes.",
            intent="product_inquiry",
            confidence=0.95,
            language="en",
            context={"test": "data", "channel": "test_script"},
            enable_pii_scrubbing=True
        )
        if logged_user:
            print("[OK] User message logged successfully")
        else:
            print("[ERROR] User message logging failed!")

        # Log an assistant message
        print("\n[3/4] Logging assistant message...")
        logged_assistant = session_manager.log_message(
            session_id=session_id,
            role="assistant",
            content="Hello! We offer pizza boxes in multiple sizes...",
            intent="product_inquiry",
            confidence=0.95,
            language="en",
            context={"test": "response", "source": "agent"},
            enable_pii_scrubbing=False  # Don't scrub assistant messages
        )
        if logged_assistant:
            print("[OK] Assistant message logged successfully")
        else:
            print("[ERROR] Assistant message logging failed!")

        # Retrieve conversation history
        print("\n[4/4] Retrieving conversation history...")
        history = session_manager.get_conversation_history(
            session_id=session_id,
            limit=10
        )
        print(f"[RESULT] Retrieved {len(history)} messages from database")

        if len(history) > 0:
            print("\n[OK] Conversation history working!")
            print("\nMessages:")
            for i, msg in enumerate(history, 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:50]
                print(f"  {i}. [{role}] {content}...")
        else:
            print("\n[ERROR] No messages retrieved!")
            print("This means the ConversationMessage table is not working.")
            print("The table migration likely failed due to JSON field syntax error.")

        print("\n" + "=" * 70)
        print("CONCLUSION")
        print("=" * 70)
        if len(history) >= 2:
            print("[✓] Message logging and retrieval WORKING")
            print("    Context retention should work now!")
        else:
            print("[✗] Message logging or retrieval BROKEN")
            print("    The ConversationMessage table migration failed.")
            print("    Need to manually create table or fix DataFlow JSON handling.")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
