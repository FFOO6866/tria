#!/usr/bin/env python3
"""
TIER 1 UNIT TESTS - Text Preprocessing
=======================================

Tests text preprocessing and cleaning logic in isolation.

REQUIREMENTS:
- Speed: < 1 second per test
- Isolation: No external dependencies
- Mocking: Allowed
- Focus: Text preprocessing correctness

TEST COVERAGE:
1. Text normalization (whitespace, case)
2. Special character handling
3. HTML/Markdown stripping
4. Language detection (mocked)
5. Text sanitization
"""

import pytest
import re
from typing import Optional


class TextPreprocessor:
    """
    Text preprocessing utilities for RAG pipeline.
    This would typically live in src/rag/preprocessing.py
    """

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize whitespace in text.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    @staticmethod
    def remove_special_characters(text: str, keep_punctuation: bool = True) -> str:
        """
        Remove special characters from text.

        Args:
            text: Input text
            keep_punctuation: Whether to keep basic punctuation

        Returns:
            Cleaned text
        """
        if keep_punctuation:
            # Keep alphanumeric, spaces, and basic punctuation
            pattern = r'[^a-zA-Z0-9\s.,!?;:\-\']'
        else:
            # Keep only alphanumeric and spaces
            pattern = r'[^a-zA-Z0-9\s]'

        return re.sub(pattern, '', text)

    @staticmethod
    def strip_html(text: str) -> str:
        """
        Remove HTML tags from text.

        Args:
            text: Input text with potential HTML

        Returns:
            Text without HTML tags
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        return text

    @staticmethod
    def strip_markdown(text: str) -> str:
        """
        Remove Markdown formatting from text.

        Args:
            text: Input text with potential Markdown

        Returns:
            Text without Markdown formatting
        """
        # Remove headers (handle optional leading whitespace)
        text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text

    @staticmethod
    def clean_policy_text(text: str) -> str:
        """
        Clean policy document text for RAG processing.

        Args:
            text: Raw policy text

        Returns:
            Cleaned text ready for chunking
        """
        # Strip HTML and Markdown
        text = TextPreprocessor.strip_html(text)
        text = TextPreprocessor.strip_markdown(text)

        # Normalize whitespace
        text = TextPreprocessor.normalize_whitespace(text)

        return text


# ============================================================================
# TIER 1 UNIT TESTS
# ============================================================================


@pytest.mark.timeout(1)
def test_normalize_whitespace_basic():
    """Test basic whitespace normalization."""
    preprocessor = TextPreprocessor()

    text = "This  has   multiple    spaces"
    result = preprocessor.normalize_whitespace(text)

    assert result == "This has multiple spaces"


@pytest.mark.timeout(1)
def test_normalize_whitespace_newlines():
    """Test normalization of newlines and tabs."""
    preprocessor = TextPreprocessor()

    text = "Line one\n\nLine two\t\tTabbed"
    result = preprocessor.normalize_whitespace(text)

    # Should replace all whitespace with single space
    assert result == "Line one Line two Tabbed"


@pytest.mark.timeout(1)
def test_normalize_whitespace_leading_trailing():
    """Test removal of leading/trailing whitespace."""
    preprocessor = TextPreprocessor()

    text = "   Leading and trailing   "
    result = preprocessor.normalize_whitespace(text)

    assert result == "Leading and trailing"
    assert not result.startswith(' ')
    assert not result.endswith(' ')


@pytest.mark.timeout(1)
def test_remove_special_characters_with_punctuation():
    """Test special character removal while keeping punctuation."""
    preprocessor = TextPreprocessor()

    text = "Hello@World! This#is$a%test^with&special*chars."
    result = preprocessor.remove_special_characters(text, keep_punctuation=True)

    # Should keep letters, numbers, spaces, and basic punctuation
    assert "Hello" in result
    assert "World" in result
    assert "!" in result
    assert "." in result
    # Should remove special chars
    assert "@" not in result
    assert "#" not in result
    assert "$" not in result


@pytest.mark.timeout(1)
def test_remove_special_characters_without_punctuation():
    """Test special character removal including punctuation."""
    preprocessor = TextPreprocessor()

    text = "Hello, World! Test 123."
    result = preprocessor.remove_special_characters(text, keep_punctuation=False)

    # Should keep only alphanumeric and spaces
    assert "Hello" in result
    assert "World" in result
    assert "123" in result
    # Should remove all punctuation
    assert "," not in result
    assert "!" not in result
    assert "." not in result


@pytest.mark.timeout(1)
def test_strip_html_basic():
    """Test basic HTML tag removal."""
    preprocessor = TextPreprocessor()

    text = "<p>This is a <strong>test</strong> paragraph.</p>"
    result = preprocessor.strip_html(text)

    assert result == "This is a test paragraph."
    assert "<" not in result
    assert ">" not in result


@pytest.mark.timeout(1)
def test_strip_html_entities():
    """Test HTML entity decoding."""
    preprocessor = TextPreprocessor()

    text = "Price:&nbsp;$100&nbsp;&amp;&nbsp;Tax:&nbsp;$10"
    result = preprocessor.strip_html(text)

    assert "&nbsp;" not in result
    assert "&amp;" not in result
    assert " " in result
    assert "&" in result


@pytest.mark.timeout(1)
def test_strip_html_nested_tags():
    """Test removal of nested HTML tags."""
    preprocessor = TextPreprocessor()

    text = "<div><p>Nested <span>tags</span> test</p></div>"
    result = preprocessor.strip_html(text)

    assert result == "Nested tags test"


@pytest.mark.timeout(1)
def test_strip_markdown_headers():
    """Test Markdown header removal."""
    preprocessor = TextPreprocessor()

    text = "# Header 1\n## Header 2\n### Header 3\nRegular text"
    result = preprocessor.strip_markdown(text)

    assert "# " not in result
    assert "Header 1" in result
    assert "Header 2" in result
    assert "Regular text" in result


@pytest.mark.timeout(1)
def test_strip_markdown_emphasis():
    """Test Markdown bold/italic removal."""
    preprocessor = TextPreprocessor()

    text = "This is **bold** and *italic* and __also bold__ and _also italic_"
    result = preprocessor.strip_markdown(text)

    # Text should remain but formatting removed
    assert "bold" in result
    assert "italic" in result
    assert "**" not in result
    assert "*" not in result or result.count('*') == 0
    assert "__" not in result
    assert "_" not in result or result.count('_') == 0


@pytest.mark.timeout(1)
def test_strip_markdown_links():
    """Test Markdown link removal while keeping link text."""
    preprocessor = TextPreprocessor()

    text = "Visit [our website](https://example.com) for more info"
    result = preprocessor.strip_markdown(text)

    # Link text should remain
    assert "our website" in result
    # Link formatting should be removed
    assert "[" not in result
    assert "]" not in result
    assert "https://example.com" not in result


@pytest.mark.timeout(1)
def test_strip_markdown_code():
    """Test Markdown code block and inline code removal."""
    preprocessor = TextPreprocessor()

    text = "Here is `inline code` and\n```\ncode block\n```\ntext"
    result = preprocessor.strip_markdown(text)

    # Code formatting should be removed
    assert "`" not in result
    # Text should remain (or code content, depending on implementation)
    assert "inline code" in result or "text" in result


@pytest.mark.timeout(1)
def test_clean_policy_text_comprehensive():
    """Test comprehensive policy text cleaning."""
    preprocessor = TextPreprocessor()

    text = """
    <div>
    # REFUND POLICY

    We offer **full refunds** within [30 days](https://policy.com).

    - Item must be `unused`
    - Original packaging required

    Contact: support@example.com
    </div>
    """

    result = preprocessor.clean_policy_text(text)

    # Should have clean text
    assert "REFUND POLICY" in result
    assert "full refunds" in result
    assert "30 days" in result

    # Should remove formatting
    assert "<" not in result
    assert "#" not in result
    assert "**" not in result
    assert "`" not in result

    # Should normalize whitespace
    assert "  " not in result  # No double spaces


@pytest.mark.timeout(1)
def test_empty_text_handling():
    """Test handling of empty text."""
    preprocessor = TextPreprocessor()

    assert preprocessor.normalize_whitespace("") == ""
    assert preprocessor.strip_html("") == ""
    assert preprocessor.strip_markdown("") == ""
    assert preprocessor.clean_policy_text("") == ""


@pytest.mark.timeout(1)
def test_unicode_preservation():
    """Test that unicode characters are preserved."""
    preprocessor = TextPreprocessor()

    text = "中文文本 **bold** English text"
    result = preprocessor.strip_markdown(text)

    # Unicode should be preserved
    assert "中文文本" in result
    assert "English text" in result


@pytest.mark.timeout(1)
def test_email_preservation():
    """Test that email addresses are preserved during cleaning."""
    preprocessor = TextPreprocessor()

    text = "Contact us at support@example.com for help"
    result = preprocessor.clean_policy_text(text)

    # Email should be preserved (@ is allowed in some contexts)
    assert "support" in result
    assert "example" in result


@pytest.mark.timeout(1)
def test_number_preservation():
    """Test that numbers are preserved during cleaning."""
    preprocessor = TextPreprocessor()

    text = "Refund within **30 days** or call +65 1234 5678"
    result = preprocessor.clean_policy_text(text)

    # Numbers should be preserved
    assert "30" in result
    assert "65" in result
    assert "1234" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
