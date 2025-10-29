# Existing Agent-to-Agent (A2A) Framework Analysis
**TRIA AI-BPO Order Processing System**

**Date:** 2025-10-18
**Version:** 1.0
**Status:** Documentation Complete
**Purpose:** Analyze existing multi-agent orchestration for RAG, memory, and A2A extension planning

---

## Executive Summary

The TRIA AI-BPO system implements a **functional multi-agent orchestration pattern** in `enhanced_api.py` where 5 specialized agents collaborate to process WhatsApp orders through a sequential pipeline. The current implementation is **stateless, synchronous, and focused on order processing** with semantic product search via OpenAI embeddings.

**Key Findings:**
- ✅ Working 5-agent orchestration (Customer Service → Operations → Inventory → Delivery → Finance)
- ✅ Real-time data flow via `agent_timeline` tracking mechanism
- ✅ Semantic search foundation (product embeddings in PostgreSQL)
- ✅ Kailash WorkflowBuilder + LocalRuntime pattern established
- ✅ DataFlow CRUD nodes (45 auto-generated nodes from 5 models)
- ⚠️ **NO conversation memory** - each request is isolated
- ⚠️ **NO knowledge base** - policies/FAQs not integrated (RAG module exists but not used)
- ⚠️ **NO A2A status queries** - agents don't communicate bidirectionally
- ⚠️ **NO state persistence** - agents reconstruct context on every call

**Extension Readiness:** The architecture is well-positioned for RAG, conversation memory, and A2A enhancements without requiring major refactoring.

---

## 1. Current Architecture Overview

### 1.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         TRIA AI-BPO Platform                          │
│                         (FastAPI + Kailash SDK)                       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      ENHANCED_API.PY (Main Orchestrator)              │
│                                                                        │
│  POST /api/process_order_enhanced(request: OrderRequest)             │
│      │                                                                 │
│      ├─► agent_timeline: List[AgentStatus] = []                      │
│      │                                                                 │
│      └─► Sequential Agent Pipeline:                                  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ AGENT 1: Customer Service Agent (Lines 228-461)             │    │
│  │                                                               │    │
│  │ 🧠 Responsibilities:                                          │    │
│  │   • Semantic product search (OpenAI embeddings)              │    │
│  │   • GPT-4 order parsing with catalog-aware prompt            │    │
│  │   • Extract: outlet_name, line_items, is_urgent              │    │
│  │                                                               │    │
│  │ 🔧 Technologies:                                              │    │
│  │   • semantic_product_search() → PostgreSQL vector search     │    │
│  │   • LLMAgentNode (Kailash) → GPT-4 API                       │    │
│  │   • extract_json_from_llm_response()                         │    │
│  │                                                               │    │
│  │ 📤 Output:                                                    │    │
│  │   parsed_order = {                                           │    │
│  │     "outlet_name": str,                                      │    │
│  │     "line_items": [                                          │    │
│  │       {"sku": str, "description": str, "quantity": int,      │    │
│  │        "uom": str}                                           │    │
│  │     ],                                                        │    │
│  │     "is_urgent": bool                                        │    │
│  │   }                                                           │    │
│  │                                                               │    │
│  │ 📊 AgentStatus Details:                                       │    │
│  │   • Semantic search results (top 10 products)                │    │
│  │   • GPT-4 matched items with SKUs                            │    │
│  │   • Processing time (typically 2-4 seconds)                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             │                                         │
│                             │ parsed_order (Dict)                     │
│                             ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ AGENT 2: Operations Orchestrator (Lines 466-496)            │    │
│  │                                                               │    │
│  │ 🧠 Responsibilities:                                          │    │
│  │   • Validate order completeness                              │    │
│  │   • Calculate total items (sum of quantities)                │    │
│  │   • Classify order size (large if >1000 items)               │    │
│  │   • Route to downstream agents                               │    │
│  │                                                               │    │
│  │ 📤 Output:                                                    │    │
│  │   • total_items: int                                         │    │
│  │   • is_large_order: bool                                     │    │
│  │   • Delegation signals to Inventory, Delivery, Finance       │    │
│  │                                                               │    │
│  │ 📊 AgentStatus Details:                                       │    │
│  │   • Total items count                                        │    │
│  │   • Order classification (Standard/LARGE ORDER)              │    │
│  │   • Priority level (Normal/HIGH if urgent)                   │    │
│  │   • Delegated tasks list                                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             │                                         │
│                             │ line_items + is_large_order             │
│                             ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ AGENT 3: Inventory Manager (Lines 501-547)                  │    │
│  │                                                               │    │
│  │ 🧠 Responsibilities:                                          │    │
│  │   • Load Master_Inventory_File_2025.xlsx                     │    │
│  │   • Verify stock availability (from products_map)            │    │
│  │   • Check stock vs. requested quantity                       │    │
│  │   • Reference DO_Template.xlsx for delivery prep            │    │
│  │                                                               │    │
│  │ 🔧 Technologies:                                              │    │
│  │   • pandas.read_excel() for inventory Excel                  │    │
│  │   • products_map (from semantic search) for stock checks     │    │
│  │                                                               │    │
│  │ 📤 Output:                                                    │    │
│  │   • Stock verification results per SKU                       │    │
│  │   • Availability status (✓ Available / ⚠ Low stock)          │    │
│  │                                                               │    │
│  │ 📊 AgentStatus Details:                                       │    │
│  │   • Excel file loaded (rows count)                           │    │
│  │   • Per-item stock status                                    │    │
│  │   • DO template reference                                    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             │                                         │
│                             │ stock_details                           │
│                             ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ AGENT 4: Delivery Coordinator (Lines 552-574)               │    │
│  │                                                               │    │
│  │ 🧠 Responsibilities:                                          │    │
│  │   • Calculate delivery date (next day or same-day if urgent) │    │
│  │   • Determine time slot (09:00-12:00 or URGENT)              │    │
│  │   • Optimize delivery route                                  │    │
│  │   • Auto-assign driver                                       │    │
│  │                                                               │    │
│  │ 📤 Output:                                                    │    │
│  │   • delivery_date: datetime                                  │    │
│  │   • time_slot: str                                           │    │
│  │   • route: str                                               │    │
│  │                                                               │    │
│  │ 📊 AgentStatus Details:                                       │    │
│  │   • Scheduled delivery date                                  │    │
│  │   • Time slot allocation                                     │    │
│  │   • Route plan                                               │    │
│  │   • Driver assignment status                                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             │                                         │
│                             │ delivery_date                           │
│                             ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ AGENT 5: Finance Controller (Lines 579-630)                 │    │
│  │                                                               │    │
│  │ 🧠 Responsibilities:                                          │    │
│  │   • Calculate pricing from product catalog                   │    │
│  │   • Apply tax (8% GST from env var)                          │    │
│  │   • Generate invoice number                                  │    │
│  │   • Post to Xero API (if configured)                         │    │
│  │                                                               │    │
│  │ 🔧 Technologies:                                              │    │
│  │   • calculate_order_total() using Decimal precision          │    │
│  │   • products_map for unit prices                             │    │
│  │   • Xero API integration (optional)                          │    │
│  │                                                               │    │
│  │ 📤 Output:                                                    │    │
│  │   • subtotal, tax, total (Decimal)                           │    │
│  │   • invoice_number: str                                      │    │
│  │   • xero_status: str (if posted)                             │    │
│  │                                                               │    │
│  │ 📊 AgentStatus Details:                                       │    │
│  │   • Per-line-item pricing breakdown                          │    │
│  │   • Subtotal, tax, total                                     │    │
│  │   • Invoice number generated                                 │    │
│  │   • Xero posting status                                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                             │                                         │
│                             │ totals                                  │
│                             ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ DATABASE PERSISTENCE (Lines 636-716)                         │    │
│  │                                                               │    │
│  │ 🔧 Kailash DataFlow Operations:                               │    │
│  │   1. OutletListNode → Find/create outlet                     │    │
│  │   2. OrderCreateNode → Create order record                   │    │
│  │                                                               │    │
│  │ 📤 Final Output:                                              │    │
│  │   • order_id: int (database ID)                              │    │
│  │   • run_id: str (workflow execution ID)                      │    │
│  │   • agent_timeline: List[AgentStatus] (5 agents)             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                   OrderResponse returned to API caller
```

### 1.2 Agent Communication Flow

**Current Pattern: SEQUENTIAL PIPELINE (Top-Down)**

```
Request (WhatsApp message)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Agent 1: Customer Service                                        │
│ Input: whatsapp_message, outlet_name (optional)                 │
│ Output: parsed_order = {outlet_name, line_items, is_urgent}     │
│ Data Passed: parsed_order, products_map, relevant_products      │
└─────────────────────────────────────────────────────────────────┘
    │
    │ parsed_order (in-memory Dict)
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Agent 2: Operations Orchestrator                                │
│ Input: parsed_order (from Agent 1)                              │
│ Output: total_items, is_large_order                             │
│ Data Passed: line_items, total_items, is_large_order            │
└─────────────────────────────────────────────────────────────────┘
    │
    │ line_items + classification
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Agent 3: Inventory Manager                                      │
│ Input: line_items, products_map (from Agent 1)                  │
│ Output: stock_details (availability per SKU)                    │
│ Data Passed: stock_details                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    │ stock verification results
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Agent 4: Delivery Coordinator                                   │
│ Input: parsed_order.is_urgent, outlet_name                      │
│ Output: delivery_date, time_slot, route                         │
│ Data Passed: delivery_date                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    │ delivery schedule
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ Agent 5: Finance Controller                                     │
│ Input: line_items, products_map                                 │
│ Output: subtotal, tax, total, invoice_number                    │
│ Data Passed: totals                                             │
└─────────────────────────────────────────────────────────────────┘
    │
    │ Complete order data
    ▼
Database Persistence (OrderCreateNode)
    │
    │ order_id
    ▼
API Response (OrderResponse with agent_timeline)
```

**Key Characteristics:**
- **Synchronous**: Each agent executes sequentially (blocking)
- **In-memory data passing**: Variables (`parsed_order`, `line_items`, `products_map`) passed directly
- **No state persistence**: Each request starts fresh (stateless)
- **One-way communication**: Agents don't query each other (no bidirectional A2A)
- **Timeline tracking**: `agent_timeline` accumulates status after each agent completes

---

## 2. Data Models and Structures

### 2.1 AgentStatus Data Model

**Location:** `enhanced_api.py:134-142`

```python
class AgentStatus(BaseModel):
    """Agent status with real data"""
    agent_name: str                     # Agent identifier
    status: str                         # idle, processing, completed, error
    current_task: str                   # Human-readable task description
    details: List[str]                  # Real data points (what agent did)
    progress: int                       # 0-100
    start_time: Optional[float] = None  # Unix timestamp
    end_time: Optional[float] = None    # Unix timestamp
```

**Usage Pattern:**
```python
agent_timeline.append(AgentStatus(
    agent_name="Customer Service Agent",
    status="completed",
    current_task="Parsed order with GPT-4 + Semantic Search",
    details=[
        "Used OpenAI Embeddings API for semantic search",
        "Semantic Search: Found 8 relevant products",
        "  • CNP-014-FB-01: 10-Inch Pizza Box (95.2% match)",
        # ... more details
        "Processing time: 3.24s"
    ],
    progress=100,
    start_time=1729234567.89,
    end_time=1729234571.13
))
```

### 2.2 Order Data Flow

**Core Data Structure: `parsed_order` (Dict)**

Generated by Agent 1 (Customer Service), consumed by all downstream agents:

```python
parsed_order = {
    "outlet_name": str,        # Customer/outlet name
    "line_items": [            # List of ordered items
        {
            "sku": str,        # Product SKU (from catalog)
            "description": str, # Product description
            "quantity": int,    # Ordered quantity
            "uom": str         # Unit of measure (piece, box, pack)
        }
    ],
    "is_urgent": bool          # Urgency flag
}
```

**Data Transformations:**

```
WhatsApp Message (raw text)
    │
    │ semantic_product_search() → relevant_products (List[Dict])
    │ LLMAgentNode (GPT-4) + catalog-aware prompt → JSON extraction
    ▼
parsed_order (Dict)
    │
    │ extract_json_from_llm_response() → validation
    ▼
line_items (List[Dict]) ─┬─► Inventory: stock checks
                         ├─► Delivery: scheduling
                         └─► Finance: pricing
    │
    │ calculate_order_total() → Decimal calculations
    ▼
Database: Order.parsed_items (JSONB field)
```

### 2.3 Database Models (DataFlow)

**Location:** `src/models/dataflow_models.py`

The system uses **DataFlow** auto-generated CRUD nodes (9 nodes per model):

| Model | Purpose | Auto-Generated Nodes |
|-------|---------|---------------------|
| **Product** | Product catalog with SKU, pricing, embeddings | ProductCreate, ProductRead, ProductUpdate, ProductDelete, ProductList, ProductCount, ProductExists, ProductBulkCreate, ProductBulkUpdate |
| **Outlet** | Pizza outlet information | OutletCreate, OutletRead, OutletUpdate, OutletDelete, OutletList, OutletCount, OutletExists, OutletBulkCreate, OutletBulkUpdate |
| **Order** | Customer order record | OrderCreate, OrderRead, OrderUpdate, OrderDelete, OrderList, OrderCount, OrderExists, OrderBulkCreate, OrderBulkUpdate |
| **DeliveryOrder** | Delivery order (DO) record | DeliveryOrderCreate, etc. |
| **Invoice** | Invoice with Xero integration | InvoiceCreate, etc. |

**Total:** 45 auto-generated CRUD nodes available in the system.

**Key Fields:**

```python
# Order model (most important for A2A queries)
@db.model
class Order:
    outlet_id: int                      # FK to Outlet
    whatsapp_message: str               # Original message
    parsed_items: Dict[str, Any]        # JSON: parsed_order structure
    total_amount: Decimal               # Calculated total (SGD)
    status: str                         # pending, processing, completed, failed
    anomaly_detected: bool = False      # Large order flag
    escalated: bool = False             # Manual review needed
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime]
```

---

## 3. Kailash SDK Usage Patterns

### 3.1 WorkflowBuilder Pattern

**Pattern 1: LLMAgentNode for GPT-4 Parsing**

```python
# Location: enhanced_api.py:383-399
parse_workflow = WorkflowBuilder()
parse_workflow.add_node("LLMAgentNode", "parse_order", {
    "provider": "openai",
    "model": os.getenv("OPENAI_MODEL", "gpt-4")
})

parse_results, parse_run_id = runtime.execute(
    parse_workflow.build(),
    parameters={
        "parse_order": {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.whatsapp_message}
            ]
        }
    }
)
```

**Pattern 2: DataFlow CRUD Nodes**

```python
# Location: enhanced_api.py:647-652
outlets_workflow = WorkflowBuilder()
outlets_workflow.add_node("OutletListNode", "find_outlet", {
    "filters": {"name": outlet_name},
    "limit": 1
})

outlet_results, _ = runtime.execute(outlets_workflow.build())
```

**Pattern 3: Multi-Node Workflow (NOT CURRENTLY USED)**

Current implementation creates separate workflows for each operation. Future A2A could use:

```python
# PROPOSED A2A pattern (not in current code):
a2a_workflow = WorkflowBuilder()

# Node 1: Query order
a2a_workflow.add_node("OrderReadNode", "get_order", {"id": order_id})

# Node 2: Query delivery status
a2a_workflow.add_node("DeliveryOrderListNode", "get_delivery", {
    "filters": {"order_id": order_id}
})

# Node 3: Query invoice
a2a_workflow.add_node("InvoiceListNode", "get_invoice", {
    "filters": {"order_id": order_id}
})

# Execute all in single workflow
results, _ = runtime.execute(a2a_workflow.build())

# Access results
order = results['get_order']
delivery = results['get_delivery']
invoice = results['get_invoice']
```

### 3.2 Runtime Execution

**Global Runtime Instance:**
```python
# enhanced_api.py:76
runtime: Optional[LocalRuntime] = None

# Startup initialization:
@app.on_event("startup")
async def startup_event():
    global runtime
    runtime = LocalRuntime()
```

**Execution Pattern:**
```python
results, run_id = runtime.execute(workflow.build())
# ⚠️ CRITICAL: Always call .build() on workflow before executing!
```

---

## 4. Integration Points for Extensions

### 4.1 RAG Knowledge Retrieval Integration Points

#### **Point 1: Enhanced Customer Service Agent** (Lines 228-461)

**Current State:**
- Uses semantic product search for catalog matching
- GPT-4 prompt is manually constructed with catalog section
- NO policy/FAQ knowledge retrieval

**Extension Opportunity:**
```python
# BEFORE (current):
system_prompt = f"""You are an order processing assistant...
{catalog_section}  # Only product catalog
"""

# AFTER (with RAG):
from src.rag import search_knowledge_base

# Retrieve relevant policies
relevant_policies = search_knowledge_base(
    query=request.whatsapp_message,
    collection="policies_en",
    top_n=3
)

policy_context = "\n\n".join([doc for doc in relevant_policies])

system_prompt = f"""You are TRIA's AI customer service assistant...

RELEVANT POLICIES:
{policy_context}

PRODUCT CATALOG:
{catalog_section}

INSTRUCTIONS:
...
"""
```

**Benefits:**
- Answer policy questions ("What's your refund policy?")
- Handle non-order queries ("When do you deliver?")
- Grounded responses from knowledge base

#### **Point 2: New General Query Endpoint**

**Proposed:** `/api/chatbot` endpoint for conversational queries

```python
@app.post("/api/chatbot")
async def chatbot_query(request: ChatbotRequest):
    """
    General conversational endpoint with RAG + conversation memory

    Handles:
    - Policy questions
    - Product inquiries
    - Order status checks (A2A)
    - FAQs
    """
    # 1. Detect intent
    intent = classify_intent(request.message)

    # 2. RAG retrieval (if policy/FAQ question)
    if intent in ['policy_question', 'faq', 'general_inquiry']:
        knowledge = search_knowledge_base(
            query=request.message,
            collection=f"policies_{request.language or 'en'}",
            top_n=5
        )

    # 3. Conversation memory (load context)
    session_context = load_conversation_context(request.session_id)

    # 4. A2A call (if order status query)
    if intent == 'order_status':
        order_data = query_order_status(extract_order_id(request.message))

    # 5. GPT-4 response generation
    response = generate_response(
        message=request.message,
        knowledge=knowledge,
        context=session_context,
        order_data=order_data
    )

    # 6. Save to conversation memory
    save_conversation_turn(request.session_id, request.message, response)

    return ChatbotResponse(response=response)
```

### 4.2 Conversation Memory Integration Points

#### **Point 1: Session Management Middleware**

**Proposed:** Redis + PostgreSQL dual-tier memory

```python
# New module: src/memory/session_manager.py

import redis
from datetime import datetime, timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_or_create_session(user_id: str, outlet_id: Optional[int] = None) -> str:
    """
    Create or retrieve session ID for user

    Returns:
        session_id (UUID format)
    """
    session_key = f"user:{user_id}:active_session"
    session_id = redis_client.get(session_key)

    if not session_id:
        session_id = str(uuid.uuid4())
        redis_client.setex(session_key, 1800, session_id)  # 30 min TTL

        # Initialize session in PostgreSQL
        db.execute("""
            INSERT INTO conversation_sessions
            (session_id, user_id, outlet_id, language, start_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_id, user_id, outlet_id, 'en', datetime.now()))

    return session_id

def load_conversation_context(session_id: str, limit: int = 10) -> List[Dict]:
    """
    Load recent conversation history for context window

    Returns:
        List of messages in chronological order
    """
    # Try Redis first (hot cache)
    cache_key = f"session:{session_id}:history"
    cached = redis_client.lrange(cache_key, 0, limit - 1)

    if cached:
        return [json.loads(msg) for msg in cached]

    # Fallback to PostgreSQL
    messages = db.query("""
        SELECT role, content, timestamp
        FROM conversation_messages
        WHERE session_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """, (session_id, limit))

    return messages[::-1]  # Chronological order

def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_response: str,
    intent: Optional[str] = None
):
    """
    Save conversation turn to both Redis and PostgreSQL
    """
    timestamp = datetime.now()

    # Save user message
    msg_user = {
        "role": "user",
        "content": user_message,
        "timestamp": timestamp.isoformat()
    }

    # Save assistant response
    msg_assistant = {
        "role": "assistant",
        "content": assistant_response,
        "timestamp": timestamp.isoformat()
    }

    # Redis (hot cache, TTL 30 min)
    cache_key = f"session:{session_id}:history"
    redis_client.lpush(cache_key, json.dumps(msg_user))
    redis_client.lpush(cache_key, json.dumps(msg_assistant))
    redis_client.expire(cache_key, 1800)

    # PostgreSQL (persistent storage)
    db.execute("""
        INSERT INTO conversation_messages (session_id, role, content, intent, timestamp)
        VALUES
            (%s, 'user', %s, %s, %s),
            (%s, 'assistant', %s, NULL, %s)
    """, (session_id, user_message, intent, timestamp,
          session_id, assistant_response, timestamp))
```

#### **Point 2: Enhanced Order Endpoint with Memory**

**Modification to `process_order_enhanced`:**

```python
@app.post("/api/process_order_enhanced", response_model=OrderResponse)
async def process_order_enhanced(request: OrderRequest):
    # NEW: Session management
    session_id = get_or_create_session(
        user_id=request.user_id or "anonymous",
        outlet_id=None  # Will be set after outlet resolution
    )

    # NEW: Load conversation context (for context-aware parsing)
    conversation_context = load_conversation_context(session_id, limit=5)

    # EXISTING: Agent 1 processing...
    # (semantic search, GPT-4 parsing)

    # NEW: Save conversation turn
    save_conversation_turn(
        session_id=session_id,
        user_message=request.whatsapp_message,
        assistant_response=f"Order #{created_order_id} processed successfully",
        intent="order_placement"
    )

    # EXISTING: Return response...
```

### 4.3 A2A Status Query Integration Points

#### **Point 1: New A2A Orchestration Endpoint**

```python
@app.post("/api/a2a/query_order_status")
async def a2a_query_order_status(order_id: int):
    """
    A2A endpoint for querying complete order status

    Calls:
    - Operations Agent (order details)
    - Inventory Agent (stock info)
    - Delivery Agent (delivery status)
    - Finance Agent (invoice status)
    """
    # Single multi-node workflow
    a2a_workflow = WorkflowBuilder()

    # Query order
    a2a_workflow.add_node("OrderReadNode", "get_order", {"id": order_id})

    # Query delivery
    a2a_workflow.add_node("DeliveryOrderListNode", "get_delivery", {
        "filters": {"order_id": order_id}, "limit": 1
    })

    # Query invoice
    a2a_workflow.add_node("InvoiceListNode", "get_invoice", {
        "filters": {"order_id": order_id}, "limit": 1
    })

    # Execute in parallel
    results, _ = runtime.execute(a2a_workflow.build())

    # Format unified response
    return {
        "order_id": order_id,
        "order": results.get('get_order'),
        "delivery": results.get('get_delivery'),
        "invoice": results.get('get_invoice'),
        "status_summary": format_status_summary(results)
    }
```

#### **Point 2: Customer Service Agent A2A Calls**

**Enhancement to chatbot endpoint:**

```python
def handle_customer_query(message: str, session_id: str) -> str:
    """
    Intelligent query handler with A2A capabilities
    """
    # Classify intent
    intent = classify_intent(message)

    if intent == 'order_status':
        # Extract order ID from message
        order_id = extract_order_id(message)  # GPT-4 or regex

        # A2A call to query status
        status_data = requests.post(
            "http://localhost:8001/api/a2a/query_order_status",
            json={"order_id": order_id}
        ).json()

        # Format natural language response
        return format_order_status_response(status_data)

    elif intent in ['policy_question', 'faq']:
        # RAG retrieval
        knowledge = search_knowledge_base(message, collection="policies_en")
        return generate_rag_response(message, knowledge)

    elif intent == 'order_placement':
        # Delegate to existing order processing endpoint
        return "I can help you place an order. What would you like to order?"

    else:
        # General conversation with memory
        context = load_conversation_context(session_id)
        return generate_conversational_response(message, context)
```

---

## 5. Existing Patterns to Extend

### 5.1 Semantic Search Pattern (Ready for RAG)

**Current Implementation:** `src/semantic_search.py`

```python
def semantic_product_search(
    message: str,
    database_url: str,
    api_key: str,
    top_n: int = 10,
    min_similarity: float = 0.3
) -> List[Dict]:
    """
    Find most relevant products using OpenAI embeddings + cosine similarity

    Steps:
    1. Generate query embedding (text-embedding-3-small)
    2. Load products with embeddings from PostgreSQL
    3. Calculate cosine similarity
    4. Return top N results
    """
```

**Extension to RAG:**

This same pattern can be applied to policy documents in ChromaDB:

```python
# src/rag/retrieval.py (NEW MODULE)

def search_knowledge_base(
    query: str,
    collection: str = "policies_en",
    top_n: int = 5,
    min_similarity: float = 0.3
) -> List[str]:
    """
    Search RAG knowledge base using same semantic search pattern

    ChromaDB handles:
    - Embedding generation (OpenAI)
    - Vector similarity search
    - Document retrieval
    """
    from src.rag import get_chroma_client

    client = get_chroma_client()
    collection = client.get_collection(name=collection)

    results = collection.query(
        query_texts=[query],
        n_results=top_n
    )

    # Filter by similarity threshold
    filtered = []
    for doc, distance in zip(results['documents'][0], results['distances'][0]):
        similarity = 1 - distance  # Convert distance to similarity
        if similarity >= min_similarity:
            filtered.append(doc)

    return filtered
```

### 5.2 Catalog-Aware Prompt Pattern

**Current Implementation:** `enhanced_api.py:291-378`

The system builds dynamic GPT-4 prompts with catalog context:

```python
# Build focused system prompt with only relevant products
catalog_section = format_search_results_for_llm(relevant_products)

system_prompt = f"""You are an order processing assistant...

{catalog_section}

INSTRUCTIONS:
1. Find the customer/outlet name in the message
2. For each product the customer mentions:
   - Match it to ONE of the products in the RELEVANT PRODUCTS list above
   - Use the EXACT SKU from the catalog
...
"""
```

**Extension to RAG:**

Same pattern can integrate policy knowledge:

```python
# NEW: RAG-enhanced prompt
relevant_policies = search_knowledge_base(query=message, collection="policies_en")
policy_section = format_policies_for_llm(relevant_policies)

system_prompt = f"""You are TRIA's AI customer service assistant...

RELEVANT POLICIES:
{policy_section}

PRODUCT CATALOG:
{catalog_section}

CONVERSATION HISTORY:
{conversation_history}

INSTRUCTIONS:
- Answer customer questions using the RELEVANT POLICIES above
- For orders, use the PRODUCT CATALOG
- Maintain context from CONVERSATION HISTORY
...
"""
```

### 5.3 Error Handling Pattern (Production-Ready)

**Current Implementation:** NO FALLBACKS principle

```python
# Example 1: Fail explicitly if semantic search finds no products
if len(relevant_products) == 0:
    raise HTTPException(
        status_code=404,
        detail="No products matched your order. Please provide more specific product descriptions."
    )

# Example 2: Fail explicitly if GPT-4 parsing fails
if isinstance(parsed_data, dict) and 'response' in parsed_data:
    content = parsed_data['response'].get('content', '{}')
    parsed_order = extract_json_from_llm_response(content)
else:
    raise HTTPException(
        status_code=500,
        detail="GPT-4 response parsing failed - no valid order data extracted"
    )

# Example 3: Fail if outlet not found
if not outlet_id:
    raise HTTPException(
        status_code=404,
        detail=f"Outlet '{outlet_name}' not found in database."
    )
```

**Extension to RAG/A2A:**

Apply same pattern to knowledge retrieval:

```python
# RAG error handling
relevant_policies = search_knowledge_base(query=message)

if len(relevant_policies) == 0:
    # OPTION 1: Explicit error
    raise HTTPException(
        status_code=404,
        detail="No relevant policies found. Please rephrase your question."
    )

    # OPTION 2: Graceful fallback to general response
    response = "I don't have specific policy information on that topic. "
    response += "Please contact customer service for assistance."
    return response

# A2A error handling
if intent == 'order_status':
    order_id = extract_order_id(message)

    if not order_id:
        return "I couldn't find an order number in your message. Please provide the order number (e.g., #12345)."

    try:
        status = query_order_status(order_id)
    except HTTPException as e:
        if e.status_code == 404:
            return f"I couldn't find order #{order_id}. Please check the order number and try again."
        raise
```

---

## 6. Recommendations for Extension

### 6.1 Phase 1: RAG Knowledge Base (Week 1-2)

**Priority: HIGH** - Foundation for conversational AI

**Tasks:**
1. ✅ ChromaDB setup (already installed, basic structure exists in `src/rag/`)
2. Index policy documents:
   - Extract text from .docx files (`doc/policy/*.docx`)
   - Chunk with 500-token chunks, 100-token overlap
   - Generate embeddings (text-embedding-3-small)
   - Store in ChromaDB collections (policies_en, faqs_en, etc.)

3. Implement retrieval functions:
   - `search_knowledge_base(query, collection, top_n)`
   - `format_policies_for_llm(results)`

4. Test integration:
   - Query: "What's your refund policy?"
   - Expected: Relevant policy chunks retrieved
   - Validate: GPT-4 generates grounded response

**Files to Create:**
- `src/rag/chroma_client.py` - ChromaDB client wrapper
- `src/rag/document_processor.py` - .docx text extraction + chunking
- `src/rag/knowledge_indexer.py` - One-time indexing script
- `src/rag/retrieval.py` - Search functions
- `scripts/build_knowledge_base.py` - Setup script

**Integration Point:**
- Modify `enhanced_api.py` Customer Service Agent (lines 291-378)
- Add policy retrieval before GPT-4 prompt construction

### 6.2 Phase 2: Conversation Memory (Week 2-3)

**Priority: HIGH** - Required for multi-turn conversations

**Tasks:**
1. Database schema:
   ```sql
   CREATE TABLE conversation_sessions (
       session_id UUID PRIMARY KEY,
       user_id VARCHAR(255),
       outlet_id INTEGER REFERENCES outlets(id),
       language VARCHAR(10),
       start_time TIMESTAMP,
       end_time TIMESTAMP,
       message_count INTEGER DEFAULT 0,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   CREATE TABLE conversation_messages (
       id SERIAL PRIMARY KEY,
       session_id UUID REFERENCES conversation_sessions(session_id),
       role VARCHAR(20),
       content TEXT,
       intent VARCHAR(50),
       timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. Redis setup:
   - Install Redis (Docker or native)
   - Configure connection in `.env`
   - Implement session cache (30-min TTL)

3. Session management module:
   - `src/memory/session_manager.py`
   - Functions: `get_or_create_session()`, `load_conversation_context()`, `save_conversation_turn()`

4. Integration:
   - Add session_id to all API requests
   - Load context before GPT-4 calls
   - Save turns after responses

**Files to Create:**
- `src/memory/session_manager.py`
- `src/memory/context_builder.py`
- `migrations/002_conversation_tables.sql`

**Integration Points:**
- `/api/process_order_enhanced` - Add session management
- New `/api/chatbot` endpoint - Full conversation support

### 6.3 Phase 3: A2A Status Queries (Week 3-4)

**Priority: MEDIUM** - Enhances customer service capabilities

**Tasks:**
1. Implement A2A orchestration endpoint:
   - `/api/a2a/query_order_status`
   - Multi-node workflow (OrderRead + DeliveryOrderList + InvoiceList)
   - Unified response format

2. Intent classification:
   - Simple GPT-4 classification prompt or regex patterns
   - Intents: order_placement, order_status, policy_question, faq, general_inquiry

3. Order ID extraction:
   - Regex: `#?(\d{1,10})`
   - GPT-4 fallback for natural language ("my last order")

4. Natural language formatting:
   - Convert API responses to conversational text
   - Example: "Your order #12345 was delivered on Oct 15, 2025. Status: Completed."

**Files to Create:**
- `src/agents/a2a_orchestrator.py`
- `src/agents/intent_classifier.py`
- `src/utils/nl_formatter.py`

**Integration Points:**
- `/api/chatbot` endpoint - Route to A2A for status queries
- Customer Service Agent - Call A2A APIs based on intent

### 6.4 Phase 4: Multi-Language Support (Week 4-5)

**Priority: MEDIUM** - Depends on market requirements

**Tasks:**
1. Language detection:
   - Install `langdetect` library
   - Auto-detect language from user message

2. Multi-language policy documents:
   - Translate policies to Chinese, Malay
   - Store in `doc/policy/zh/`, `doc/policy/ms/`
   - Index in separate ChromaDB collections

3. Language-aware RAG:
   - Query collection based on detected language
   - `search_knowledge_base(query, collection=f"policies_{language}")`

4. GPT-4 response in user's language:
   - System prompt: "Always respond in the same language as the user"
   - GPT-4 handles this natively

**Files to Create:**
- `src/utils/language_detector.py`
- `doc/policy/zh/*.docx` (translated documents)
- `doc/policy/ms/*.docx` (translated documents)

**Integration Points:**
- All endpoints - Detect language, route to correct collection
- RAG retrieval - Language-aware collection selection

### 6.5 Phase 5: PDPA Compliance (Week 5-6)

**Priority: HIGH** - Legal requirement for production

**Tasks:**
1. PII detection & scrubbing:
   - Install `presidio-analyzer` (optional, or use regex)
   - Detect: phone numbers, emails, NRIC, credit cards
   - Scrub before storing in conversation logs

2. Data retention policies:
   - Automated cleanup jobs (PostgreSQL cron)
   - Delete conversations older than 90 days
   - Anonymize summaries after 2 years

3. Encryption:
   - PostgreSQL: Transparent Data Encryption (TDE)
   - Redis: TLS connections
   - API: HTTPS only

4. Audit logging:
   - Log all data access (who, what, when)
   - Immutable audit trail

**Files to Create:**
- `src/privacy/pii_scrubber.py`
- `src/privacy/audit_logger.py`
- `migrations/003_data_retention_jobs.sql`

**Integration Points:**
- All endpoints - Scrub PII before database storage
- Scheduled jobs - Run daily cleanup

---

## 7. Architecture Diagrams

### 7.1 Current State (Stateless Order Processing)

```
┌────────────────────────────────────────────────────────────┐
│                    WhatsApp Message                         │
│              "Need 500 boxes for 10 inch pizzas"           │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│                 FastAPI: /api/process_order_enhanced        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Agent 1: Customer Service                          │   │
│  │ • Semantic search (PostgreSQL embeddings)          │   │
│  │ • GPT-4 parsing                                    │   │
│  │ • Output: parsed_order                             │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Agent 2: Operations                                │   │
│  │ • Validate, classify                               │   │
│  │ • Output: total_items, is_large_order              │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Agent 3: Inventory                                 │   │
│  │ • Excel inventory check                            │   │
│  │ • Stock verification                               │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Agent 4: Delivery                                  │   │
│  │ • Schedule delivery                                │   │
│  │ • Route planning                                   │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Agent 5: Finance                                   │   │
│  │ • Calculate pricing                                │   │
│  │ • Generate invoice                                 │   │
│  │ • Post to Xero (optional)                          │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Database: OrderCreateNode                          │   │
│  │ • Save order to PostgreSQL                         │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│              OrderResponse (with agent_timeline)            │
│  • order_id: 12345                                          │
│  • agent_timeline: [5 agents with details]                 │
│  • total: $450.00 SGD                                       │
└────────────────────────────────────────────────────────────┘
```

### 7.2 Proposed State (Conversational AI with RAG + A2A)

```
┌────────────────────────────────────────────────────────────┐
│                    WhatsApp Message                         │
│      "What's your refund policy for damaged items?"        │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│              FastAPI: /api/chatbot (NEW)                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Session Management                                 │   │
│  │ • Get/create session_id (Redis)                    │   │
│  │ • Load conversation context (last 10 messages)     │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Intent Classification                              │   │
│  │ • GPT-4 quick classification                       │   │
│  │ • Intents: order, status, policy, faq, general     │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│         ┌───────────────┼───────────────┐                  │
│         │               │               │                  │
│         ▼               ▼               ▼                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ RAG      │  │ A2A          │  │ Order        │        │
│  │ Knowledge│  │ Status Query │  │ Processing   │        │
│  │ Base     │  │              │  │ (existing)   │        │
│  │          │  │              │  │              │        │
│  │ ChromaDB │  │ Multi-node   │  │ 5-agent      │        │
│  │ search   │  │ workflow     │  │ pipeline     │        │
│  └──────────┘  └──────────────┘  └──────────────┘        │
│         │               │               │                  │
│         └───────────────┴───────────────┘                  │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Response Generation (GPT-4)                        │   │
│  │ • Context: conversation history                    │   │
│  │ • Knowledge: retrieved policies                    │   │
│  │ • Data: A2A results (if applicable)                │   │
│  └────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Save Conversation Turn                             │   │
│  │ • Redis: Hot cache (30 min TTL)                    │   │
│  │ • PostgreSQL: Persistent storage                   │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│              ChatbotResponse                                │
│  "If you receive damaged items:                             │
│   1. Report within 24 hours                                 │
│   2. Provide photos                                         │
│   3. We'll arrange full replacement or refund               │
│                                                              │
│   Do you have a specific order you need help with?"        │
└────────────────────────────────────────────────────────────┘
```

---

## 8. Key Takeaways

### 8.1 Strengths of Current Implementation

1. **Functional Multi-Agent Orchestration**
   - 5 specialized agents working in sequence
   - Clear separation of concerns (Customer Service, Operations, Inventory, Delivery, Finance)
   - Real-time tracking via `agent_timeline`

2. **Production-Ready Data Handling**
   - NO MOCKUPS: Real PostgreSQL, Excel, GPT-4, Xero API
   - NO HARDCODING: Environment variables for all config
   - NO FALLBACKS: Explicit error handling

3. **Semantic Search Foundation**
   - OpenAI embeddings already integrated (product catalog)
   - Pattern can be extended to RAG knowledge base
   - Cosine similarity search working in production

4. **Kailash SDK Best Practices**
   - WorkflowBuilder + LocalRuntime pattern
   - DataFlow CRUD nodes (45 auto-generated)
   - Proper `.build()` before `runtime.execute()`

5. **Extensibility Points Identified**
   - Customer Service Agent (lines 228-461) - RAG integration ready
   - Session management - Redis + PostgreSQL architecture designed
   - A2A endpoints - Multi-node workflow pattern established

### 8.2 Gaps Requiring Extension

1. **NO Conversation Memory**
   - Each request is stateless
   - No context across messages
   - Solution: Redis (hot cache) + PostgreSQL (persistent storage)

2. **NO Knowledge Base**
   - Policies/FAQs not integrated
   - RAG module structure exists (`src/rag/`) but not connected to API
   - Solution: ChromaDB indexing + retrieval functions

3. **NO A2A Status Queries**
   - Agents don't communicate bidirectionally
   - Customer Service can't query order status
   - Solution: A2A orchestration endpoint + intent routing

4. **NO Multi-Language Support**
   - Currently English only
   - Solution: Language detection + multi-language RAG collections

### 8.3 Implementation Priority

**Phase 1 (Weeks 1-2): RAG Knowledge Base** ⭐⭐⭐
- Critical for conversational AI
- Extends existing semantic search pattern
- Low complexity, high impact

**Phase 2 (Weeks 2-3): Conversation Memory** ⭐⭐⭐
- Required for multi-turn conversations
- Architecture already designed (Redis + PostgreSQL)
- Medium complexity, high impact

**Phase 3 (Weeks 3-4): A2A Status Queries** ⭐⭐
- Enhances customer service capabilities
- Leverages existing DataFlow CRUD nodes
- Medium complexity, medium impact

**Phase 4 (Weeks 4-5): Multi-Language** ⭐
- Depends on market requirements
- Low complexity if Phase 1 complete
- Medium impact (depends on user base)

**Phase 5 (Weeks 5-6): PDPA Compliance** ⭐⭐⭐
- Legal requirement for production
- High complexity, critical for launch
- Must-have before public deployment

---

## 9. Next Steps

### Immediate Actions (This Week)

1. **Review & Approval**
   - [ ] Stakeholder review of this analysis
   - [ ] Confirm extension priorities (RAG → Memory → A2A?)
   - [ ] Budget approval (estimated $600-700/month operational cost)

2. **Environment Setup**
   - [ ] ChromaDB configuration (persistent storage)
   - [ ] Redis installation (Docker or native)
   - [ ] PostgreSQL schema updates (conversation tables)

3. **Document Preparation**
   - [ ] Locate policy .docx files (`doc/policy/`)
   - [ ] Review for chunking appropriateness
   - [ ] Prepare test queries for RAG validation

4. **Proof of Concept**
   - [ ] Index 1 policy document in ChromaDB
   - [ ] Test semantic search retrieval
   - [ ] Integrate retrieval into 1 test endpoint

### Decision Required

**Proceed with implementation?**
- [ ] YES - Begin Phase 1 (RAG Knowledge Base)
- [ ] NO - Revise priorities
- [ ] PARTIAL - Which phases to implement? (Select: RAG / Memory / A2A / Multi-Lang / PDPA)

---

**End of Analysis**

**Prepared by:** Claude Code (SDK Navigator)
**Date:** 2025-10-18
**Version:** 1.0
**Status:** ANALYSIS COMPLETE
**Repository:** `C:\Users\fujif\OneDrive\Documents\GitHub\tria`

---

## Appendix: Code Reference Index

### Key Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `src/enhanced_api.py` | 1447 | Main orchestrator with 5-agent pipeline |
| `src/semantic_search.py` | 246 | Semantic product search (OpenAI embeddings) |
| `src/process_order_with_catalog.py` | 253 | Catalog processing utilities |
| `src/models/dataflow_models.py` | 166 | DataFlow models (5 models, 45 nodes) |
| `src/rag/__init__.py` | 39 | RAG module structure (ready for implementation) |
| `doc/CHATBOT_ARCHITECTURE_PROPOSAL.md` | 924 | Detailed RAG/memory/A2A architecture proposal |

### Critical Code Locations

| Feature | File | Lines |
|---------|------|-------|
| Agent 1: Customer Service | `enhanced_api.py` | 228-461 |
| Agent 2: Operations | `enhanced_api.py` | 466-496 |
| Agent 3: Inventory | `enhanced_api.py` | 501-547 |
| Agent 4: Delivery | `enhanced_api.py` | 552-574 |
| Agent 5: Finance | `enhanced_api.py` | 579-630 |
| AgentStatus Model | `enhanced_api.py` | 134-142 |
| OrderResponse Model | `enhanced_api.py` | 145-152 |
| Semantic Search | `semantic_search.py` | 157-218 |
| DataFlow Models | `dataflow_models.py` | 19-165 |
| WorkflowBuilder Usage | `enhanced_api.py` | 175-180, 383-399, 647-652 |
| Runtime Execution | `enhanced_api.py` | 119, 180, 399 |
