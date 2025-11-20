"""
Leading-Edge Conversation Memory Models
========================================

PostgreSQL + SQLAlchemy ORM for conversation persistence.
Industry-standard approach with cross-process accessibility.

Architecture:
- Direct SQLAlchemy ORM (not DataFlow) for cross-process access
- PostgreSQL JSONB columns for semi-structured data
- ChromaDB semantic memory integration (separate module)
- DSPy optimization for retrieval (separate module)

NO MOCKING - Real PostgreSQL with production-ready patterns.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class ConversationSession(Base):
    """
    Conversation session tracking with PostgreSQL JSONB

    Industry-standard ORM pattern for session management.
    Uses JSONB for flexible metadata storage with indexing support.
    """
    __tablename__ = 'conversation_sessions'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True,
                       default=lambda: str(uuid.uuid4()))

    # Core fields
    user_id = Column(String(100), nullable=False, index=True)
    outlet_id = Column(Integer, nullable=True, index=True)
    language = Column(String(10), nullable=False, default='en')

    # Timestamps
    start_time = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Metrics
    message_count = Column(Integer, nullable=False, default=0)

    # JSONB columns for flexible data
    intents = Column(JSONB, nullable=False, default={})  # {"primary": "order", "confidence": 0.95}
    context = Column(JSONB, nullable=False, default={})  # Session-level context

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True,
                       onupdate=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_session_user_created', 'user_id', 'created_at'),
        Index('idx_session_outlet_created', 'outlet_id', 'created_at'),
        Index('idx_session_start_time', 'start_time'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'outlet_id': self.outlet_id,
            'language': self.language,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'message_count': self.message_count,
            'intents': self.intents,
            'context': self.context,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationMessage(Base):
    """
    Individual conversation messages with PII scrubbing and semantic indexing

    Industry-standard ORM with:
    - JSONB for flexible metadata
    - Full-text search support (ts_vector)
    - ChromaDB integration via embedding_id
    """
    __tablename__ = 'conversation_messages'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to session
    session_id = Column(String(36), nullable=False, index=True)

    # Message content
    role = Column(String(20), nullable=False, index=True)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, default='en')

    # Intent classification
    intent = Column(String(50), nullable=True, index=True)
    confidence = Column(Float, nullable=False, default=0.0)

    # Metadata (JSONB for flexibility)
    context = Column(JSONB, nullable=False, default={})

    # PII compliance
    pii_scrubbed = Column(Boolean, nullable=False, default=False)

    # Semantic search integration
    embedding_id = Column(String(100), nullable=True, index=True)  # ChromaDB document ID

    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False,
                      server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_message_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_message_role_intent', 'role', 'intent'),
        Index('idx_message_timestamp', 'timestamp'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'language': self.language,
            'intent': self.intent,
            'confidence': self.confidence,
            'context': self.context,
            'pii_scrubbed': self.pii_scrubbed,
            'embedding_id': self.embedding_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserInteractionSummary(Base):
    """
    Aggregated user analytics with long-term retention

    Industry-standard pattern for user profiling and analytics.
    """
    __tablename__ = 'user_interaction_summaries'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), unique=True, nullable=False, index=True)

    # Optional outlet linking
    outlet_id = Column(Integer, nullable=True, index=True)

    # Aggregated metrics
    total_conversations = Column(Integer, nullable=False, default=0)
    total_messages = Column(Integer, nullable=False, default=0)

    # JSONB for analytics data
    common_intents = Column(JSONB, nullable=False, default={})  # {"order": 45, "inquiry": 30}
    analytics_metadata = Column('metadata', JSONB, nullable=False, default={})  # Column name 'metadata', attribute name 'analytics_metadata'

    # User preferences
    preferred_language = Column(String(10), nullable=False, default='en')
    avg_satisfaction = Column(Float, nullable=False, default=0.0)

    # Temporal tracking
    first_interaction = Column(DateTime(timezone=True), nullable=True, index=True)
    last_interaction = Column(DateTime(timezone=True), nullable=True, index=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), nullable=False,
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True,
                       onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_summary_outlet_last', 'outlet_id', 'last_interaction'),
        Index('idx_summary_last_interaction', 'last_interaction'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'user_id': self.user_id,
            'outlet_id': self.outlet_id,
            'total_conversations': self.total_conversations,
            'total_messages': self.total_messages,
            'common_intents': self.common_intents,
            'preferred_language': self.preferred_language,
            'avg_satisfaction': self.avg_satisfaction,
            'first_interaction': self.first_interaction.isoformat() if self.first_interaction else None,
            'last_interaction': self.last_interaction.isoformat() if self.last_interaction else None,
            'metadata': self.analytics_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def create_tables(engine):
    """
    Create all conversation tables in PostgreSQL

    Args:
        engine: SQLAlchemy engine instance

    Note:
        This is idempotent - safe to call multiple times.
        Uses IF NOT EXISTS internally.
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """
    Drop all conversation tables (for testing only!)

    Args:
        engine: SQLAlchemy engine instance

    Warning:
        This will DELETE ALL CONVERSATION DATA!
        Only use in development/testing.
    """
    Base.metadata.drop_all(engine)
