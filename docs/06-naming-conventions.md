# Naming Conventions

**TRIA AIBPO Naming Standards**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## File Naming

### Python Files
- Module files: `snake_case.py`
- Examples: `enhanced_api.py`, `database.py`, `config_validator.py`

### Documentation
- Markdown: `kebab-case.md` or `SCREAMING_SNAKE_CASE.md`
- Numbered: `01-platform-overview.md`

### Configuration
- `.env`, `.env.example`, `.env.docker`
- `docker-compose.yml`, `pyproject.toml`

---

## Code Naming

### Functions
```python
def load_product_catalog():  # verb_noun
def get_db_engine():
def validate_order_total():
```

### Classes
```python
class ProductCache:  # PascalCase
class CustomerServiceAgent:
class ConversationManager:
```

### Variables
```python
database_url = "..."  # snake_case
api_key = config.OPENAI_API_KEY
order_total = calculate_total(items)
```

### Constants
```python
MAX_QUANTITY_PER_ITEM = 10000  # SCREAMING_SNAKE_CASE
TAX_RATE = 0.08
```

---

## Database Naming

### Tables
- Singular nouns: `product`, `order`, `conversation`
- Snake_case: `delivery_order`, `conversation_context`

### Columns
- Snake_case: `unit_price`, `whatsapp_user_id`
- Boolean prefix: `is_active`, `has_error`

---

## API Endpoints

```
POST /chat
POST /process-order
GET /health
GET /orders/{order_id}
WS /ws
```

---

## See Also

- [Directory Structure](07-directory-structure.md)
- [Development Standards](04-development-standards.md)

---

**Last Updated**: 2025-11-21
