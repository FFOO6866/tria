"""
TRIA DSPy Optimization Framework
=================================

Automatic prompt optimization using DSPy framework.

Modules:
- dspy_modules: DSPy signature definitions for intent and RAG
- metrics: Evaluation metrics for optimization
- training_data: Dataset management utilities
- dspy_framework: Main optimizer class
"""

from .dspy_modules import IntentClassifier, RAGQA
from .metrics import (
    intent_accuracy_metric,
    rag_groundedness_metric,
    combined_metric
)
from .training_data import (
    load_training_data,
    prepare_dspy_examples,
    split_train_val
)
from .dspy_framework import DSPyOptimizer

__all__ = [
    'IntentClassifier',
    'RAGQA',
    'intent_accuracy_metric',
    'rag_groundedness_metric',
    'combined_metric',
    'load_training_data',
    'prepare_dspy_examples',
    'split_train_val',
    'DSPyOptimizer'
]
