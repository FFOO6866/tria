"""
ChromaDB Client Manager
========================

Handles ChromaDB client initialization and collection management.

Features:
- Persistent storage in data/chromadb/
- Collection management with OpenAI embeddings
- Follows semantic_search.py patterns
- Production-ready with proper error handling

Collections:
- policies_en: English policy documents
- faqs_en: English FAQ documents
- escalation_rules: Escalation routing guides
- tone_personality: TRIA tone and personality guidelines
"""

import os
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


# Project root and ChromaDB storage path
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHROMA_PERSIST_DIR = PROJECT_ROOT / "data" / "chromadb"


def get_chroma_client(persist_directory: Optional[Path] = None) -> chromadb.ClientAPI:
    """
    Get or create ChromaDB client with persistent storage

    Args:
        persist_directory: Optional custom directory for ChromaDB data
                          Defaults to PROJECT_ROOT/data/chromadb/

    Returns:
        ChromaDB client instance

    Raises:
        RuntimeError: If ChromaDB initialization fails
    """
    if persist_directory is None:
        persist_directory = CHROMA_PERSIST_DIR

    # Ensure directory exists
    persist_directory.mkdir(parents=True, exist_ok=True)

    try:
        client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=False
            )
        )
        return client
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize ChromaDB client at {persist_directory}. "
            f"Error: {str(e)}"
        ) from e


def get_openai_embedding_function(api_key: str, model: str = "text-embedding-3-small") -> embedding_functions.OpenAIEmbeddingFunction:
    """
    Create OpenAI embedding function for ChromaDB

    Args:
        api_key: OpenAI API key
        model: Embedding model name (default: text-embedding-3-small)

    Returns:
        OpenAI embedding function for ChromaDB collections

    Note:
        Uses the same model as product semantic search for consistency
    """
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=model
    )


def get_or_create_collection(
    collection_name: str,
    api_key: str,
    client: Optional[chromadb.ClientAPI] = None,
    reset: bool = False
) -> chromadb.Collection:
    """
    Get or create a ChromaDB collection with OpenAI embeddings

    Args:
        collection_name: Name of the collection (e.g., 'policies_en', 'faqs_en')
        api_key: OpenAI API key for embeddings
        client: Optional ChromaDB client (will create default if None)
        reset: If True, delete and recreate the collection (use with caution)

    Returns:
        ChromaDB collection instance

    Raises:
        RuntimeError: If collection creation/retrieval fails
    """
    if client is None:
        client = get_chroma_client()

    # Get embedding function
    embedding_function = get_openai_embedding_function(api_key)

    try:
        # Delete if reset requested
        if reset:
            try:
                client.delete_collection(name=collection_name)
            except Exception:
                pass  # Collection doesn't exist, that's fine

        # Get or create collection
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity like semantic_search.py
        )

        return collection
    except Exception as e:
        raise RuntimeError(
            f"Failed to get or create collection '{collection_name}'. "
            f"Error: {str(e)}"
        ) from e


def list_collections(client: Optional[chromadb.ClientAPI] = None) -> list[str]:
    """
    List all existing collections in ChromaDB

    Args:
        client: Optional ChromaDB client (will create default if None)

    Returns:
        List of collection names
    """
    if client is None:
        client = get_chroma_client()

    collections = client.list_collections()
    return [col.name for col in collections]


def get_collection_stats(collection_name: str, client: Optional[chromadb.ClientAPI] = None) -> dict:
    """
    Get statistics for a collection

    Args:
        collection_name: Name of the collection
        client: Optional ChromaDB client (will create default if None)

    Returns:
        Dictionary with collection statistics

    Raises:
        ValueError: If collection doesn't exist
    """
    if client is None:
        client = get_chroma_client()

    try:
        collection = client.get_collection(name=collection_name)
        count = collection.count()

        return {
            'name': collection_name,
            'count': count,
            'metadata': collection.metadata
        }
    except Exception as e:
        raise ValueError(f"Collection '{collection_name}' not found or inaccessible: {str(e)}") from e


def delete_collection(collection_name: str, client: Optional[chromadb.ClientAPI] = None) -> None:
    """
    Delete a collection (use with caution)

    Args:
        collection_name: Name of the collection to delete
        client: Optional ChromaDB client (will create default if None)

    Raises:
        RuntimeError: If deletion fails
    """
    if client is None:
        client = get_chroma_client()

    try:
        client.delete_collection(name=collection_name)
    except Exception as e:
        raise RuntimeError(f"Failed to delete collection '{collection_name}': {str(e)}") from e


def health_check(client: Optional[chromadb.ClientAPI] = None) -> dict:
    """
    Perform health check on ChromaDB

    Verifies that ChromaDB is accessible and operational.
    This should be called at application startup.

    Args:
        client: Optional ChromaDB client (will create default if None)

    Returns:
        Dictionary with health check results:
        {
            'status': 'healthy' | 'unhealthy',
            'accessible': bool,
            'collections_count': int,
            'collections': list[str],
            'error': str (only if unhealthy)
        }
    """
    try:
        if client is None:
            client = get_chroma_client()

        # Test basic operations
        collections = list_collections(client)

        return {
            'status': 'healthy',
            'accessible': True,
            'collections_count': len(collections),
            'collections': collections
        }

    except Exception as e:
        return {
            'status': 'unhealthy',
            'accessible': False,
            'collections_count': 0,
            'collections': [],
            'error': str(e)
        }
