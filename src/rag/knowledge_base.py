"""
Knowledge Base Wrapper - High-Level API for RAG System
========================================================

Production-ready knowledge base interface that combines document processing,
indexing, and retrieval into a simple API.

Features:
- Unified interface for RAG operations
- Automatic collection management
- Multi-collection search capabilities
- LLM-ready context formatting
- Production error handling

Architecture:
    This module wraps the lower-level modules:
    - document_processor.py: Text extraction and chunking
    - knowledge_indexer.py: Embedding generation and indexing
    - retrieval.py: Semantic search and retrieval
    - chroma_client.py: ChromaDB client management

Usage:
    from src.rag.knowledge_base import KnowledgeBase

    # Initialize
    kb = KnowledgeBase(api_key=os.getenv("OPENAI_API_KEY"))

    # Index documents
    kb.index_documents(policy_dir="doc/policy/")

    # Search
    results = kb.search("What is the return policy?")
    llm_context = kb.format_for_llm(results)
"""

import os
from pathlib import Path
from typing import List, Dict, Optional

from .document_processor import process_document, process_directory
from .knowledge_indexer import index_policy_documents, verify_indexing
from .retrieval import (
    search_policies,
    search_faqs,
    search_escalation_rules,
    search_tone_guidelines,
    search_all_collections,
    format_results_for_llm,
    format_multi_collection_results_for_llm
)
from .chroma_client import get_chroma_client, get_collection_stats, list_collections


class KnowledgeBase:
    """
    High-level knowledge base interface for RAG operations

    This class provides a simple API for:
    - Indexing policy documents
    - Searching knowledge base
    - Formatting results for LLM prompts
    - Managing collections

    Attributes:
        api_key: OpenAI API key for embeddings
        client: ChromaDB client instance
    """

    def __init__(self, api_key: str):
        """
        Initialize knowledge base

        Args:
            api_key: OpenAI API key for embeddings

        Raises:
            ValueError: If API key is not provided
            RuntimeError: If ChromaDB initialization fails
        """
        if not api_key:
            raise ValueError("OpenAI API key is required for knowledge base operations")

        self.api_key = api_key
        self.client = get_chroma_client()

    def index_documents(
        self,
        policy_dir: Path,
        reset_collections: bool = False
    ) -> Dict[str, List[Dict]]:
        """
        Index all policy documents from a directory

        Args:
            policy_dir: Directory containing .docx policy files
            reset_collections: If True, reset collections before indexing

        Returns:
            Dictionary with indexing results per collection

        Raises:
            FileNotFoundError: If directory doesn't exist
            RuntimeError: If indexing fails
        """
        return index_policy_documents(
            policy_dir=Path(policy_dir),
            api_key=self.api_key,
            reset_collections=reset_collections
        )

    def search(
        self,
        query: str,
        collection: str = "all",
        top_n: int = 5,
        min_similarity: Optional[float] = None
    ) -> List[Dict]:
        """
        Search knowledge base for relevant information

        Args:
            query: Search query text
            collection: Collection to search ('policies', 'faqs', 'escalation', 'tone', or 'all')
            top_n: Number of results to return (per collection if 'all')
            min_similarity: Optional minimum similarity threshold (0-1)

        Returns:
            List of search results (or dict with results per collection if 'all')

        Raises:
            ValueError: If collection name is invalid
            RuntimeError: If search fails
        """
        if collection == "all":
            return search_all_collections(
                query=query,
                api_key=self.api_key,
                top_n_per_collection=top_n,
                min_similarity=min_similarity
            )
        elif collection == "policies":
            return search_policies(query, self.api_key, top_n, min_similarity)
        elif collection == "faqs":
            return search_faqs(query, self.api_key, top_n, min_similarity)
        elif collection == "escalation":
            return search_escalation_rules(query, self.api_key, top_n, min_similarity)
        elif collection == "tone":
            return search_tone_guidelines(query, self.api_key, top_n, min_similarity)
        else:
            raise ValueError(
                f"Invalid collection '{collection}'. "
                f"Valid options: 'policies', 'faqs', 'escalation', 'tone', 'all'"
            )

    def format_for_llm(
        self,
        results: List[Dict],
        collection_type: str = "knowledge"
    ) -> str:
        """
        Format search results for LLM context

        Args:
            results: List of search results
            collection_type: Type of collection for header

        Returns:
            Formatted text for LLM prompt
        """
        # Handle multi-collection results (from search with collection='all')
        if isinstance(results, dict):
            return format_multi_collection_results_for_llm(results)

        # Handle single collection results
        return format_results_for_llm(results, collection_type)

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics for all collections

        Returns:
            Dictionary mapping collection names to document counts
        """
        return verify_indexing(self.api_key)

    def list_collections(self) -> List[str]:
        """
        List all collections in the knowledge base

        Returns:
            List of collection names
        """
        return list_collections(self.client)

    def get_collection_info(self, collection_name: str) -> Dict:
        """
        Get detailed information about a collection

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection statistics

        Raises:
            ValueError: If collection doesn't exist
        """
        return get_collection_stats(collection_name, self.client)

    def retrieve_context(
        self,
        query: str,
        collections: List[str] = ["policies", "faqs"],
        top_n_per_collection: int = 3
    ) -> str:
        """
        Retrieve relevant context from multiple collections and format for LLM

        This is a convenience method that combines search and formatting.

        Args:
            query: Search query text
            collections: List of collections to search
            top_n_per_collection: Number of results per collection

        Returns:
            Formatted context ready for LLM prompt

        Example:
            context = kb.retrieve_context(
                "What is the return policy?",
                collections=["policies", "faqs"]
            )

            system_prompt = f'''
            You are TRIA customer support.

            {context}

            Answer the customer's question using the information above.
            '''
        """
        all_results = {}

        for collection in collections:
            try:
                results = self.search(
                    query=query,
                    collection=collection,
                    top_n=top_n_per_collection
                )
                all_results[collection] = results
            except Exception as e:
                print(f"[WARNING] Failed to search {collection}: {str(e)}")
                all_results[collection] = []

        return format_multi_collection_results_for_llm(all_results)


# Convenience functions for backward compatibility
def index_documents(policy_dir: Path, api_key: str, reset_collections: bool = False) -> Dict[str, List[Dict]]:
    """
    Convenience function to index documents without creating KnowledgeBase instance

    Args:
        policy_dir: Directory containing .docx policy files
        api_key: OpenAI API key
        reset_collections: If True, reset collections before indexing

    Returns:
        Dictionary with indexing results per collection
    """
    kb = KnowledgeBase(api_key)
    return kb.index_documents(policy_dir, reset_collections)


def retrieve_knowledge(query: str, api_key: str, collection: str = "all", top_n: int = 5) -> List[Dict]:
    """
    Convenience function to search knowledge base without creating KnowledgeBase instance

    Args:
        query: Search query text
        api_key: OpenAI API key
        collection: Collection to search
        top_n: Number of results to return

    Returns:
        List of search results
    """
    kb = KnowledgeBase(api_key)
    return kb.search(query, collection, top_n)


def semantic_search(query: str, api_key: str, top_n: int = 5) -> List[Dict]:
    """
    Convenience function for semantic search across all collections

    Args:
        query: Search query text
        api_key: OpenAI API key
        top_n: Number of results per collection

    Returns:
        Dictionary with results from all collections
    """
    kb = KnowledgeBase(api_key)
    return kb.search(query, collection="all", top_n=top_n)
