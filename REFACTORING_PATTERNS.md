# Kailash to SQLAlchemy Refactoring Patterns

Quick reference for converting remaining workflow patterns to direct database operations.

## Pattern 1: List/Query Records

### Before (Kailash Workflow)
```python
workflow = WorkflowBuilder()
workflow.add_node("OutletListNode", "list_outlets", {
    "filters": {"name": "Canadian Pizza"},
    "limit": 100
})
results, _ = runtime.execute(workflow.build())
outlet_data = results.get('list_outlets', [])

# Complex extraction logic
outlets = []
if isinstance(outlet_data, list) and len(outlet_data) > 0:
    if isinstance(outlet_data[0], dict) and 'records' in outlet_data[0]:
        outlets = outlet_data[0]['records']
    elif isinstance(outlet_data[0], dict):
        outlets = [outlet_data[0]]
```

### After (Direct SQLAlchemy)
```python
with get_db_session() as session:
    outlets = list_outlets(session, limit=100, filters={"name": "Canadian Pizza"})
```

---

## Pattern 2: Get Single Record by ID

### Before (Kailash Workflow)
```python
workflow = WorkflowBuilder()
workflow.add_node("OutletReadNode", "get_outlet", {
    "filters": {"id": outlet_id},
    "limit": 1
})
results, _ = runtime.execute(workflow.build())
outlet_data = results.get('get_outlet', [])

# Extraction
outlet = None
if isinstance(outlet_data, list) and len(outlet_data) > 0:
    outlet = outlet_data[0]
```

### After (Direct SQLAlchemy)
```python
with get_db_session() as session:
    outlet = get_outlet_by_id(session, outlet_id)
```

---

## Pattern 3: Create Record

### Before (Kailash Workflow)
```python
workflow = WorkflowBuilder()
workflow.add_node("OrderCreateNode", "create_order", {
    "outlet_id": outlet_id,
    "whatsapp_message": message,
    "parsed_items": items,
    "total_amount": total,
    "status": "pending"
})
results, _ = runtime.execute(workflow.build())
order_data = results.get('create_order', {})

# Handle result format
if isinstance(order_data, dict) and 'record' in order_data:
    created_order = order_data['record']
elif isinstance(order_data, dict):
    created_order = order_data
```

### After (Direct SQLAlchemy)
```python
with get_db_session() as session:
    created_order = create_order(session, {
        "outlet_id": outlet_id,
        "whatsapp_message": message,
        "parsed_items": items,
        "total_amount": total,
        "status": "pending"
    })
```

---

## Pattern 4: Query with Filters

### Before (Kailash Workflow)
```python
workflow = WorkflowBuilder()
workflow.add_node("ProductListNode", "find_products", {
    "filters": {
        "category": "boxes",
        "is_active": True
    },
    "limit": 50
})
results, _ = runtime.execute(workflow.build())
products = results.get('find_products', [])
```

### After (Direct SQLAlchemy)
```python
with get_db_session() as session:
    products = list_products(session, limit=50, filters={
        "category": "boxes",
        "is_active": True
    })
```

---

## Pattern 5: LLM Agent Node (Special Case)

### Before (Kailash Workflow)
```python
workflow = WorkflowBuilder()
workflow.add_node("LLMAgentNode", "parse_order", {
    "model": "gpt-4",
    "system_prompt": system_prompt,
    "user_prompt": user_message,
    "response_format": "json"
})
results, _ = runtime.execute(workflow.build())
parsed_result = results.get('parse_order', {})
```

### After (Direct OpenAI API)
```python
from openai import OpenAI
import json

client = OpenAI(api_key=config.OPENAI_API_KEY)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    response_format={"type": "json_object"}
)

parsed_result = json.loads(response.choices[0].message.content)
```

---

## Available Helper Functions

Located in `src/database_operations.py`:

### Outlets
- `list_outlets(session, limit=100, filters=None)` → List[Dict]
- `get_outlet_by_id(session, outlet_id)` → Optional[Dict]
- `get_outlet_by_name(session, name)` → Optional[Dict]

### Products
- `list_products(session, limit=100, filters=None)` → List[Dict]
- `get_product_by_sku(session, sku)` → Optional[Dict]

### Orders
- `create_order(session, order_data)` → Dict
- `get_order_by_id(session, order_id)` → Optional[Dict]
- `list_orders(session, limit=100, filters=None)` → List[Dict]

### Conversations
- `get_conversation_session(session, session_id)` → Optional[Dict]
- `get_conversation_messages(session, session_id, limit=10, role_filter=None)` → List[Dict]

---

## Common Issues & Solutions

### Issue 1: "RuntimeError: No active session"
**Cause**: Trying to use session outside `with` block

**Solution**:
```python
# Wrong
session = get_db_session()
outlets = list_outlets(session)  # Error!

# Right
with get_db_session() as session:
    outlets = list_outlets(session)  # Works!
```

### Issue 2: "AttributeError: 'dict' object has no attribute 'id'"
**Cause**: ORM models return dictionaries, not objects

**Solution**:
```python
# Wrong
outlet = get_outlet_by_id(session, 1)
print(outlet.id)  # Error!

# Right
outlet = get_outlet_by_id(session, 1)
print(outlet['id'])  # Works!
print(outlet.get('id'))  # Even safer!
```

### Issue 3: Decimal serialization in JSON responses
**Cause**: `Decimal` objects not JSON serializable

**Solution**: Models already have `.to_dict()` that converts Decimal to float:
```python
order = get_order_by_id(session, 1)
# order['total_amount'] is already a float, not Decimal
```

---

## Step-by-Step Refactoring Checklist

For each workflow usage:

1. [ ] Identify the workflow node type (OutletListNode, OrderCreateNode, etc.)
2. [ ] Find corresponding helper function in `database_operations.py`
3. [ ] Wrap in `with get_db_session() as session:` block
4. [ ] Replace workflow call with helper function
5. [ ] Remove complex result extraction logic
6. [ ] Test the endpoint/function
7. [ ] Remove timeout wrapper if present

---

## Example: Full Endpoint Refactoring

### Before: `/api/orders/{order_id}` endpoint

```python
@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    if not db or not runtime:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        workflow = WorkflowBuilder()
        workflow.add_node("OrderReadNode", "get_order", {
            "filters": {"id": order_id},
            "limit": 1
        })

        results, _ = execute_with_timeout(
            runtime.execute,
            args=(workflow.build(),),
            timeout_seconds=60
        )
        order_data = results.get('get_order', [])

        # Complex extraction
        order = None
        if isinstance(order_data, list) and len(order_data) > 0:
            if isinstance(order_data[0], dict) and 'records' in order_data[0]:
                records = order_data[0]['records']
                order = records[0] if len(records) > 0 else None
            elif isinstance(order_data[0], dict):
                order = order_data[0]

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return {"order": order}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### After: Simplified with SQLAlchemy

```python
@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    try:
        with get_db_session() as session:
            order = get_order_by_id(session, order_id)

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        return {"order": order}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Reduction**: 35 lines → 12 lines (66% reduction)

---

## Testing After Refactoring

### Unit Test Example
```python
def test_get_outlet_by_id():
    from database_operations import get_db_session, get_outlet_by_id

    with get_db_session() as session:
        outlet = get_outlet_by_id(session, 1)

    assert outlet is not None
    assert outlet['id'] == 1
    assert 'name' in outlet
```

### Integration Test Example
```python
def test_outlet_endpoint():
    response = client.get("/api/outlets")
    assert response.status_code == 200
    data = response.json()
    assert 'outlets' in data
    assert data['count'] > 0
```

---

*Quick Reference - Keep this open while refactoring!*
