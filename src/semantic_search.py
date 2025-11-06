"""
Semantic Product Search Module
================================

Production-ready semantic search for product catalog using OpenAI embeddings
and numpy cosine similarity.

Features:
- Handles typos and language variations
- Semantic understanding of product descriptions
- Fast numpy-based cosine similarity for small catalogs
- Connection pooling for scalability
- Parameterized queries for SQL injection protection
- Production ready - no mocks, no hardcoding

Usage:
    from src.semantic_search import semantic_product_search

    products = semantic_product_search(
        message="I need 500 pizza boxes for 10 inch pizzas",
        database_url="postgresql://...",
        top_n=10
    )
"""

import os
import json
import numpy as np
import logging
from typing import List, Dict, Optional
from sqlalchemy import text
from openai import OpenAI

# Import centralized database connection
from database import get_db_engine

# Configure logging
logger = logging.getLogger(__name__)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0 to 1, higher is more similar)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def generate_query_embedding(message: str, api_key: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Generate embedding for customer message using OpenAI API

    Args:
        message: Customer WhatsApp message or order text
        api_key: OpenAI API key
        model: Embedding model to use

    Returns:
        Embedding vector as list of floats

    Raises:
        RuntimeError: If OpenAI API call fails
    """
    client = OpenAI(api_key=api_key)

    try:
        response = client.embeddings.create(
            model=model,
            input=message
        )
        return response.data[0].embedding
    except Exception as e:
        # NO FALLBACK - Raise exception with graceful error message
        raise RuntimeError(
            f"Failed to generate product embeddings from OpenAI API. "
            f"This is required for semantic product search. "
            f"Error: {str(e)}"
        ) from e


def load_products_with_embeddings(database_url: str) -> List[Dict]:
    """
    Load all active products with their embeddings from database

    Uses centralized database engine with global connection pooling.
    Parameterized queries prevent SQL injection.

    Args:
        database_url: PostgreSQL connection string (passed to get_db_engine)

    Returns:
        List of product dictionaries with embeddings

    Raises:
        RuntimeError: If database connection or query fails
    """
    try:
        # Get global engine with connection pooling
        # Engine is reused across all calls for optimal performance
        engine = get_db_engine(database_url)

        # Use parameterized query for SQL injection protection
        # Note: This query has no user input, but good practice for consistency
        query = text("""
            SELECT sku, description, unit_price, uom, category, stock_quantity, embedding
            FROM products
            WHERE is_active = :is_active
            AND embedding IS NOT NULL
            AND embedding != :empty_string
            ORDER BY sku
        """)

        products = []

        # Use context manager for automatic connection cleanup
        # Connection is returned to pool, NOT destroyed
        with engine.connect() as conn:
            result = conn.execute(query, {
                'is_active': True,
                'empty_string': ''
            })

            for row in result:
                # Parse embedding from JSON
                embedding_json = row[6]
                try:
                    embedding = json.loads(embedding_json)
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping product {row[0]}: Invalid embedding JSON - {str(e)}")
                    continue  # Skip products with invalid embeddings

                # Clean description (remove problematic Unicode)
                description = str(row[1])
                description = description.replace('\u2300', 'diameter ')
                description = description.replace('⌀', 'diameter ')

                products.append({
                    'sku': str(row[0]),
                    'description': description,
                    'unit_price': float(row[2]) if row[2] else 0.0,
                    'uom': str(row[3]) if row[3] else 'pieces',
                    'category': str(row[4]) if row[4] else '',
                    'stock_quantity': int(row[5]) if row[5] else 0,
                    'embedding': np.array(embedding, dtype=np.float32)
                })

        # NO engine.dispose() - Keep pool alive for reuse!
        # This is the key fix: connections are returned to pool, not destroyed

        return products

    except Exception as e:
        logger.error(f"Database error while loading products: {str(e)}")
        raise RuntimeError(
            f"Failed to load products from database. "
            f"Please check database connection and table structure. "
            f"Error: {str(e)}"
        ) from e


def semantic_product_search(
    message: str,
    database_url: str,
    api_key: str,
    top_n: int = 10,
    min_similarity: float = 0.3
) -> List[Dict]:
    """
    Find most relevant products using semantic similarity

    Args:
        message: Customer order message or query
        database_url: PostgreSQL connection string
        api_key: OpenAI API key
        top_n: Number of top products to return
        min_similarity: Minimum similarity threshold (0-1)

    Returns:
        List of top N most relevant products with similarity scores
        NOTE: Empty list is valid if search succeeds but no products meet similarity threshold

    Raises:
        RuntimeError: If OpenAI API fails or database has no products with embeddings
    """
    # Generate embedding for query - raises RuntimeError on API failure
    query_embedding = generate_query_embedding(message, api_key)
    query_vector = np.array(query_embedding, dtype=np.float32)

    # Load all products with embeddings
    products = load_products_with_embeddings(database_url)

    # NO FALLBACK - If no products have embeddings, this is a configuration error
    if len(products) == 0:
        raise RuntimeError(
            "No products with embeddings found in database. "
            "Product embeddings are required for semantic search. "
            "Please ensure products have been processed with embeddings generation."
        )

    # Calculate cosine similarity for each product
    results = []
    for product in products:
        similarity = cosine_similarity(query_vector, product['embedding'])

        if similarity >= min_similarity:
            results.append({
                'sku': product['sku'],
                'description': product['description'],
                'unit_price': product['unit_price'],
                'uom': product['uom'],
                'category': product['category'],
                'stock_quantity': product['stock_quantity'],
                'similarity': float(similarity)
            })

    # Sort by similarity (highest first) and return top N
    results.sort(key=lambda x: x['similarity'], reverse=True)

    # NOTE: Returning empty list here is VALID - it means search succeeded
    # but no products met the similarity threshold. This is different from
    # API failures or missing embeddings (which raise exceptions above)
    return results[:top_n]


def format_search_results_for_llm(results: List[Dict]) -> str:
    """
    Format semantic search results for GPT-4 system prompt

    Args:
        results: List of search results with similarity scores

    Returns:
        Formatted text for LLM prompt
    """
    if len(results) == 0:
        return "NO MATCHING PRODUCTS FOUND"

    catalog_text = "RELEVANT PRODUCTS (Semantic Match):\n"
    catalog_text += "=" * 60 + "\n"

    for idx, product in enumerate(results, 1):
        catalog_text += f"\n[{idx}] SKU: {product['sku']} (Match: {product['similarity']*100:.1f}%)\n"
        catalog_text += f"    Description: {product['description']}\n"
        catalog_text += f"    Price: ${product['unit_price']:.2f} per {product['uom']}\n"
        catalog_text += f"    Stock: {product['stock_quantity']} {product['uom']}s\n"

    catalog_text += "=" * 60

    return catalog_text
