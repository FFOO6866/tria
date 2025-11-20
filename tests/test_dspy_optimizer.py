"""
Tests for DSPy Optimization Framework
======================================

Comprehensive tests for DSPy-based automatic prompt optimization.

Test Strategy:
- Mock OpenAI calls for faster tests
- Test with small datasets to reduce API costs
- Validate all components work together
- Test error handling and edge cases

NO MOCKING - Uses real DSPy but with mocked OpenAI for speed.
"""

import pytest
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import dspy

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optimization.dspy_modules import (
    IntentClassifier,
    RAGQA,
    IntentClassifierSignature,
    RAGQASignature,
    validate_intent,
    validate_confidence
)
from optimization.metrics import (
    intent_accuracy_metric,
    intent_combined_metric,
    rag_groundedness_metric,
    rag_combined_metric,
    evaluate_predictions
)
from optimization.training_data import (
    load_training_data,
    prepare_dspy_examples,
    split_train_val,
    stratified_split,
    get_dataset_stats
)
from optimization.dspy_framework import (
    DSPyOptimizer,
    optimize_from_file
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_intent_data():
    """Sample intent classification data"""
    return [
        {
            "message": "I need 500 meal trays",
            "intent": "order_placement",
            "conversation_history": [],
            "confidence": 0.95
        },
        {
            "message": "Where is my order?",
            "intent": "order_status",
            "conversation_history": [],
            "confidence": 0.98
        },
        {
            "message": "Do you have biodegradable containers?",
            "intent": "product_inquiry",
            "conversation_history": [],
            "confidence": 0.92
        },
        {
            "message": "What's your return policy?",
            "intent": "policy_question",
            "conversation_history": [],
            "confidence": 0.97
        },
        {
            "message": "My order arrived damaged",
            "intent": "complaint",
            "conversation_history": [],
            "confidence": 0.94
        }
    ]


@pytest.fixture
def sample_rag_data():
    """Sample RAG QA data"""
    return [
        {
            "question": "What is the return policy?",
            "context": "Returns accepted within 30 days. Items must be unused.",
            "expected_answer": "Returns accepted within 30 days if unused.",
            "sources": "doc_1"
        },
        {
            "question": "How long does shipping take?",
            "context": "Standard shipping takes 3-5 business days. Express is 1-2 days.",
            "expected_answer": "Standard shipping is 3-5 days, express is 1-2 days.",
            "sources": "doc_2"
        },
        {
            "question": "Do you offer bulk discounts?",
            "context": "Bulk discounts available. 5% for 1000+ units, 10% for 5000+.",
            "expected_answer": "5% discount for 1000+ units, 10% for 5000+ units.",
            "sources": "doc_3"
        }
    ]


@pytest.fixture
def temp_json_file(sample_intent_data):
    """Create temporary JSON file with sample data"""
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.json',
        delete=False
    ) as f:
        json.dump(sample_intent_data, f)
        return f.name


@pytest.fixture
def mock_openai():
    """Mock OpenAI API for faster tests"""
    with patch('dspy.OpenAI') as mock:
        # Create mock LM
        mock_lm = MagicMock()
        mock.return_value = mock_lm
        yield mock_lm


# ============================================================================
# TEST DSPY MODULES
# ============================================================================

def test_intent_classifier_signature():
    """Test IntentClassifierSignature has correct fields"""
    # DSPy signatures are classes, just verify they can be instantiated
    assert IntentClassifierSignature is not None
    # Check signature string representation
    sig_str = str(IntentClassifierSignature)
    assert "message" in sig_str
    assert "intent" in sig_str
    assert "confidence" in sig_str


def test_rag_qa_signature():
    """Test RAGQASignature has correct fields"""
    # DSPy signatures are classes, just verify they can be instantiated
    assert RAGQASignature is not None
    # Check signature string representation
    sig_str = str(RAGQASignature)
    assert "question" in sig_str
    assert "context" in sig_str
    assert "answer" in sig_str


def test_validate_intent():
    """Test intent validation"""
    # Valid intents
    assert validate_intent("order_placement") is True
    assert validate_intent("order_status") is True
    assert validate_intent("product_inquiry") is True

    # Invalid intents
    assert validate_intent("invalid_intent") is False
    assert validate_intent("") is False
    assert validate_intent("ORDER_PLACEMENT") is False  # Case sensitive


def test_validate_confidence():
    """Test confidence validation"""
    # Valid confidence scores
    assert validate_confidence(0.5) is True
    assert validate_confidence(0.0) is True
    assert validate_confidence(1.0) is True
    assert validate_confidence("0.75") is True  # String conversion

    # Invalid confidence scores
    assert validate_confidence(-0.1) is False
    assert validate_confidence(1.5) is False
    assert validate_confidence("invalid") is False
    assert validate_confidence(None) is False


# ============================================================================
# TEST METRICS
# ============================================================================

def test_intent_accuracy_metric():
    """Test intent accuracy metric"""
    # Create example and prediction
    example = dspy.Example(
        message="Test message",
        conversation_history="[]",
        intent="order_placement"
    )

    # Correct prediction
    correct_pred = dspy.Prediction(
        intent="order_placement",
        confidence=0.95,
        reasoning="Clear order intent"
    )
    assert intent_accuracy_metric(example, correct_pred) == 1.0

    # Incorrect prediction
    incorrect_pred = dspy.Prediction(
        intent="order_status",
        confidence=0.85,
        reasoning="Thought it was status check"
    )
    assert intent_accuracy_metric(example, incorrect_pred) == 0.0


def test_intent_combined_metric():
    """Test intent combined metric (accuracy + latency + cost)"""
    example = dspy.Example(
        message="Test",
        conversation_history="[]",
        intent="order_placement"
    )

    prediction = dspy.Prediction(
        intent="order_placement",
        confidence=0.95,
        reasoning="Test"
    )

    # Mock trace with token counts
    trace = Mock()
    trace.prompt_tokens = 500  # Reasonable token count

    score = intent_combined_metric(example, prediction, trace)

    # Should be > 0 and <= 1
    assert 0.0 <= score <= 1.0
    # Should be relatively high (correct + reasonable tokens)
    assert score >= 0.6


def test_rag_groundedness_metric():
    """Test RAG groundedness metric"""
    example = dspy.Example(
        question="What is the policy?",
        context="Our policy is to accept returns within 30 days.",
        expected_answer="Returns within 30 days"
    )

    # Grounded answer
    grounded_pred = dspy.Prediction(
        answer="Returns are accepted within 30 days.",
        confidence=0.95,
        sources="doc_1"
    )
    grounded_score = rag_groundedness_metric(example, grounded_pred)
    assert grounded_score > 0.5  # Should be relatively high

    # Hallucinated answer
    hallucinated_pred = dspy.Prediction(
        answer="I believe returns are generally accepted in retail.",
        confidence=0.7,
        sources=""
    )
    hallucinated_score = rag_groundedness_metric(example, hallucinated_pred)
    assert hallucinated_score < grounded_score  # Should be lower


def test_evaluate_predictions():
    """Test batch evaluation of predictions"""
    examples = [
        dspy.Example(message="Test 1", conversation_history="[]", intent="order_placement"),
        dspy.Example(message="Test 2", conversation_history="[]", intent="order_status"),
        dspy.Example(message="Test 3", conversation_history="[]", intent="product_inquiry")
    ]

    predictions = [
        dspy.Prediction(intent="order_placement", confidence=0.9, reasoning=""),
        dspy.Prediction(intent="order_status", confidence=0.95, reasoning=""),
        dspy.Prediction(intent="order_status", confidence=0.8, reasoning="")  # Wrong
    ]

    results = evaluate_predictions(
        examples,
        predictions,
        intent_accuracy_metric
    )

    assert "mean_score" in results
    assert "scores" in results
    assert "num_evaluated" in results
    assert results["num_evaluated"] == 3
    assert results["mean_score"] == pytest.approx(2/3, 0.01)  # 2 correct out of 3


# ============================================================================
# TEST TRAINING DATA
# ============================================================================

def test_load_training_data(temp_json_file):
    """Test loading training data from JSON file"""
    data = load_training_data(temp_json_file, task_type="intent")

    assert isinstance(data, list)
    assert len(data) == 5
    assert "message" in data[0]
    assert "intent" in data[0]


def test_load_training_data_file_not_found():
    """Test loading from non-existent file raises error"""
    with pytest.raises(FileNotFoundError):
        load_training_data("/nonexistent/file.json", task_type="intent")


def test_prepare_dspy_examples(sample_intent_data):
    """Test converting raw data to DSPy examples"""
    examples = prepare_dspy_examples(sample_intent_data, task_type="intent")

    assert len(examples) == 5
    assert all(isinstance(ex, dspy.Example) for ex in examples)

    # Check first example
    ex = examples[0]
    assert ex.message == "I need 500 meal trays"
    assert ex.intent == "order_placement"


def test_split_train_val(sample_intent_data):
    """Test train/val splitting"""
    examples = prepare_dspy_examples(sample_intent_data, task_type="intent")

    train, val = split_train_val(examples, val_ratio=0.4, shuffle=False)

    # Check sizes
    assert len(train) == 3  # 60% of 5
    assert len(val) == 2    # 40% of 5

    # Check no overlap
    train_messages = {ex.message for ex in train}
    val_messages = {ex.message for ex in val}
    assert len(train_messages & val_messages) == 0


def test_stratified_split(sample_intent_data):
    """Test stratified splitting preserves label distribution"""
    # Create more examples with duplicate intents for stratification
    extended_data = sample_intent_data * 3  # 15 examples, 3 of each intent
    examples = prepare_dspy_examples(extended_data, task_type="intent")

    train, val = stratified_split(
        examples,
        label_field="intent",
        val_ratio=0.2,
        random_seed=42
    )

    # Check we got examples
    assert len(train) > 0
    assert len(val) > 0
    assert len(train) + len(val) == len(examples)


def test_get_dataset_stats(sample_intent_data):
    """Test dataset statistics"""
    examples = prepare_dspy_examples(sample_intent_data, task_type="intent")

    stats = get_dataset_stats(examples, label_field="intent")

    assert stats["total"] == 5
    assert "label_distribution" in stats
    assert len(stats["label_distribution"]) == 5  # All different intents


# ============================================================================
# TEST DSPY OPTIMIZER
# ============================================================================

def test_dspy_optimizer_initialization():
    """Test DSPyOptimizer initialization"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        optimizer = DSPyOptimizer(api_key="test-key")

        assert optimizer.api_key == "test-key"
        assert optimizer.model == "gpt-3.5-turbo"
        assert optimizer.cache_dir.exists()
        assert optimizer.model_dir.exists()


def test_dspy_optimizer_no_api_key():
    """Test DSPyOptimizer fails without API key"""
    with patch.dict('os.environ', clear=True):
        with pytest.raises(ValueError, match="API key is required"):
            DSPyOptimizer()


@pytest.mark.skip(reason="Requires real OpenAI API - expensive and slow")
def test_optimize_intent_classifier_real():
    """
    INTEGRATION TEST - Requires real OpenAI API

    This test is skipped by default to avoid API costs.
    Run with: pytest -v -k test_optimize_intent_classifier_real -m ""
    """
    # Load real data
    data_file = Path(__file__).parent.parent / "data" / "eval" / "intent_classification_eval.json"
    if not data_file.exists():
        pytest.skip("Intent eval data not found")

    # Use only first 5 examples to reduce cost
    raw_data = load_training_data(str(data_file), task_type="intent")[:5]
    examples = prepare_dspy_examples(raw_data, task_type="intent")

    # Split
    train, val = split_train_val(examples, val_ratio=0.4)

    # Optimize
    optimizer = DSPyOptimizer()
    optimized, results = optimizer.optimize_intent_classifier(
        train,
        val,
        max_bootstrapped_demos=2,  # Reduce to save costs
        max_labeled_demos=2
    )

    # Verify results
    assert optimized is not None
    assert "mean_score" in results
    assert results["mean_score"] >= 0.0


@pytest.mark.skip(reason="Requires real OpenAI API - expensive and slow")
def test_optimize_rag_qa_real():
    """
    INTEGRATION TEST - Requires real OpenAI API

    This test is skipped by default to avoid API costs.
    """
    # Load real data
    data_file = Path(__file__).parent.parent / "data" / "eval" / "rag_qa_eval.json"
    if not data_file.exists():
        pytest.skip("RAG eval data not found")

    # Use only first 3 examples
    raw_data = load_training_data(str(data_file), task_type="rag")[:3]
    examples = prepare_dspy_examples(raw_data, task_type="rag")

    # Optimize
    optimizer = DSPyOptimizer()
    optimized, results = optimizer.optimize_rag_qa(
        examples,
        examples,  # Use same for train/val
        max_bootstrapped_demos=2,
        max_labeled_demos=2
    )

    # Verify
    assert optimized is not None
    assert "mean_score" in results


def test_save_and_load_model():
    """Test model persistence"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        with tempfile.TemporaryDirectory() as tmpdir:
            optimizer = DSPyOptimizer(
                api_key="test-key",
                model_dir=tmpdir
            )

            # Create a model
            model = IntentClassifier()

            # Save it
            saved_path = optimizer.save_model(
                model,
                "test_intent",
                metadata={"version": "1.0"}
            )

            assert Path(saved_path).exists()

            # Check metadata exists
            metadata_path = Path(saved_path).with_suffix('.metadata.json')
            assert metadata_path.exists()


def test_list_models():
    """Test listing saved models"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        with tempfile.TemporaryDirectory() as tmpdir:
            optimizer = DSPyOptimizer(
                api_key="test-key",
                model_dir=tmpdir
            )

            # Initially empty
            models = optimizer.list_models()
            assert len(models) == 0

            # Save a model
            model = IntentClassifier()
            optimizer.save_model(model, "test_intent")

            # Should show up
            models = optimizer.list_models()
            assert len(models) == 1
            assert "test_intent" in models[0]["name"]


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================

def test_invalid_training_data():
    """Test handling of invalid training data"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Invalid JSON
        f.write("not valid json")
        f.flush()

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_training_data(f.name, task_type="intent")


def test_missing_required_fields():
    """Test validation catches missing fields"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Missing 'intent' field
        invalid_data = [
            {"message": "Test message"}  # Missing intent
        ]
        json.dump(invalid_data, f)
        f.flush()

        with pytest.raises(ValueError, match="missing required fields"):
            load_training_data(f.name, task_type="intent")


def test_empty_examples_split():
    """Test splitting with empty examples raises error"""
    with pytest.raises(ValueError):
        split_train_val([], val_ratio=0.2)


def test_invalid_val_ratio():
    """Test invalid validation ratio raises error"""
    examples = [dspy.Example(message="Test", intent="test")]

    with pytest.raises(ValueError):
        split_train_val(examples, val_ratio=0.0)

    with pytest.raises(ValueError):
        split_train_val(examples, val_ratio=1.0)

    with pytest.raises(ValueError):
        split_train_val(examples, val_ratio=1.5)


# ============================================================================
# INTEGRATION TESTS (WITH REAL DATA FILES)
# ============================================================================

def test_load_real_intent_eval_data():
    """Test loading real intent evaluation dataset"""
    data_file = Path(__file__).parent.parent / "data" / "eval" / "intent_classification_eval.json"

    if not data_file.exists():
        pytest.skip("Intent eval data file not found")

    data = load_training_data(str(data_file), task_type="intent")

    assert len(data) == 50  # Should have 50 examples
    assert all("message" in ex for ex in data)
    assert all("intent" in ex for ex in data)


def test_load_real_rag_eval_data():
    """Test loading real RAG evaluation dataset"""
    data_file = Path(__file__).parent.parent / "data" / "eval" / "rag_qa_eval.json"

    if not data_file.exists():
        pytest.skip("RAG eval data file not found")

    data = load_training_data(str(data_file), task_type="rag")

    assert len(data) == 50  # Should have 50 examples
    assert all("question" in ex for ex in data)
    assert all("context" in ex for ex in data)


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_prepare_examples_performance(sample_intent_data):
    """Test preparing examples is reasonably fast"""
    import time

    # Create larger dataset
    large_dataset = sample_intent_data * 100  # 500 examples

    start = time.time()
    examples = prepare_dspy_examples(large_dataset, task_type="intent")
    duration = time.time() - start

    assert len(examples) == 500
    assert duration < 1.0  # Should take less than 1 second


def test_metric_evaluation_performance():
    """Test metric evaluation is fast"""
    import time

    # Create 100 examples
    examples = [
        dspy.Example(message=f"Test {i}", conversation_history="[]", intent="order_placement")
        for i in range(100)
    ]

    predictions = [
        dspy.Prediction(intent="order_placement", confidence=0.9, reasoning="")
        for _ in range(100)
    ]

    start = time.time()
    results = evaluate_predictions(examples, predictions, intent_accuracy_metric)
    duration = time.time() - start

    assert results["num_evaluated"] == 100
    assert duration < 0.5  # Should be very fast


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
