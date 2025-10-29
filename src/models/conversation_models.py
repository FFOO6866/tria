"""
TRIA AI-BPO Conversation Memory Models
=======================================

DataFlow models for conversation tracking and analytics.
Each @db.model automatically generates 9 nodes for CRUD operations.

NO MOCKING - These connect to real PostgreSQL database.
"""

from datetime import datetime
from typing import Optional, Dict, Any


def initialize_conversation_models(db):
    """
    Initialize conversation memory DataFlow models

    Args:
        db: DataFlow instance configured with PostgreSQL connection

    Returns:
        Dictionary of model classes for reference
    """

    # ========================================================================
    # CONVERSATION SESSION MODEL
    # ========================================================================
    @db.model
    class ConversationSession:
        """
        Track individual conversation sessions with outlets

        Each session represents a complete interaction (order placement,
        inquiry, etc.) with start/end timestamps and metadata.

        Generates nodes:
        - ConversationSessionCreateNode
        - ConversationSessionReadNode
        - ConversationSessionUpdateNode
        - ConversationSessionDeleteNode
        - ConversationSessionListNode
        - ConversationSessionCountNode
        - ConversationSessionExistsNode
        - ConversationSessionBulkCreateNode
        - ConversationSessionBulkUpdateNode
        """
        session_id: str                         # Unique session identifier (UUID)
        user_id: Optional[str] = None           # WhatsApp user ID
        outlet_id: Optional[int] = None         # Foreign key to Outlet (if identified)
        language: str = "en"                    # Detected language (en, zh, ms, ta)
        start_time: datetime = None             # Session start timestamp
        end_time: Optional[datetime] = None     # Session end timestamp
        message_count: int = 0                  # Total messages in session
        intents: Dict[str, Any] = {}            # JSON: detected intents and confidence
        context: Dict[str, Any] = {}            # JSON: session context data
        created_at: datetime = None
        updated_at: Optional[datetime] = None

        # Index configuration for performance
        __dataflow__ = {
            'indexes': [
                {'fields': ['session_id'], 'unique': True},
                {'fields': ['user_id']},
                {'fields': ['outlet_id']},
                {'fields': ['start_time']},
                {'fields': ['created_at']},
            ],
            'table_name': 'conversation_sessions'
        }

    # ========================================================================
    # CONVERSATION MESSAGE MODEL
    # ========================================================================
    @db.model
    class ConversationMessage:
        """
        Individual messages within conversation sessions

        Stores complete message history with PII scrubbing, intent detection,
        and contextual metadata. Implements 90-day retention policy.

        Generates nodes:
        - ConversationMessageCreateNode
        - ConversationMessageReadNode
        - ConversationMessageUpdateNode
        - ConversationMessageDeleteNode
        - ConversationMessageListNode
        - ConversationMessageCountNode
        - ConversationMessageExistsNode
        - ConversationMessageBulkCreateNode
        - ConversationMessageBulkUpdateNode
        """
        session_id: str                         # Foreign key to ConversationSession
        role: str                               # "user" or "assistant"
        content: str                            # Message content
        language: str = "en"                    # Message language
        intent: Optional[str] = None            # Detected intent (order, inquiry, complaint)
        confidence: float = 0.0                 # Intent confidence score (0-1)
        context: Dict[str, Any] = {}            # JSON: message context and metadata
        pii_scrubbed: bool = False              # True if PII has been removed
        embedding_vector: Optional[str] = None  # Optional: Vector embedding for semantic search
        timestamp: datetime = None              # Message timestamp
        created_at: datetime = None

        # Index configuration for performance
        __dataflow__ = {
            'indexes': [
                {'fields': ['session_id']},
                {'fields': ['timestamp']},
                {'fields': ['role']},
                {'fields': ['intent']},
                {'fields': ['created_at']},
            ],
            'table_name': 'conversation_messages',
            # Data retention: 90 days
            'retention_policy': {
                'field': 'created_at',
                'days': 90
            }
        }

    # ========================================================================
    # USER INTERACTION SUMMARY MODEL
    # ========================================================================
    @db.model
    class UserInteractionSummary:
        """
        Aggregated analytics for user/outlet interaction patterns

        Long-term analytics and user profiling data with 2-year retention.
        Used for personalization, trend analysis, and service improvement.

        Generates nodes:
        - UserInteractionSummaryCreateNode
        - UserInteractionSummaryReadNode
        - UserInteractionSummaryUpdateNode
        - UserInteractionSummaryDeleteNode
        - UserInteractionSummaryListNode
        - UserInteractionSummaryCountNode
        - UserInteractionSummaryExistsNode
        - UserInteractionSummaryBulkCreateNode
        - UserInteractionSummaryBulkUpdateNode
        """
        user_id: str                            # WhatsApp user ID (unique)
        outlet_id: Optional[int] = None         # Foreign key to Outlet (if linked)
        total_conversations: int = 0            # Total conversation sessions
        total_messages: int = 0                 # Total messages sent
        common_intents: Dict[str, Any] = {}     # JSON: intent frequency map
        preferred_language: str = "en"          # Most frequently used language
        avg_satisfaction: float = 0.0           # Average satisfaction score (0-5)
        last_interaction: Optional[datetime] = None  # Most recent interaction timestamp
        first_interaction: Optional[datetime] = None # First interaction timestamp
        metadata: Dict[str, Any] = {}           # JSON: additional analytics data
        created_at: datetime = None
        updated_at: Optional[datetime] = None

        # Index configuration for performance
        __dataflow__ = {
            'indexes': [
                {'fields': ['user_id'], 'unique': True},
                {'fields': ['outlet_id']},
                {'fields': ['last_interaction']},
                {'fields': ['created_at']},
            ],
            'table_name': 'user_interaction_summaries',
            # Data retention: 2 years
            'retention_policy': {
                'field': 'created_at',
                'days': 730
            }
        }

    # Return model classes for reference
    return {
        "ConversationSession": ConversationSession,
        "ConversationMessage": ConversationMessage,
        "UserInteractionSummary": UserInteractionSummary
    }
