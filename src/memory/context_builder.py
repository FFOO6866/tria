#!/usr/bin/env python3
"""
TRIA AI-BPO Context Builder
============================

Builds conversation context for GPT-4 from database message history.
Formats messages in GPT-4 API format with system prompts and user context.

NO MOCKING - Retrieves real conversation data from PostgreSQL.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime.local import LocalRuntime


def build_conversation_context(
    session_id: str,
    max_messages: int = 10,
    runtime: Optional[LocalRuntime] = None
) -> Dict[str, Any]:
    """
    Build complete conversation context for GPT-4

    Retrieves session metadata and message history from database,
    formats for GPT-4 API consumption.

    Args:
        session_id: Session identifier
        max_messages: Maximum number of messages to include
        runtime: Kailash LocalRuntime instance (creates new if not provided)

    Returns:
        Dictionary containing:
        - session: Session metadata (outlet_id, language, intents)
        - messages: List of messages formatted for GPT-4
        - message_count: Number of messages in history
        - user_id: User identifier

    Example:
        {
            "session": {
                "session_id": "uuid",
                "user_id": "6591234567",
                "outlet_id": 1,
                "language": "en",
                "intents": {"primary": "order", "confidence": 0.95}
            },
            "messages": [
                {"role": "user", "content": "I need 400 pizza boxes"},
                {"role": "assistant", "content": "Order confirmed..."}
            ],
            "message_count": 2,
            "user_id": "6591234567"
        }
    """
    if runtime is None:
        runtime = LocalRuntime()

    # Step 1: Retrieve session metadata
    session_workflow = WorkflowBuilder()
    session_workflow.add_node("ConversationSessionListNode", "get_session", {
        "filters": {"session_id": session_id},
        "limit": 1
    })

    try:
        session_results, _ = runtime.execute(session_workflow.build())
        session_data = session_results.get('get_session', [])

        # Extract session
        session = None
        if isinstance(session_data, list) and len(session_data) > 0:
            if isinstance(session_data[0], dict):
                if 'records' in session_data[0]:
                    records = session_data[0]['records']
                    session = records[0] if len(records) > 0 else None
                else:
                    session = session_data[0]

        if not session:
            raise ValueError(f"Session {session_id} not found in database")

        # Step 2: Retrieve message history
        messages_workflow = WorkflowBuilder()
        messages_workflow.add_node("ConversationMessageListNode", "get_messages", {
            "filters": {"session_id": session_id},
            "order_by": ["timestamp"],  # Oldest first
            "limit": max_messages
        })

        messages_results, _ = runtime.execute(messages_workflow.build())
        messages_data = messages_results.get('get_messages', [])

        # Extract messages
        messages = []
        if isinstance(messages_data, list) and len(messages_data) > 0:
            if isinstance(messages_data[0], dict):
                if 'records' in messages_data[0]:
                    messages = messages_data[0]['records']
                else:
                    messages = messages_data

        # Step 3: Format messages for GPT-4
        formatted_messages = format_messages_for_gpt4(messages)

        return {
            "session": {
                "session_id": session.get('session_id'),
                "user_id": session.get('user_id'),
                "outlet_id": session.get('outlet_id'),
                "language": session.get('language', 'en'),
                "intents": session.get('intents', {}),
                "context": session.get('context', {})
            },
            "messages": formatted_messages,
            "message_count": len(formatted_messages),
            "user_id": session.get('user_id')
        }

    except Exception as e:
        raise RuntimeError(f"Failed to build conversation context: {str(e)}") from e


def format_messages_for_gpt4(
    messages: List[Dict[str, Any]],
    include_metadata: bool = False
) -> List[Dict[str, str]]:
    """
    Format database messages for GPT-4 API

    Converts database message records to GPT-4 message format:
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Args:
        messages: List of message dictionaries from database
        include_metadata: Include intent and confidence in content (default: False)

    Returns:
        List of messages in GPT-4 format

    Example:
        Input (from DB):
        [
            {
                "role": "user",
                "content": "I need pizza boxes",
                "intent": "order_placement",
                "confidence": 0.95,
                "timestamp": datetime(...)
            }
        ]

        Output (for GPT-4):
        [
            {
                "role": "user",
                "content": "I need pizza boxes"
            }
        ]
    """
    formatted = []

    for msg in messages:
        # Basic message structure
        formatted_msg = {
            "role": msg.get('role', 'user'),
            "content": msg.get('content', '')
        }

        # Optionally include metadata in content
        if include_metadata:
            intent = msg.get('intent')
            confidence = msg.get('confidence', 0.0)
            if intent and confidence > 0:
                formatted_msg['content'] = (
                    f"{formatted_msg['content']}\n"
                    f"[Intent: {intent}, Confidence: {confidence:.2f}]"
                )

        formatted.append(formatted_msg)

    return formatted


def create_system_prompt_with_context(
    session_context: Dict[str, Any],
    base_system_prompt: str,
    include_history: bool = True
) -> List[Dict[str, str]]:
    """
    Create complete GPT-4 messages array with system prompt and context

    Args:
        session_context: Context from build_conversation_context()
        base_system_prompt: Base system prompt for GPT-4
        include_history: Include conversation history in messages (default: True)

    Returns:
        Complete messages array for GPT-4 API:
        [
            {"role": "system", "content": "Enhanced system prompt..."},
            {"role": "user", "content": "Previous message 1"},
            {"role": "assistant", "content": "Previous response 1"},
            ...
        ]

    Example:
        >>> context = build_conversation_context("session-id")
        >>> messages = create_system_prompt_with_context(
        ...     context,
        ...     "You are an order processing assistant...",
        ...     include_history=True
        ... )
        >>> # Send to GPT-4 API
    """
    # Extract session metadata
    session = session_context.get('session', {})
    user_id = session_context.get('user_id')
    outlet_id = session.get('outlet_id')
    language = session.get('language', 'en')
    intents = session.get('intents', {})

    # Enhance system prompt with context
    enhanced_prompt = f"""{base_system_prompt}

CONVERSATION CONTEXT:
- User ID: {user_id}
- Outlet ID: {outlet_id if outlet_id else 'Not identified'}
- Language: {language}
- Primary Intent: {intents.get('primary', 'Unknown')} (Confidence: {intents.get('confidence', 0):.2f})
- Message Count: {session_context.get('message_count', 0)}

Remember this context when processing the current request.
"""

    # Build messages array
    messages = [
        {"role": "system", "content": enhanced_prompt}
    ]

    # Add conversation history if requested
    if include_history:
        history_messages = session_context.get('messages', [])
        messages.extend(history_messages)

    return messages


def get_recent_user_messages(
    session_id: str,
    limit: int = 5,
    runtime: Optional[LocalRuntime] = None
) -> List[str]:
    """
    Get recent user messages as simple text list

    Useful for quick context without full GPT-4 formatting.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to retrieve
        runtime: Kailash LocalRuntime instance

    Returns:
        List of user message content strings (oldest first)

    Example:
        >>> recent = get_recent_user_messages("session-id", limit=3)
        >>> print(recent)
        ["I need pizza boxes", "400 pieces", "10 inch size"]
    """
    if runtime is None:
        runtime = LocalRuntime()

    # Retrieve user messages only
    workflow = WorkflowBuilder()
    workflow.add_node("ConversationMessageListNode", "get_user_messages", {
        "filters": {
            "session_id": session_id,
            "role": "user"
        },
        "order_by": ["timestamp"],
        "limit": limit
    })

    try:
        results, _ = runtime.execute(workflow.build())
        messages_data = results.get('get_user_messages', [])

        # Extract messages
        messages = []
        if isinstance(messages_data, list) and len(messages_data) > 0:
            if isinstance(messages_data[0], dict):
                if 'records' in messages_data[0]:
                    messages = messages_data[0]['records']
                else:
                    messages = messages_data

        # Extract content only
        return [msg.get('content', '') for msg in messages if msg.get('content')]

    except Exception as e:
        print(f"[ERROR] Failed to retrieve user messages: {e}")
        return []


def detect_conversation_intent(
    messages: List[Dict[str, Any]],
    confidence_threshold: float = 0.7
) -> Optional[str]:
    """
    Detect primary conversation intent from message history

    Analyzes intent field from messages and returns most common intent
    above confidence threshold.

    Args:
        messages: Message history from database
        confidence_threshold: Minimum confidence to consider (0-1)

    Returns:
        Most common intent or None if no high-confidence intents found

    Example:
        >>> messages = get_conversation_history("session-id")
        >>> intent = detect_conversation_intent(messages)
        >>> print(intent)
        "order_placement"
    """
    intent_counts = {}

    for msg in messages:
        intent = msg.get('intent')
        confidence = msg.get('confidence', 0.0)

        if intent and confidence >= confidence_threshold:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    if not intent_counts:
        return None

    # Return most common intent
    return max(intent_counts, key=intent_counts.get)


def get_session_summary(
    session_id: str,
    runtime: Optional[LocalRuntime] = None
) -> Dict[str, Any]:
    """
    Get quick session summary for logging/debugging

    Args:
        session_id: Session identifier
        runtime: Kailash LocalRuntime instance

    Returns:
        Dictionary with session summary:
        {
            "session_id": "uuid",
            "user_id": "6591234567",
            "duration_seconds": 120,
            "message_count": 4,
            "primary_intent": "order_placement",
            "language": "en",
            "status": "active" or "closed"
        }
    """
    if runtime is None:
        runtime = LocalRuntime()

    try:
        # Get session
        workflow = WorkflowBuilder()
        workflow.add_node("ConversationSessionListNode", "get_session", {
            "filters": {"session_id": session_id},
            "limit": 1
        })

        results, _ = runtime.execute(workflow.build())
        session_data = results.get('get_session', [])

        # Extract session
        session = None
        if isinstance(session_data, list) and len(session_data) > 0:
            if isinstance(session_data[0], dict):
                if 'records' in session_data[0]:
                    records = session_data[0]['records']
                    session = records[0] if len(records) > 0 else None
                else:
                    session = session_data[0]

        if not session:
            return {"error": f"Session {session_id} not found"}

        # Calculate duration
        start_time = session.get('start_time')
        end_time = session.get('end_time')

        duration_seconds = 0
        status = "closed" if end_time else "active"

        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_seconds = (end_time - start_time).total_seconds()
            elif status == "active":
                duration_seconds = (datetime.now() - start_time).total_seconds()

        # Extract intent
        intents = session.get('intents', {})
        primary_intent = intents.get('primary', 'unknown')

        return {
            "session_id": session.get('session_id'),
            "user_id": session.get('user_id'),
            "duration_seconds": int(duration_seconds),
            "message_count": session.get('message_count', 0),
            "primary_intent": primary_intent,
            "language": session.get('language', 'en'),
            "status": status
        }

    except Exception as e:
        return {"error": str(e)}
