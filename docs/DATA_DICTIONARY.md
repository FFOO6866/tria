# TRIA AIBPO Data Dictionary

**Version**: 1.0.0
**Last Updated**: 2025-12-08
**Purpose**: Single source of truth for all data definitions, naming conventions, and standards

---

## 1. Database Schema

### 1.1 Core Tables

#### `products`
Product catalog for order processing.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key, auto-increment | 1 |
| `sku` | VARCHAR(50) | NO | Stock Keeping Unit, unique | "PB-9-REG" |
| `name` | VARCHAR(255) | NO | Product name | "9 inch Pizza Box" |
| `description` | TEXT | YES | Product description | "Standard 9 inch..." |
| `category` | VARCHAR(100) | YES | Product category | "Pizza Boxes" |
| `unit_price` | DECIMAL(10,2) | NO | Price per unit | 0.45 |
| `unit_of_measure` | VARCHAR(20) | YES | Unit type | "piece", "carton" |
| `min_order_qty` | INTEGER | YES | Minimum order quantity | 100 |
| `is_active` | BOOLEAN | NO | Active status | true |
| `embedding` | VECTOR(1536) | YES | OpenAI embedding for semantic search | [0.01, -0.02, ...] |
| `created_at` | TIMESTAMP | NO | Creation timestamp | 2025-01-01 00:00:00 |
| `updated_at` | TIMESTAMP | NO | Last update timestamp | 2025-12-08 00:00:00 |

**Indexes**: `sku` (unique), `category`, `is_active`

---

#### `outlets`
Restaurant/store locations for orders.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key | 1 |
| `name` | VARCHAR(255) | NO | Outlet name | "Canadian Pizza - Bukit Bintang" |
| `code` | VARCHAR(20) | YES | Outlet code | "CP-BB" |
| `address` | TEXT | YES | Full address | "123 Jalan Bukit Bintang..." |
| `city` | VARCHAR(100) | YES | City | "Kuala Lumpur" |
| `state` | VARCHAR(100) | YES | State/Region | "Wilayah Persekutuan" |
| `postal_code` | VARCHAR(20) | YES | Postal code | "55100" |
| `phone` | VARCHAR(50) | YES | Contact phone | "+60 3-2141-0001" |
| `email` | VARCHAR(255) | YES | Contact email | "bb@canadianpizza.my" |
| `xero_contact_id` | VARCHAR(100) | YES | Xero contact reference | "abc-123-def" |
| `is_active` | BOOLEAN | NO | Active status | true |
| `created_at` | TIMESTAMP | NO | Creation timestamp | 2025-01-01 00:00:00 |

**Indexes**: `code` (unique), `xero_contact_id`, `is_active`

---

#### `orders`
Customer orders.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key | 1001 |
| `order_number` | VARCHAR(50) | NO | Unique order reference | "ORD-2025-001001" |
| `outlet_id` | INTEGER | NO | FK to outlets | 1 |
| `status` | VARCHAR(50) | NO | Order status | "pending", "confirmed", "delivered" |
| `subtotal` | DECIMAL(12,2) | NO | Order subtotal | 450.00 |
| `tax_amount` | DECIMAL(12,2) | NO | Tax amount | 36.00 |
| `total_amount` | DECIMAL(12,2) | NO | Total amount | 486.00 |
| `notes` | TEXT | YES | Order notes | "Urgent delivery" |
| `delivery_date` | DATE | YES | Requested delivery date | 2025-12-10 |
| `xero_invoice_id` | VARCHAR(100) | YES | Xero invoice reference | "INV-0001" |
| `conversation_id` | VARCHAR(100) | YES | Source conversation | "sess_abc123" |
| `created_at` | TIMESTAMP | NO | Creation timestamp | 2025-12-08 10:00:00 |
| `updated_at` | TIMESTAMP | NO | Last update | 2025-12-08 10:00:00 |

**Indexes**: `order_number` (unique), `outlet_id`, `status`, `xero_invoice_id`

---

#### `order_line_items`
Individual items in an order.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key | 1 |
| `order_id` | INTEGER | NO | FK to orders | 1001 |
| `product_id` | INTEGER | NO | FK to products | 5 |
| `sku` | VARCHAR(50) | NO | Product SKU (denormalized) | "PB-9-REG" |
| `product_name` | VARCHAR(255) | NO | Product name (denormalized) | "9 inch Pizza Box" |
| `quantity` | INTEGER | NO | Ordered quantity | 500 |
| `unit_price` | DECIMAL(10,2) | NO | Unit price at order time | 0.45 |
| `line_total` | DECIMAL(12,2) | NO | quantity * unit_price | 225.00 |

**Indexes**: `order_id`, `product_id`

---

#### `conversation_sessions`
Chat conversation sessions.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | VARCHAR(100) | NO | Session ID (UUID) | "sess_abc123def456" |
| `user_id` | VARCHAR(100) | NO | User identifier | "user_whatsapp_60123456789" |
| `outlet_id` | INTEGER | YES | Associated outlet | 1 |
| `channel` | VARCHAR(50) | NO | Communication channel | "whatsapp", "web", "api" |
| `status` | VARCHAR(50) | NO | Session status | "active", "closed", "escalated" |
| `language` | VARCHAR(10) | YES | Preferred language | "en", "zh", "ms" |
| `metadata` | JSONB | YES | Additional metadata | {"browser": "Chrome"} |
| `created_at` | TIMESTAMP | NO | Session start | 2025-12-08 10:00:00 |
| `updated_at` | TIMESTAMP | NO | Last activity | 2025-12-08 10:05:00 |
| `closed_at` | TIMESTAMP | YES | Session end | 2025-12-08 10:30:00 |

**Indexes**: `user_id`, `outlet_id`, `status`, `created_at`

---

#### `conversation_messages`
Individual messages in conversations.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key | 1 |
| `session_id` | VARCHAR(100) | NO | FK to conversation_sessions | "sess_abc123" |
| `role` | VARCHAR(20) | NO | Message sender | "user", "assistant", "system" |
| `content` | TEXT | NO | Message content | "I need 500 pizza boxes" |
| `intent` | VARCHAR(50) | YES | Classified intent | "order_inquiry", "product_search" |
| `confidence` | DECIMAL(5,4) | YES | Intent confidence | 0.9523 |
| `metadata` | JSONB | YES | Additional data | {"tokens": 150} |
| `created_at` | TIMESTAMP | NO | Message timestamp | 2025-12-08 10:01:00 |

**Indexes**: `session_id`, `role`, `intent`, `created_at`

---

### 1.2 Xero Integration Tables

#### `invoices`
Xero invoice records.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key | 1 |
| `xero_invoice_id` | VARCHAR(100) | NO | Xero invoice ID | "abc-123-def" |
| `order_id` | INTEGER | YES | FK to orders | 1001 |
| `invoice_number` | VARCHAR(50) | NO | Invoice number | "INV-0001" |
| `status` | VARCHAR(50) | NO | Invoice status | "DRAFT", "AUTHORISED", "PAID" |
| `total` | DECIMAL(12,2) | NO | Invoice total | 486.00 |
| `due_date` | DATE | YES | Payment due date | 2025-12-22 |
| `created_at` | TIMESTAMP | NO | Creation time | 2025-12-08 10:00:00 |
| `synced_at` | TIMESTAMP | YES | Last Xero sync | 2025-12-08 10:01:00 |

---

#### `delivery_orders`
Delivery order records.

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| `id` | INTEGER | NO | Primary key | 1 |
| `order_id` | INTEGER | NO | FK to orders | 1001 |
| `do_number` | VARCHAR(50) | NO | DO number | "DO-2025-001001" |
| `status` | VARCHAR(50) | NO | DO status | "pending", "dispatched", "delivered" |
| `delivery_date` | DATE | YES | Delivery date | 2025-12-10 |
| `driver_name` | VARCHAR(100) | YES | Driver name | "Ahmad" |
| `vehicle_number` | VARCHAR(20) | YES | Vehicle plate | "WXY 1234" |
| `notes` | TEXT | YES | Delivery notes | "Call before delivery" |
| `created_at` | TIMESTAMP | NO | Creation time | 2025-12-08 10:00:00 |

---

## 2. API Data Contracts

### 2.1 Chatbot API

#### Request: `POST /api/chatbot`

```json
{
  "message": "string (required) - User message, max 4000 chars",
  "outlet_id": "integer (required) - Outlet ID for context",
  "user_id": "string (required) - User identifier",
  "session_id": "string (required) - Session UUID",
  "language": "string (optional) - Language code: en, zh, ms"
}
```

**Headers**:
- `Content-Type: application/json`
- `Idempotency-Key: <UUID>` - Required, prevents duplicate processing

#### Response: Success (200)

```json
{
  "response": "string - AI assistant response",
  "session_id": "string - Session ID",
  "intent": "string - Classified intent",
  "confidence": "float - Intent confidence (0-1)",
  "metadata": {
    "tokens_used": "integer",
    "response_time_ms": "integer",
    "cache_hit": "boolean"
  }
}
```

#### Response: Error (4xx/5xx)

```json
{
  "detail": "string - Error message",
  "error_code": "string (optional) - Error code",
  "request_id": "string (optional) - Request trace ID"
}
```

---

### 2.2 Health Check API

#### Request: `GET /health`

#### Response (200):

```json
{
  "status": "healthy | degraded | unhealthy",
  "timestamp": "ISO8601 timestamp",
  "version": "string - API version",
  "circuit_breakers": {
    "xero": "open | closed | half-open",
    "openai": "open | closed | half-open",
    "database": "open | closed | half-open"
  },
  "database": "connected | error: <message>",
  "redis": "connected | error: <message>",
  "xero": "connected to <tenant> | not_configured | error: <message>",
  "chromadb": "connected | not_initialized | error: <message>",
  "components": {
    "session_manager": "initialized | error",
    "chatbot": {
      "intent_classifier": "initialized | error",
      "customer_service_agent": "initialized | error",
      "knowledge_base": "initialized | error"
    },
    "advanced_features": {
      "multilevel_cache": "initialized | disabled",
      "streaming": "enabled | disabled"
    }
  }
}
```

---

## 3. ChromaDB Collections

### 3.1 RAG Collections

| Collection | Purpose | Document Type | Expected Count |
|------------|---------|---------------|----------------|
| `policies_en` | TRIA Rules and Policies | Policy chunks | 50-100 |
| `faqs_en` | Product FAQ Handbook | FAQ entries | 100-200 |
| `escalation_rules` | Escalation Routing Guide | Escalation rules | 20-50 |
| `tone_personality` | Tone and Personality | Tone guidelines | 30-50 |

### 3.2 Cache Collections

| Collection | Purpose | TTL |
|------------|---------|-----|
| `response_cache_l2` | Semantic response cache | 24 hours |

### 3.3 Document Schema

```json
{
  "id": "string - Unique document ID",
  "document": "string - Text content",
  "metadata": {
    "source": "string - Source file path",
    "chunk_index": "integer - Chunk number",
    "section": "string - Document section",
    "language": "string - Language code"
  },
  "embedding": "[float] - 1536-dim OpenAI embedding"
}
```

---

## 4. Environment Variables

### 4.1 Required Variables (NO DEFAULTS)

| Variable | Type | Description | Format |
|----------|------|-------------|--------|
| `DATABASE_URL` | string | PostgreSQL connection | `postgresql://user:pass@host:port/db` |
| `OPENAI_API_KEY` | string | OpenAI API key | `sk-...` |
| `TAX_RATE` | float | Tax rate for orders | `0.08` (8%) |
| `XERO_SALES_ACCOUNT_CODE` | string | Xero sales account | Account code |
| `XERO_TAX_TYPE` | string | Xero tax type | Tax type code |

### 4.2 Optional Variables (With Defaults)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_MODEL` | string | `gpt-4` | OpenAI model |
| `OPENAI_TEMPERATURE` | float | `0.7` | Response temperature |
| `OPENAI_MAX_TOKENS` | int | `2000` | Max response tokens |
| `API_PORT` | int | `8000` | API server port |
| `ENHANCED_API_PORT` | int | `8001` | Enhanced API port |
| `REDIS_HOST` | string | `localhost` | Redis host |
| `REDIS_PORT` | int | `6379` | Redis port |
| `REDIS_DB` | int | `0` | Redis database |
| `LOG_LEVEL` | string | `INFO` | Logging level |
| `ENVIRONMENT` | string | `development` | Environment name |

### 4.3 Xero OAuth Variables

| Variable | Type | Description |
|----------|------|-------------|
| `XERO_CLIENT_ID` | string | OAuth client ID |
| `XERO_CLIENT_SECRET` | string | OAuth client secret |
| `XERO_REFRESH_TOKEN` | string | OAuth refresh token |
| `XERO_TENANT_ID` | string | Xero tenant ID |
| `XERO_REDIRECT_URI` | string | OAuth redirect URI |

---

## 5. Intent Classification

### 5.1 Intent Types

| Intent | Description | Trigger Keywords |
|--------|-------------|------------------|
| `greeting` | User greeting | hello, hi, hey, good morning |
| `order_inquiry` | Order-related questions | order, buy, purchase, need |
| `product_search` | Product search | find, search, looking for, what products |
| `pricing_inquiry` | Price questions | price, cost, how much, rate |
| `delivery_inquiry` | Delivery questions | delivery, shipping, when, arrive |
| `complaint` | Customer complaint | problem, issue, wrong, unhappy |
| `general_inquiry` | General questions | how, what, why, help |

### 5.2 Escalation Tiers

| Tier | Threshold | Handler |
|------|-----------|---------|
| 1 | Confidence < 0.3 | Human review |
| 2 | Complaint detected | Supervisor |
| 3 | Urgent + high value | Manager |

---

## 6. File Path Standards

### 6.1 Data Files

| Path | Purpose | Format |
|------|---------|--------|
| `data/inventory/Master_Inventory_File_2025.xlsx` | Product catalog | Excel |
| `data/templates/DO_Template.xlsx` | Delivery order template | Excel |
| `data/chromadb/` | ChromaDB persistence | SQLite + binary |
| `data/xero_tokens.json` | Xero OAuth tokens | JSON |
| `data/policy_usage.jsonl` | Policy analytics | JSONL |

### 6.2 Policy Documents

| Path | Purpose |
|------|---------|
| `docs/policy/TRIA_Rules_and_Policies_v1.0.docx` | Business rules |
| `docs/policy/TRIA_Product_FAQ_Handbook_v1.0.docx` | Product FAQ |
| `docs/policy/TRIA_Escalation_Routing_Guide_v1.0.docx` | Escalation rules |
| `docs/policy/TRIA_Tone_and_Personality_v1.0.docx` | Tone guidelines |

---

## 7. Naming Standards Reference

### 7.1 Quick Reference

| Type | Convention | Example |
|------|------------|---------|
| Python files | snake_case | `enhanced_api.py` |
| Python functions | snake_case, verb_noun | `get_db_engine()` |
| Python classes | PascalCase | `CustomerServiceAgent` |
| Python constants | SCREAMING_SNAKE | `MAX_TOKENS` |
| Database tables | snake_case, singular preferred | `product`, `order` |
| Database columns | snake_case | `unit_price`, `created_at` |
| API endpoints | kebab-case | `/process-order` |
| Environment vars | SCREAMING_SNAKE | `DATABASE_URL` |

### 7.2 Prefixes/Suffixes

| Pattern | Meaning | Example |
|---------|---------|---------|
| `is_*` | Boolean flag | `is_active` |
| `has_*` | Boolean presence | `has_embedding` |
| `*_at` | Timestamp | `created_at`, `updated_at` |
| `*_id` | Foreign key | `outlet_id`, `order_id` |
| `*_count` | Counter | `product_count` |
| `get_*` | Getter function | `get_db_engine()` |
| `create_*` | Creation function | `create_order()` |
| `validate_*` | Validation function | `validate_config()` |

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-08 | Initial data dictionary |

---

**Maintained by**: Development Team
**Review Frequency**: Monthly or on schema changes
