"""
RAG Knowledge Base Retrieval
==============================

Semantic search over ChromaDB collections for policy documents, FAQs, and escalation rules.

Features:
- Semantic search using OpenAI embeddings
- Multi-collection search capabilities
- Follows semantic_search.py patterns
- Production-ready error handling

Usage:
    from rag.retrieval import search_policies, search_faqs

    # Search policies
    results = search_policies("What is the return policy?", api_key="...")

    # Search FAQs
    results = search_faqs("How do I track my order?", api_key="...")
"""

import os
from typing import List, Dict, Optional
from openai import OpenAI

from .chroma_client import get_chroma_client, get_or_create_collection


def search_knowledge_base(
    query: str,
    collection_name: str,
    api_key: str,
    top_n: int = 5,
    min_similarity: Optional[float] = None
) -> List[Dict]:
    """
    Search a knowledge base collection using semantic similarity

    Args:
        query: Search query text
        collection_name: ChromaDB collection to search
        api_key: OpenAI API key for query embedding
        top_n: Number of top results to return
        min_similarity: Optional minimum similarity threshold (0-1)
                       Note: ChromaDB uses distance, not similarity

    Returns:
        List of search results with text and metadata:
        [
            {
                'text': 'chunk text...',
                'source': 'filename.docx',
                'chunk_index': 0,
                'distance': 0.15,  # Lower is more similar
                'id': 'doc_chunk_0'
            },
            ...
        ]

    Raises:
        ValueError: If collection doesn't exist
        RuntimeError: If search fails
    """
    # Get ChromaDB client and collection
    # IMPORTANT: Must use get_or_create_collection to get the collection WITH its embedding function
    # Using client.get_collection() alone doesn't preserve the embedding function
    client = get_chroma_client()

    try:
        collection = get_or_create_collection(
            collection_name=collection_name,
            api_key=api_key,
            client=client,
            reset=False
        )
    except Exception as e:
        raise ValueError(
            f"Collection '{collection_name}' not found. "
            f"Please run build_knowledge_base.py first. "
            f"Error: {str(e)}"
        ) from e

    # ChromaDB handles embedding generation automatically
    # Just pass the query text and it will use the collection's embedding function
    try:
        results = collection.query(
            query_texts=[query],
            n_results=top_n,
            include=['documents', 'metadatas', 'distances']
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to search collection '{collection_name}'. "
            f"Error: {str(e)}"
        ) from e

    # Format results
    formatted_results = []

    if not results['documents'] or not results['documents'][0]:
        return []  # No results found

    for idx in range(len(results['documents'][0])):
        distance = results['distances'][0][idx] if results['distances'] else None

        # Filter by minimum similarity if specified
        # Note: ChromaDB returns distance (lower is better), need to convert to similarity
        # Similarity ≈ 1 - (distance / 2) for cosine distance
        if min_similarity is not None and distance is not None:
            similarity = 1 - (distance / 2)
            if similarity < min_similarity:
                continue

        formatted_results.append({
            'text': results['documents'][0][idx],
            'source': results['metadatas'][0][idx].get('source', 'unknown'),
            'chunk_index': results['metadatas'][0][idx].get('chunk_index', 0),
            'total_chunks': results['metadatas'][0][idx].get('total_chunks', 0),
            'distance': distance,
            'similarity': 1 - (distance / 2) if distance is not None else None,
            'id': results['ids'][0][idx] if results['ids'] else None
        })

    return formatted_results


def search_policies(
    query: str,
    api_key: str,
    top_n: int = 5,
    min_similarity: Optional[float] = None
) -> List[Dict]:
    """
    Search TRIA policies collection

    Args:
        query: Search query text
        api_key: OpenAI API key
        top_n: Number of top results to return
        min_similarity: Optional minimum similarity threshold (0-1)

    Returns:
        List of relevant policy chunks
    """
    return search_knowledge_base(
        query=query,
        collection_name='policies_en',
        api_key=api_key,
        top_n=top_n,
        min_similarity=min_similarity
    )


def search_faqs(
    query: str,
    api_key: str,
    top_n: int = 5,
    min_similarity: Optional[float] = None
) -> List[Dict]:
    """
    Search TRIA FAQs collection

    Args:
        query: Search query text
        api_key: OpenAI API key
        top_n: Number of top results to return
        min_similarity: Optional minimum similarity threshold (0-1)

    Returns:
        List of relevant FAQ chunks
    """
    return search_knowledge_base(
        query=query,
        collection_name='faqs_en',
        api_key=api_key,
        top_n=top_n,
        min_similarity=min_similarity
    )


def search_escalation_rules(
    query: str,
    api_key: str,
    top_n: int = 3,
    min_similarity: Optional[float] = None
) -> List[Dict]:
    """
    Search escalation routing rules collection

    Args:
        query: Search query text
        api_key: OpenAI API key
        top_n: Number of top results to return
        min_similarity: Optional minimum similarity threshold (0-1)

    Returns:
        List of relevant escalation rule chunks
    """
    return search_knowledge_base(
        query=query,
        collection_name='escalation_rules',
        api_key=api_key,
        top_n=top_n,
        min_similarity=min_similarity
    )


def search_tone_guidelines(
    query: str,
    api_key: str,
    top_n: int = 3,
    min_similarity: Optional[float] = None
) -> List[Dict]:
    """
    Search TRIA tone and personality guidelines collection

    Args:
        query: Search query text
        api_key: OpenAI API key
        top_n: Number of top results to return
        min_similarity: Optional minimum similarity threshold (0-1)

    Returns:
        List of relevant tone guideline chunks
    """
    return search_knowledge_base(
        query=query,
        collection_name='tone_personality',
        api_key=api_key,
        top_n=top_n,
        min_similarity=min_similarity
    )


def search_all_collections(
    query: str,
    api_key: str,
    top_n_per_collection: int = 3,
    min_similarity: Optional[float] = None
) -> Dict[str, List[Dict]]:
    """
    Search all knowledge base collections

    Args:
        query: Search query text
        api_key: OpenAI API key
        top_n_per_collection: Number of results per collection
        min_similarity: Optional minimum similarity threshold (0-1)

    Returns:
        Dictionary with results from each collection:
        {
            'policies': [...],
            'faqs': [...],
            'escalation_rules': [...],
            'tone_guidelines': [...]
        }
    """
    results = {}

    # Search each collection
    try:
        results['policies'] = search_policies(query, api_key, top_n_per_collection, min_similarity)
    except Exception as e:
        print(f"[WARNING] Failed to search policies: {str(e)}")
        results['policies'] = []

    try:
        results['faqs'] = search_faqs(query, api_key, top_n_per_collection, min_similarity)
    except Exception as e:
        print(f"[WARNING] Failed to search FAQs: {str(e)}")
        results['faqs'] = []

    try:
        results['escalation_rules'] = search_escalation_rules(query, api_key, top_n_per_collection, min_similarity)
    except Exception as e:
        print(f"[WARNING] Failed to search escalation rules: {str(e)}")
        results['escalation_rules'] = []

    try:
        results['tone_guidelines'] = search_tone_guidelines(query, api_key, top_n_per_collection, min_similarity)
    except Exception as e:
        print(f"[WARNING] Failed to search tone guidelines: {str(e)}")
        results['tone_guidelines'] = []

    return results


def format_results_for_llm(results: List[Dict], collection_type: str = "knowledge") -> str:
    """
    Format search results for LLM context (follows semantic_search.py pattern)

    Args:
        results: List of search results
        collection_type: Type of collection for header

    Returns:
        Formatted text for LLM prompt
    """
    if len(results) == 0:
        return f"NO RELEVANT {collection_type.upper()} FOUND"

    context_text = f"RELEVANT {collection_type.upper()}:\n"
    context_text += "=" * 60 + "\n"

    for idx, result in enumerate(results, 1):
        similarity_pct = result['similarity'] * 100 if result['similarity'] else 0
        context_text += f"\n[{idx}] From: {result['source']} (Match: {similarity_pct:.1f}%)\n"
        context_text += f"{result['text']}\n"

    context_text += "=" * 60

    return context_text


def format_multi_collection_results_for_llm(results: Dict[str, List[Dict]]) -> str:
    """
    Format multi-collection search results for LLM context

    Args:
        results: Dictionary with results from multiple collections

    Returns:
        Formatted text for LLM prompt
    """
    sections = []

    if results.get('policies'):
        sections.append(format_results_for_llm(results['policies'], "POLICIES"))

    if results.get('faqs'):
        sections.append(format_results_for_llm(results['faqs'], "FAQs"))

    if results.get('escalation_rules'):
        sections.append(format_results_for_llm(results['escalation_rules'], "ESCALATION RULES"))

    if results.get('tone_guidelines'):
        sections.append(format_results_for_llm(results['tone_guidelines'], "TONE GUIDELINES"))

    if not sections:
        return "NO RELEVANT KNOWLEDGE BASE INFORMATION FOUND"

    return "\n\n".join(sections)
