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
project_root = Path(__file__).parent.parent
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


def generate_embeddings_batch(texts: List[str], retry_count: int = 0) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single API call (much faster!)

    Args:
        texts: List of texts to embed
        retry_count: Current retry attempt

    Returns:
        List of embedding vectors (one per input text)
    """
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts
        )
        # API returns embeddings in the same order as input texts
        return [item.embedding for item in response.data]
    except Exception as e:
        if retry_count < MAX_RETRIES:
            wait_time = RETRY_DELAY * (2 ** retry_count)  # Exponential backoff
            print(f"  [RETRY] Batch API error, waiting {wait_time}s: {e}")
            time.sleep(wait_time)
            return generate_embeddings_batch(texts, retry_count + 1)
        else:
            print(f"  [ERROR] Batch failed after {MAX_RETRIES} retries: {e}")
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
    SELECT sku, description, description, category
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

# Generate embeddings using BATCH PROCESSING for speed
num_batches = (len(products_to_embed) + BATCH_SIZE - 1) // BATCH_SIZE
print(f"\n[>>] Generating embeddings in {num_batches} batches...")
print(f"    (This will make {num_batches} API calls instead of {len(products_to_embed)})")
print(f"    Expected speedup: ~{len(products_to_embed)//num_batches}x faster!")
print("")

embedded_count = 0
failed_count = 0
start_time = time.time()

# Process in batches
for batch_idx in range(num_batches):
    batch_start = batch_idx * BATCH_SIZE
    batch_end = min(batch_start + BATCH_SIZE, len(products_to_embed))
    batch_products = products_to_embed[batch_start:batch_end]

    print(f"\n[Batch {batch_idx + 1}/{num_batches}] Processing products {batch_start + 1}-{batch_end}...")

    # Prepare batch texts
    batch_texts = []
    batch_metadata = []  # Store (sku, name) for display

    for sku, name, description, category in batch_products:
        product_text = create_product_text(sku, name or description, category)
        batch_texts.append(product_text)
        batch_metadata.append((sku, name or description))

    # Generate embeddings for entire batch in ONE API call
    embeddings = generate_embeddings_batch(batch_texts)

    if embeddings:
        # Store each embedding
        for idx, (embedding, (sku, name)) in enumerate(zip(embeddings, batch_metadata)):
            safe_name = name.replace('\u2300', 'diameter').replace('⌀', 'diameter')[:50]

            embedding_json = json.dumps(embedding)

            try:
                cursor.execute("""
                    UPDATE products
                    SET embedding = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE sku = %s
                """, (embedding_json, sku))

                print(f"  [{batch_start + idx + 1}/{len(products_to_embed)}] {sku}: {safe_name} - [OK]")
                embedded_count += 1
            except Exception as e:
                print(f"  [{batch_start + idx + 1}/{len(products_to_embed)}] {sku}: [ERROR] {e}")
                failed_count += 1
    else:
        print(f"  [ERROR] Batch failed - all {len(batch_products)} products in this batch")
        failed_count += len(batch_products)

    # Small delay between batches (respects rate limits: 5000 req/min = 83/sec)
    # With BATCH_SIZE=100, we're well under the limit
    if batch_idx < num_batches - 1:
        time.sleep(0.2)  # 200ms between batches

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
