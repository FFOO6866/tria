"""
Semantic Product Search Module
================================

Production-ready semantic search for product catalog using OpenAI embeddings
and numpy cosine similarity.

Features:
- Handles typos and language variations
- Semantic understanding of product descriptions
- Fast numpy-based cosine similarity for small catalogs
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
from typing import List, Dict, Optional
import psycopg2
from openai import OpenAI


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

    Args:
        database_url: PostgreSQL connection string

    Returns:
        List of product dictionaries with embeddings
    """
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

    # Connect
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        client_encoding='UTF8'
    )
    cursor = conn.cursor()

    # Load products with embeddings
    cursor.execute("""
        SELECT sku, description, unit_price, uom, category, stock_quantity, embedding
        FROM products
        WHERE is_active = TRUE
        AND embedding IS NOT NULL
        AND embedding != ''
        ORDER BY sku
    """)

    products = []
    for row in cursor.fetchall():
        # Parse embedding from JSON
        embedding_json = row[6]
        try:
            embedding = json.loads(embedding_json)
        except:
            continue  # Skip products with invalid embeddings

        # Clean description
        description = str(row[1])
        description = description.replace('\u2300', 'diameter ')
        description = description.replace('⌀', 'diameter ')

        products.append({
            'sku': str(row[0]),
            'description': description,
            'unit_price': float(row[2]),
            'uom': str(row[3]),
            'category': str(row[4]),
            'stock_quantity': int(row[5]),
            'embedding': np.array(embedding, dtype=np.float32)
        })

    cursor.close()
    conn.close()

    return products


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
