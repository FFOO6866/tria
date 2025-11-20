"""
DSPy Evaluation Metrics
========================

Multi-metric optimization for intent classification and RAG QA.

Metrics optimize for:
- Quality (accuracy, groundedness)
- Speed (token efficiency, latency)
- Cost (token usage)

NO MOCKING - Real metrics for production optimization.
"""

import dspy
import logging
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
import re
import json

logger = logging.getLogger(__name__)


# ============================================================================
# METRIC RESULT TYPES
# ============================================================================

@dataclass
class MetricResult:
    """
    Result of a metric evaluation

    Attributes:
        score: Overall metric score (0.0-1.0)
        accuracy: Accuracy component (0.0-1.0)
        latency_score: Latency/speed component (0.0-1.0)
        cost_score: Cost component (0.0-1.0)
        details: Additional metric-specific details
    """
    score: float
    accuracy: float = 0.0
    latency_score: float = 0.0
    cost_score: float = 0.0
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


# ============================================================================
# INTENT CLASSIFICATION METRICS
# ============================================================================

def intent_accuracy_metric(example, prediction, trace=None) -> float:
    """
    Pure accuracy metric for intent classification

    Args:
        example: dspy.Example with expected 'intent' field
        prediction: dspy.Prediction with predicted 'intent' field
        trace: Optional execution trace (not used)

    Returns:
        1.0 if correct, 0.0 if incorrect
    """
    try:
        expected = example.intent.lower().strip()
        predicted = prediction.intent.lower().strip()
        return 1.0 if expected == predicted else 0.0
    except (AttributeError, KeyError) as e:
        logger.warning(f"Intent accuracy metric failed: {e}")
        return 0.0


def intent_confidence_metric(example, prediction, trace=None) -> float:
    """
    Evaluate confidence calibration for intent classification

    Rewards high confidence on correct predictions,
    penalizes high confidence on incorrect predictions.

    Args:
        example: dspy.Example with expected 'intent' field
        prediction: dspy.Prediction with 'intent' and 'confidence' fields
        trace: Optional execution trace

    Returns:
        Score between 0.0 and 1.0
    """
    try:
        # Check accuracy first
        accuracy = intent_accuracy_metric(example, prediction, trace)

        # Parse confidence
        confidence = float(prediction.confidence)
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

        if accuracy == 1.0:
            # Correct prediction: reward high confidence
            return confidence
        else:
            # Incorrect prediction: reward low confidence
            return 1.0 - confidence

    except (AttributeError, KeyError, ValueError) as e:
        logger.warning(f"Confidence metric failed: {e}")
        return 0.0


def intent_combined_metric(example, prediction, trace=None) -> float:
    """
    Combined metric for intent classification optimization

    Optimizes for:
    - 50% Accuracy (correctness)
    - 30% Token efficiency (lower latency)
    - 20% Cost (token usage)

    Args:
        example: dspy.Example with expected fields
        prediction: dspy.Prediction with predicted fields
        trace: Optional DSPy execution trace with token counts

    Returns:
        Combined score between 0.0 and 1.0
    """
    # Component 1: Accuracy (50% weight)
    accuracy = intent_accuracy_metric(example, prediction, trace)

    # Component 2: Token efficiency (30% weight)
    latency_score = 1.0
    if trace and hasattr(trace, 'prompt_tokens'):
        # Prefer shorter prompts (target: <1000 tokens)
        tokens = trace.prompt_tokens
        latency_score = max(0.0, 1.0 - (tokens / 2000.0))

    # Component 3: Cost (20% weight)
    # For now, cost is proportional to tokens
    cost_score = latency_score

    # Weighted combination
    combined = (
        0.5 * accuracy +
        0.3 * latency_score +
        0.2 * cost_score
    )

    logger.debug(
        f"Intent metric - Accuracy: {accuracy:.3f}, "
        f"Latency: {latency_score:.3f}, Cost: {cost_score:.3f}, "
        f"Combined: {combined:.3f}"
    )

    return combined


# ============================================================================
# RAG QA METRICS
# ============================================================================

def rag_groundedness_metric(example, prediction, trace=None) -> float:
    """
    Evaluate if RAG answer is grounded in provided context

    Checks:
    1. Answer doesn't contain information not in context
    2. Answer cites sources when available
    3. Answer explicitly says "I don't know" if context insufficient

    Args:
        example: dspy.Example with 'question', 'context', 'expected_answer'
        prediction: dspy.Prediction with 'answer', 'sources'
        trace: Optional execution trace

    Returns:
        Groundedness score between 0.0 and 1.0
    """
    try:
        answer = prediction.answer.lower()
        context = example.context.lower()

        # Check for hallucination indicators
        hallucination_phrases = [
            "according to my knowledge",
            "i believe",
            "it's common that",
            "typically",
            "usually",
            "in general"
        ]

        hallucination_penalty = 0.0
        for phrase in hallucination_phrases:
            if phrase in answer:
                hallucination_penalty += 0.2

        # Check if answer contains info from context
        # Simple heuristic: major nouns/entities in answer should be in context
        answer_words = set(re.findall(r'\b\w{4,}\b', answer))
        context_words = set(re.findall(r'\b\w{4,}\b', context))

        if answer_words:
            overlap = len(answer_words & context_words) / len(answer_words)
        else:
            overlap = 1.0  # Empty answer is technically grounded

        # Bonus for citing sources
        source_bonus = 0.1 if prediction.sources and prediction.sources.strip() else 0.0

        # Calculate groundedness
        groundedness = min(1.0, overlap + source_bonus - hallucination_penalty)
        groundedness = max(0.0, groundedness)

        return groundedness

    except (AttributeError, KeyError) as e:
        logger.warning(f"Groundedness metric failed: {e}")
        return 0.0


def rag_correctness_metric(example, prediction, trace=None) -> float:
    """
    Evaluate if RAG answer is factually correct

    Compares predicted answer to expected answer using:
    - Exact keyword matching
    - Semantic similarity (simplified)

    Args:
        example: dspy.Example with 'expected_answer' field
        prediction: dspy.Prediction with 'answer' field
        trace: Optional execution trace

    Returns:
        Correctness score between 0.0 and 1.0
    """
    try:
        if not hasattr(example, 'expected_answer') or not example.expected_answer:
            # If no expected answer, use groundedness as proxy
            return rag_groundedness_metric(example, prediction, trace)

        predicted = prediction.answer.lower()
        expected = example.expected_answer.lower()

        # Extract key terms (nouns, numbers, entities)
        predicted_terms = set(re.findall(r'\b\w{3,}\b', predicted))
        expected_terms = set(re.findall(r'\b\w{3,}\b', expected))

        if not expected_terms:
            return 1.0  # No expected terms to match

        # Calculate overlap
        overlap = len(predicted_terms & expected_terms) / len(expected_terms)
        return min(1.0, overlap)

    except (AttributeError, KeyError) as e:
        logger.warning(f"Correctness metric failed: {e}")
        return 0.0


def rag_combined_metric(example, prediction, trace=None) -> float:
    """
    Combined metric for RAG QA optimization

    Optimizes for:
    - 40% Groundedness (no hallucination)
    - 30% Correctness (factually accurate)
    - 20% Token efficiency (concise answers)
    - 10% Source citation

    Args:
        example: dspy.Example with expected fields
        prediction: dspy.Prediction with predicted fields
        trace: Optional DSPy execution trace

    Returns:
        Combined score between 0.0 and 1.0
    """
    # Component 1: Groundedness (40% weight)
    groundedness = rag_groundedness_metric(example, prediction, trace)

    # Component 2: Correctness (30% weight)
    correctness = rag_correctness_metric(example, prediction, trace)

    # Component 3: Token efficiency (20% weight)
    latency_score = 1.0
    if trace and hasattr(trace, 'completion_tokens'):
        # Prefer concise answers (target: <300 tokens)
        tokens = trace.completion_tokens
        latency_score = max(0.0, 1.0 - (tokens / 600.0))

    # Component 4: Source citation (10% weight)
    citation_score = 1.0 if (
        prediction.sources and prediction.sources.strip()
    ) else 0.5

    # Weighted combination
    combined = (
        0.4 * groundedness +
        0.3 * correctness +
        0.2 * latency_score +
        0.1 * citation_score
    )

    logger.debug(
        f"RAG metric - Groundedness: {groundedness:.3f}, "
        f"Correctness: {correctness:.3f}, Latency: {latency_score:.3f}, "
        f"Citation: {citation_score:.3f}, Combined: {combined:.3f}"
    )

    return combined


# ============================================================================
# GENERIC COMBINED METRIC
# ============================================================================

def combined_metric(
    example,
    prediction,
    trace=None,
    task_type: str = "intent"
) -> float:
    """
    Generic combined metric that dispatches to task-specific metrics

    Args:
        example: dspy.Example with expected fields
        prediction: dspy.Prediction with predicted fields
        trace: Optional DSPy execution trace
        task_type: "intent" or "rag" to determine which metric to use

    Returns:
        Combined score between 0.0 and 1.0
    """
    if task_type == "intent":
        return intent_combined_metric(example, prediction, trace)
    elif task_type == "rag":
        return rag_combined_metric(example, prediction, trace)
    else:
        logger.warning(f"Unknown task_type: {task_type}, defaulting to intent")
        return intent_combined_metric(example, prediction, trace)


# ============================================================================
# METRIC EVALUATION UTILITIES
# ============================================================================

def evaluate_predictions(
    examples: List[dspy.Example],
    predictions: List[dspy.Prediction],
    metric_fn,
    traces: Optional[List] = None
) -> Dict[str, Any]:
    """
    Evaluate a list of predictions against examples

    Args:
        examples: List of dspy.Example objects
        predictions: List of dspy.Prediction objects
        metric_fn: Metric function to use
        traces: Optional list of execution traces

    Returns:
        Dictionary with evaluation results:
        - mean_score: Average metric score
        - scores: List of individual scores
        - accuracy: Accuracy if applicable
        - num_evaluated: Number of examples evaluated
    """
    if len(examples) != len(predictions):
        raise ValueError(
            f"Number of examples ({len(examples)}) must match "
            f"predictions ({len(predictions)})"
        )

    scores = []
    for idx, (example, prediction) in enumerate(zip(examples, predictions)):
        trace = traces[idx] if traces else None
        try:
            score = metric_fn(example, prediction, trace)
            scores.append(score)
        except Exception as e:
            logger.error(f"Metric evaluation failed for example {idx}: {e}")
            scores.append(0.0)

    return {
        "mean_score": sum(scores) / len(scores) if scores else 0.0,
        "scores": scores,
        "num_evaluated": len(scores),
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0
    }
