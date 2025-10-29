"""
TRIA AI-BPO Conversation Memory Module
=======================================

Session management and conversation context for GPT-4 chatbot.
Uses DataFlow models for real PostgreSQL database operations.

NO MOCKING - All operations use real database.
"""

from .session_manager import SessionManager
from .context_builder import build_conversation_context, format_messages_for_gpt4

__all__ = [
    "SessionManager",
    "build_conversation_context",
    "format_messages_for_gpt4"
]
