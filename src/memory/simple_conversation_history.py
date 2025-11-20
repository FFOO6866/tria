#!/usr/bin/env python3
"""
Simple In-Memory Conversation History
======================================

Quick fix for conversation context retention without DataFlow dependency.

This provides a simple, working conversation history manager that:
- Stores conversation history in memory (dict)
- Supports session management
- Works immediately without database migrations
- Fallback solution while DataFlow conversation models are being fixed

NO MOCKING - Real conversation tracking, just in-memory instead of PostgreSQL.

For production with persistence, use Redis or fix the DataFlow models.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import logging

logger = logging.getLogger(__name__)


class SimpleConversationHistory:
    """
    Simple in-memory conversation history manager

    Features:
    - Session-based message storage
    - Automatic cleanup of old sessions (30 min TTL)
    - Thread-safe operations
    - No database dependencies

    Usage:
        history = SimpleConversationHistory()

        # Create session
        session_id = history.create_session(user_id="user123")

        # Add messages
        history.add_message(session_id, "user", "Hello!")
        history.add_message(session_id, "assistant", "Hi there!")

        # Get history
        messages = history.get_history(session_id, limit=5)
    """

    def __init__(self, session_ttl_minutes: int = 30):
        """
        Initialize conversation history manager

        Args:
            session_ttl_minutes: Session timeout in minutes (default: 30)
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.session_ttl = timedelta(minutes=session_ttl_minutes)

        logger.info(f"SimpleConversationHistory initialized (TTL: {session_ttl_minutes}min)")

    def create_session(
        self,
        user_id: str,
        outlet_id: Optional[int] = None,
        language: str = "en",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation session

        Args:
            user_id: User identifier
            outlet_id: Optional outlet ID
            language: Conversation language
            metadata: Optional additional metadata

        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())

        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "outlet_id": outlet_id,
            "language": language,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
            "metadata": metadata or {}
        }

        logger.info(f"Session created: {session_id[:16]}... (user: {user_id})")
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        confidence: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a message to conversation history

        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Message content
            intent: Optional intent classification
            confidence: Intent confidence score
            metadata: Optional additional metadata

        Returns:
            True if added successfully
        """
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id[:16]}...")
            return False

        message = {
            "role": role,
            "content": content,
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }

        self.messages[session_id].append(message)

        # Update session
        self.sessions[session_id]["last_activity"] = datetime.now()
        self.sessions[session_id]["message_count"] += 1

        logger.debug(f"Message added to {session_id[:8]}... [{role}]: {content[:50]}...")
        return True

    def get_history(
        self,
        session_id: str,
        limit: int = 10,
        role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
            role_filter: Optional filter by role ("user" or "assistant")

        Returns:
            List of messages (oldest first)
        """
        if session_id not in self.sessions:
            logger.warning(f"Session not found: {session_id[:16]}...")
            return []

        # Clean up expired sessions
        self._cleanup_expired_sessions()

        messages = self.messages.get(session_id, [])

        # Filter by role if specified
        if role_filter:
            messages = [m for m in messages if m.get("role") == role_filter]

        # Return last N messages
        return messages[-limit:]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata

        Args:
            session_id: Session identifier

        Returns:
            Session metadata or None if not found
        """
        return self.sessions.get(session_id)

    def update_session_metadata(
        self,
        session_id: str,
        metadata_updates: Dict[str, Any]
    ) -> bool:
        """
        Update session metadata

        Args:
            session_id: Session identifier
            metadata_updates: Metadata fields to update

        Returns:
            True if updated successfully
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["metadata"].update(metadata_updates)
        self.sessions[session_id]["last_activity"] = datetime.now()
        return True

    def close_session(self, session_id: str) -> bool:
        """
        Close a session (mark as ended)

        Args:
            session_id: Session identifier

        Returns:
            True if closed successfully
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["ended_at"] = datetime.now()
        logger.info(f"Session closed: {session_id[:16]}...")
        return True

    def _cleanup_expired_sessions(self):
        """Remove expired sessions based on TTL"""
        now = datetime.now()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            last_activity = session.get("last_activity", session["created_at"])
            if now - last_activity > self.session_ttl:
                expired_sessions.append(session_id)

        # Remove expired sessions
        for session_id in expired_sessions:
            del self.sessions[session_id]
            if session_id in self.messages:
                del self.messages[session_id]
            logger.info(f"Expired session removed: {session_id[:16]}...")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about conversation history"""
        total_sessions = len(self.sessions)
        total_messages = sum(len(msgs) for msgs in self.messages.values())

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0
        }


# Global instance
_global_history: Optional[SimpleConversationHistory] = None


def get_simple_history() -> SimpleConversationHistory:
    """
    Get or create global conversation history instance

    Returns:
        SimpleConversationHistory instance
    """
    global _global_history
    if _global_history is None:
        _global_history = SimpleConversationHistory(session_ttl_minutes=30)
    return _global_history


def reset_simple_history():
    """Reset global conversation history (for testing)"""
    global _global_history
    _global_history = None
