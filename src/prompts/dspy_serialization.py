"""
DSPy Model Serialization Utilities
===================================

Utilities for serializing and deserializing DSPy models for prompt management.

Features:
- Save DSPy optimized models to JSON format
- Load DSPy models from JSON format
- Extract prompt content and metadata from DSPy modules
- Version management for DSPy models

Usage:
    from src.prompts.dspy_serialization import save_dspy_model, load_dspy_model

    # After DSPy optimization
    optimized_classifier = optimizer.compile(IntentClassifier(), ...)

    # Save to JSON
    save_dspy_model(
        model=optimized_classifier,
        prompt_type="intent_classification",
        version="dspy_v2",
        output_path="src/prompts/dspy/"
    )

    # Load from JSON
    model_data = load_dspy_model(
        prompt_type="intent_classification",
        version="dspy_v2",
        input_path="src/prompts/dspy/"
    )
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# SERIALIZATION
# ============================================================================

def save_dspy_model(
    model: Any,
    prompt_type: str,
    version: str,
    output_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Save DSPy model to JSON format

    Args:
        model: DSPy optimized model (e.g., compiled IntentClassifier)
        prompt_type: Type of prompt (intent_classification, rag_qa, etc.)
        version: Version string (e.g., "dspy_v2")
        output_path: Directory to save the model
        metadata: Optional metadata (optimizer info, metrics, etc.)

    Returns:
        Path to saved file

    Example:
        >>> save_dspy_model(
        ...     model=optimized_classifier,
        ...     prompt_type="intent_classification",
        ...     version="dspy_v2",
        ...     output_path="src/prompts/dspy/",
        ...     metadata={
        ...         "optimizer": "BootstrapFewShot",
        ...         "validation_accuracy": 0.94,
        ...         "training_examples": 50
        ...     }
        ... )
    """
    try:
        # Extract content from DSPy model
        content = extract_prompt_from_dspy_model(model)

        # Build metadata
        model_metadata = metadata or {}
        model_metadata.update({
            "created_at": datetime.utcnow().isoformat(),
            "model_type": type(model).__name__,
            "version": version
        })

        # Add few-shot examples if available
        if hasattr(model, 'demos') and model.demos:
            model_metadata["few_shot_examples"] = [
                demo_to_dict(demo) for demo in model.demos[:5]  # First 5 examples
            ]

        # Build JSON structure
        model_data = {
            "version": version,
            "prompt_type": prompt_type,
            "created_at": datetime.utcnow().isoformat(),
            "content": content,
            "metadata": model_metadata
        }

        # Save to file
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{prompt_type}_{version}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved DSPy model to {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to save DSPy model: {e}")
        raise


def extract_prompt_from_dspy_model(model: Any) -> str:
    """
    Extract prompt content from DSPy model

    DSPy models store prompts in different attributes depending on the module type.
    This function attempts to extract the prompt in a generic way.

    Args:
        model: DSPy model instance

    Returns:
        Extracted prompt text
    """
    # Try common attributes where DSPy stores prompts
    prompt_attrs = [
        'signature',
        'extended_signature',
        'prompt',
        'instructions',
        '_instructions'
    ]

    for attr in prompt_attrs:
        if hasattr(model, attr):
            value = getattr(model, attr)
            if isinstance(value, str):
                return value
            elif hasattr(value, '__str__'):
                return str(value)

    # If no direct prompt found, try to get from predict module
    if hasattr(model, 'predict') or hasattr(model, 'classify'):
        predictor = getattr(model, 'predict', None) or getattr(model, 'classify', None)
        if predictor and hasattr(predictor, 'signature'):
            return str(predictor.signature)

    # Last resort: convert entire model to string
    logger.warning("Could not extract prompt from DSPy model, using string representation")
    return str(model)


def demo_to_dict(demo: Any) -> Dict[str, Any]:
    """
    Convert DSPy demo/example to dictionary

    Args:
        demo: DSPy Example or demo object

    Returns:
        Dictionary representation
    """
    try:
        # DSPy Example objects have attributes
        if hasattr(demo, '__dict__'):
            return {k: v for k, v in demo.__dict__.items() if not k.startswith('_')}
        else:
            return {"value": str(demo)}
    except Exception as e:
        logger.warning(f"Failed to convert demo to dict: {e}")
        return {"error": str(e)}


# ============================================================================
# DESERIALIZATION
# ============================================================================

def load_dspy_model(
    prompt_type: str,
    version: str,
    input_path: str
) -> Dict[str, Any]:
    """
    Load DSPy model from JSON format

    Args:
        prompt_type: Type of prompt (intent_classification, rag_qa, etc.)
        version: Version string (e.g., "dspy_v2")
        input_path: Directory containing the model

    Returns:
        Dictionary with model data (content, metadata)

    Example:
        >>> data = load_dspy_model(
        ...     prompt_type="intent_classification",
        ...     version="dspy_v2",
        ...     input_path="src/prompts/dspy/"
        ... )
        >>> print(data["content"])
        >>> print(data["metadata"]["validation_accuracy"])
    """
    try:
        # Build filepath
        input_dir = Path(input_path)
        filename = f"{prompt_type}_{version}.json"
        filepath = input_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"DSPy model not found: {filepath}")

        # Load JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            model_data = json.load(f)

        logger.info(f"Loaded DSPy model from {filepath}")
        return model_data

    except Exception as e:
        logger.error(f"Failed to load DSPy model: {e}")
        raise


# ============================================================================
# VALIDATION
# ============================================================================

def validate_dspy_model(model_data: Dict[str, Any]) -> bool:
    """
    Validate DSPy model data structure

    Args:
        model_data: Model data dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["version", "prompt_type", "created_at", "content", "metadata"]

    for field in required_fields:
        if field not in model_data:
            logger.error(f"Missing required field: {field}")
            return False

    # Validate metadata
    if not isinstance(model_data["metadata"], dict):
        logger.error("Metadata must be a dictionary")
        return False

    # Validate content
    if not isinstance(model_data["content"], str) or len(model_data["content"]) == 0:
        logger.error("Content must be a non-empty string")
        return False

    return True


# ============================================================================
# COMPARISON
# ============================================================================

def compare_dspy_models(
    model1_data: Dict[str, Any],
    model2_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare two DSPy models

    Args:
        model1_data: First model data
        model2_data: Second model data

    Returns:
        Comparison results with metrics diff
    """
    comparison = {
        "version1": model1_data.get("version"),
        "version2": model2_data.get("version"),
        "metrics_comparison": {}
    }

    # Compare metadata metrics
    metrics1 = model1_data.get("metadata", {})
    metrics2 = model2_data.get("metadata", {})

    # Common metrics to compare
    metric_fields = [
        "validation_accuracy",
        "avg_latency_ms",
        "avg_tokens",
        "training_examples"
    ]

    for field in metric_fields:
        if field in metrics1 and field in metrics2:
            val1 = metrics1[field]
            val2 = metrics2[field]
            diff = val2 - val1
            pct_change = (diff / val1 * 100) if val1 != 0 else 0

            comparison["metrics_comparison"][field] = {
                "model1": val1,
                "model2": val2,
                "diff": diff,
                "pct_change": pct_change
            }

    return comparison


# ============================================================================
# MIGRATION
# ============================================================================

def migrate_manual_to_dspy_format(
    manual_prompt_path: str,
    prompt_type: str,
    version: str,
    output_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Migrate manual prompt to DSPy format (for compatibility)

    This is useful when you want to manage both manual and DSPy prompts
    in the same format.

    Args:
        manual_prompt_path: Path to manual prompt text file
        prompt_type: Type of prompt
        version: Version string (e.g., "manual_v1")
        output_path: Directory to save the DSPy-formatted file
        metadata: Optional metadata

    Returns:
        Path to saved file
    """
    try:
        # Read manual prompt
        with open(manual_prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Build metadata
        model_metadata = metadata or {}
        model_metadata.update({
            "created_at": datetime.utcnow().isoformat(),
            "source": "manual",
            "migrated": True
        })

        # Build DSPy-compatible structure
        model_data = {
            "version": version,
            "prompt_type": prompt_type,
            "created_at": datetime.utcnow().isoformat(),
            "content": content,
            "metadata": model_metadata
        }

        # Save to file
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{prompt_type}_{version}.json"
        filepath = output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Migrated manual prompt to DSPy format: {filepath}")
        return filepath

    except Exception as e:
        logger.error(f"Failed to migrate manual prompt: {e}")
        raise


# ============================================================================
# UTILITIES
# ============================================================================

def list_dspy_models(input_path: str) -> List[Dict[str, str]]:
    """
    List all DSPy models in a directory

    Args:
        input_path: Directory containing DSPy models

    Returns:
        List of model info dictionaries
    """
    models = []
    input_dir = Path(input_path)

    if not input_dir.exists():
        logger.warning(f"Directory not found: {input_dir}")
        return models

    for filepath in input_dir.glob("*.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            models.append({
                "filename": filepath.name,
                "prompt_type": data.get("prompt_type", "unknown"),
                "version": data.get("version", "unknown"),
                "created_at": data.get("created_at", "unknown")
            })
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")

    return sorted(models, key=lambda x: x["created_at"], reverse=True)


def get_latest_version(prompt_type: str, input_path: str) -> Optional[str]:
    """
    Get latest version for a prompt type

    Args:
        prompt_type: Type of prompt
        input_path: Directory containing DSPy models

    Returns:
        Latest version string or None
    """
    models = list_dspy_models(input_path)

    # Filter by prompt type
    matching = [m for m in models if m["prompt_type"] == prompt_type]

    if not matching:
        return None

    # Return latest (already sorted by created_at)
    return matching[0]["version"]


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example usage of serialization utilities"""

    # Example 1: Save DSPy model
    # ---------------------------
    # Assume you have an optimized DSPy model from optimization
    # optimized_classifier = optimizer.compile(IntentClassifier(), ...)

    # save_dspy_model(
    #     model=optimized_classifier,
    #     prompt_type="intent_classification",
    #     version="dspy_v2",
    #     output_path="src/prompts/dspy/",
    #     metadata={
    #         "optimizer": "BootstrapFewShot",
    #         "validation_accuracy": 0.94,
    #         "avg_latency_ms": 180,
    #         "avg_tokens": 220,
    #         "training_examples": 50
    #     }
    # )

    # Example 2: Load DSPy model
    # ---------------------------
    # model_data = load_dspy_model(
    #     prompt_type="intent_classification",
    #     version="dspy_v2",
    #     input_path="src/prompts/dspy/"
    # )
    # print(f"Content: {model_data['content']}")
    # print(f"Accuracy: {model_data['metadata']['validation_accuracy']}")

    # Example 3: Compare models
    # --------------------------
    # model1 = load_dspy_model("intent_classification", "dspy_v1", "src/prompts/dspy/")
    # model2 = load_dspy_model("intent_classification", "dspy_v2", "src/prompts/dspy/")
    # comparison = compare_dspy_models(model1, model2)
    # print(f"Accuracy improvement: {comparison['metrics_comparison']['validation_accuracy']['pct_change']:.1f}%")

    # Example 4: List all models
    # ---------------------------
    # models = list_dspy_models("src/prompts/dspy/")
    # for model in models:
    #     print(f"{model['prompt_type']} {model['version']} - {model['created_at']}")

    pass


if __name__ == "__main__":
    example_usage()
