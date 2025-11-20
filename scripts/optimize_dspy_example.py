"""
DSPy Optimization Example Script
=================================

Example script showing how to use the DSPy optimization framework
to automatically improve intent classification and RAG QA prompts.

Usage:
    python scripts/optimize_dspy_example.py --task intent
    python scripts/optimize_dspy_example.py --task rag
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optimization.dspy_framework import DSPyOptimizer, optimize_from_file
from optimization.training_data import load_training_data, prepare_dspy_examples, split_train_val

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def optimize_intent_classifier():
    """
    Optimize intent classification using DSPy

    This will:
    1. Load training data from data/eval/intent_classification_eval.json
    2. Split into train/validation sets
    3. Run DSPy BootstrapFewShot optimization
    4. Evaluate and save the optimized model
    """
    logger.info("Starting intent classifier optimization...")

    # Load data
    data_file = Path(__file__).parent.parent / "data" / "eval" / "intent_classification_eval.json"
    logger.info(f"Loading data from {data_file}")

    optimized, results = optimize_from_file(
        str(data_file),
        task_type="intent",
        val_ratio=0.2
    )

    # Print results
    logger.info("\n" + "="*60)
    logger.info("INTENT CLASSIFIER OPTIMIZATION RESULTS")
    logger.info("="*60)
    logger.info(f"Validation Score: {results['mean_score']:.3f}")
    logger.info(f"Min Score: {results['min_score']:.3f}")
    logger.info(f"Max Score: {results['max_score']:.3f}")
    logger.info(f"Examples Evaluated: {results['num_evaluated']}")
    logger.info("="*60 + "\n")

    # Save model
    optimizer = DSPyOptimizer()
    model_path = optimizer.save_model(
        optimized,
        "intent_optimized",
        metadata={
            "validation_score": results['mean_score'],
            "num_examples": results['num_evaluated'],
            "task": "intent_classification"
        }
    )
    logger.info(f"Saved optimized model to: {model_path}")

    return optimized, results


def optimize_rag_qa():
    """
    Optimize RAG QA using DSPy

    This will:
    1. Load training data from data/eval/rag_qa_eval.json
    2. Split into train/validation sets
    3. Run DSPy BootstrapFewShot optimization
    4. Evaluate and save the optimized model
    """
    logger.info("Starting RAG QA optimization...")

    # Load data
    data_file = Path(__file__).parent.parent / "data" / "eval" / "rag_qa_eval.json"
    logger.info(f"Loading data from {data_file}")

    optimized, results = optimize_from_file(
        str(data_file),
        task_type="rag",
        val_ratio=0.2
    )

    # Print results
    logger.info("\n" + "="*60)
    logger.info("RAG QA OPTIMIZATION RESULTS")
    logger.info("="*60)
    logger.info(f"Validation Score: {results['mean_score']:.3f}")
    logger.info(f"Min Score: {results['min_score']:.3f}")
    logger.info(f"Max Score: {results['max_score']:.3f}")
    logger.info(f"Examples Evaluated: {results['num_evaluated']}")
    logger.info("="*60 + "\n")

    # Save model
    optimizer = DSPyOptimizer()
    model_path = optimizer.save_model(
        optimized,
        "rag_optimized",
        metadata={
            "validation_score": results['mean_score'],
            "num_examples": results['num_evaluated'],
            "task": "rag_qa"
        }
    )
    logger.info(f"Saved optimized model to: {model_path}")

    return optimized, results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="DSPy Optimization Example")
    parser.add_argument(
        "--task",
        type=str,
        choices=["intent", "rag", "both"],
        default="intent",
        help="Task to optimize: intent, rag, or both"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key (or set OPENAI_API_KEY env var)"
    )

    args = parser.parse_args()

    # Check API key
    api_key = args.api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error(
            "OpenAI API key required. "
            "Provide via --api-key or set OPENAI_API_KEY environment variable."
        )
        sys.exit(1)

    # Run optimization
    try:
        if args.task == "intent":
            optimize_intent_classifier()
        elif args.task == "rag":
            optimize_rag_qa()
        elif args.task == "both":
            optimize_intent_classifier()
            optimize_rag_qa()

        logger.info("Optimization complete!")

    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
