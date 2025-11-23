#!/usr/bin/env python3
"""
Product Embeddings Migration Script
====================================

Adds `embedding` column to products table and generates embeddings for all products.

Usage:
    python scripts/migrate_product_embeddings.py

Requirements:
    - OpenAI API key in environment (OPENAI_API_KEY)
    - PostgreSQL database connection (DATABASE_URL)

NO MOCKING - Uses real OpenAI API and PostgreSQL database.
"""

import os
import sys
import json
import logging
from typing import List
from sqlalchemy import text, inspect
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import get_db_engine
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if column exists in table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def add_embedding_column(engine):
    """Add embedding column to products table if it doesn't exist"""
    logger.info("Checking if embedding column exists...")

    if check_column_exists(engine, 'products', 'embedding'):
        logger.info("✓ embedding column already exists")
        return

    logger.info("Adding embedding column to products table...")

    with engine.connect() as conn:
        # Add column as TEXT (will store JSON array)
        conn.execute(text("""
            ALTER TABLE products
            ADD COLUMN embedding TEXT;
        """))
        conn.commit()

    logger.info("✓ embedding column added successfully")


def generate_embedding(text: str, api_key: str, model: str = "text-embedding-3-small") -> List[float]:
    """Generate embedding for text using OpenAI API"""
    client = OpenAI(api_key=api_key)

    try:
        response = client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        raise RuntimeError(f"Failed to generate embedding: {e}") from e


def populate_embeddings(engine, api_key: str):
    """Generate and store embeddings for all products"""
    logger.info("Loading products without embeddings...")

    # Get products without embeddings
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, sku, description, category
            FROM products
            WHERE is_active = :is_active
            AND (embedding IS NULL OR embedding = '')
            ORDER BY id
        """), {"is_active": True})

        products = []
        for row in result:
            products.append({
                'id': row.id,
                'sku': row.sku,
                'description': row.description,
                'category': row.category
            })

    if len(products) == 0:
        logger.info("✓ All products already have embeddings")
        return

    logger.info(f"Generating embeddings for {len(products)} products...")

    # Generate embeddings with progress tracking
    for idx, product in enumerate(products, 1):
        try:
            # Create text for embedding: combine category + description
            # This helps semantic search understand product context better
            embedding_text = f"{product['category']}: {product['description']}"

            # Clean problematic Unicode characters
            embedding_text = embedding_text.replace('\u2300', 'diameter ')
            embedding_text = embedding_text.replace('⌀', 'diameter ')

            # Generate embedding
            embedding_vector = generate_embedding(embedding_text, api_key)

            # Store as JSON string
            embedding_json = json.dumps(embedding_vector)

            # Update database
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE products
                    SET embedding = :embedding
                    WHERE id = :id
                """), {
                    "embedding": embedding_json,
                    "id": product['id']
                })
                conn.commit()

            logger.info(f"  [{idx}/{len(products)}] {product['sku']} - ✓")

        except Exception as e:
            logger.error(f"  [{idx}/{len(products)}] {product['sku']} - FAILED: {e}")
            continue

    logger.info(f"✓ Embeddings generated for {len(products)} products")


def verify_embeddings(engine):
    """Verify embeddings were generated successfully"""
    logger.info("Verifying embeddings...")

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total_products,
                COUNT(embedding) as products_with_embeddings,
                COUNT(*) - COUNT(embedding) as products_without_embeddings
            FROM products
            WHERE is_active = true
        """))

        stats = result.fetchone()

        logger.info(f"  Total products: {stats.total_products}")
        logger.info(f"  With embeddings: {stats.products_with_embeddings}")
        logger.info(f"  Without embeddings: {stats.products_without_embeddings}")

        if stats.products_without_embeddings == 0:
            logger.info("✓ All active products have embeddings")
            return True
        else:
            logger.warning(f"⚠ {stats.products_without_embeddings} products still need embeddings")
            return False


def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("Product Embeddings Migration")
    logger.info("=" * 60)

    try:
        # Get configuration
        database_url = config.get_database_url()
        api_key = config.OPENAI_API_KEY

        # Get database engine
        engine = get_db_engine(database_url)

        # Step 1: Add embedding column
        logger.info("\n[Step 1/3] Adding embedding column...")
        add_embedding_column(engine)

        # Step 2: Generate embeddings
        logger.info("\n[Step 2/3] Generating embeddings...")
        populate_embeddings(engine, api_key)

        # Step 3: Verify
        logger.info("\n[Step 3/3] Verifying embeddings...")
        success = verify_embeddings(engine)

        logger.info("\n" + "=" * 60)
        if success:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.warning("⚠️  Migration completed with warnings (some products missing embeddings)")
        logger.info("=" * 60)

        return 0 if success else 1

    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        logger.exception(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
