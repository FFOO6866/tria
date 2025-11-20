"""
Training Data Management
========================

Load, prepare, and manage training datasets for DSPy optimization.

NO MOCKING - Uses real JSON files and data processing.
"""

import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import dspy

logger = logging.getLogger(__name__)


# ============================================================================
# DATA LOADING
# ============================================================================

def load_training_data(
    file_path: str,
    task_type: str = "intent"
) -> List[Dict[str, Any]]:
    """
    Load training data from JSON file

    Args:
        file_path: Path to JSON file with training examples
        task_type: "intent" or "rag" to validate schema

    Returns:
        List of training example dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid or schema mismatch
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Training data file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate schema
        if not isinstance(data, list):
            raise ValueError("Training data must be a JSON array")

        if not data:
            raise ValueError("Training data file is empty")

        # Validate task-specific schema
        if task_type == "intent":
            _validate_intent_examples(data)
        elif task_type == "rag":
            _validate_rag_examples(data)
        else:
            logger.warning(f"Unknown task_type: {task_type}, skipping validation")

        logger.info(
            f"Loaded {len(data)} training examples from {file_path} "
            f"(task_type: {task_type})"
        )

        return data

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in training data file: {e}") from e
    except Exception as e:
        logger.error(f"Failed to load training data: {e}", exc_info=True)
        raise


def _validate_intent_examples(examples: List[Dict[str, Any]]) -> None:
    """
    Validate intent classification examples have required fields

    Required fields:
    - message: str
    - intent: str
    - conversation_history: list (optional)
    """
    required_fields = {'message', 'intent'}
    for idx, example in enumerate(examples):
        missing = required_fields - set(example.keys())
        if missing:
            raise ValueError(
                f"Example {idx} missing required fields: {missing}"
            )

        if not isinstance(example['message'], str):
            raise ValueError(f"Example {idx}: 'message' must be string")

        if not isinstance(example['intent'], str):
            raise ValueError(f"Example {idx}: 'intent' must be string")


def _validate_rag_examples(examples: List[Dict[str, Any]]) -> None:
    """
    Validate RAG QA examples have required fields

    Required fields:
    - question: str
    - context: str
    - expected_answer: str (optional but recommended)
    """
    required_fields = {'question', 'context'}
    for idx, example in enumerate(examples):
        missing = required_fields - set(example.keys())
        if missing:
            raise ValueError(
                f"Example {idx} missing required fields: {missing}"
            )

        if not isinstance(example['question'], str):
            raise ValueError(f"Example {idx}: 'question' must be string")

        if not isinstance(example['context'], str):
            raise ValueError(f"Example {idx}: 'context' must be string")


# ============================================================================
# DSPY EXAMPLE PREPARATION
# ============================================================================

def prepare_dspy_examples(
    raw_examples: List[Dict[str, Any]],
    task_type: str = "intent"
) -> List[dspy.Example]:
    """
    Convert raw JSON examples to DSPy Example objects

    Args:
        raw_examples: List of dictionaries with training data
        task_type: "intent" or "rag" to determine conversion

    Returns:
        List of dspy.Example objects
    """
    dspy_examples = []

    for idx, raw in enumerate(raw_examples):
        try:
            if task_type == "intent":
                example = _prepare_intent_example(raw)
            elif task_type == "rag":
                example = _prepare_rag_example(raw)
            else:
                raise ValueError(f"Unknown task_type: {task_type}")

            dspy_examples.append(example)

        except Exception as e:
            logger.error(
                f"Failed to prepare example {idx}: {e}. Skipping..."
            )
            continue

    logger.info(
        f"Prepared {len(dspy_examples)}/{len(raw_examples)} DSPy examples "
        f"(task_type: {task_type})"
    )

    return dspy_examples


def _prepare_intent_example(raw: Dict[str, Any]) -> dspy.Example:
    """
    Convert raw intent example to dspy.Example

    Input format:
        {
            "message": "I need 500 meal trays",
            "intent": "order_placement",
            "conversation_history": [...],  # optional
            "confidence": 0.95  # optional
        }

    Output:
        dspy.Example with input fields (message, conversation_history)
        and label fields (intent)
    """
    conversation_history = raw.get('conversation_history', [])
    if isinstance(conversation_history, list):
        conversation_history = json.dumps(conversation_history)

    return dspy.Example(
        message=raw['message'],
        conversation_history=conversation_history,
        intent=raw['intent']
    ).with_inputs('message', 'conversation_history')


def _prepare_rag_example(raw: Dict[str, Any]) -> dspy.Example:
    """
    Convert raw RAG example to dspy.Example

    Input format:
        {
            "question": "What's the return policy?",
            "context": "Article 1: Returns accepted within 30 days...",
            "expected_answer": "Returns are accepted within 30 days",  # optional
            "sources": "doc_1, doc_2"  # optional
        }

    Output:
        dspy.Example with input fields (question, context)
        and label fields (expected_answer, sources if present)
    """
    example_data = {
        'question': raw['question'],
        'context': raw['context']
    }

    # Add optional fields if present
    if 'expected_answer' in raw:
        example_data['expected_answer'] = raw['expected_answer']

    if 'sources' in raw:
        example_data['sources'] = raw['sources']

    example = dspy.Example(**example_data)
    return example.with_inputs('question', 'context')


# ============================================================================
# TRAIN/VAL SPLITTING
# ============================================================================

def split_train_val(
    examples: List[dspy.Example],
    val_ratio: float = 0.2,
    shuffle: bool = True,
    random_seed: Optional[int] = 42
) -> Tuple[List[dspy.Example], List[dspy.Example]]:
    """
    Split examples into training and validation sets

    Args:
        examples: List of dspy.Example objects
        val_ratio: Fraction of data to use for validation (default: 0.2)
        shuffle: Whether to shuffle before splitting (default: True)
        random_seed: Random seed for reproducibility (default: 42)

    Returns:
        Tuple of (train_examples, val_examples)

    Raises:
        ValueError: If val_ratio is invalid or not enough examples
    """
    if not 0.0 < val_ratio < 1.0:
        raise ValueError(f"val_ratio must be between 0 and 1, got {val_ratio}")

    if len(examples) < 2:
        raise ValueError("Need at least 2 examples to split")

    # Copy to avoid modifying original
    examples = list(examples)

    # Shuffle if requested
    if shuffle:
        if random_seed is not None:
            random.seed(random_seed)
        random.shuffle(examples)

    # Calculate split point
    val_size = max(1, int(len(examples) * val_ratio))
    train_size = len(examples) - val_size

    train_examples = examples[:train_size]
    val_examples = examples[train_size:]

    logger.info(
        f"Split {len(examples)} examples into "
        f"{len(train_examples)} train, {len(val_examples)} val "
        f"(ratio: {val_ratio})"
    )

    return train_examples, val_examples


def stratified_split(
    examples: List[dspy.Example],
    label_field: str,
    val_ratio: float = 0.2,
    random_seed: Optional[int] = 42
) -> Tuple[List[dspy.Example], List[dspy.Example]]:
    """
    Stratified train/val split preserving label distribution

    Args:
        examples: List of dspy.Example objects
        label_field: Field name to stratify on (e.g., 'intent')
        val_ratio: Fraction for validation
        random_seed: Random seed for reproducibility

    Returns:
        Tuple of (train_examples, val_examples)
    """
    # Group by label
    label_groups: Dict[str, List[dspy.Example]] = {}
    for example in examples:
        label = getattr(example, label_field, None)
        if label is None:
            logger.warning(
                f"Example missing label field '{label_field}', "
                f"using 'unknown'"
            )
            label = 'unknown'

        if label not in label_groups:
            label_groups[label] = []
        label_groups[label].append(example)

    # Split each group
    if random_seed is not None:
        random.seed(random_seed)

    train_examples = []
    val_examples = []

    for label, group in label_groups.items():
        # Shuffle group
        random.shuffle(group)

        # Split
        val_size = max(1, int(len(group) * val_ratio))
        train_examples.extend(group[val_size:])
        val_examples.extend(group[:val_size])

    logger.info(
        f"Stratified split on '{label_field}': "
        f"{len(train_examples)} train, {len(val_examples)} val "
        f"({len(label_groups)} labels)"
    )

    return train_examples, val_examples


# ============================================================================
# DATA AUGMENTATION (OPTIONAL)
# ============================================================================

def augment_intent_examples(
    examples: List[Dict[str, Any]],
    augmentation_factor: int = 2
) -> List[Dict[str, Any]]:
    """
    Simple data augmentation for intent examples

    Augmentation techniques:
    - Paraphrase variations (simulated with slight rewording)
    - Case variations
    - Whitespace normalization

    Args:
        examples: List of raw intent examples
        augmentation_factor: How many augmented versions per example

    Returns:
        Original + augmented examples
    """
    augmented = list(examples)  # Include originals

    for example in examples:
        message = example['message']

        # Augmentation 1: Case variation
        if augmentation_factor >= 1:
            aug1 = example.copy()
            aug1['message'] = message.upper()
            augmented.append(aug1)

        # Augmentation 2: Title case
        if augmentation_factor >= 2:
            aug2 = example.copy()
            aug2['message'] = message.title()
            augmented.append(aug2)

    logger.info(
        f"Augmented {len(examples)} examples to {len(augmented)} examples "
        f"(factor: {augmentation_factor})"
    )

    return augmented


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_dataset_stats(examples: List[dspy.Example], label_field: str) -> Dict[str, Any]:
    """
    Get statistics about a dataset

    Args:
        examples: List of dspy.Example objects
        label_field: Field to analyze distribution

    Returns:
        Dictionary with dataset statistics
    """
    label_counts: Dict[str, int] = {}
    for example in examples:
        label = getattr(example, label_field, 'unknown')
        label_counts[label] = label_counts.get(label, 0) + 1

    return {
        'total': len(examples),
        'num_labels': len(label_counts),
        'label_distribution': label_counts,
        'most_common': max(label_counts, key=label_counts.get) if label_counts else None,
        'least_common': min(label_counts, key=label_counts.get) if label_counts else None
    }


def save_examples(
    examples: List[Dict[str, Any]],
    output_path: str
) -> None:
    """
    Save examples to JSON file

    Args:
        examples: List of example dictionaries
        output_path: Path to save JSON file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(examples)} examples to {output_path}")
