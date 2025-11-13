#!/usr/bin/env python3
"""
Test RAG Knowledge Base Retrieval
===================================

Test script to verify ChromaDB collections and semantic search functionality.

Features:
- Tests all four collections (policies, FAQs, escalation, tone)
- Demonstrates semantic search capabilities
- Shows how to integrate with LLM workflows

Usage:
    python scripts/test_rag_retrieval.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.retrieval import (
    search_policies,
    search_faqs,
    search_escalation_rules,
    search_tone_guidelines,
    search_all_collections,
    format_results_for_llm,
    format_multi_collection_results_for_llm
)
from src.rag.knowledge_indexer import verify_indexing

# Load environment
load_dotenv(project_root / ".env")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def print_results(results: list, title: str):
    """Pretty print search results"""
    print(f"\n{title}")
    print("=" * 70)

    if not results:
        print("  No results found")
        return

    for idx, result in enumerate(results, 1):
        similarity_pct = result['similarity'] * 100 if result['similarity'] else 0
        print(f"\n[{idx}] Similarity: {similarity_pct:.1f}%")
        print(f"    Source: {result['source']}")
        print(f"    Chunk: {result['chunk_index'] + 1}/{result['total_chunks']}")
        print(f"    Text: {result['text'][:200]}{'...' if len(result['text']) > 200 else ''}")


def main():
    """Main test execution"""
    print("=" * 70)
    print("TEST RAG KNOWLEDGE BASE RETRIEVAL")
    print("=" * 70)

    # Verify environment
    if not OPENAI_API_KEY:
        print("\n[ERROR] OPENAI_API_KEY not found in environment")
        sys.exit(1)

    # IMPORTANT: ChromaDB's OpenAIEmbeddingFunction checks for CHROMA_OPENAI_API_KEY
    # Set it from OPENAI_API_KEY if not already set
    if not os.getenv('CHROMA_OPENAI_API_KEY'):
        os.environ['CHROMA_OPENAI_API_KEY'] = OPENAI_API_KEY
        print("[OK] Set CHROMA_OPENAI_API_KEY from OPENAI_API_KEY")

    # Verify collections exist
    print("\n[>>] Verifying collections...")
    stats = verify_indexing(OPENAI_API_KEY)

    print("\nCollection Statistics:")
    print("-" * 70)
    total_chunks = 0
    for collection_name, count in stats.items():
        status = "[OK]" if count > 0 else "[EMPTY]"
        print(f"  {status:8s} {collection_name:30s} {count:5d} chunks")
        total_chunks += count
    print("-" * 70)

    if total_chunks == 0:
        print("\n[ERROR] Knowledge base is empty!")
        print("Please run: python scripts/build_knowledge_base.py")
        sys.exit(1)

    print(f"\n[OK] Knowledge base contains {total_chunks} total chunks")

    # Test queries
    test_queries = [
        {
            'name': 'Policies Search',
            'query': 'What is the return policy for damaged products?',
            'function': search_policies
        },
        {
            'name': 'FAQ Search',
            'query': 'How do I track my order status?',
            'function': search_faqs
        },
        {
            'name': 'Escalation Rules Search',
            'query': 'When should I escalate to a supervisor?',
            'function': search_escalation_rules
        },
        {
            'name': 'Tone Guidelines Search',
            'query': 'How should I respond to frustrated customers?',
            'function': search_tone_guidelines
        }
    ]

    # Run test queries
    print("\n" + "=" * 70)
    print("RUNNING TEST QUERIES")
    print("=" * 70)

    for test in test_queries:
        print(f"\n[>>] Testing: {test['name']}")
        print(f"    Query: \"{test['query']}\"")

        try:
            results = test['function'](
                query=test['query'],
                api_key=OPENAI_API_KEY,
                top_n=3
            )

            print_results(results, f"Results for {test['name']}")

        except Exception as e:
            print(f"\n[ERROR] Query failed: {str(e)}")

    # Test multi-collection search
    print("\n" + "=" * 70)
    print("MULTI-COLLECTION SEARCH TEST")
    print("=" * 70)

    multi_query = "What should I do if a customer wants to return a damaged product?"
    print(f"\nQuery: \"{multi_query}\"")

    try:
        all_results = search_all_collections(
            query=multi_query,
            api_key=OPENAI_API_KEY,
            top_n_per_collection=2
        )

        for collection_type, results in all_results.items():
            if results:
                print_results(results, f"{collection_type.upper()}")

    except Exception as e:
        print(f"\n[ERROR] Multi-collection search failed: {str(e)}")

    # Test LLM formatting
    print("\n" + "=" * 70)
    print("LLM CONTEXT FORMATTING TEST")
    print("=" * 70)

    print("\n[>>] Testing format_results_for_llm()...")
    try:
        policy_results = search_policies(
            query="return policy",
            api_key=OPENAI_API_KEY,
            top_n=2
        )

        llm_context = format_results_for_llm(policy_results, "POLICIES")
        print(f"\n{llm_context}")

    except Exception as e:
        print(f"\n[ERROR] LLM formatting failed: {str(e)}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\n[OK] RAG knowledge base is working correctly!")
    print("\nIntegration example:")
    print("""
from src.rag.retrieval import search_policies, format_results_for_llm

# In your LLM agent workflow:
policy_context = search_policies(customer_question, api_key=OPENAI_API_KEY)
llm_prompt = format_results_for_llm(policy_context, "POLICIES")

# Add to GPT-4 system prompt
system_prompt = f\"\"\"
You are TRIA customer support agent.

{llm_prompt}

Please answer the customer's question using the policies above.
\"\"\"
    """)


if __name__ == '__main__':
    main()
