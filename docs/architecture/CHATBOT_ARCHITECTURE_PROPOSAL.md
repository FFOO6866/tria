# TRIA AI Chatbot - Professional Architecture Proposal

**Date:** 2025-10-18
**Version:** 1.0
**Status:** PROPOSED

---

## Executive Summary

Transform the current order-processing chatbot into a **full-fledged professional AI customer service agent** with:

- ✅ **Multi-language support** (English, Chinese, Malay, etc.)
- ✅ **Conversational intelligence** (not just order processing)
- ✅ **Full context awareness** (conversation memory + knowledge base)
- ✅ **Policy compliance** (RAG-powered knowledge retrieval)
- ✅ **A2A capabilities** (agent-to-agent for status checks, order queries)
- ✅ **PDPA/GDPR compliance** (privacy-first design)
- ✅ **Industry best practices** (RAG, vector DB, structured memory)

---

## 1. Current State Analysis

### 1.1 Existing Capabilities ✅
- **OpenAI GPT-4** integration (chat + embeddings)
- **Product embeddings** in PostgreSQL (semantic product search)
- **Multi-agent orchestration** (5 specialized agents)
- **Real-time order processing**
- **ChromaDB** installed (ready for vector storage)

### 1.2 Gaps to Address 🔧
- **No conversation memory** (stateless interactions)
- **No knowledge base** (policies not integrated)
- **Limited to order processing** (no general Q&A)
- **No multi-language support** (English only)
- **No A2A for status checks** (can't query order status)
- **No privacy controls** (PII handling, data retention)

---

## 2. Proposed Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (WhatsApp UI)                       │
│          User sends message in English/Chinese/Malay             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CUSTOMER SERVICE AGENT                         │
│                     (Intelligent Router)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ Intent      │  │ Language     │  │ Context Manager     │   │
│  │ Classifier  │  │ Detector     │  │ (Memory + History)  │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌───────────┐   ┌──────────────┐   ┌────────────┐
    │ RAG       │   │ Order        │   │ A2A        │
    │ Knowledge │   │ Processing   │   │ Status     │
    │ Base      │   │ Agent        │   │ Query      │
    └───────────┘   └──────────────┘   └────────────┘
            │               │               │
            ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐    │
│  │ ChromaDB     │  │ PostgreSQL    │  │ Redis Cache      │    │
│  │ (Vector DB)  │  │ (Structured)  │  │ (Session State)  │    │
│  │              │  │               │  │                  │    │
│  │ - Policies   │  │ - Orders      │  │ - Conversations  │    │
│  │ - FAQs       │  │ - Products    │  │ - User context   │    │
│  │ - Guides     │  │ - Customers   │  │ - Temp data      │    │
│  └──────────────┘  └───────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

#### A. **Intelligent Customer Service Agent**
- **Intent Classification**: Determine user intent (order, question, complaint, status check)
- **Language Detection**: Auto-detect language (en, zh, ms)
- **Context Management**: Maintain conversation state and history
- **Response Generation**: GPT-4 powered responses with RAG

#### B. **RAG Knowledge Base (ChromaDB)**
- **Policy Documents**: TRIA rules, escalation guides, tone/personality
- **FAQ Database**: Product FAQs, common questions
- **Dynamic Retrieval**: Semantic search for relevant context
- **Multi-language**: Store documents in all supported languages

#### C. **Conversation Memory System**
- **Short-term (Redis)**: Current session context (5-10 messages)
- **Long-term (PostgreSQL)**: Historical conversations (90 days retention)
- **PII Handling**: Automatic anonymization for logs
- **Context Window**: Sliding window of relevant history

#### D. **A2A Integration**
- **Order Status Agent**: Query order status, delivery info
- **Inventory Agent**: Check product availability
- **Finance Agent**: Query invoice status, payment info
- **Escalation Agent**: Route to human if needed

---

## 3. RAG (Retrieval-Augmented Generation) Strategy

### 3.1 Why RAG?

| Aspect | Without RAG | With RAG |
|--------|-------------|----------|
| **Knowledge** | Limited to GPT-4 training data | Real-time policy updates |
| **Accuracy** | May hallucinate policies | Grounded in actual documents |
| **Updates** | Requires model retraining | Update vector DB only |
| **Cost** | High token usage (long context) | Lower (only relevant chunks) |
| **Compliance** | Hard to prove sources | Traceable citations |

### 3.2 Knowledge Base Structure

```
doc/policy/ (Source Documents)
├── TRIA_Rules_and_Policies_v1.0.docx
├── TRIA_Escalation_Routing_Guide_v1.0.docx
├── TRIA_Product_FAQ_Handbook_v1.0.docx
└── TRIA_Tone_and_Personality_v1.0.docx

            ↓ (Document Processing)

ChromaDB Collections:
├── policies_en (English policies, 50+ chunks)
├── policies_zh (Chinese policies, 50+ chunks)
├── faqs_en (English FAQs, 100+ Q&A pairs)
├── faqs_zh (Chinese FAQs, 100+ Q&A pairs)
├── escalation_rules (Routing logic, 20+ scenarios)
└── product_catalog (Product info + existing embeddings)
```

### 3.3 RAG Flow

```
User Query: "What's your refund policy for damaged items?"
    │
    ▼
1. Generate query embedding (OpenAI text-embedding-3-small)
    │
    ▼
2. Search ChromaDB for top 3-5 relevant chunks
   Results:
   - Chunk 1: "Refund Policy - Damaged Goods (Score: 0.92)"
   - Chunk 2: "Return Process Timeline (Score: 0.87)"
   - Chunk 3: "Quality Guarantee (Score: 0.81)"
    │
    ▼
3. Construct GPT-4 prompt:
   System: You are TRIA's customer service assistant...
   Context: [Retrieved policy chunks]
   History: [Last 5 messages]
   User: What's your refund policy for damaged items?
    │
    ▼
4. GPT-4 generates response grounded in retrieved context
    │
    ▼
5. Return response with optional citations
```

---

## 4. Conversation Memory Architecture

### 4.1 Multi-Tier Memory Strategy

#### **Tier 1: Working Memory (Redis)** 🔥
- **Purpose**: Current active conversation
- **TTL**: 30 minutes of inactivity
- **Scope**: Last 10 messages
- **Structure**:
  ```json
  {
    "session_id": "sess_20251018_abc123",
    "user_id": "user_12345",
    "outlet_id": "outlet_001",
    "language": "en",
    "conversation_history": [
      {
        "role": "user",
        "content": "Hi, I need to order boxes",
        "timestamp": "2025-10-18T10:30:00Z"
      },
      {
        "role": "assistant",
        "content": "Hello! I'd be happy to help...",
        "timestamp": "2025-10-18T10:30:02Z"
      }
    ],
    "context": {
      "current_intent": "order_placement",
      "mentioned_products": ["10inch_box", "12inch_box"],
      "outlet_name": "Pacific Pizza Downtown"
    }
  }
  ```

#### **Tier 2: Session Memory (PostgreSQL)** 💾
- **Purpose**: Full conversation storage
- **Retention**: 90 days (PDPA compliant)
- **Structure**:
  ```sql
  CREATE TABLE conversation_sessions (
    session_id UUID PRIMARY KEY,
    user_id VARCHAR(255),
    outlet_id INTEGER REFERENCES outlets(id),
    language VARCHAR(10),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    message_count INTEGER,
    intents JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES conversation_sessions(session_id),
    role VARCHAR(20), -- 'user' or 'assistant'
    content TEXT,
    language VARCHAR(10),
    intent VARCHAR(50),
    context JSONB,
    pii_scrubbed BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

#### **Tier 3: Summary Memory (PostgreSQL)** 📊
- **Purpose**: Long-term user insights (anonymized)
- **Retention**: 2 years
- **Structure**:
  ```sql
  CREATE TABLE user_interaction_summary (
    user_id VARCHAR(255) PRIMARY KEY,
    total_conversations INTEGER,
    common_intents JSONB,
    preferred_language VARCHAR(10),
    avg_satisfaction DECIMAL(3,2),
    last_interaction TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```

### 4.2 Context Management

**Context Window Strategy:**
```python
def build_conversation_context(session_id: str) -> str:
    """
    Build GPT-4 context from multi-tier memory

    Returns:
        Formatted context with:
        - System prompt (TRIA personality)
        - Retrieved knowledge (RAG)
        - Conversation history (last 10 messages)
        - User context (outlet, preferences)
    """
    # 1. Get working memory (Redis)
    session = redis.get(f"session:{session_id}")

    # 2. Get conversation history (PostgreSQL)
    messages = db.query(
        "SELECT role, content FROM conversation_messages "
        "WHERE session_id = %s ORDER BY timestamp DESC LIMIT 10",
        (session_id,)
    )

    # 3. Build context
    context = {
        "system": SYSTEM_PROMPT,
        "knowledge": [],  # Populated by RAG
        "history": messages[::-1],  # Chronological order
        "user_info": {
            "outlet": session["outlet_name"],
            "language": session["language"],
            "intent": session["context"]["current_intent"]
        }
    }

    return context
```

---

## 5. Multi-Language Support

### 5.1 Language Detection

```python
from langdetect import detect

def detect_language(text: str) -> str:
    """
    Auto-detect language with fallback

    Supported:
    - en: English
    - zh: Chinese (Simplified/Traditional)
    - ms: Malay
    """
    try:
        lang = detect(text)
        return lang if lang in ['en', 'zh', 'ms'] else 'en'
    except:
        return 'en'  # Default to English
```

### 5.2 Multi-Language RAG

**Strategy: Separate Collections per Language**

```python
# Load policy documents
POLICY_SOURCES = {
    "en": {
        "policies": "doc/policy/en/TRIA_Rules_and_Policies_v1.0.docx",
        "faqs": "doc/policy/en/TRIA_Product_FAQ_Handbook_v1.0.docx",
        "escalation": "doc/policy/en/TRIA_Escalation_Routing_Guide_v1.0.docx",
        "tone": "doc/policy/en/TRIA_Tone_and_Personality_v1.0.docx"
    },
    "zh": {
        "policies": "doc/policy/zh/TRIA_Rules_and_Policies_v1.0_CN.docx",
        "faqs": "doc/policy/zh/TRIA_Product_FAQ_Handbook_v1.0_CN.docx",
        # ... Chinese versions
    }
}

# Query in user's language
def retrieve_knowledge(query: str, language: str = "en") -> List[str]:
    collection_name = f"policies_{language}"
    results = chroma_client.query(
        collection_name=collection_name,
        query_texts=[query],
        n_results=5
    )
    return results['documents'][0]
```

### 5.3 Response in User's Language

**GPT-4 handles this natively:**

```python
SYSTEM_PROMPT = """
You are TRIA's AI customer service assistant.

IMPORTANT: Always respond in the same language as the user's message.
- If user writes in English, respond in English
- If user writes in Chinese (中文), respond in Chinese
- If user writes in Malay, respond in Malay

Tone: Professional, friendly, helpful
"""
```

---

## 6. A2A (Agent-to-Agent) Integration

### 6.1 Status Query Capabilities

**Customer Service Agent can now call other agents:**

```python
class CustomerServiceAgent:
    def handle_status_query(self, order_id: str) -> dict:
        """
        A2A call to Operations/Delivery agents
        """
        # Query order status from database
        order_status = self.operations_agent.get_order_status(order_id)

        # Query delivery info
        delivery_info = self.delivery_agent.get_delivery_status(order_id)

        # Format response
        return {
            "order_id": order_id,
            "status": order_status["status"],
            "items": order_status["line_items"],
            "delivery": {
                "estimated_date": delivery_info["estimated_delivery"],
                "tracking": delivery_info["tracking_number"]
            }
        }
```

### 6.2 Integration Points

| User Query | A2A Integration | Backend API |
|------------|----------------|-------------|
| "Where's my order #12345?" | Operations Agent | `GET /api/orders/{order_id}` |
| "Do you have 10" boxes in stock?" | Inventory Agent | `GET /api/inventory/check` |
| "What's the status of invoice #INV-001?" | Finance Agent | `GET /api/invoices/{invoice_id}` |
| "Cancel my order" | Operations Agent | `POST /api/orders/{order_id}/cancel` |

---

## 7. PDPA/GDPR Compliance

### 7.1 Data Privacy Architecture

```
┌──────────────────────────────────────────────────────┐
│            USER DATA PROTECTION LAYERS                │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Layer 1: PII Detection & Scrubbing                  │
│  ─────────────────────────────────                   │
│  • Phone numbers → [PHONE]                           │
│  • Email → [EMAIL]                                   │
│  • Credit cards → [CARD]                             │
│  • NRIC/Passport → [ID]                              │
│                                                       │
│  Layer 2: Data Minimization                          │
│  ────────────────────────                            │
│  • Store only necessary data                         │
│  • Anonymize where possible                          │
│  • Hash user IDs                                     │
│                                                       │
│  Layer 3: Retention Policies                         │
│  ─────────────────────────                           │
│  • Working memory: 30 min TTL                        │
│  • Conversations: 90 days                            │
│  • Summaries: 2 years (anonymized)                   │
│                                                       │
│  Layer 4: Access Controls                            │
│  ──────────────────────                              │
│  • Encrypted at rest (PostgreSQL TDE)                │
│  • Encrypted in transit (TLS 1.3)                    │
│  • Role-based access                                 │
│                                                       │
│  Layer 5: Audit Logging                              │
│  ────────────────────                                │
│  • WHO accessed WHAT data WHEN                       │
│  • Immutable audit trail                             │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### 7.2 PII Scrubbing Implementation

```python
import re
from typing import Dict

PII_PATTERNS = {
    "phone": r"\+?[\d\s\-\(\)]{8,}",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "nric": r"\b[STFG]\d{7}[A-Z]\b",  # Singapore NRIC
    "credit_card": r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"
}

def scrub_pii(text: str) -> tuple[str, Dict]:
    """
    Remove PII from text while preserving meaning

    Returns:
        (scrubbed_text, pii_found)
    """
    scrubbed = text
    pii_found = {}

    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, scrubbed)
        if matches:
            pii_found[pii_type] = len(matches)
            scrubbed = re.sub(pattern, f"[{pii_type.upper()}]", scrubbed)

    return scrubbed, pii_found

# Usage in chatbot
def store_message(session_id: str, role: str, content: str):
    # Scrub PII before storage
    scrubbed_content, pii_found = scrub_pii(content)

    db.execute("""
        INSERT INTO conversation_messages
        (session_id, role, content, pii_scrubbed, pii_types)
        VALUES (%s, %s, %s, %s, %s)
    """, (session_id, role, scrubbed_content,
          len(pii_found) > 0, json.dumps(pii_found)))
```

### 7.3 Data Retention Policy

```sql
-- Automated cleanup job (runs daily)
CREATE OR REPLACE FUNCTION cleanup_old_conversations()
RETURNS void AS $$
BEGIN
    -- Delete conversations older than 90 days
    DELETE FROM conversation_messages
    WHERE timestamp < NOW() - INTERVAL '90 days';

    DELETE FROM conversation_sessions
    WHERE end_time < NOW() - INTERVAL '90 days';

    -- Anonymize summaries older than 2 years
    UPDATE user_interaction_summary
    SET user_id = 'ANONYMIZED_' || MD5(user_id)
    WHERE updated_at < NOW() - INTERVAL '2 years'
    AND user_id NOT LIKE 'ANONYMIZED_%';
END;
$$ LANGUAGE plpgsql;
```

---

## 8. Implementation Phases

### **Phase 1: Foundation (Week 1-2)** 🏗️

**Goal**: RAG knowledge base + conversation memory

**Tasks**:
1. ✅ Document processing pipeline
   - Extract text from .docx files
   - Chunk documents (500 tokens/chunk, 100 overlap)
   - Generate embeddings (text-embedding-3-small)

2. ✅ ChromaDB setup
   - Create collections (policies_en, faqs_en, etc.)
   - Index policy documents
   - Test semantic retrieval

3. ✅ Conversation memory
   - Redis setup for session state
   - PostgreSQL tables (conversation_sessions, messages)
   - Context management functions

**Deliverables**:
- [ ] `src/rag/document_processor.py` - Process .docx to chunks
- [ ] `src/rag/knowledge_base.py` - ChromaDB client + retrieval
- [ ] `src/memory/session_manager.py` - Conversation memory
- [ ] `scripts/build_knowledge_base.py` - One-time setup script

**Success Criteria**:
- Policy documents indexed in ChromaDB
- Semantic search returns relevant policy chunks
- Conversations persist across messages

---

### **Phase 2: Intelligent Agent (Week 3-4)** 🤖

**Goal**: Context-aware conversational AI

**Tasks**:
1. ✅ Enhanced Customer Service Agent
   - Intent classification (order vs. query vs. complaint)
   - RAG integration for knowledge retrieval
   - Response generation with GPT-4

2. ✅ Multi-turn conversation
   - Context window management
   - Conversation state tracking
   - Natural conversation flow

3. ✅ TRIA personality
   - System prompt from Tone & Personality doc
   - Consistent brand voice
   - Professional yet friendly tone

**Deliverables**:
- [ ] `src/agents/enhanced_customer_service_agent.py`
- [ ] `src/agents/intent_classifier.py`
- [ ] `src/prompts/system_prompts.py`

**Success Criteria**:
- Agent answers policy questions correctly
- Maintains context across 5+ message exchanges
- Consistent TRIA tone in all responses

---

### **Phase 3: Multi-Language (Week 5)** 🌍

**Goal**: English + Chinese support

**Tasks**:
1. ✅ Language detection
2. ✅ Multi-language policy documents
   - Translate policies to Chinese
   - Index in separate collections

3. ✅ Language-aware RAG
4. ✅ Response in user's language

**Deliverables**:
- [ ] `doc/policy/zh/` - Chinese policy translations
- [ ] `src/rag/multilingual_retrieval.py`
- [ ] Language detection in chatbot

**Success Criteria**:
- Detects language automatically
- Retrieves Chinese policies for Chinese queries
- Responds in user's language

---

### **Phase 4: A2A Integration (Week 6)** 🔄

**Goal**: Query order status, inventory, invoices

**Tasks**:
1. ✅ A2A orchestration layer
2. ✅ Status query endpoints
   - Order status API
   - Inventory check API
   - Invoice status API

3. ✅ Natural language → API mapping
   - Parse "Where's my order #123?" → API call
   - Format API response → natural language

**Deliverables**:
- [ ] `src/agents/a2a_orchestrator.py`
- [ ] API endpoints: `/api/a2a/order_status`, `/api/a2a/inventory_check`
- [ ] Natural language query parser

**Success Criteria**:
- "Where's my order?" → Returns actual order status
- "Do you have 10" boxes?" → Returns real inventory count
- Agent makes correct A2A calls based on intent

---

### **Phase 5: PDPA Compliance (Week 7)** 🔒

**Goal**: Privacy-first architecture

**Tasks**:
1. ✅ PII detection & scrubbing
2. ✅ Data retention policies
3. ✅ Audit logging
4. ✅ Encryption at rest & in transit

**Deliverables**:
- [ ] `src/privacy/pii_scrubber.py`
- [ ] Automated cleanup jobs
- [ ] Privacy policy documentation
- [ ] PDPA compliance audit report

**Success Criteria**:
- PII automatically scrubbed from logs
- Data deleted after retention period
- Audit trail for all data access
- Passes PDPA compliance audit

---

### **Phase 6: Production Optimization (Week 8)** 🚀

**Goal**: Performance, monitoring, scaling

**Tasks**:
1. ✅ Caching strategy
   - Redis cache for frequent queries
   - Embedding cache (avoid re-computing)

2. ✅ Monitoring & observability
   - Conversation analytics dashboard
   - Response time tracking
   - Error rate monitoring

3. ✅ Load testing & optimization
4. ✅ Fallback & error handling

**Deliverables**:
- [ ] Performance optimization report
- [ ] Monitoring dashboard
- [ ] Load test results (1000 concurrent users)
- [ ] Production runbook

**Success Criteria**:
- <500ms p95 response time
- <1% error rate
- Handles 1000 concurrent conversations
- Auto-recovery from failures

---

## 9. Technology Stack

### 9.1 Core Technologies

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **LLM** | OpenAI GPT-4 | Multi-language, proven reliability |
| **Embeddings** | text-embedding-3-small | Cost-effective, 1536-dim |
| **Vector DB** | ChromaDB | Already installed, easy to use |
| **Conversation Memory** | Redis + PostgreSQL | Fast cache + durable storage |
| **Document Processing** | python-docx, pypdf | Handle .docx policy files |
| **Language Detection** | langdetect | Lightweight, accurate |
| **PII Detection** | presidio (optional) | Enterprise-grade PII detection |

### 9.2 Infrastructure

```yaml
Production Stack:
  - Application: Python 3.11 + FastAPI
  - Vector DB: ChromaDB (persistent disk)
  - Cache: Redis 7.0 (in-memory)
  - Database: PostgreSQL 15 (encrypted)
  - LLM: OpenAI API (GPT-4, embeddings)
  - Monitoring: Prometheus + Grafana
  - Logging: ELK Stack (optional)
```

---

## 10. Cost Estimation

### 10.1 OpenAI API Costs

**Assumptions**: 1000 conversations/day, avg 10 messages/conversation

| Operation | Model | Cost per 1M tokens | Daily Usage | Monthly Cost |
|-----------|-------|-------------------|-------------|--------------|
| Embeddings | text-embedding-3-small | $0.02 | 5M tokens | $3.00 |
| Chat | GPT-4 Turbo | $10 (input) + $30 (output) | 20M tokens | $800 |
| **Total** | | | | **~$803/month** |

**Optimization**:
- Cache frequent queries (50% reduction) → $400/month
- Use GPT-3.5 for simple queries → $200/month
- **Optimized cost: ~$600/month**

### 10.2 Infrastructure Costs

| Component | Spec | Monthly Cost |
|-----------|------|--------------|
| Redis | 4GB RAM | $30 |
| PostgreSQL | 50GB SSD | $50 |
| ChromaDB | 20GB SSD | $20 |
| **Total** | | **$100/month** |

**Grand Total: ~$700/month** for production-grade AI chatbot

---

## 11. Success Metrics

### 11.1 Performance KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Response Time** | <500ms p95 | API latency monitoring |
| **Accuracy** | >90% correct answers | Human evaluation sample |
| **User Satisfaction** | >4.0/5.0 | Post-conversation survey |
| **Intent Classification** | >85% accuracy | Manual audit (100 samples) |
| **Multi-language Quality** | >4.0/5.0 | Native speaker evaluation |
| **Uptime** | 99.9% | System monitoring |

### 11.2 Business KPIs

| Metric | Target | Impact |
|--------|--------|---------|
| **Order Processing Time** | -30% | Faster orders via chat |
| **Support Ticket Reduction** | -50% | Self-service via chatbot |
| **Customer Satisfaction** | +20% | Better support experience |
| **Agent Productivity** | +40% | Escalate only complex cases |

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Hallucinations** | High | RAG with citations, human escalation |
| **Policy drift** | Medium | Monthly knowledge base updates |
| **Privacy breach** | High | PII scrubbing, encryption, audit logs |
| **API costs** | Medium | Caching, query optimization, usage alerts |
| **Language quality** | Medium | Native speaker validation, feedback loop |
| **Downtime** | High | Redundancy, fallback to human agents |

---

## 13. Next Steps

### Immediate Actions (Week 1)

1. **Review & Approval**
   - [ ] Stakeholder review of this proposal
   - [ ] Budget approval ($700/month operational cost)
   - [ ] Resource allocation (1-2 developers for 8 weeks)

2. **Environment Setup**
   - [ ] ChromaDB installation & configuration
   - [ ] Redis setup for session cache
   - [ ] Update PostgreSQL schema (conversation tables)

3. **Document Processing**
   - [ ] Extract text from policy .docx files
   - [ ] Review and organize for chunking
   - [ ] Prepare Chinese translations (if needed)

4. **Proof of Concept**
   - [ ] Build minimal RAG pipeline (1 policy doc)
   - [ ] Test conversation memory (5 messages)
   - [ ] Demonstrate multi-language query

### Decision Required

**Proceed with implementation?**
- [ ] YES - Begin Phase 1 immediately
- [ ] NO - Revise proposal
- [ ] PARTIAL - Which phases to prioritize?

---

## 14. Appendix

### A. Sample Conversation Flow

```
User: "Hi, I need help with my order"
│
├─> Intent: general_inquiry
├─> Language: English
├─> Context: New conversation
│
Agent: "Hello! I'm here to help. What can I assist you with today?
        You can:
        • Place a new order
        • Check order status
        • Ask about our products
        • Get delivery information"

User: "What's your refund policy for damaged items?"
│
├─> Intent: policy_question
├─> RAG Query: "refund policy damaged items"
├─> Retrieved: [Chunk 1: Refund Policy, Chunk 2: Quality Guarantee]
│
Agent: "According to our policy, if you receive damaged items:

        1. Report within 24 hours of delivery
        2. Provide photos of damaged items
        3. We'll arrange for:
           • Full replacement (free delivery), OR
           • Full refund to your account

        The process typically takes 3-5 business days.

        Do you have a specific order you need help with?"

User: "Yes, order #12345"
│
├─> Intent: status_check
├─> A2A Call: Operations Agent → Get order #12345 status
├─> Retrieved: Order details from database
│
Agent: "I found your order #12345:

        Status: Delivered on Oct 15, 2025
        Items: 600 x 10" boxes, 200 x 12" boxes

        Is there an issue with this delivery?"
```

### B. RAG Retrieval Example

**Query**: "Can I cancel my order after it's been confirmed?"

**Chroma Query**:
```python
results = collection.query(
    query_texts=["Can I cancel my order after it's been confirmed?"],
    n_results=3
)
```

**Retrieved Chunks**:
1. **Score: 0.91** - "Order Cancellation Policy: Orders can be cancelled within 2 hours of confirmation. After 2 hours, orders enter production and cannot be cancelled. Contact us immediately if you need to cancel."

2. **Score: 0.85** - "Modification Policy: Order modifications (quantity, items, delivery date) can be made up to 6 hours before scheduled delivery. Contact customer service for changes."

3. **Score: 0.78** - "Refund Timeline: Cancelled orders are refunded within 5-7 business days to the original payment method."

**GPT-4 Response** (grounded in retrieved context):
```
"Yes, you can cancel your order, but timing is important:

• Within 2 hours of confirmation: Full cancellation possible
• After 2 hours: Order enters production, cancellation not available

If you're within the 2-hour window, I can help you cancel right now.
When was your order confirmed?"
```

### C. Technology Alternatives Considered

| Decision | Choice | Alternative | Reason |
|----------|--------|-------------|---------|
| Vector DB | ChromaDB | Pinecone, Weaviate | Already installed, simpler |
| LLM | GPT-4 | Claude, Llama | Multi-language support |
| Cache | Redis | Memcached | Richer data structures |
| Embeddings | OpenAI | Cohere, HuggingFace | Integration with GPT-4 |

---

**End of Proposal**

**Prepared by**: Claude Code
**Date**: 2025-10-18
**Version**: 1.0
**Status**: AWAITING APPROVAL
