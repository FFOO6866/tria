# Data Models

**TRIA AIBPO Database Schema**

Version: 1.1.0 | Last Updated: 2025-11-21

---

## PostgreSQL Models

### Product Catalog
File: `src/models/dataflow_models.py`

**Fields:**
- `sku`: Product SKU (e.g., "TRI-001-TR-01")
- `description`: Product name
- `unit_price`: Price in SGD (Decimal)
- `uom`: Unit of measure (piece, box, pack, carton)
- `category`: Product category
- `stock_quantity`: Current stock level
- `is_active`: Active in catalog

### Outlets

**Fields:**
- `name`: Outlet name
- `address`: Full address
- `contact_person`: Contact name
- `contact_number`: Phone number
- `whatsapp_user_id`: WhatsApp ID for matching

### Orders

**Fields:**
- `outlet_id`: Foreign key to Outlet
- `whatsapp_message`: Original WhatsApp text
- `parsed_items`: JSON with extracted items
- `total_amount`: Calculated total (SGD)
- `status`: pending, processing, completed, failed
- `anomaly_detected`: Boolean flag
- `escalated`: Boolean flag

### Delivery Orders

**Fields:**
- `order_id`: Foreign key to Order
- `do_number`: Unique DO number (DO-YYYYMMDD-XXXXX)
- `excel_path`: Path to generated DO Excel file
- `delivery_date`: Scheduled delivery date
- `status`: scheduled, in_transit, delivered

### Invoices

**Fields:**
- `order_id`: Foreign key to Order
- `invoice_number`: Invoice number (INV-YYYYMMDD-XXXXX)
- `xero_invoice_id`: Xero's internal invoice ID
- `xero_url`: Direct link to Xero invoice
- `subtotal`: Subtotal before tax (Decimal)
- `tax`: GST 8% (Decimal)
- `total`: Final total (Decimal)

---

## Conversation Models

File: `src/models/conversation_models.py`

### Conversations
- `conversation_id`: Unique ID
- `user_id`: User identifier
- `start_time`: Conversation start
- `end_time`: Conversation end
- `message_count`: Number of messages

### Messages
- `message_id`: Unique ID
- `conversation_id`: Foreign key
- `role`: user, assistant, system
- `content`: Message text
- `timestamp`: Message time

---

## See Also

- [System Architecture](02-system-architecture.md)
- [src/models/](../src/models/) - Model implementations

---

**Last Updated**: 2025-11-21
