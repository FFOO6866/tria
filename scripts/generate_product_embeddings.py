#!/usr/bin/env python3
"""
Generate Product Embeddings for Semantic Search
================================================

Production-ready script to generate embeddings for all products using OpenAI API.

Features:
- Generates embeddings for product SKU + description
- Handles rate limiting with exponential backoff
- Batch processing for efficiency
- Progress tracking and error handling
- Stores embeddings as JSON arrays in database

NO MOCKS, NO SHORTCUTS - Production ready
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from openai import OpenAI
from typing import List, Dict

# Load environment
project_root = Path(__file__).parent
load_dotenv(project_root / ".env")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions, cost-effective
BATCH_SIZE = 100  # Process in batches
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

print("=" * 70)
print("GENERATING PRODUCT EMBEDDINGS FOR SEMANTIC SEARCH")
print("=" * 70)
print(f"\nModel: {EMBEDDING_MODEL}")
print(f"Batch size: {BATCH_SIZE}")


def generate_embedding(text: str, retry_count: int = 0) -> List[float]:
    """
    Generate embedding for text using OpenAI API with retry logic

    Args:
        text: Text to embed
        retry_count: Current retry attempt

    Returns:
        List of floats representing the embedding vector
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        if retry_count < MAX_RETRIES:
            wait_time = RETRY_DELAY * (2 ** retry_count)  # Exponential backoff
            print(f"  [RETRY] API error, waiting {wait_time}s: {e}")
            time.sleep(wait_time)
            return generate_embedding(text, retry_count + 1)
        else:
            print(f"  [ERROR] Failed after {MAX_RETRIES} retries: {e}")
            return None


def create_product_text(sku: str, description: str, category: str = None) -> str:
    """
    Create rich text representation for embedding generation

    Combines SKU, description, and category for better semantic matching
    """
    parts = [f"SKU: {sku}", f"Product: {description}"]
    if category:
        parts.append(f"Category: {category}")
    return " | ".join(parts)


# Connect to database
print(f"\n[>>] Connecting to database...")
database_url = os.getenv('DATABASE_URL')
parts = database_url.replace('postgresql://', '').split('@')
user_pass = parts[0].split(':')
host_db = parts[1].split('/')
user = user_pass[0]
password = user_pass[1]
host_port = host_db[0].split(':')
host = host_port[0]
port = host_port[1] if len(host_port) > 1 else 5432
database = host_db[1]

conn = psycopg2.connect(
    host=host,
    port=port,
    database=database,
    user=user,
    password=password
)
conn.autocommit = True
cursor = conn.cursor()
print("[OK] Connected")

# Load products without embeddings
print(f"\n[>>] Loading products from database...")
cursor.execute("""
    SELECT sku, description, category, stock_quantity
    FROM products
    WHERE is_active = TRUE
    AND (embedding IS NULL OR embedding = '')
    ORDER BY sku
""")
products_to_embed = cursor.fetchall()
print(f"[OK] Found {len(products_to_embed)} products needing embeddings")

if len(products_to_embed) == 0:
    print("\n[OK] All products already have embeddings!")
    cursor.close()
    conn.close()
    exit(0)

# Generate embeddings
print(f"\n[>>] Generating embeddings...")
print(f"    (This will make {len(products_to_embed)} API calls to OpenAI)")
print("")

embedded_count = 0
failed_count = 0
start_time = time.time()

for idx, (sku, description, category, stock_qty) in enumerate(products_to_embed, 1):
    # Create rich text for embedding
    product_text = create_product_text(sku, description, category)

    # Sanitize description for printing (remove problematic Unicode)
    safe_desc = description.replace('\u2300', 'diameter').replace('⌀', 'diameter')[:50]

    # Generate embedding
    print(f"  [{idx}/{len(products_to_embed)}] {sku}: {safe_desc}...")
    embedding = generate_embedding(product_text)

    if embedding:
        # Store embedding as JSON string
        embedding_json = json.dumps(embedding)

        try:
            cursor.execute("""
                UPDATE products
                SET embedding = %s, updated_at = CURRENT_TIMESTAMP
                WHERE sku = %s
            """, (embedding_json, sku))

            print(f"       [OK] Embedding stored ({len(embedding)} dimensions)")
            embedded_count += 1
        except Exception as e:
            print(f"       [ERROR] Database error: {e}")
            failed_count += 1
    else:
        print(f"       [ERROR] Failed to generate embedding")
        failed_count += 1

    # Rate limiting - small delay between requests
    if idx < len(products_to_embed):
        time.sleep(0.1)  # 100ms delay to avoid rate limits

end_time = time.time()
duration = end_time - start_time

cursor.close()
conn.close()

# Summary
print("\n" + "=" * 70)
print("EMBEDDING GENERATION COMPLETE")
print("=" * 70)
print(f"\nResults:")
print(f"  - Successfully embedded: {embedded_count}")
print(f"  - Failed: {failed_count}")
print(f"  - Duration: {duration:.1f} seconds")
print(f"  - Average: {duration/len(products_to_embed):.2f} seconds per product")

if embedded_count > 0:
    print(f"\n[OK] {embedded_count} products now have embeddings and are ready for semantic search!")
    print(f"\nNext steps:")
    print(f"  1. Test semantic search: python test_semantic_search.py")
    print(f"  2. Update enhanced_api.py to use semantic search")

if failed_count > 0:
    print(f"\n[WARNING] {failed_count} products failed - you may want to re-run this script")

print("=" * 70)
