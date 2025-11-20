"""
DSPy Optimization Framework
============================

Main optimizer class for automatic prompt improvement using DSPy.

Features:
- Intent classification optimization
- RAG QA optimization
- Multi-metric optimization (accuracy + latency + cost)
- A/B testing support
- Model versioning and serialization

NO MOCKING - Uses real OpenAI API through DSPy.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import dspy
from dspy.teleprompt import BootstrapFewShot

from .dspy_modules import IntentClassifier, RAGQA
from .metrics import (
    intent_combined_metric,
    rag_combined_metric,
    combined_metric,
    evaluate_predictions
)
from .training_data import (
    load_training_data,
    prepare_dspy_examples,
    split_train_val,
    get_dataset_stats
)

logger = logging.getLogger(__name__)


# ============================================================================
# DSPY OPTIMIZER
# ============================================================================

class DSPyOptimizer:
    """
    Automatic prompt optimization framework using DSPy

    Features:
    - Optimizes intent classification prompts
    - Optimizes RAG QA prompts
    - Multi-metric optimization (accuracy + speed + cost)
    - Model versioning and persistence
    - A/B testing support

    Usage:
        optimizer = DSPyOptimizer(api_key="...")

        # Optimize intent classifier
        optimized_intent = optimizer.optimize_intent_classifier(
            train_examples=train_set,
            val_examples=val_set
        )

        # Optimize RAG QA
        optimized_rag = optimizer.optimize_rag_qa(
            train_examples=train_set,
            val_examples=val_set
        )

        # Save optimized models
        optimizer.save_model(optimized_intent, "intent_v2.json")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        cache_dir: str = "./data/dspy_cache",
        model_dir: str = "./data/dspy_models"
    ):
        """
        Initialize DSPy optimizer

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: Model to use for optimization (default: gpt-3.5-turbo)
            cache_dir: Directory to cache DSPy prompts
            model_dir: Directory to save optimized models

        Raises:
            ValueError: If API key is not provided
        """
        # NO HARDCODING - Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Provide via api_key parameter or set OPENAI_API_KEY environment variable."
            )

        self.model = model
        self.cache_dir = Path(cache_dir)
        self.model_dir = Path(model_dir)

        # Create directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Configure DSPy
        # In DSPy 3.0+, use LM class directly
        self.lm = dspy.LM(
            model=f"openai/{model}",
            api_key=self.api_key,
            max_tokens=1000
        )
        dspy.settings.configure(lm=self.lm)

        logger.info(
            f"DSPyOptimizer initialized with model={model}, "
            f"cache_dir={cache_dir}, model_dir={model_dir}"
        )

    def optimize_intent_classifier(
        self,
        train_examples: List[dspy.Example],
        val_examples: Optional[List[dspy.Example]] = None,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
        metric: Optional[callable] = None
    ) -> Tuple[IntentClassifier, Dict[str, Any]]:
        """
        Optimize intent classification with BootstrapFewShot

        Args:
            train_examples: Training examples (dspy.Example objects)
            val_examples: Validation examples (optional, defaults to train)
            max_bootstrapped_demos: Max few-shot examples from bootstrapping
            max_labeled_demos: Max few-shot examples from labeled data
            metric: Custom metric function (defaults to intent_combined_metric)

        Returns:
            Tuple of (optimized_classifier, evaluation_results)
        """
        logger.info(
            f"Starting intent classifier optimization with "
            f"{len(train_examples)} train examples"
        )

        if val_examples is None:
            val_examples = train_examples
            logger.warning("No validation set provided, using training set")

        # Use combined metric by default
        metric_fn = metric or intent_combined_metric

        # Create baseline classifier
        baseline = IntentClassifier()

        # Create optimizer
        optimizer = BootstrapFewShot(
            metric=metric_fn,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
            max_rounds=2  # Limit rounds to control API costs
        )

        # Optimize
        logger.info("Running DSPy optimization...")
        try:
            optimized = optimizer.compile(
                baseline,
                trainset=train_examples,
                valset=val_examples
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            raise RuntimeError(f"DSPy optimization failed: {e}") from e

        # Evaluate
        logger.info("Evaluating optimized classifier...")
        eval_results = self._evaluate_intent_classifier(
            optimized,
            val_examples,
            metric_fn
        )

        logger.info(
            f"Intent classifier optimization complete. "
            f"Validation score: {eval_results['mean_score']:.3f}"
        )

        return optimized, eval_results

    def optimize_rag_qa(
        self,
        train_examples: List[dspy.Example],
        val_examples: Optional[List[dspy.Example]] = None,
        max_bootstrapped_demos: int = 3,
        max_labeled_demos: int = 3,
        metric: Optional[callable] = None
    ) -> Tuple[RAGQA, Dict[str, Any]]:
        """
        Optimize RAG QA with BootstrapFewShot

        Args:
            train_examples: Training examples (dspy.Example objects)
            val_examples: Validation examples (optional)
            max_bootstrapped_demos: Max few-shot examples from bootstrapping
            max_labeled_demos: Max few-shot examples from labeled data
            metric: Custom metric function (defaults to rag_combined_metric)

        Returns:
            Tuple of (optimized_rag, evaluation_results)
        """
        logger.info(
            f"Starting RAG QA optimization with "
            f"{len(train_examples)} train examples"
        )

        if val_examples is None:
            val_examples = train_examples
            logger.warning("No validation set provided, using training set")

        # Use combined metric by default
        metric_fn = metric or rag_combined_metric

        # Create baseline RAG
        baseline = RAGQA()

        # Create optimizer
        optimizer = BootstrapFewShot(
            metric=metric_fn,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
            max_rounds=2
        )

        # Optimize
        logger.info("Running DSPy optimization...")
        try:
            optimized = optimizer.compile(
                baseline,
                trainset=train_examples,
                valset=val_examples
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            raise RuntimeError(f"DSPy optimization failed: {e}") from e

        # Evaluate
        logger.info("Evaluating optimized RAG QA...")
        eval_results = self._evaluate_rag_qa(
            optimized,
            val_examples,
            metric_fn
        )

        logger.info(
            f"RAG QA optimization complete. "
            f"Validation score: {eval_results['mean_score']:.3f}"
        )

        return optimized, eval_results

    def _evaluate_intent_classifier(
        self,
        classifier: IntentClassifier,
        examples: List[dspy.Example],
        metric_fn: callable
    ) -> Dict[str, Any]:
        """
        Evaluate intent classifier on examples

        Args:
            classifier: IntentClassifier to evaluate
            examples: List of dspy.Example objects
            metric_fn: Metric function to use

        Returns:
            Dictionary with evaluation results
        """
        predictions = []
        for example in examples:
            try:
                pred = classifier(
                    message=example.message,
                    conversation_history=example.conversation_history
                )
                predictions.append(pred)
            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                # Create dummy prediction for failed cases
                predictions.append(dspy.Prediction(
                    intent="general_query",
                    confidence=0.0,
                    reasoning="Prediction failed"
                ))

        # Evaluate
        eval_results = evaluate_predictions(
            examples,
            predictions,
            metric_fn
        )

        return eval_results

    def _evaluate_rag_qa(
        self,
        rag: RAGQA,
        examples: List[dspy.Example],
        metric_fn: callable
    ) -> Dict[str, Any]:
        """
        Evaluate RAG QA on examples

        Args:
            rag: RAGQA module to evaluate
            examples: List of dspy.Example objects
            metric_fn: Metric function to use

        Returns:
            Dictionary with evaluation results
        """
        predictions = []
        for example in examples:
            try:
                pred = rag(
                    question=example.question,
                    context=example.context
                )
                predictions.append(pred)
            except Exception as e:
                logger.error(f"Prediction failed: {e}")
                predictions.append(dspy.Prediction(
                    answer="Unable to answer",
                    confidence=0.0,
                    sources=""
                ))

        # Evaluate
        eval_results = evaluate_predictions(
            examples,
            predictions,
            metric_fn
        )

        return eval_results

    # ========================================================================
    # MODEL PERSISTENCE
    # ========================================================================

    def save_model(
        self,
        model: dspy.Module,
        model_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save optimized DSPy model to disk

        Args:
            model: Optimized dspy.Module to save
            model_name: Name for the model (e.g., "intent_v2")
            metadata: Optional metadata to save with model

        Returns:
            Path to saved model file
        """
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{model_name}_{timestamp}.json"
        filepath = self.model_dir / filename

        # Save model
        try:
            model.save(str(filepath))
            logger.info(f"Saved model to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}", exc_info=True)
            raise RuntimeError(f"Model save failed: {e}") from e

        # Save metadata
        if metadata:
            metadata_path = filepath.with_suffix('.metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to {metadata_path}")

        return str(filepath)

    def load_model(
        self,
        model_path: str,
        model_class: type
    ) -> dspy.Module:
        """
        Load optimized DSPy model from disk

        Args:
            model_path: Path to saved model file
            model_class: Class of model to load (IntentClassifier or RAGQA)

        Returns:
            Loaded dspy.Module

        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If loading fails
        """
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        try:
            # Create new instance and load state
            model = model_class()
            model.load(str(model_path))
            logger.info(f"Loaded model from {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise RuntimeError(f"Model load failed: {e}") from e

    def list_models(self, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all saved models

        Args:
            model_type: Optional filter by model name prefix (e.g., "intent")

        Returns:
            List of model info dictionaries
        """
        models = []
        for model_file in self.model_dir.glob("*.json"):
            # Skip metadata files
            if ".metadata" in model_file.name:
                continue

            # Filter by type if specified
            if model_type and not model_file.stem.startswith(model_type):
                continue

            # Load metadata if exists
            metadata_file = model_file.with_suffix('.metadata.json')
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

            models.append({
                'name': model_file.stem,
                'path': str(model_file),
                'size': model_file.stat().st_size,
                'created': datetime.fromtimestamp(
                    model_file.stat().st_ctime
                ).isoformat(),
                'metadata': metadata
            })

        return sorted(models, key=lambda x: x['created'], reverse=True)

    # ========================================================================
    # A/B TESTING UTILITIES
    # ========================================================================

    def compare_models(
        self,
        model_a: dspy.Module,
        model_b: dspy.Module,
        test_examples: List[dspy.Example],
        metric_fn: callable,
        model_a_name: str = "Model A",
        model_b_name: str = "Model B"
    ) -> Dict[str, Any]:
        """
        Compare two models on test set for A/B testing

        Args:
            model_a: First model (e.g., baseline)
            model_b: Second model (e.g., optimized)
            test_examples: Test examples
            metric_fn: Metric function for evaluation
            model_a_name: Name for first model
            model_b_name: Name for second model

        Returns:
            Comparison results dictionary
        """
        logger.info(
            f"Comparing {model_a_name} vs {model_b_name} "
            f"on {len(test_examples)} examples"
        )

        # Determine model type
        is_intent = isinstance(model_a, IntentClassifier)

        # Evaluate model A
        if is_intent:
            results_a = self._evaluate_intent_classifier(
                model_a, test_examples, metric_fn
            )
        else:
            results_a = self._evaluate_rag_qa(
                model_a, test_examples, metric_fn
            )

        # Evaluate model B
        if is_intent:
            results_b = self._evaluate_intent_classifier(
                model_b, test_examples, metric_fn
            )
        else:
            results_b = self._evaluate_rag_qa(
                model_b, test_examples, metric_fn
            )

        # Calculate improvement
        improvement = (
            (results_b['mean_score'] - results_a['mean_score'])
            / results_a['mean_score'] * 100
            if results_a['mean_score'] > 0 else 0.0
        )

        comparison = {
            'model_a_name': model_a_name,
            'model_b_name': model_b_name,
            'model_a_score': results_a['mean_score'],
            'model_b_score': results_b['mean_score'],
            'improvement_pct': improvement,
            'winner': model_b_name if results_b['mean_score'] > results_a['mean_score'] else model_a_name,
            'num_examples': len(test_examples),
            'model_a_details': results_a,
            'model_b_details': results_b
        }

        logger.info(
            f"Comparison complete. {comparison['winner']} wins with "
            f"{improvement:+.1f}% improvement"
        )

        return comparison


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def optimize_from_file(
    training_file: str,
    task_type: str = "intent",
    val_ratio: float = 0.2,
    api_key: Optional[str] = None
) -> Tuple[dspy.Module, Dict[str, Any]]:
    """
    Convenience function to optimize from training file

    Args:
        training_file: Path to JSON training data
        task_type: "intent" or "rag"
        val_ratio: Validation split ratio (default: 0.2)
        api_key: Optional OpenAI API key

    Returns:
        Tuple of (optimized_model, evaluation_results)
    """
    # Load data
    raw_data = load_training_data(training_file, task_type)
    examples = prepare_dspy_examples(raw_data, task_type)

    # Split
    train_examples, val_examples = split_train_val(
        examples,
        val_ratio=val_ratio
    )

    logger.info(f"Loaded {len(examples)} examples from {training_file}")
    logger.info(f"Split: {len(train_examples)} train, {len(val_examples)} val")

    # Optimize
    optimizer = DSPyOptimizer(api_key=api_key)

    if task_type == "intent":
        optimized, results = optimizer.optimize_intent_classifier(
            train_examples,
            val_examples
        )
    elif task_type == "rag":
        optimized, results = optimizer.optimize_rag_qa(
            train_examples,
            val_examples
        )
    else:
        raise ValueError(f"Unknown task_type: {task_type}")

    return optimized, results
