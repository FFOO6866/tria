# Conversation Memory Quick Reference

## 🚀 Quick Start

### Initialization (Already Done in enhanced_api.py)

```python
from dataflow import DataFlow
from models.conversation_models import initialize_conversation_models

db = DataFlow(database_url="postgresql://...", auto_migrate=True)
initialize_conversation_models(db)
```

## 📊 Three Models = 27 Auto-Generated Nodes

### ConversationSession (9 nodes)
Track conversation sessions with outlets

### ConversationMessage (9 nodes)
Store individual messages within sessions

### UserInteractionSummary (9 nodes)
Aggregate user analytics and profiling

## 🔧 Common Operations

### 1. Start a New Conversation Session

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
    "intents": {"primary": "order_placement", "confidence": 0.95},
    "context": {"channel": "whatsapp"}
})

runtime = LocalRuntime()
results, _ = runtime.execute(workflow.build())
```

### 2. Log User Message

```python
workflow = WorkflowBuilder()
workflow.add_node("ConversationMessageCreateNode", "log_user_msg", {
    "session_id": session_id,
    "role": "user",
    "content": "Hi, we need 400 boxes for 10 inch pizzas",
    "language": "en",
    "intent": "order_placement",
    "confidence": 0.95,
    "timestamp": datetime.now()
})

results, _ = runtime.execute(workflow.build())
```

### 3. Log Assistant Response

```python
workflow = WorkflowBuilder()
workflow.add_node("ConversationMessageCreateNode", "log_assistant_msg", {
    "session_id": session_id,
    "role": "assistant",
    "content": "I understand you need 400 boxes. Processing...",
    "language": "en",
    "intent": "acknowledgment",
    "confidence": 1.0,
    "timestamp": datetime.now()
})

results, _ = runtime.execute(workflow.build())
```

### 4. Get Conversation History

```python
workflow = WorkflowBuilder()
workflow.add_node("ConversationMessageListNode", "get_history", {
    "filters": {"session_id": session_id},
    "order_by": ["timestamp"],
    "limit": 100
})

results, _ = runtime.execute(workflow.build())
messages = results.get('get_history', [])[0]['records']  # Extract records
```

### 5. Update User Analytics

```python
workflow = WorkflowBuilder()

# Check if user exists
workflow.add_node("UserInteractionSummaryListNode", "check_user", {
    "filters": {"user_id": user_id},
    "limit": 1
})

results, _ = runtime.execute(workflow.build())
user_data = results.get('check_user', [])[0].get('records', [])

if user_data:
    # Update existing
    workflow2 = WorkflowBuilder()
    workflow2.add_node("UserInteractionSummaryUpdateNode", "update", {
        "id": user_data[0]['id'],
        "total_conversations": user_data[0]['total_conversations'] + 1,
        "last_interaction": datetime.now()
    })
    runtime.execute(workflow2.build())
else:
    # Create new
    workflow2 = WorkflowBuilder()
    workflow2.add_node("UserInteractionSummaryCreateNode", "create", {
        "user_id": user_id,
        "total_conversations": 1,
        "total_messages": 3,
        "preferred_language": "en",
        "first_interaction": datetime.now()
    })
    runtime.execute(workflow2.build())
```

### 6. Analytics - Sessions Today

```python
from datetime import datetime

workflow = WorkflowBuilder()
workflow.add_node("ConversationSessionListNode", "today_sessions", {
    "filters": {
        "created_at": {
            "$gte": datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        }
    }
})

results, _ = runtime.execute(workflow.build())
count = len(results.get('today_sessions', [])[0].get('records', []))
```

## 🎯 Complete WhatsApp Integration Example

```python
def handle_whatsapp_message(user_id: str, message: str, outlet_id: int):
    """Complete conversation memory integration"""

    # 1. Create session
    session_id = str(uuid.uuid4())
    session_workflow = WorkflowBuilder()
    session_workflow.add_node("ConversationSessionCreateNode", "create", {
        "session_id": session_id,
        "user_id": user_id,
        "outlet_id": outlet_id,
        "language": "en",
        "start_time": datetime.now(),
        "intents": {"primary": "order_placement"},
        "context": {"channel": "whatsapp"}
    })
    runtime.execute(session_workflow.build())

    # 2. Log user message
    msg_workflow = WorkflowBuilder()
    msg_workflow.add_node("ConversationMessageCreateNode", "log_user", {
        "session_id": session_id,
        "role": "user",
        "content": message,
        "language": "en",
        "timestamp": datetime.now()
    })
    runtime.execute(msg_workflow.build())

    # 3. Process order (your existing logic)
    response = process_order(message)

    # 4. Log assistant response
    resp_workflow = WorkflowBuilder()
    resp_workflow.add_node("ConversationMessageCreateNode", "log_assistant", {
        "session_id": session_id,
        "role": "assistant",
        "content": response,
        "language": "en",
        "timestamp": datetime.now()
    })
    runtime.execute(resp_workflow.build())

    # 5. Update user summary
    update_user_summary(user_id, session_id)

    return response
```

## 📋 Field Reference

### ConversationSession Fields
```python
{
    "session_id": str,              # Required - UUID
    "user_id": str,                 # Optional - WhatsApp ID
    "outlet_id": int,               # Optional - FK to Outlet
    "language": str,                # Default: "en"
    "start_time": datetime,         # Required
    "end_time": datetime,           # Optional
    "message_count": int,           # Default: 0
    "intents": dict,                # JSON - {"primary": "order", "confidence": 0.95}
    "context": dict,                # JSON - {"channel": "whatsapp"}
    "created_at": datetime,         # Auto
    "updated_at": datetime          # Auto
}
```

### ConversationMessage Fields
```python
{
    "session_id": str,              # Required - FK to Session
    "role": str,                    # Required - "user" or "assistant"
    "content": str,                 # Required - Message text
    "language": str,                # Default: "en"
    "intent": str,                  # Optional - "order_placement"
    "confidence": float,            # Default: 0.0
    "context": dict,                # JSON - message metadata
    "pii_scrubbed": bool,           # Default: False
    "embedding_vector": str,        # Optional - for semantic search
    "timestamp": datetime,          # Required
    "created_at": datetime          # Auto
}
```

### UserInteractionSummary Fields
```python
{
    "user_id": str,                 # Required - Unique WhatsApp ID
    "outlet_id": int,               # Optional - FK to Outlet
    "total_conversations": int,     # Default: 0
    "total_messages": int,          # Default: 0
    "common_intents": dict,         # JSON - {"order": 10, "inquiry": 5}
    "preferred_language": str,      # Default: "en"
    "avg_satisfaction": float,      # Default: 0.0
    "last_interaction": datetime,   # Optional
    "first_interaction": datetime,  # Optional
    "metadata": dict,               # JSON - additional data
    "created_at": datetime,         # Auto
    "updated_at": datetime          # Auto
}
```

## 🔍 MongoDB-Style Query Filters

All ListNodes support MongoDB-style filters:

```python
# Greater than
{"created_at": {"$gt": datetime.now()}}

# Less than
{"created_at": {"$lt": cutoff_date}}

# In list
{"language": {"$in": ["en", "zh", "ms"]}}

# Regex match
{"content": {"$regex": "pizza"}}

# AND conditions (implicit)
{"language": "en", "role": "user"}
```

## ⏰ Data Retention

- **ConversationMessage**: 90 days (auto-purge configured)
- **UserInteractionSummary**: 2 years (730 days)
- **ConversationSession**: No auto-purge (metadata only)

## 🛠️ Troubleshooting

### Issue: "records not found in result"
```python
# DataFlow returns nested structure
result = results.get('node_id', [])
if isinstance(result, list) and len(result) > 0:
    if 'records' in result[0]:
        data = result[0]['records']  # ✅ CORRECT
```

### Issue: "JSON serialization error"
```python
# DataFlow handles JSON automatically
workflow.add_node("Node", "id", {
    "context": {"key": "value"}  # ✅ Pass dict directly
})
# NOT: "context": json.dumps({"key": "value"})  # ❌ WRONG
```

### Issue: "datetime not JSON serializable"
```python
# Use datetime objects directly
workflow.add_node("Node", "id", {
    "timestamp": datetime.now()  # ✅ CORRECT
})
# NOT: "timestamp": datetime.now().isoformat()  # ❌ WRONG
```

## 📚 Full Documentation

See `docs/conversation_memory_system.md` for complete documentation.

## 🧪 Testing

Run example:
```bash
python examples/conversation_memory_example.py
```

## 🎓 Key Takeaways

1. **27 nodes auto-generated** - No manual CRUD implementation needed
2. **Real PostgreSQL** - No mocking, production-ready
3. **JSONB fields** - Flexible schema for context/metadata
4. **Auto-migration** - Tables created automatically
5. **MongoDB filters** - Powerful query capabilities
6. **90-day retention** - Automatic PII cleanup
7. **Built on DataFlow** - Full Kailash SDK integration
