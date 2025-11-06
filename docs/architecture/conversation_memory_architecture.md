# Conversation Memory System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TRIA AI-BPO Platform                              │
│                   (enhanced_api.py - FastAPI)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DataFlow Framework                                │
│                   (Kailash SDK v0.4.6+)                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Models (8 total)                                            │  │
│  │  ┌────────────────────┐  ┌─────────────────────────────┐    │  │
│  │  │ Business Models    │  │ Conversation Models (NEW)   │    │  │
│  │  │ ----------------   │  │ -------------------------   │    │  │
│  │  │ • Product          │  │ • ConversationSession       │    │  │
│  │  │ • Outlet           │  │ • ConversationMessage       │    │  │
│  │  │ • Order            │  │ • UserInteractionSummary    │    │  │
│  │  │ • DeliveryOrder    │  │                             │    │  │
│  │  │ • Invoice          │  │ (27 auto-generated nodes)   │    │  │
│  │  │                    │  │                             │    │  │
│  │  │ (45 nodes)         │  │                             │    │  │
│  │  └────────────────────┘  └─────────────────────────────┘    │  │
│  │                                                              │  │
│  │  Total: 72 CRUD Nodes (9 per model)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                               │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  conversation_sessions                                       │  │
│  │  ----------------------------------------------------------- │  │
│  │  id, session_id (PK), user_id, outlet_id, language,        │  │
│  │  start_time, end_time, message_count, intents (JSONB),     │  │
│  │  context (JSONB), created_at, updated_at                   │  │
│  │                                                              │  │
│  │  Indexes: session_id (unique), user_id, outlet_id,         │  │
│  │           start_time, created_at                            │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  conversation_messages                                       │  │
│  │  ----------------------------------------------------------- │  │
│  │  id, session_id (FK), role, content (TEXT), language,      │  │
│  │  intent, confidence, context (JSONB), pii_scrubbed,        │  │
│  │  embedding_vector, timestamp, created_at                   │  │
│  │                                                              │  │
│  │  Indexes: session_id, timestamp, role, intent, created_at  │  │
│  │  Retention: 90 days (auto-cleanup)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  user_interaction_summaries                                  │  │
│  │  ----------------------------------------------------------- │  │
│  │  id, user_id (PK), outlet_id, total_conversations,         │  │
│  │  total_messages, common_intents (JSONB),                   │  │
│  │  preferred_language, avg_satisfaction, last_interaction,   │  │
│  │  first_interaction, metadata (JSONB), created_at,          │  │
│  │  updated_at                                                 │  │
│  │                                                              │  │
│  │  Indexes: user_id (unique), outlet_id, last_interaction,   │  │
│  │           created_at                                        │  │
│  │  Retention: 2 years (730 days)                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow: WhatsApp Order Processing with Conversation Memory

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. WhatsApp Message Received                                        │
│    User: "Hi, we need 400 boxes for 10 inch pizzas"                │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. Create Conversation Session                                      │
│    ┌──────────────────────────────────────────────────────────┐    │
│    │ ConversationSessionCreateNode                            │    │
│    │ {                                                        │    │
│    │   session_id: uuid4(),                                   │    │
│    │   user_id: "6591234567",                                 │    │
│    │   outlet_id: 1,                                          │    │
│    │   language: "en",                                        │    │
│    │   start_time: now(),                                     │    │
│    │   intents: {primary: "order", confidence: 0.95}         │    │
│    │ }                                                        │    │
│    └──────────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. Log User Message                                                 │
│    ┌──────────────────────────────────────────────────────────┐    │
│    │ ConversationMessageCreateNode                            │    │
│    │ {                                                        │    │
│    │   session_id: session_id,                                │    │
│    │   role: "user",                                          │    │
│    │   content: "Hi, we need 400 boxes...",                   │    │
│    │   intent: "order_placement",                             │    │
│    │   confidence: 0.95,                                      │    │
│    │   timestamp: now()                                       │    │
│    │ }                                                        │    │
│    └──────────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. Process Order (Existing Logic)                                   │
│    • Semantic product search                                        │
│    • GPT-4 parsing                                                  │
│    • Order creation                                                 │
│    • Delivery scheduling                                            │
│    • Invoice generation                                             │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. Log Assistant Response                                           │
│    ┌──────────────────────────────────────────────────────────┐    │
│    │ ConversationMessageCreateNode                            │    │
│    │ {                                                        │    │
│    │   session_id: session_id,                                │    │
│    │   role: "assistant",                                     │    │
│    │   content: "Order processed. 400 boxes confirmed.",      │    │
│    │   intent: "order_confirmation",                          │    │
│    │   confidence: 1.0,                                       │    │
│    │   timestamp: now()                                       │    │
│    │ }                                                        │    │
│    └──────────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. Update User Analytics                                            │
│    ┌──────────────────────────────────────────────────────────┐    │
│    │ UserInteractionSummaryUpdateNode (or Create if new)      │    │
│    │ {                                                        │    │
│    │   user_id: "6591234567",                                 │    │
│    │   total_conversations: previous + 1,                     │    │
│    │   total_messages: previous + 2,                          │    │
│    │   last_interaction: now(),                               │    │
│    │   common_intents: {order_placement: count + 1}          │    │
│    │ }                                                        │    │
│    └──────────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. Send Response to WhatsApp                                        │
│    "Order processed! 400 x 10-inch pizza boxes confirmed."         │
└─────────────────────────────────────────────────────────────────────┘
```

## Node Generation Pattern

Each DataFlow model automatically generates 9 CRUD nodes:

```
@db.model
class ConversationSession:
    session_id: str
    user_id: str
    # ... other fields

    ↓ DataFlow Auto-Generation ↓

┌─────────────────────────────────────────────────────────────────────┐
│ Generated Nodes (9 per model)                                       │
├─────────────────────────────────────────────────────────────────────┤
│ 1. ConversationSessionCreateNode      → Create single record        │
│ 2. ConversationSessionReadNode        → Read by ID                  │
│ 3. ConversationSessionUpdateNode      → Update by ID                │
│ 4. ConversationSessionDeleteNode      → Delete by ID                │
│ 5. ConversationSessionListNode        → Query with filters          │
│ 6. ConversationSessionCountNode       → Count matching records      │
│ 7. ConversationSessionExistsNode      → Check existence             │
│ 8. ConversationSessionBulkCreateNode  → Batch insert                │
│ 9. ConversationSessionBulkUpdateNode  → Batch update                │
└─────────────────────────────────────────────────────────────────────┘
```

## Query Pattern Examples

### 1. Session Timeline Query
```python
workflow.add_node("ConversationSessionListNode", "timeline", {
    "filters": {
        "user_id": "6591234567",
        "start_time": {
            "$gte": "2025-01-01T00:00:00",
            "$lt": "2025-02-01T00:00:00"
        }
    },
    "order_by": ["-start_time"],
    "limit": 50
})
```

### 2. Message History Query
```python
workflow.add_node("ConversationMessageListNode", "history", {
    "filters": {
        "session_id": "session-uuid",
        "role": "user"  # Only user messages
    },
    "order_by": ["timestamp"]
})
```

### 3. User Analytics Query
```python
workflow.add_node("UserInteractionSummaryListNode", "top_users", {
    "filters": {
        "total_conversations": {"$gte": 10}
    },
    "order_by": ["-total_conversations"],
    "limit": 100
})
```

### 4. Intent Analysis Query
```python
workflow.add_node("ConversationMessageListNode", "orders", {
    "filters": {
        "intent": "order_placement",
        "confidence": {"$gte": 0.8}
    }
})
```

## Data Retention Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│ Conversation Data Lifecycle                                         │
└─────────────────────────────────────────────────────────────────────┘

Day 0-90: Full Message History
├── conversation_messages (all fields)
├── Full text content
├── PII data (if not scrubbed)
└── Used for: Recent conversation context, customer service

Day 91+: Message Purge
├── conversation_messages → DELETED
└── retention_policy triggers automatic cleanup

Day 0-730: User Analytics
├── user_interaction_summaries (active)
├── Aggregated data only (no PII)
├── Intent statistics
└── Used for: Long-term analytics, personalization

Day 731+: Summary Archive
├── user_interaction_summaries → DELETED
└── Can export to cold storage before deletion

Perpetual: Session Metadata
├── conversation_sessions (retained)
├── Metadata only (no message content)
├── Used for: Session tracking, audit logs
└── Manual cleanup via workflows
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────────────┐
│ External System Integration                                         │
└─────────────────────────────────────────────────────────────────────┘

WhatsApp API
    ↓ incoming message
    ↓
ConversationSessionCreateNode
ConversationMessageCreateNode (role: user)
    ↓
GPT-4 API (order parsing)
    ↓
Product Database (semantic search)
    ↓
OrderCreateNode (existing model)
    ↓
ConversationMessageCreateNode (role: assistant)
UserInteractionSummaryUpdateNode
    ↓
WhatsApp API (send response)
```

## Performance Characteristics

### Index Strategy
```
conversation_sessions:
  - session_id (UNIQUE B-tree) → O(log n) lookup
  - user_id (B-tree) → O(log n) user sessions
  - outlet_id (B-tree) → O(log n) outlet sessions
  - start_time (B-tree) → O(log n) time range queries
  - created_at (B-tree) → O(log n) chronological queries

conversation_messages:
  - session_id (B-tree) → O(log n) session messages
  - timestamp (B-tree) → O(log n) time-ordered retrieval
  - role (B-tree) → O(log n) role-based filtering
  - intent (B-tree) → O(log n) intent analysis
  - created_at (B-tree) → O(log n) retention queries

user_interaction_summaries:
  - user_id (UNIQUE B-tree) → O(log n) user lookup
  - outlet_id (B-tree) → O(log n) outlet analytics
  - last_interaction (B-tree) → O(log n) activity queries
  - created_at (B-tree) → O(log n) cohort analysis
```

### Query Performance Estimates
- Single session lookup: <5ms
- User message history (100 msgs): <20ms
- Analytics aggregation (1000 users): <100ms
- Bulk insert (1000 messages): <500ms

## Security & Privacy

```
┌─────────────────────────────────────────────────────────────────────┐
│ PII Protection Strategy                                             │
└─────────────────────────────────────────────────────────────────────┘

1. Collection Phase
   ├── Original message stored with pii_scrubbed=False
   └── User ID anonymized (hash or pseudonym)

2. Processing Phase (within 24 hours)
   ├── Run PII detection workflow
   ├── Scrub phone numbers, addresses, emails
   ├── Update pii_scrubbed=True
   └── Log scrubbing event in context

3. Retention Phase
   ├── 90-day countdown from created_at
   ├── Automatic deletion via retention_policy
   └── Only aggregated data remains in summaries

4. GDPR Compliance
   ├── Right to access: ConversationMessageListNode
   ├── Right to erasure: ConversationMessageDeleteNode
   └── Right to export: Generate PDF/CSV from ListNode
```

## Monitoring & Alerting

```
Key Metrics to Track:

1. Volume Metrics
   - Sessions per day
   - Messages per session
   - Active users

2. Performance Metrics
   - Average query latency
   - Database connection pool usage
   - Index hit rates

3. Data Health Metrics
   - Retention compliance (messages >90 days)
   - PII scrubbing completion rate
   - Orphaned sessions (no messages)

4. Business Metrics
   - Intent distribution
   - User satisfaction trends
   - Language preferences
```

## Future Enhancements

```
Phase 2: Semantic Search
├── Use embedding_vector field
├── Store OpenAI embeddings
└── Enable similarity search for FAQs

Phase 3: Real-time Analytics
├── Streaming aggregation
├── Live dashboards
└── Anomaly detection

Phase 4: Multi-language Support
├── Automatic language detection
├── Translation services
└── Cross-language analytics

Phase 5: Sentiment Analysis
├── Message sentiment scoring
├── Satisfaction prediction
└── Escalation triggers
```

## Architecture Principles

1. **No Mocking**: All database operations use real PostgreSQL
2. **Auto-generation**: 27 CRUD nodes generated automatically by DataFlow
3. **Zero Config**: Auto-migration creates tables on startup
4. **Type Safety**: Full type hints throughout Python code
5. **Scalability**: Indexed tables, bulk operations, JSONB flexibility
6. **Privacy-First**: Built-in retention policies, PII scrubbing support
7. **Observability**: Context tracking, intent logging, analytics ready

---

**Last Updated**: 2025-10-18
**Architecture Version**: 1.0
**DataFlow Version**: v0.4.6+
