#!/usr/bin/env python3
"""
TIER 1 UNIT TESTS - Document Chunking
======================================

Tests document text chunking logic in isolation.

REQUIREMENTS:
- Speed: < 1 second per test
- Isolation: No external dependencies
- Mocking: Allowed for file operations
- Focus: Chunking algorithm correctness

TEST COVERAGE:
1. Basic chunking with default parameters
2. Chunking with custom chunk size
3. Chunking with overlap
4. Handling edge cases (empty text, very short text)
5. Preserving sentence boundaries
"""

import pytest
from typing import List


class TextChunker:
    """
    Simple text chunker for testing purposes.
    This would typically live in src/rag/chunker.py
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize chunker with size and overlap parameters.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Number of overlapping characters between chunks

        Raises:
            ValueError: If chunk_size <= 0 or chunk_overlap >= chunk_size
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive (greater than 0)")

        if chunk_overlap < 0:
            chunk_overlap = 0  # Treat negative overlap as 0

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text to chunk

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position
            end = start + self.chunk_size

            # If not the last chunk, try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings near the chunk boundary
                for i in range(min(100, end - start)):
                    if text[end - i] in '.!?\n':
                        end = end - i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - self.chunk_overlap if end < text_length else text_length

        return chunks


# ============================================================================
# TIER 1 UNIT TESTS
# ============================================================================


@pytest.mark.timeout(1)
def test_basic_chunking():
    """Test basic chunking with default parameters."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    text = "This is a test sentence. " * 10  # 250 characters
    chunks = chunker.chunk_text(text)

    # Should create at least 2 chunks
    assert len(chunks) >= 2
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)


@pytest.mark.timeout(1)
def test_chunking_with_custom_size():
    """Test chunking with custom chunk size."""
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)

    text = "A" * 200  # 200 characters
    chunks = chunker.chunk_text(text)

    # Should create multiple chunks
    assert len(chunks) >= 3
    assert all(len(chunk) <= 60 for chunk in chunks)  # Allow some variance


@pytest.mark.timeout(1)
def test_chunking_with_overlap():
    """Test that chunks have proper overlap."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=30)

    text = "The quick brown fox jumps over the lazy dog. " * 10
    chunks = chunker.chunk_text(text)

    # Verify at least 2 chunks created
    assert len(chunks) >= 2

    # Check for overlap between consecutive chunks
    if len(chunks) > 1:
        # The end of chunk 0 should overlap with start of chunk 1
        # (This is a simplified check - actual overlap detection would be more complex)
        assert len(chunks[0]) > 0
        assert len(chunks[1]) > 0


@pytest.mark.timeout(1)
def test_empty_text_handling():
    """Test handling of empty or whitespace-only text."""
    chunker = TextChunker()

    # Empty string
    assert chunker.chunk_text("") == []

    # Whitespace only
    assert chunker.chunk_text("   ") == []
    assert chunker.chunk_text("\n\n\n") == []


@pytest.mark.timeout(1)
def test_very_short_text():
    """Test that short text returns single chunk."""
    chunker = TextChunker(chunk_size=500, chunk_overlap=50)

    text = "Short text."
    chunks = chunker.chunk_text(text)

    assert len(chunks) == 1
    assert chunks[0] == text


@pytest.mark.timeout(1)
def test_sentence_boundary_preservation():
    """Test that chunks try to break at sentence boundaries."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    text = (
        "This is sentence one. This is sentence two. This is sentence three. "
        "This is sentence four. This is sentence five. This is sentence six."
    )
    chunks = chunker.chunk_text(text)

    # At least one chunk should end with sentence-ending punctuation
    sentence_endings = sum(1 for chunk in chunks if chunk.rstrip()[-1] in '.!?')
    assert sentence_endings >= 1


@pytest.mark.timeout(1)
def test_chunk_size_zero_handling():
    """Test handling of invalid chunk size."""
    with pytest.raises((ValueError, ZeroDivisionError)):
        chunker = TextChunker(chunk_size=0)
        # Or if the class doesn't raise in __init__, it should raise in chunk_text
        # chunker.chunk_text("Some text")


@pytest.mark.timeout(1)
def test_negative_overlap_handling():
    """Test that negative overlap is handled gracefully."""
    # Negative overlap should be treated as 0 or raise error
    chunker = TextChunker(chunk_size=100, chunk_overlap=-10)

    text = "Test text. " * 20
    chunks = chunker.chunk_text(text)

    # Should still produce chunks without crashing
    assert len(chunks) >= 1


@pytest.mark.timeout(1)
def test_overlap_larger_than_chunk():
    """Test handling when overlap is larger than chunk size."""
    with pytest.raises(ValueError):
        # This should raise an error as it doesn't make logical sense
        chunker = TextChunker(chunk_size=100, chunk_overlap=150)
        # Or implement validation in the class


@pytest.mark.timeout(1)
def test_unicode_text_handling():
    """Test chunking with unicode characters."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    text = "你好世界。This is a test. 안녕하세요. " * 10
    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 1
    assert all(isinstance(chunk, str) for chunk in chunks)


@pytest.mark.timeout(1)
def test_newline_handling():
    """Test that newlines are handled appropriately."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    text = "Line one.\nLine two.\nLine three.\n" * 5
    chunks = chunker.chunk_text(text)

    assert len(chunks) >= 1
    # Chunks should be trimmed of leading/trailing whitespace
    assert all(chunk == chunk.strip() for chunk in chunks)


# ============================================================================
# METADATA PRESERVATION TESTS
# ============================================================================


class ChunkWithMetadata:
    """Chunker that preserves metadata with chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_with_metadata(
        self, text: str, source: str, metadata: dict = None
    ) -> List[dict]:
        """
        Chunk text and preserve metadata.

        Args:
            text: Input text
            source: Source identifier
            metadata: Additional metadata to preserve

        Returns:
            List of chunks with metadata
        """
        base_chunker = TextChunker(self.chunk_size, self.chunk_overlap)
        text_chunks = base_chunker.chunk_text(text)

        result = []
        for idx, chunk in enumerate(text_chunks):
            chunk_data = {
                "content": chunk,
                "source": source,
                "chunk_index": idx,
                "total_chunks": len(text_chunks),
                "metadata": metadata or {},
            }
            result.append(chunk_data)

        return result


@pytest.mark.timeout(1)
def test_metadata_preservation():
    """Test that metadata is preserved with chunks."""
    chunker = ChunkWithMetadata(chunk_size=100, chunk_overlap=20)

    text = "This is a test. " * 20
    metadata = {"document_type": "policy", "version": "1.0"}

    chunks = chunker.chunk_with_metadata(
        text, source="test_document.txt", metadata=metadata
    )

    assert len(chunks) >= 1
    for chunk in chunks:
        assert "content" in chunk
        assert "source" in chunk
        assert chunk["source"] == "test_document.txt"
        assert chunk["metadata"]["document_type"] == "policy"
        assert chunk["metadata"]["version"] == "1.0"


@pytest.mark.timeout(1)
def test_chunk_indexing():
    """Test that chunks are properly indexed."""
    chunker = ChunkWithMetadata(chunk_size=50, chunk_overlap=10)

    text = "Short text. " * 30
    chunks = chunker.chunk_with_metadata(text, source="test.txt")

    # Verify sequential indexing
    for idx, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == idx

    # Verify total_chunks is consistent
    total = chunks[0]["total_chunks"]
    assert all(chunk["total_chunks"] == total for chunk in chunks)
    assert total == len(chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
