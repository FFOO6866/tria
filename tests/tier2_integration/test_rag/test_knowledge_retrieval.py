#!/usr/bin/env python3
"""
TIER 2 INTEGRATION TESTS - Knowledge Retrieval
===============================================

Tests semantic search and knowledge retrieval with REAL ChromaDB.

REQUIREMENTS:
- Speed: < 5 seconds per test
- Infrastructure: Real ChromaDB instance
- NO MOCKING: Absolutely forbidden
- Focus: RAG retrieval accuracy with real embeddings

CRITICAL SETUP:
ChromaDB must be running with real data.
Data directory: C:/Users/fujif/OneDrive/Documents/GitHub/tria/data/chromadb/

TEST COVERAGE:
1. Basic semantic search over policy documents
2. Query accuracy with different question types
3. Multi-language query support
4. Relevance scoring validation
5. Top-k retrieval correctness
"""

import pytest
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# ChromaDB imports
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    pytest.skip("ChromaDB not installed", allow_module_level=True)


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def chromadb_client():
    """
    Create ChromaDB client connected to REAL database.
    NO MOCKING - uses actual ChromaDB instance.

    CRITICAL: Uses test-specific path to avoid conflicts with production ChromaDB
    """
    # Use TEST-SPECIFIC persistent storage (NOT production path)
    data_dir = project_root / "data" / "chromadb_test"
    data_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(data_dir),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True  # For test cleanup
        )
    )

    yield client

    # Cleanup after all tests in module
    # Note: Be careful with reset in production-like environments


@pytest.fixture(scope="module")
def policy_collection(chromadb_client):
    """
    Create or get policy document collection with REAL data.
    NO MOCKING - loads actual policy documents.
    """
    collection_name = "test_policies"

    # Try to get existing collection or create new one
    try:
        collection = chromadb_client.get_collection(name=collection_name)
    except Exception:
        collection = chromadb_client.create_collection(
            name=collection_name,
            metadata={"description": "Test policy documents"}
        )

    # Load test policy documents if collection is empty
    if collection.count() == 0:
        # Load from fixtures
        fixtures_dir = project_root / "tests" / "fixtures" / "policies"

        documents = []
        metadatas = []
        ids = []

        # Load refund policy
        refund_path = fixtures_dir / "refund_policy.txt"
        if refund_path.exists():
            with open(refund_path, 'r', encoding='utf-8') as f:
                text = f.read()
                # Split into chunks (simple splitting for test)
                chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
                for idx, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "source": "refund_policy.txt",
                        "chunk_index": idx,
                        "policy_type": "refund"
                    })
                    ids.append(f"refund_{idx}")

        # Load cancellation policy
        cancel_path = fixtures_dir / "cancellation_policy.txt"
        if cancel_path.exists():
            with open(cancel_path, 'r', encoding='utf-8') as f:
                text = f.read()
                chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
                for idx, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "source": "cancellation_policy.txt",
                        "chunk_index": idx,
                        "policy_type": "cancellation"
                    })
                    ids.append(f"cancel_{idx}")

        # Load shipping policy
        shipping_path = fixtures_dir / "shipping_policy.txt"
        if shipping_path.exists():
            with open(shipping_path, 'r', encoding='utf-8') as f:
                text = f.read()
                chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
                for idx, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "source": "shipping_policy.txt",
                        "chunk_index": idx,
                        "policy_type": "shipping"
                    })
                    ids.append(f"shipping_{idx}")

        # Add to collection (REAL ChromaDB operation)
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

    yield collection


@pytest.fixture(scope="module")
def expected_results():
    """Load expected query results from fixtures."""
    fixtures_dir = project_root / "tests" / "fixtures" / "conversations"
    expected_path = fixtures_dir / "expected_results.json"

    with open(expected_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================================
# TIER 2 INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_basic_semantic_search(policy_collection):
    """Test basic semantic search retrieves relevant documents."""
    # REAL ChromaDB query - NO MOCKING
    results = policy_collection.query(
        query_texts=["What is your refund policy?"],
        n_results=3
    )

    # Validate results structure
    assert "documents" in results
    assert "distances" in results
    assert "metadatas" in results

    # Should retrieve documents
    assert len(results["documents"][0]) > 0

    # Check that refund-related content was retrieved
    retrieved_text = " ".join(results["documents"][0]).lower()
    assert any(keyword in retrieved_text for keyword in ["refund", "return", "money back"])


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_refund_policy_queries(policy_collection, expected_results):
    """Test refund policy queries return accurate results."""
    refund_queries = expected_results["expected_rag_results"]["refund_policy_queries"]

    for test_case in refund_queries:
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]
        min_score = test_case["min_relevance_score"]
        expected_chunks = test_case["expected_chunks"]

        # REAL ChromaDB query
        results = policy_collection.query(
            query_texts=[query],
            n_results=expected_chunks
        )

        # Validate retrieval
        assert len(results["documents"][0]) >= 1, f"No results for query: {query}"

        # Check keywords present in retrieved documents
        retrieved_text = " ".join(results["documents"][0]).lower()
        keywords_found = sum(
            1 for keyword in expected_keywords
            if keyword.lower() in retrieved_text
        )

        # At least 50% of keywords should be present
        assert keywords_found >= len(expected_keywords) * 0.5, \
            f"Query '{query}' missing expected keywords. Found {keywords_found}/{len(expected_keywords)}"

        # Check relevance scores (distances - lower is better)
        # ChromaDB returns distances, not similarity scores
        # Distances should be reasonably low (< 1.0 for good matches)
        if results["distances"][0]:
            avg_distance = sum(results["distances"][0]) / len(results["distances"][0])
            # Convert to similarity approximation
            approx_similarity = 1 / (1 + avg_distance)
            assert approx_similarity >= min_score * 0.8, \
                f"Query '{query}' relevance too low: {approx_similarity:.2f} < {min_score * 0.8:.2f}"


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_cancellation_policy_queries(policy_collection, expected_results):
    """Test cancellation policy queries return accurate results."""
    cancel_queries = expected_results["expected_rag_results"]["cancellation_policy_queries"]

    for test_case in cancel_queries:
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]

        # REAL ChromaDB query
        results = policy_collection.query(
            query_texts=[query],
            n_results=3
        )

        # Validate retrieval
        assert len(results["documents"][0]) >= 1

        # Check for cancellation-related content
        retrieved_text = " ".join(results["documents"][0]).lower()
        keywords_found = sum(
            1 for keyword in expected_keywords
            if keyword.lower() in retrieved_text
        )

        assert keywords_found >= len(expected_keywords) * 0.5, \
            f"Query '{query}' missing expected keywords"


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_shipping_policy_queries(policy_collection, expected_results):
    """Test shipping policy queries return accurate results."""
    shipping_queries = expected_results["expected_rag_results"]["shipping_policy_queries"]

    for test_case in shipping_queries:
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]

        # REAL ChromaDB query
        results = policy_collection.query(
            query_texts=[query],
            n_results=3
        )

        # Validate retrieval
        assert len(results["documents"][0]) >= 1

        # Check for shipping-related content
        retrieved_text = " ".join(results["documents"][0]).lower()
        keywords_found = sum(
            1 for keyword in expected_keywords
            if keyword.lower() in retrieved_text
        )

        assert keywords_found >= len(expected_keywords) * 0.5, \
            f"Query '{query}' missing expected keywords"


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_top_k_retrieval(policy_collection):
    """Test that top-k retrieval returns correct number of results."""
    query = "Tell me about refunds and cancellations"

    for k in [1, 3, 5]:
        # REAL ChromaDB query with different k values
        results = policy_collection.query(
            query_texts=[query],
            n_results=k
        )

        # Should return exactly k results (or fewer if collection is small)
        assert len(results["documents"][0]) <= k
        assert len(results["distances"][0]) == len(results["documents"][0])


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_metadata_filtering(policy_collection):
    """Test retrieval with metadata filtering."""
    # Query for refund policy specifically
    results = policy_collection.query(
        query_texts=["refund information"],
        n_results=5,
        where={"policy_type": "refund"}
    )

    # All results should be from refund policy
    assert len(results["documents"][0]) > 0
    for metadata in results["metadatas"][0]:
        assert metadata["policy_type"] == "refund"


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_multilingual_query_support(policy_collection, expected_results):
    """Test that multilingual queries work with ChromaDB."""
    multilingual_queries = expected_results["expected_rag_results"]["multilingual_queries"]

    for test_case in multilingual_queries:
        query = test_case["query"]
        expected_keywords = test_case["expected_keywords"]

        # REAL ChromaDB query with non-English text
        results = policy_collection.query(
            query_texts=[query],
            n_results=3
        )

        # Should still retrieve relevant English documents
        assert len(results["documents"][0]) >= 1

        # Check that relevant content was found
        retrieved_text = " ".join(results["documents"][0]).lower()
        keywords_found = sum(
            1 for keyword in expected_keywords
            if keyword.lower() in retrieved_text
        )

        # Lower threshold for multilingual (semantic search should still work)
        assert keywords_found >= 1, \
            f"Multilingual query '{query}' found no relevant keywords"


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_empty_query_handling(policy_collection):
    """Test handling of empty or invalid queries."""
    # Empty query should handle gracefully
    results = policy_collection.query(
        query_texts=[""],
        n_results=3
    )

    # Should return results (or handle gracefully without error)
    assert "documents" in results


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_relevance_score_ordering(policy_collection):
    """Test that results are ordered by relevance (distance)."""
    query = "What is the refund policy for defective products?"

    # REAL ChromaDB query
    results = policy_collection.query(
        query_texts=[query],
        n_results=5
    )

    distances = results["distances"][0]

    # Distances should be in ascending order (lower distance = more relevant)
    for i in range(len(distances) - 1):
        assert distances[i] <= distances[i + 1], \
            "Results not properly ordered by relevance"


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_collection_persistence(chromadb_client):
    """Test that ChromaDB persists data across client reconnections."""
    collection_name = "test_persistence"

    # Create collection and add data
    collection = chromadb_client.get_or_create_collection(name=collection_name)
    collection.add(
        documents=["Test document for persistence"],
        ids=["persist_1"],
        metadatas=[{"test": "true"}]
    )

    # Get count
    initial_count = collection.count()
    assert initial_count >= 1

    # Get collection again (simulates reconnection)
    collection_reloaded = chromadb_client.get_collection(name=collection_name)

    # Count should be the same
    assert collection_reloaded.count() == initial_count

    # Should be able to query the same data
    results = collection_reloaded.get(ids=["persist_1"])
    assert len(results["documents"]) == 1
    assert results["documents"][0] == "Test document for persistence"

    # Cleanup
    chromadb_client.delete_collection(name=collection_name)


@pytest.mark.integration
@pytest.mark.timeout(5)
def test_batch_query_performance(policy_collection):
    """Test batch querying for multiple questions."""
    queries = [
        "What is your refund policy?",
        "How do I cancel my order?",
        "What are the shipping times?"
    ]

    # REAL ChromaDB batch query
    results = policy_collection.query(
        query_texts=queries,
        n_results=2
    )

    # Should return results for all queries
    assert len(results["documents"]) == len(queries)

    # Each query should have results
    for query_results in results["documents"]:
        assert len(query_results) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
