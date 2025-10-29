"""
Knowledge Base Indexer
=======================

Processes policy documents and creates embeddings for ChromaDB collections.

Features:
- Automatic collection routing based on document type
- OpenAI text-embedding-3-small embeddings (same as products)
- Batch processing with progress tracking
- Production-ready error handling and retry logic

Document Type Mapping:
- TRIA_Rules_and_Policies_*.docx → policies_en
- TRIA_Product_FAQ_*.docx → faqs_en
- TRIA_Escalation_Routing_*.docx → escalation_rules
- TRIA_Tone_and_Personality_*.docx → tone_personality
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from openai import OpenAI

from .chroma_client import get_chroma_client, get_or_create_collection
from .document_processor import process_document, get_document_summary


# Document type to collection mapping
DOCUMENT_COLLECTIONS = {
    'rules_and_policies': 'policies_en',
    'product_faq': 'faqs_en',
    'escalation_routing': 'escalation_rules',
    'tone_and_personality': 'tone_personality'
}


def classify_document(filename: str) -> str:
    """
    Determine which collection a document belongs to based on filename

    Args:
        filename: Document filename

    Returns:
        Collection name (e.g., 'policies_en', 'faqs_en')

    Raises:
        ValueError: If document type cannot be determined
    """
    filename_lower = filename.lower()

    if 'rules_and_policies' in filename_lower or 'policy' in filename_lower:
        return DOCUMENT_COLLECTIONS['rules_and_policies']
    elif 'faq' in filename_lower:
        return DOCUMENT_COLLECTIONS['product_faq']
    elif 'escalation' in filename_lower:
        return DOCUMENT_COLLECTIONS['escalation_routing']
    elif 'tone_and_personality' in filename_lower or 'tone' in filename_lower:
        return DOCUMENT_COLLECTIONS['tone_and_personality']
    else:
        raise ValueError(
            f"Cannot classify document '{filename}'. "
            f"Expected one of: rules_and_policies, faq, escalation, tone_and_personality"
        )


def index_document(
    file_path: Path,
    api_key: str,
    collection_name: Optional[str] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    batch_size: int = 100
) -> Dict[str, any]:
    """
    Index a single document into ChromaDB collection

    Args:
        file_path: Path to .docx file
        api_key: OpenAI API key for embeddings
        collection_name: Optional collection name (auto-detected if None)
        chunk_size: Tokens per chunk
        chunk_overlap: Overlap tokens
        batch_size: Number of chunks to index at once

    Returns:
        Dictionary with indexing statistics

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If indexing fails
    """
    # Auto-classify if collection not specified
    if collection_name is None:
        collection_name = classify_document(file_path.name)

    print(f"\n[>>] Processing: {file_path.name}")
    print(f"    Collection: {collection_name}")

    # Process document into chunks
    chunks = process_document(file_path, chunk_size, chunk_overlap)
    summary = get_document_summary(chunks)

    print(f"    Chunks: {summary['total_chunks']}")
    print(f"    Avg chunk size: {summary['avg_tokens']} tokens")

    # Get or create collection
    client = get_chroma_client()
    collection = get_or_create_collection(collection_name, api_key, client)

    # Prepare data for ChromaDB
    documents = []
    metadatas = []
    ids = []

    for chunk in chunks:
        # Document text
        documents.append(chunk['text'])

        # Metadata
        metadatas.append({
            'source': chunk['source'],
            'chunk_index': chunk['chunk_index'],
            'total_chunks': chunk['total_chunks']
        })

        # Unique ID: filename_chunkindex
        chunk_id = f"{file_path.stem}_chunk_{chunk['chunk_index']}"
        ids.append(chunk_id)

    # Index in batches
    total_indexed = 0
    failed_count = 0

    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]

        try:
            # ChromaDB automatically generates embeddings via OpenAI
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )

            total_indexed += len(batch_docs)
            print(f"    [OK] Indexed batch {i // batch_size + 1}/{(len(documents) + batch_size - 1) // batch_size}")

            # Small delay to avoid rate limits
            time.sleep(0.1)

        except Exception as e:
            print(f"    [ERROR] Batch {i // batch_size + 1} failed: {str(e)}")
            failed_count += len(batch_docs)
            continue

    result = {
        'filename': file_path.name,
        'collection': collection_name,
        'total_chunks': len(chunks),
        'indexed': total_indexed,
        'failed': failed_count,
        'success': failed_count == 0
    }

    if result['success']:
        print(f"    [OK] Successfully indexed {total_indexed} chunks")
    else:
        print(f"    [WARNING] Indexed {total_indexed}/{len(chunks)} chunks ({failed_count} failed)")

    return result


def index_policy_documents(
    policy_dir: Path,
    api_key: str,
    file_pattern: str = "*.docx",
    reset_collections: bool = False
) -> Dict[str, List[Dict]]:
    """
    Index all policy documents from a directory

    Args:
        policy_dir: Directory containing policy .docx files
        api_key: OpenAI API key for embeddings
        file_pattern: Glob pattern for files
        reset_collections: If True, reset collections before indexing

    Returns:
        Dictionary with results per collection:
        {
            'policies_en': [result1, result2, ...],
            'faqs_en': [...],
            ...
        }

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    if not policy_dir.exists():
        raise FileNotFoundError(f"Policy directory not found: {policy_dir}")

    print("=" * 70)
    print("INDEXING POLICY DOCUMENTS FOR RAG KNOWLEDGE BASE")
    print("=" * 70)
    print(f"\nDirectory: {policy_dir}")
    print(f"Pattern: {file_pattern}")
    print(f"Reset collections: {reset_collections}")

    # Reset collections if requested
    if reset_collections:
        print("\n[>>] Resetting collections...")
        client = get_chroma_client()
        for collection_name in DOCUMENT_COLLECTIONS.values():
            try:
                get_or_create_collection(collection_name, api_key, client, reset=True)
                print(f"    [OK] Reset collection: {collection_name}")
            except Exception as e:
                print(f"    [WARNING] Could not reset {collection_name}: {str(e)}")

    # Find all policy documents
    docx_files = list(policy_dir.glob(file_pattern))

    if len(docx_files) == 0:
        raise FileNotFoundError(f"No .docx files found in {policy_dir}")

    print(f"\n[>>] Found {len(docx_files)} documents to index")

    # Track results by collection
    results_by_collection = {name: [] for name in DOCUMENT_COLLECTIONS.values()}
    overall_success = 0
    overall_failed = 0

    # Process each document
    start_time = time.time()

    for idx, file_path in enumerate(docx_files, 1):
        print(f"\n[{idx}/{len(docx_files)}]")

        try:
            result = index_document(file_path, api_key)
            results_by_collection[result['collection']].append(result)

            if result['success']:
                overall_success += 1
            else:
                overall_failed += 1

        except Exception as e:
            print(f"    [ERROR] Failed to index {file_path.name}: {str(e)}")
            overall_failed += 1
            continue

    end_time = time.time()
    duration = end_time - start_time

    # Print summary
    print("\n" + "=" * 70)
    print("INDEXING COMPLETE")
    print("=" * 70)

    print(f"\nOverall Results:")
    print(f"  - Successfully indexed: {overall_success}")
    print(f"  - Failed: {overall_failed}")
    print(f"  - Duration: {duration:.1f} seconds")

    print(f"\nCollections Summary:")
    for collection_name, results in results_by_collection.items():
        if results:
            total_chunks = sum(r['indexed'] for r in results)
            doc_count = len(results)
            print(f"  - {collection_name}: {doc_count} documents, {total_chunks} chunks")

    print("\n" + "=" * 70)

    return results_by_collection


def verify_indexing(api_key: str) -> Dict[str, int]:
    """
    Verify all collections have been indexed

    Args:
        api_key: OpenAI API key

    Returns:
        Dictionary mapping collection names to document counts
    """
    client = get_chroma_client()
    stats = {}

    for collection_name in DOCUMENT_COLLECTIONS.values():
        try:
            collection = client.get_collection(name=collection_name)
            count = collection.count()
            stats[collection_name] = count
        except Exception:
            stats[collection_name] = 0

    return stats
