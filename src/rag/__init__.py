"""
RAG (Retrieval-Augmented Generation) Knowledge Base Module
============================================================

ChromaDB-based vector database infrastructure for policy documents,
FAQs, and escalation rules.

Features:
- OpenAI text-embedding-3-small embeddings (same as product search)
- Persistent storage in data/chromadb/
- Intelligent document chunking with overlap
- Semantic search over policy knowledge base

Usage:
    from src.rag import build_knowledge_base, search_policies

    # One-time setup
    build_knowledge_base()

    # Query knowledge base
    results = search_policies("What is the return policy?")
"""

from .chroma_client import get_chroma_client, get_or_create_collection
from .document_processor import extract_text_from_docx, chunk_text
from .knowledge_indexer import index_policy_documents
from .retrieval import search_knowledge_base, search_policies, search_faqs

__all__ = [
    'get_chroma_client',
    'get_or_create_collection',
    'extract_text_from_docx',
    'chunk_text',
    'index_policy_documents',
    'search_knowledge_base',
    'search_policies',
    'search_faqs',
]
