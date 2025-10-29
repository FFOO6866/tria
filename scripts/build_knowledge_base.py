#!/usr/bin/env python3
"""
Build RAG Knowledge Base
=========================

One-time setup script to index all policy documents into ChromaDB collections.

Features:
- Processes all .docx files in doc/policy/
- Creates embeddings using OpenAI text-embedding-3-small
- Stores in persistent ChromaDB at data/chromadb/
- Progress tracking and error handling

Collections Created:
- policies_en: TRIA Rules and Policies
- faqs_en: Product FAQ Handbook
- escalation_rules: Escalation Routing Guide
- tone_personality: Tone and Personality Guidelines

Usage:
    python scripts/build_knowledge_base.py

    # Reset and rebuild
    python scripts/build_knowledge_base.py --reset

NO MOCKS, NO SHORTCUTS - Production ready
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.knowledge_indexer import index_policy_documents, verify_indexing
from src.rag.chroma_client import list_collections, get_collection_stats

# Load environment
load_dotenv(project_root / ".env")

# Configuration
POLICY_DIR = project_root / "doc" / "policy"
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def validate_environment():
    """Validate required environment and files"""
    errors = []

    # Check OpenAI API key
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not found in environment variables (.env file)")

    # Check policy directory
    if not POLICY_DIR.exists():
        errors.append(f"Policy directory not found: {POLICY_DIR}")

    # Check for .docx files
    if POLICY_DIR.exists():
        docx_files = list(POLICY_DIR.glob("*.docx"))
        if len(docx_files) == 0:
            errors.append(f"No .docx files found in {POLICY_DIR}")

    if errors:
        print("=" * 70)
        print("VALIDATION ERRORS")
        print("=" * 70)
        for error in errors:
            print(f"  ❌ {error}")
        print("=" * 70)
        sys.exit(1)


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Build RAG Knowledge Base from policy documents")
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset all collections before indexing (WARNING: deletes existing data)'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing collections without indexing'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("BUILD RAG KNOWLEDGE BASE")
    print("=" * 70)

    # Validate environment
    print("\n[>>] Validating environment...")
    validate_environment()
    print("[OK] Environment validated")

    # Verify only mode
    if args.verify_only:
        print("\n[>>] Verifying existing collections...")
        stats = verify_indexing(OPENAI_API_KEY)

        print("\nCollection Statistics:")
        print("-" * 70)
        for collection_name, count in stats.items():
            status = "[OK]" if count > 0 else "[EMPTY]"
            print(f"  {status:8s} {collection_name:30s} {count:5d} chunks")
        print("-" * 70)

        total_chunks = sum(stats.values())
        if total_chunks > 0:
            print(f"\n[OK] Knowledge base contains {total_chunks} total chunks")
        else:
            print("\n[WARNING] Knowledge base is empty - run without --verify-only to index documents")

        sys.exit(0)

    # Show warning for reset
    if args.reset:
        print("\n" + "!" * 70)
        print("WARNING: --reset will DELETE all existing knowledge base data")
        print("!" * 70)
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("[CANCELLED] Indexing cancelled by user")
            sys.exit(0)

    # Index policy documents
    try:
        results = index_policy_documents(
            policy_dir=POLICY_DIR,
            api_key=OPENAI_API_KEY,
            reset_collections=args.reset
        )

        # Verify indexing
        print("\n[>>] Verifying collections...")
        stats = verify_indexing(OPENAI_API_KEY)

        print("\nFinal Collection Statistics:")
        print("-" * 70)
        for collection_name, count in stats.items():
            status = "[OK]" if count > 0 else "[EMPTY]"
            print(f"  {status:8s} {collection_name:30s} {count:5d} chunks")
        print("-" * 70)

        total_chunks = sum(stats.values())
        print(f"\n[OK] Knowledge base built successfully with {total_chunks} total chunks!")

        print("\nNext steps:")
        print("  1. Test retrieval: python scripts/test_rag_retrieval.py")
        print("  2. Integrate with LLM agent workflows")

    except Exception as e:
        print(f"\n[ERROR] Failed to build knowledge base: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
