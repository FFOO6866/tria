#!/usr/bin/env python3
"""
Build RAG Knowledge Base from Markdown
=======================================

Index markdown policy documents into ChromaDB collections.

This version processes the comprehensive markdown files in docs/policy/en/
instead of the minimal .docx summaries.

Usage:
    python scripts/build_knowledge_base_from_markdown.py
    python scripts/build_knowledge_base_from_markdown.py --reset --yes

NO MOCKS, NO SHORTCUTS - Production ready
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.document_processor import chunk_text, count_tokens
from src.rag.chroma_client import get_chroma_client, get_or_create_collection
from openai import OpenAI
import time

# Load environment
load_dotenv(project_root / ".env")

# Configuration
POLICY_EN_DIR = project_root / "docs" / "policy" / "en"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Collection mapping (same as knowledge_indexer.py)
DOCUMENT_COLLECTIONS = {
    "Rules_and_Policies": "policies_en",
    "Product_FAQ": "faqs_en",
    "Escalation_Routing": "escalation_rules",
    "Tone_and_Personality": "tone_personality"
}


def get_collection_for_file(filename: str) -> str:
    """Determine collection based on filename"""
    if "Rules_and_Policies" in filename or "Rules" in filename:
        return "policies_en"
    elif "Product_FAQ" in filename or "FAQ" in filename:
        return "faqs_en"
    elif "Escalation" in filename:
        return "escalation_rules"
    elif "Tone" in filename or "Personality" in filename:
        return "tone_personality"
    else:
        raise ValueError(f"Unknown document type: {filename}")


def index_markdown_document(
    file_path: Path,
    api_key: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100
):
    """
    Index a single markdown document

    Args:
        file_path: Path to markdown file
        api_key: OpenAI API key for embeddings
        chunk_size: Max tokens per chunk
        chunk_overlap: Overlap between chunks

    Returns:
        Dict with indexing results
    """
    print(f"\n[>>] Processing: {file_path.name}")

    # Read markdown file
    with open(file_path, 'r', encoding='utf-8') as f:
        full_text = f.read()

    if not full_text.strip():
        raise RuntimeError(f"File is empty: {file_path}")

    # Determine collection
    collection_name = get_collection_for_file(file_path.name)
    print(f"    Collection: {collection_name}")

    # Chunk the document
    chunks = chunk_text(full_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"    Chunks: {len(chunks)}")

    if len(chunks) > 0:
        avg_tokens = sum(count_tokens(c) for c in chunks) / len(chunks)
        print(f"    Avg chunk size: {avg_tokens:.0f} tokens")

    # Get or create collection
    client = get_chroma_client()
    collection = get_or_create_collection(collection_name, api_key, client)

    # Generate embeddings and index
    openai_client = OpenAI(api_key=api_key)

    # Process in batches
    batch_size = 10
    indexed_count = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        # Generate embeddings for batch
        embeddings_response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )

        embeddings = [e.embedding for e in embeddings_response.data]

        # Prepare metadata
        ids = [f"{file_path.stem}_chunk_{i+j}" for j in range(len(batch))]
        metadatas = [
            {
                "source": file_path.name,
                "chunk_index": i + j,
                "total_chunks": len(chunks),
                "collection": collection_name
            }
            for j in range(len(batch))
        ]

        # Add to collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=batch,
            metadatas=metadatas
        )

        indexed_count += len(batch)
        print(f"    [OK] Indexed batch {(i//batch_size)+1}/{(len(chunks)+batch_size-1)//batch_size}")

        # Small delay to avoid rate limits
        time.sleep(0.1)

    print(f"    [OK] Successfully indexed {indexed_count} chunks")

    return {
        "filename": file_path.name,
        "collection": collection_name,
        "chunks": len(chunks),
        "success": True
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build RAG from markdown files")
    parser.add_argument('--reset', action='store_true', help='Reset collections first')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation')
    args = parser.parse_args()

    print("=" * 70)
    print("BUILD RAG KNOWLEDGE BASE FROM MARKDOWN")
    print("=" * 70)

    # Validate environment
    if not OPENAI_API_KEY:
        print("\n[ERROR] OPENAI_API_KEY not found in environment")
        sys.exit(1)

    if not POLICY_EN_DIR.exists():
        print(f"\n[ERROR] Policy directory not found: {POLICY_EN_DIR}")
        sys.exit(1)

    # Find markdown files (exclude README)
    md_files = [f for f in POLICY_EN_DIR.glob("*.md") if "README" not in f.name]

    if len(md_files) == 0:
        print(f"\n[ERROR] No markdown files found in {POLICY_EN_DIR}")
        sys.exit(1)

    print(f"\n[OK] Found {len(md_files)} markdown files to index")
    for f in md_files:
        print(f"  - {f.name}")

    # Reset collections if requested
    if args.reset:
        if not args.yes:
            response = input("\n[WARNING] Reset will delete existing data. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("[CANCELLED]")
                sys.exit(0)

        print("\n[>>] Resetting collections...")
        client = get_chroma_client()
        for collection_name in DOCUMENT_COLLECTIONS.values():
            try:
                get_or_create_collection(collection_name, OPENAI_API_KEY, client, reset=True)
                print(f"    [OK] Reset: {collection_name}")
            except Exception as e:
                print(f"    [WARNING] Could not reset {collection_name}: {e}")

    # Index all documents
    print("\n[>>] Indexing documents...")
    start_time = time.time()

    success_count = 0
    results_by_collection = {name: [] for name in DOCUMENT_COLLECTIONS.values()}

    for idx, file_path in enumerate(md_files, 1):
        print(f"\n[{idx}/{len(md_files)}]")
        try:
            result = index_markdown_document(file_path, OPENAI_API_KEY)
            results_by_collection[result['collection']].append(result)
            success_count += 1
        except Exception as e:
            print(f"    [ERROR] Failed: {str(e)}")
            import traceback
            traceback.print_exc()

    duration = time.time() - start_time

    # Summary
    print("\n" + "=" * 70)
    print("INDEXING COMPLETE")
    print("=" * 70)
    print(f"\nSuccessfully indexed: {success_count}/{len(md_files)}")
    print(f"Duration: {duration:.1f} seconds")

    print("\nCollections Summary:")
    total_chunks = 0
    for collection_name, results in results_by_collection.items():
        chunks = sum(r['chunks'] for r in results)
        total_chunks += chunks
        if chunks > 0:
            print(f"  - {collection_name}: {len(results)} docs, {chunks} chunks")

    print(f"\n[OK] Total chunks indexed: {total_chunks}")

    print("\nNext steps:")
    print("  1. Verify: python scripts/build_knowledge_base.py --verify-only")
    print("  2. Test: python scripts/test_rag_retrieval.py")


if __name__ == '__main__':
    main()
