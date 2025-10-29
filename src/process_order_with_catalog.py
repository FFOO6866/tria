"""
Dynamic Catalog-Based Order Processing
=======================================

Updated order processing logic that uses product catalog from database
instead of hardcoded SKUs and pricing.
"""

import os
import json
import time
import psycopg2
from typing import Dict, List, Any
from decimal import Decimal

def load_product_catalog(database_url: str) -> List[Dict[str, Any]]:
    """Load all active products from database catalog"""

    # Parse connection string
    parts = database_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_db = parts[1].split('/')
    user = user_pass[0]
    password = user_pass[1]
    host_port = host_db[0].split(':')
    host = host_port[0]
    port = host_port[1] if len(host_port) > 1 else 5432
    database = host_db[1]

    # Connect and query with UTF-8 encoding
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        client_encoding='UTF8'
    )
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sku, description, unit_price, uom, category, stock_quantity
        FROM products
        WHERE is_active = TRUE
        ORDER BY sku
    """)

    products = []
    for row in cursor.fetchall():
        # Clean description to remove problematic Unicode characters
        description = str(row[1])
        # Replace diameter symbol and other special chars with text equivalents
        description = description.replace('\u2300', 'diameter ')
        description = description.replace('⌀', 'diameter ')

        products.append({
            'sku': str(row[0]),
            'description': description,
            'unit_price': float(row[2]),
            'uom': str(row[3]),
            'category': str(row[4]),
            'stock_quantity': int(row[5])
        })

    cursor.close()
    conn.close()

    return products


def format_catalog_for_llm(products: List[Dict]) -> str:
    """Format product catalog for GPT-4 system prompt"""

    catalog_text = "PRODUCT CATALOG:\n"
    catalog_text += "=" * 60 + "\n"

    for product in products:
        catalog_text += f"\nSKU: {product['sku']}\n"
        catalog_text += f"  Description: {product['description']}\n"
        catalog_text += f"  Price: ${product['unit_price']:.2f} per {product['uom']}\n"
        catalog_text += f"  Category: {product['category']}\n"
        catalog_text += f"  Stock Available: {product['stock_quantity']} {product['uom']}s\n"

    catalog_text += "=" * 60

    return catalog_text


def build_llm_system_prompt(products: List[Dict]) -> str:
    """Build GPT-4 system prompt with product catalog"""

    catalog_text = format_catalog_for_llm(products)

    prompt = f"""You are an order processing assistant for TRIA AI-BPO Solutions.

{catalog_text}

TASK: Extract order details from the customer's WhatsApp message and match them to products in our catalog.

INSTRUCTIONS:
1. Identify the customer/outlet name from the message
2. Match each item mentioned to a product SKU from the catalog above
3. Extract quantities for each product
4. Determine if the order is urgent (keywords: urgent, ASAP, rush, emergency, same-day)
5. Return ONLY a valid JSON object with this EXACT structure:

{{
  "outlet_name": "customer name from message",
  "line_items": [
    {{
      "sku": "exact SKU from catalog",
      "description": "product description",
      "quantity": <number>,
      "uom": "piece/box/pack"
    }}
  ],
  "is_urgent": true/false
}}

MATCHING RULES:
- Match customer descriptions to products in the catalog above by analyzing the product descriptions
- When customer mentions quantities in "bundles", calculate total pieces (e.g., 4 bundles × 100 = 400 pieces)
- When customer mentions box sizes like "10 inch", "12 inch", "14 inch" - look for matching pizza box sizes in catalog
- Use EXACT SKUs from the catalog - do not modify or make up SKUs
- If customer mentions a product not in catalog, skip it
- Do NOT hallucinate or invent products

IMPORTANT:
- Return ONLY the JSON object, no other text
- Use EXACT quantities from the customer's message
- Do NOT estimate or round numbers
- If a product isn't mentioned, don't include it in line_items

EXAMPLES:

Customer: "I need 100 trays and 100 lids"
Response:
{{
  "outlet_name": "Unknown",
  "line_items": [
    {{"sku": "TRI-001-TR-01", "description": "Single-Compartment Meal Tray", "quantity": 100, "uom": "piece"}},
    {{"sku": "TRI-002-LD-01", "description": "Lid for Single-Compartment Meal Tray", "quantity": 100, "uom": "piece"}}
  ],
  "is_urgent": false
}}

Customer: "Hi, Pizza Planet here. Need 500 meal trays urgently!"
Response:
{{
  "outlet_name": "Pizza Planet",
  "line_items": [
    {{"sku": "TRI-001-TR-01", "description": "Single-Compartment Meal Tray", "quantity": 500, "uom": "piece"}}
  ],
  "is_urgent": true
}}
"""

    return prompt


def extract_json_from_llm_response(response_content: str) -> Dict:
    """
    Extract JSON from GPT-4 response content.
    Handles cases where GPT-4 adds extra text before/after JSON.
    """

    # Try direct JSON parse first
    try:
        return json.loads(response_content)
    except json.JSONDecodeError:
        pass

    # Find JSON object in the content
    start_idx = response_content.find('{')
    end_idx = response_content.rfind('}')

    if start_idx != -1 and end_idx != -1:
        json_str = response_content[start_idx:end_idx+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # NO FALLBACK! Fail explicitly with meaningful error
    raise ValueError(
        f"Failed to extract valid JSON from LLM response. "
        f"Response content (first 500 chars): {response_content[:500]}"
    )


def calculate_order_total(line_items: List[Dict], products_map: Dict[str, Dict]) -> Dict[str, Decimal]:
    """
    Calculate order totals from line items using catalog pricing

    Raises:
        ValueError: If TAX_RATE environment variable is not configured
    """

    subtotal = Decimal('0.00')

    # NO HARDCODING, NO FALLBACKS - TAX_RATE must be configured
    tax_rate_str = os.getenv('TAX_RATE')
    if not tax_rate_str:
        raise ValueError(
            "TAX_RATE environment variable is required but not configured. "
            "Please set TAX_RATE in .env file."
        )
    tax_rate = Decimal(str(tax_rate_str))

    for item in line_items:
        sku = item.get('sku')
        quantity = item.get('quantity', 0)

        if sku in products_map:
            unit_price = Decimal(str(products_map[sku]['unit_price']))
            item_total = unit_price * Decimal(str(quantity))
            subtotal += item_total

    tax = subtotal * tax_rate
    total = subtotal + tax

    return {
        'subtotal': subtotal,
        'tax': tax,
        'total': total
    }


def format_line_items_for_display(line_items: List[Dict]) -> List[str]:
    """
    Format line items for agent timeline display

    Raises:
        ValueError: If required fields (sku, description) are missing
    """

    formatted = []
    for item in line_items:
        # PRODUCTION-READY: No fallbacks - validate required fields
        sku = item.get('sku')
        desc = item.get('description')
        qty = item.get('quantity', 0)
        uom = item.get('uom', 'piece')  # UOM can default to piece (standard unit)

        if not sku:
            raise ValueError("Line item missing required 'sku' field for display formatting")
        if not desc:
            raise ValueError("Line item missing required 'description' field for display formatting")

        formatted.append(f"{qty} x {desc} ({sku})")

    return formatted
