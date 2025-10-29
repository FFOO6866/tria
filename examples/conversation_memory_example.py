#!/usr/bin/env python3
"""
TRIA AI-BPO Conversation Memory Example
========================================

Demonstrates how to use the conversation memory DataFlow models:
- ConversationSession: Track conversation sessions
- ConversationMessage: Store individual messages
- UserInteractionSummary: Aggregate user analytics

NO MOCKING - Uses real PostgreSQL database via DataFlow.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import uuid

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
load_dotenv(project_root / ".env")

from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime.local import LocalRuntime
from dataflow import DataFlow

# Import model initializers
from models.conversation_models import initialize_conversation_models


def main():
    """Demonstrate conversation memory operations"""

    print("=" * 60)
    print("TRIA AI-BPO Conversation Memory Example")
    print("=" * 60)

    # Initialize DataFlow
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[ERROR] DATABASE_URL not configured in .env")
        return

    db = DataFlow(
        database_url=database_url,
        skip_registry=True,
        auto_migrate=True
    )

    # Initialize conversation models
    models = initialize_conversation_models(db)
    print(f"[OK] Initialized {len(models)} conversation models")
    print(f"     - {', '.join(models.keys())}")
    print(f"     - 27 CRUD nodes available (9 per model)\n")

    # Initialize runtime
    runtime = LocalRuntime()

    # ========================================================================
    # EXAMPLE 1: Create a new conversation session
    # ========================================================================
    print("\n" + "=" * 60)
    print("Example 1: Create Conversation Session")
    print("=" * 60)

    session_id = str(uuid.uuid4())
    user_id = "6591234567"  # WhatsApp number
    outlet_id = 1  # Assuming outlet exists in database

    workflow = WorkflowBuilder()
    workflow.add_node("ConversationSessionCreateNode", "create_session", {
        "session_id": session_id,
        "user_id": user_id,
        "outlet_id": outlet_id,
        "language": "en",
        "start_time": datetime.now(),
        "message_count": 0,
        "intents": {
            "primary": "order_placement",
            "confidence": 0.95
        },
        "context": {
            "channel": "whatsapp",
            "platform": "tria_aibpo"
        }
    })

    results, run_id = runtime.execute(workflow.build())
    session_data = results.get('create_session', {})

    print(f"[OK] Created session: {session_id}")
    print(f"     User ID: {user_id}")
    print(f"     Outlet ID: {outlet_id}")
    print(f"     Run ID: {run_id}")

    # ========================================================================
    # EXAMPLE 2: Add messages to the session
    # ========================================================================
    print("\n" + "=" * 60)
    print("Example 2: Add Conversation Messages")
    print("=" * 60)

    messages = [
        {
            "role": "user",
            "content": "Hi, we need 400 boxes for 10 inch pizzas",
            "intent": "order_placement",
            "confidence": 0.95
        },
        {
            "role": "assistant",
            "content": "I understand you need 400 boxes for 10-inch pizzas. Let me process that for you.",
            "intent": "acknowledgment",
            "confidence": 1.0
        },
        {
            "role": "user",
            "content": "Yes, and 200 for 12 inch as well",
            "intent": "order_placement",
            "confidence": 0.92
        }
    ]

    message_ids = []
    for msg in messages:
        msg_workflow = WorkflowBuilder()
        msg_workflow.add_node("ConversationMessageCreateNode", "create_message", {
            "session_id": session_id,
            "role": msg["role"],
            "content": msg["content"],
            "language": "en",
            "intent": msg["intent"],
            "confidence": msg["confidence"],
            "context": {
                "session_context": "order_flow",
                "stage": "item_collection"
            },
            "pii_scrubbed": False,
            "timestamp": datetime.now()
        })

        msg_results, _ = runtime.execute(msg_workflow.build())
        msg_data = msg_results.get('create_message', {})
        msg_id = msg_data.get('id')
        message_ids.append(msg_id)

        print(f"[OK] Message {msg_id}: {msg['role']} - {msg['content'][:50]}...")

    # ========================================================================
    # EXAMPLE 3: Query conversation history
    # ========================================================================
    print("\n" + "=" * 60)
    print("Example 3: Query Conversation History")
    print("=" * 60)

    query_workflow = WorkflowBuilder()
    query_workflow.add_node("ConversationMessageListNode", "list_messages", {
        "filters": {"session_id": session_id},
        "order_by": ["timestamp"],
        "limit": 100
    })

    query_results, _ = runtime.execute(query_workflow.build())
    messages_result = query_results.get('list_messages', [])

    # Handle DataFlow list result structure
    messages_list = []
    if isinstance(messages_result, list) and len(messages_result) > 0:
        if isinstance(messages_result[0], dict) and 'records' in messages_result[0]:
            messages_list = messages_result[0]['records']

    print(f"[OK] Found {len(messages_list)} messages in session {session_id}")
    for msg in messages_list:
        print(f"     - {msg.get('role')}: {msg.get('content')[:50]}...")

    # ========================================================================
    # EXAMPLE 4: Update user interaction summary
    # ========================================================================
    print("\n" + "=" * 60)
    print("Example 4: Update User Interaction Summary")
    print("=" * 60)

    # Check if user summary exists
    check_workflow = WorkflowBuilder()
    check_workflow.add_node("UserInteractionSummaryListNode", "check_user", {
        "filters": {"user_id": user_id},
        "limit": 1
    })

    check_results, _ = runtime.execute(check_workflow.build())
    check_data = check_results.get('check_user', [])

    # Extract existing summary if found
    existing_summary = None
    if isinstance(check_data, list) and len(check_data) > 0:
        if isinstance(check_data[0], dict) and 'records' in check_data[0]:
            records = check_data[0]['records']
            if len(records) > 0:
                existing_summary = records[0]

    if existing_summary:
        # Update existing summary
        update_workflow = WorkflowBuilder()
        update_workflow.add_node("UserInteractionSummaryUpdateNode", "update_summary", {
            "id": existing_summary.get('id'),
            "total_conversations": existing_summary.get('total_conversations', 0) + 1,
            "total_messages": existing_summary.get('total_messages', 0) + len(messages),
            "last_interaction": datetime.now()
        })

        update_results, _ = runtime.execute(update_workflow.build())
        print(f"[OK] Updated user summary for {user_id}")
    else:
        # Create new summary
        create_workflow = WorkflowBuilder()
        create_workflow.add_node("UserInteractionSummaryCreateNode", "create_summary", {
            "user_id": user_id,
            "outlet_id": outlet_id,
            "total_conversations": 1,
            "total_messages": len(messages),
            "common_intents": {
                "order_placement": 2,
                "acknowledgment": 1
            },
            "preferred_language": "en",
            "avg_satisfaction": 4.5,
            "last_interaction": datetime.now(),
            "first_interaction": datetime.now(),
            "metadata": {
                "source": "whatsapp",
                "platform": "tria_aibpo"
            }
        })

        create_results, _ = runtime.execute(create_workflow.build())
        print(f"[OK] Created user summary for {user_id}")

    # ========================================================================
    # EXAMPLE 5: Analytics - Count sessions by language
    # ========================================================================
    print("\n" + "=" * 60)
    print("Example 5: Analytics - Sessions by Language")
    print("=" * 60)

    analytics_workflow = WorkflowBuilder()
    analytics_workflow.add_node("ConversationSessionListNode", "get_sessions", {
        "filters": {"language": "en"},
        "limit": 1000
    })

    analytics_results, _ = runtime.execute(analytics_workflow.build())
    sessions_result = analytics_results.get('get_sessions', [])

    # Extract session count
    session_count = 0
    if isinstance(sessions_result, list) and len(sessions_result) > 0:
        if isinstance(sessions_result[0], dict):
            if 'records' in sessions_result[0]:
                session_count = len(sessions_result[0]['records'])
            elif 'count' in sessions_result[0]:
                session_count = sessions_result[0]['count']

    print(f"[OK] Found {session_count} English language sessions")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    print("\nGenerated CRUD Nodes Available:")
    print("  ConversationSession: 9 nodes (Create, Read, Update, Delete, List, Count, Exists, BulkCreate, BulkUpdate)")
    print("  ConversationMessage: 9 nodes (Create, Read, Update, Delete, List, Count, Exists, BulkCreate, BulkUpdate)")
    print("  UserInteractionSummary: 9 nodes (Create, Read, Update, Delete, List, Count, Exists, BulkCreate, BulkUpdate)")
    print("\nTotal: 27 auto-generated CRUD nodes ready to use!")


if __name__ == "__main__":
    main()
