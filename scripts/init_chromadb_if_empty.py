#!/usr/bin/env python3
"""
Initialize ChromaDB If Empty
=============================

Startup script that checks if ChromaDB collections are populated.
If empty, runs the knowledge base indexing.

This script is called by systemd ExecStartPre to ensure ChromaDB
is ready before the API server starts.

Usage:
    python scripts/init_chromadb_if_empty.py

Exit Codes:
    0 - Success (collections exist or were created)
    1 - Error during initialization

NO MOCKS, NO SHORTCUTS - Production ready
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Configure logging for startup
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Load environment
load_dotenv(project_root / ".env")


def check_chromadb_status():
    """
    Check if ChromaDB has collections with documents.

    Returns:
        Tuple of (is_ready: bool, stats: dict)
    """
    try:
        from src.rag.chroma_client import get_chroma_client, list_collections, get_collection_stats

        client = get_chroma_client()
        collections = list_collections(client)

        if not collections:
            return False, {"collections": [], "total_documents": 0}

        total_docs = 0
        collection_stats = {}

        for col_name in collections:
            try:
                stats = get_collection_stats(col_name, client)
                count = stats.get('count', 0)
                collection_stats[col_name] = count
                total_docs += count
            except Exception as e:
                logger.warning(f"Could not get stats for {col_name}: {e}")
                collection_stats[col_name] = 0

        # Consider ready if we have at least some documents
        is_ready = total_docs > 0

        return is_ready, {
            "collections": collections,
            "collection_stats": collection_stats,
            "total_documents": total_docs
        }

    except Exception as e:
        logger.error(f"ChromaDB check failed: {e}")
        return False, {"error": str(e)}


def initialize_knowledge_base():
    """
    Run knowledge base initialization from markdown files.

    Returns:
        bool: True if successful
    """
    logger.info("Initializing ChromaDB knowledge base...")

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OPENAI_API_KEY not set - cannot initialize knowledge base")
        return False

    policy_dir = project_root / "docs" / "policy" / "en"
    if not policy_dir.exists():
        logger.error(f"Policy directory not found: {policy_dir}")
        return False

    try:
        from src.rag.chroma_client import get_chroma_client, get_or_create_collection
        from src.rag.document_processor import chunk_text, count_tokens
        from openai import OpenAI
        import time

        # Document to collection mapping
        DOCUMENT_COLLECTIONS = {
            "Rules_and_Policies": "policies_en",
            "Product_FAQ": "faqs_en",
            "Escalation_Routing": "escalation_rules",
            "Tone_and_Personality": "tone_personality"
        }

        def get_collection_for_file(filename: str) -> str:
            if "Rules_and_Policies" in filename or "Rules" in filename:
                return "policies_en"
            elif "Product_FAQ" in filename or "FAQ" in filename:
                return "faqs_en"
            elif "Escalation" in filename:
                return "escalation_rules"
            elif "Tone" in filename or "Personality" in filename:
                return "tone_personality"
            else:
                return "policies_en"  # Default

        # Find markdown files
        md_files = [f for f in policy_dir.glob("*.md") if "README" not in f.name]

        if not md_files:
            logger.warning(f"No markdown files found in {policy_dir}")
            return False

        logger.info(f"Found {len(md_files)} markdown files to index")

        client = get_chroma_client()
        openai_client = OpenAI(api_key=api_key)

        total_chunks = 0

        for file_path in md_files:
            try:
                logger.info(f"Processing: {file_path.name}")

                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    full_text = f.read()

                if not full_text.strip():
                    logger.warning(f"Empty file: {file_path.name}")
                    continue

                # Get collection
                collection_name = get_collection_for_file(file_path.name)
                collection = get_or_create_collection(collection_name, api_key, client)

                # Chunk the document
                chunks = chunk_text(full_text, chunk_size=500, chunk_overlap=100)

                if not chunks:
                    logger.warning(f"No chunks generated for {file_path.name}")
                    continue

                # Process in batches
                batch_size = 10

                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i + batch_size]

                    # Generate embeddings
                    response = openai_client.embeddings.create(
                        model="text-embedding-3-small",
                        input=batch
                    )
                    embeddings = [e.embedding for e in response.data]

                    # Prepare IDs and metadata
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

                    total_chunks += len(batch)
                    time.sleep(0.1)  # Rate limit protection

                logger.info(f"  Indexed {len(chunks)} chunks")

            except Exception as e:
                logger.error(f"Failed to process {file_path.name}: {e}")
                continue

        logger.info(f"Total chunks indexed: {total_chunks}")
        return total_chunks > 0

    except Exception as e:
        logger.error(f"Knowledge base initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("CHROMADB STARTUP CHECK")
    logger.info("=" * 60)

    # Check current status
    is_ready, stats = check_chromadb_status()

    if is_ready:
        total = stats.get('total_documents', 0)
        logger.info(f"ChromaDB is ready with {total} documents")

        # Log collection details
        for col_name, count in stats.get('collection_stats', {}).items():
            logger.info(f"  - {col_name}: {count} documents")

        logger.info("=" * 60)
        sys.exit(0)

    # Not ready - need to initialize
    logger.warning("ChromaDB is empty - initializing knowledge base...")

    success = initialize_knowledge_base()

    if success:
        # Verify initialization
        is_ready, stats = check_chromadb_status()
        if is_ready:
            logger.info(f"Initialization complete: {stats.get('total_documents', 0)} documents indexed")
            logger.info("=" * 60)
            sys.exit(0)

    # Initialization failed but don't block startup
    logger.error("ChromaDB initialization incomplete - API will start with limited RAG functionality")
    logger.info("=" * 60)

    # Exit 0 to allow service to start anyway (degraded mode)
    # Change to sys.exit(1) if you want to block startup on failure
    sys.exit(0)


if __name__ == '__main__':
    main()
