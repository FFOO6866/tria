# TRIA AI-BPO Conversation Memory System

## Overview

The conversation memory system provides comprehensive tracking and analytics for all customer interactions through the TRIA AI-BPO platform. Built using Kailash DataFlow framework, it automatically generates 27 CRUD nodes (9 per model) for seamless database operations.

## Architecture

### Three-Layer Model Design

#### 1. ConversationSession
**Purpose**: Track individual conversation sessions

**Fields**:
- `session_id` (str, unique): UUID for session identification
- `user_id` (str, optional): WhatsApp user identifier
- `outlet_id` (int, optional): Foreign key to Outlet table
- `language` (str): Detected language (en, zh, ms, ta)
- `start_time` (datetime): Session start timestamp
- `end_time` (datetime, optional): Session end timestamp
- `message_count` (int): Total messages in session
- `intents` (JSON): Detected intents with confidence scores
- `context` (JSON): Session context and metadata
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime, optional): Last update timestamp

**Indexes**: session_id (unique), user_id, outlet_id, start_time, created_at

**Auto-Generated Nodes**:
- `ConversationSessionCreateNode`
- `ConversationSessionReadNode`
- `ConversationSessionUpdateNode`
- `ConversationSessionDeleteNode`
- `ConversationSessionListNode`
- `ConversationSessionCountNode`
- `ConversationSessionExistsNode`
- `ConversationSessionBulkCreateNode`
- `ConversationSessionBulkUpdateNode`

#### 2. ConversationMessage
**Purpose**: Store individual messages within sessions

**Fields**:
- `session_id` (str): Foreign key to ConversationSession
- `role` (str): Message role ("user" or "assistant")
- `content` (str): Message content (unlimited with TEXT type)
- `language` (str): Message language
- `intent` (str, optional): Detected intent
- `confidence` (float): Intent confidence score (0-1)
- `context` (JSON): Message context and metadata
- `pii_scrubbed` (bool): PII removal flag
- `embedding_vector` (str, optional): Vector embedding for semantic search
- `timestamp` (datetime): Message timestamp
- `created_at` (datetime): Record creation timestamp

**Data Retention**: 90 days (configurable via retention_policy)

**Indexes**: session_id, timestamp, role, intent, created_at

**Auto-Generated Nodes**:
- `ConversationMessageCreateNode`
- `ConversationMessageReadNode`
- `ConversationMessageUpdateNode`
- `ConversationMessageDeleteNode`
- `ConversationMessageListNode`
- `ConversationMessageCountNode`
- `ConversationMessageExistsNode`
- `ConversationMessageBulkCreateNode`
- `ConversationMessageBulkUpdateNode`

#### 3. UserInteractionSummary
**Purpose**: Aggregate analytics and user profiling

**Fields**:
- `user_id` (str, unique): WhatsApp user identifier
- `outlet_id` (int, optional): Foreign key to Outlet
- `total_conversations` (int): Total conversation sessions
- `total_messages` (int): Total messages sent
- `common_intents` (JSON): Intent frequency map
- `preferred_language` (str): Most frequently used language
- `avg_satisfaction` (float): Average satisfaction score (0-5)
- `last_interaction` (datetime, optional): Most recent interaction
- `first_interaction` (datetime, optional): First interaction
- `metadata` (JSON): Additional analytics data
- `created_at` (datetime): Record creation timestamp
- `updated_at` (datetime, optional): Last update timestamp

**Data Retention**: 2 years (730 days)

**Indexes**: user_id (unique), outlet_id, last_interaction, created_at

**Auto-Generated Nodes**:
- `UserInteractionSummaryCreateNode`
- `UserInteractionSummaryReadNode`
- `UserInteractionSummaryUpdateNode`
- `UserInteractionSummaryDeleteNode`
- `UserInteractionSummaryListNode`
- `UserInteractionSummaryCountNode`
- `UserInteractionSummaryExistsNode`
- `UserInteractionSummaryBulkCreateNode`
- `UserInteractionSummaryBulkUpdateNode`

## Usage Examples

### Creating a Conversation Session

```python
from kailash.workflow.builder import WorkflowBuilder
from kailash.runtime.local import LocalRuntime
import uuid
from datetime import datetime

workflow = WorkflowBuilder()
workflow.add_node("ConversationSessionCreateNode", "create_session", {
    "session_id": str(uuid.uuid4()),
    "user_id": "6591234567",
    "outlet_id": 1,
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

runtime = LocalRuntime()
results, run_id = runtime.execute(workflow.build())
```

### Adding Messages to a Session

```python
workflow = WorkflowBuilder()
workflow.add_node("ConversationMessageCreateNode", "create_message", {
    "session_id": "your-session-uuid",
    "role": "user",
    "content": "Hi, we need 400 boxes for 10 inch pizzas",
    "language": "en",
    "intent": "order_placement",
    "confidence": 0.95,
    "context": {
        "session_context": "order_flow",
        "stage": "item_collection"
    },
    "pii_scrubbed": False,
    "timestamp": datetime.now()
})

results, run_id = runtime.execute(workflow.build())
```

### Querying Conversation History

```python
workflow = WorkflowBuilder()
workflow.add_node("ConversationMessageListNode", "list_messages", {
    "filters": {"session_id": "your-session-uuid"},
    "order_by": ["timestamp"],
    "limit": 100
})

results, run_id = runtime.execute(workflow.build())
messages_result = results.get('list_messages', [])

# Handle DataFlow list result structure
if isinstance(messages_result, list) and len(messages_result) > 0:
    if 'records' in messages_result[0]:
        messages = messages_result[0]['records']
```

### Updating User Analytics

```python
workflow = WorkflowBuilder()
workflow.add_node("UserInteractionSummaryUpdateNode", "update_summary", {
    "id": user_summary_id,
    "total_conversations": previous_count + 1,
    "total_messages": previous_messages + new_messages,
    "last_interaction": datetime.now()
})

results, run_id = runtime.execute(workflow.build())
```

### Analytics Query - Sessions by Language

```python
workflow = WorkflowBuilder()
workflow.add_node("ConversationSessionListNode", "get_sessions", {
    "filters": {"language": "en"},
    "limit": 1000
})

results, run_id = runtime.execute(workflow.build())
```

## Data Retention Policies

### Automatic Cleanup
The system implements tiered retention policies:

1. **ConversationMessage**: 90-day retention
   - Operational data for recent interactions
   - PII-scrubbed after processing
   - Automatically purged after 90 days

2. **UserInteractionSummary**: 2-year retention
   - Aggregated analytics data
   - No PII stored
   - Long-term trend analysis

3. **ConversationSession**: No automatic deletion
   - Metadata only (no message content)
   - Used for session tracking
   - Can be purged via manual workflow

### Manual Cleanup Example

```python
from datetime import datetime, timedelta

# Delete messages older than 90 days
cutoff_date = datetime.now() - timedelta(days=90)

workflow = WorkflowBuilder()
workflow.add_node("ConversationMessageBulkDeleteNode", "cleanup_old_messages", {
    "filters": {
        "created_at": {"$lt": cutoff_date.isoformat()}
    }
})

results, run_id = runtime.execute(workflow.build())
```

## Integration with TRIA AI-BPO Platform

### Enhanced API Integration

The conversation models are automatically initialized in `enhanced_api.py`:

```python
from models.conversation_models import initialize_conversation_models

db = DataFlow(
    database_url=database_url,
    skip_registry=True,
    auto_migrate=True
)

initialize_conversation_models(db)
```

### WhatsApp Integration Pattern

```python
# When receiving WhatsApp message:
1. Create/retrieve conversation session
2. Store incoming message (role="user")
3. Process order with existing agents
4. Store assistant response (role="assistant")
5. Update user interaction summary
6. Close session when interaction complete
```

## Performance Considerations

### Indexes
All tables include strategic indexes for common query patterns:
- Session lookup by ID and user
- Message retrieval by session and timestamp
- User analytics by user ID and interaction date

### JSONB Fields
Context and metadata fields use PostgreSQL JSONB for:
- Flexible schema evolution
- Efficient querying with GIN indexes
- No schema migrations for context changes

### Bulk Operations
For high-volume scenarios, use bulk nodes:
- `ConversationMessageBulkCreateNode` for batch message insertion
- `ConversationMessageBulkDeleteNode` for retention cleanup
- `UserInteractionSummaryBulkUpdateNode` for analytics updates

## Privacy & Compliance

### PII Handling
- `pii_scrubbed` flag tracks PII removal status
- Implement scrubbing before database storage
- Use context JSON for non-PII metadata

### Data Minimization
- Store only necessary conversation data
- Use aggregated summaries instead of raw data where possible
- Implement retention policies to minimize data storage

### GDPR Compliance
- Support right to erasure via delete nodes
- Provide data export via list nodes
- Track consent in session context JSON

## Monitoring & Analytics

### Key Metrics to Track

1. **Session Metrics**:
   - Average session duration
   - Messages per session
   - Sessions by language
   - Sessions by outlet

2. **User Metrics**:
   - Total active users
   - User retention rate
   - Average satisfaction score
   - Preferred languages

3. **Intent Metrics**:
   - Intent distribution
   - Intent confidence scores
   - Intent completion rates

### Example Analytics Workflow

```python
# Daily analytics report
workflow = WorkflowBuilder()

# Count sessions today
workflow.add_node("ConversationSessionListNode", "today_sessions", {
    "filters": {
        "created_at": {
            "$gte": datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        }
    }
})

# Count messages today
workflow.add_node("ConversationMessageListNode", "today_messages", {
    "filters": {
        "created_at": {
            "$gte": datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        }
    }
})

results, run_id = runtime.execute(workflow.build())
```

## Testing

See `examples/conversation_memory_example.py` for complete working examples.

### Unit Test Pattern

```python
import pytest
from dataflow import DataFlow
from models.conversation_models import initialize_conversation_models

@pytest.fixture
def db():
    db = DataFlow(
        database_url="postgresql://...",
        tdd_mode=True  # Automatic rollback
    )
    initialize_conversation_models(db)
    return db

def test_create_session(db):
    # Test session creation
    # Automatic rollback ensures clean state
    pass
```

## Database Schema

Tables created automatically by DataFlow auto-migration:

```sql
-- conversation_sessions
CREATE TABLE conversation_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR UNIQUE NOT NULL,
    user_id VARCHAR,
    outlet_id INTEGER REFERENCES outlets(id),
    language VARCHAR DEFAULT 'en',
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    message_count INTEGER DEFAULT 0,
    intents JSONB,
    context JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- conversation_messages
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR REFERENCES conversation_sessions(session_id),
    role VARCHAR NOT NULL,
    content TEXT,
    language VARCHAR DEFAULT 'en',
    intent VARCHAR,
    confidence FLOAT DEFAULT 0.0,
    context JSONB,
    pii_scrubbed BOOLEAN DEFAULT FALSE,
    embedding_vector TEXT,
    timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- user_interaction_summaries
CREATE TABLE user_interaction_summaries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR UNIQUE NOT NULL,
    outlet_id INTEGER REFERENCES outlets(id),
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    common_intents JSONB,
    preferred_language VARCHAR DEFAULT 'en',
    avg_satisfaction FLOAT DEFAULT 0.0,
    last_interaction TIMESTAMP,
    first_interaction TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

## Troubleshooting

### Common Issues

1. **"session_id not found"**
   - Ensure session created before adding messages
   - Use proper UUID format for session_id

2. **"JSON serialization error"**
   - DataFlow handles JSON automatically
   - Pass Python dict/list directly, not JSON strings

3. **"Slow query performance"**
   - Check indexes are created
   - Use filters to limit result sets
   - Consider pagination for large result sets

## Future Enhancements

- [ ] Semantic search integration using embedding_vector field
- [ ] Real-time sentiment analysis during conversations
- [ ] Automatic intent classification pipeline
- [ ] Multi-language support expansion
- [ ] Conversation quality scoring
- [ ] Automated PII detection and scrubbing
- [ ] Advanced analytics dashboard integration

## References

- [Kailash DataFlow Documentation](../../sdk-users/apps/dataflow/README.md)
- [TRIA AI-BPO Architecture](../TRIA_AIBPO_POV_SCOPE.md)
- [Example Usage](../../examples/conversation_memory_example.py)
