# DSPy Optimization Framework

Automatic prompt optimization using DSPy for intent classification and RAG QA.

## Overview

This framework implements DSPy-based automatic prompt improvement for the TRIA AI-BPO customer service system. It optimizes:

- **Intent Classification**: Improve accuracy, reduce tokens, lower cost
- **RAG QA**: Reduce hallucination, improve groundedness, better answers

### Key Features

- Multi-metric optimization (accuracy + latency + cost)
- A/B testing support
- Model versioning and serialization
- Comprehensive evaluation metrics
- Real OpenAI API integration (no mocking)

## Architecture

```
src/optimization/
├── __init__.py              # Package exports
├── dspy_modules.py          # DSPy signature definitions
├── metrics.py               # Evaluation metrics
├── training_data.py         # Dataset management
└── dspy_framework.py        # Main optimizer class

data/eval/
├── intent_classification_eval.json  # 50 intent examples
└── rag_qa_eval.json                # 50 RAG examples

tests/
└── test_dspy_optimizer.py   # 24 comprehensive tests
```

## Installation

```bash
# Install dependencies
pip install dspy-ai>=2.4.0 sentence-transformers>=2.2.0 scikit-learn>=1.3.0

# Or use requirements.txt (already includes these)
pip install -r requirements.txt
```

## Quick Start

### 1. Optimize Intent Classifier

```python
from optimization.dspy_framework import optimize_from_file

# Optimize from evaluation dataset
optimized, results = optimize_from_file(
    training_file="data/eval/intent_classification_eval.json",
    task_type="intent",
    val_ratio=0.2
)

print(f"Validation Score: {results['mean_score']:.3f}")
```

### 2. Optimize RAG QA

```python
from optimization.dspy_framework import optimize_from_file

# Optimize RAG QA
optimized, results = optimize_from_file(
    training_file="data/eval/rag_qa_eval.json",
    task_type="rag",
    val_ratio=0.2
)

print(f"Validation Score: {results['mean_score']:.3f}")
```

### 3. Command Line Usage

```bash
# Optimize intent classifier
python scripts/optimize_dspy_example.py --task intent

# Optimize RAG QA
python scripts/optimize_dspy_example.py --task rag

# Optimize both
python scripts/optimize_dspy_example.py --task both
```

## Detailed Usage

### DSPy Modules

The framework provides two main DSPy modules:

#### Intent Classifier

```python
from optimization.dspy_modules import IntentClassifier

classifier = IntentClassifier()
result = classifier(
    message="I need 500 meal trays",
    conversation_history="[]"
)

print(result.intent)        # "order_placement"
print(result.confidence)    # 0.95
print(result.reasoning)     # "Clear order intent..."
```

#### RAG QA

```python
from optimization.dspy_modules import RAGQA

qa = RAGQA()
result = qa(
    question="What's the return policy?",
    context="Returns accepted within 30 days..."
)

print(result.answer)        # "Returns accepted within 30 days..."
print(result.confidence)    # 0.95
print(result.sources)       # "doc_1"
```

### Optimization Process

```python
from optimization.dspy_framework import DSPyOptimizer
from optimization.training_data import load_training_data, prepare_dspy_examples, split_train_val

# 1. Load and prepare data
raw_data = load_training_data("data/eval/intent_classification_eval.json", task_type="intent")
examples = prepare_dspy_examples(raw_data, task_type="intent")
train, val = split_train_val(examples, val_ratio=0.2)

# 2. Initialize optimizer
optimizer = DSPyOptimizer(api_key="your-api-key")

# 3. Optimize
optimized_classifier, results = optimizer.optimize_intent_classifier(
    train_examples=train,
    val_examples=val,
    max_bootstrapped_demos=4,
    max_labeled_demos=4
)

# 4. Evaluate
print(f"Mean Score: {results['mean_score']:.3f}")
print(f"Min Score: {results['min_score']:.3f}")
print(f"Max Score: {results['max_score']:.3f}")

# 5. Save model
model_path = optimizer.save_model(
    optimized_classifier,
    "intent_v2",
    metadata={"score": results['mean_score']}
)
```

### Metrics

The framework provides three types of metrics:

#### Intent Classification Metrics

- **intent_accuracy_metric**: Pure accuracy (1.0 if correct, 0.0 if wrong)
- **intent_combined_metric**: Weighted combination:
  - 50% Accuracy
  - 30% Token efficiency (latency)
  - 20% Cost

#### RAG QA Metrics

- **rag_groundedness_metric**: Measures hallucination and citation
- **rag_correctness_metric**: Compares to expected answer
- **rag_combined_metric**: Weighted combination:
  - 40% Groundedness
  - 30% Correctness
  - 20% Token efficiency
  - 10% Source citation

### A/B Testing

Compare two models on a test set:

```python
# Compare baseline vs optimized
comparison = optimizer.compare_models(
    model_a=baseline_classifier,
    model_b=optimized_classifier,
    test_examples=test_set,
    metric_fn=intent_combined_metric,
    model_a_name="Baseline",
    model_b_name="Optimized"
)

print(f"Winner: {comparison['winner']}")
print(f"Improvement: {comparison['improvement_pct']:+.1f}%")
```

### Model Persistence

```python
# Save model
model_path = optimizer.save_model(
    optimized_classifier,
    "intent_v2",
    metadata={"version": "2.0", "accuracy": 0.95}
)

# Load model
from optimization.dspy_modules import IntentClassifier
loaded_model = optimizer.load_model(model_path, IntentClassifier)

# List all models
models = optimizer.list_models(model_type="intent")
for model in models:
    print(f"{model['name']}: {model['size']} bytes")
```

## Training Data Format

### Intent Classification

```json
[
  {
    "message": "I need 500 meal trays",
    "intent": "order_placement",
    "conversation_history": [],
    "confidence": 0.95
  }
]
```

Supported intents:
- `order_placement`
- `order_status`
- `product_inquiry`
- `policy_question`
- `complaint`
- `greeting`
- `general_query`

### RAG QA

```json
[
  {
    "question": "What is the return policy?",
    "context": "Returns accepted within 30 days...",
    "expected_answer": "Returns within 30 days if unused.",
    "sources": "doc_1"
  }
]
```

## Evaluation Datasets

The framework includes two comprehensive evaluation datasets:

- **intent_classification_eval.json**: 50 realistic customer service messages
- **rag_qa_eval.json**: 50 question-answer pairs with context

These datasets cover:
- Common customer intents (orders, inquiries, complaints)
- Policy questions (returns, shipping, payments)
- Product questions (materials, sizes, specifications)
- Support scenarios (tracking, modifications, issues)

## Testing

Run comprehensive test suite:

```bash
# Run all tests
pytest tests/test_dspy_optimizer.py -v

# Run specific test categories
pytest tests/test_dspy_optimizer.py -k "metric" -v
pytest tests/test_dspy_optimizer.py -k "training_data" -v
pytest tests/test_dspy_optimizer.py -k "optimizer" -v

# Skip integration tests (require real API)
pytest tests/test_dspy_optimizer.py -k "not real" -v
```

Test coverage:
- ✅ 24 unit tests passing
- ✅ DSPy module signatures
- ✅ Evaluation metrics
- ✅ Training data management
- ✅ Optimizer initialization
- ✅ Model persistence
- ✅ Error handling
- ✅ Performance tests

## Performance

Expected optimization results:

### Intent Classification
- **Accuracy Improvement**: +3-5% over manual prompts
- **Token Reduction**: -20-30% fewer tokens
- **Cost Savings**: -20-30% per 1K requests
- **Latency**: Similar or better

### RAG QA
- **Groundedness**: +10-15% (less hallucination)
- **Answer Quality**: +10-15% improvement
- **Token Efficiency**: -15-25% fewer tokens
- **Source Citation**: +20-30% better

## Best Practices

1. **Data Quality**: Use diverse, realistic examples
2. **Train/Val Split**: 80/20 or 70/30 split
3. **Iteration**: Start with small datasets, iterate
4. **Metrics**: Use combined metrics for production
5. **A/B Testing**: Always compare before deploying
6. **Versioning**: Save models with metadata
7. **Monitoring**: Track performance in production

## Troubleshooting

### API Key Issues

```python
# Set environment variable
export OPENAI_API_KEY="your-api-key"

# Or pass directly
optimizer = DSPyOptimizer(api_key="your-api-key")
```

### Low Optimization Scores

- Increase `max_bootstrapped_demos` (default: 4)
- Add more diverse training examples
- Check training data quality
- Use stratified splitting for imbalanced data

### High API Costs

- Use smaller validation sets during development
- Set `max_rounds=1` in BootstrapFewShot
- Use gpt-3.5-turbo instead of gpt-4
- Cache optimization results

## Integration with Existing System

### Replace Manual Prompts

```python
# Before (manual prompt)
from agents.intent_classifier import IntentClassifier
classifier = IntentClassifier()

# After (DSPy optimized)
from optimization.dspy_framework import DSPyOptimizer
from optimization.dspy_modules import IntentClassifier as DSPyIntentClassifier

optimizer = DSPyOptimizer()
optimized = optimizer.load_model("path/to/model.json", DSPyIntentClassifier)
result = optimized(message="I need 500 meal trays", conversation_history="[]")
```

### Gradual Rollout

1. **Week 1**: Optimize on 50 examples
2. **Week 2**: A/B test (10% traffic)
3. **Week 3**: Expand to 50% traffic
4. **Week 4**: Full rollout if metrics improve

## Future Enhancements

- [ ] Multi-stage optimization (retrieve → rank → answer)
- [ ] Ensemble models (combine multiple optimized prompts)
- [ ] Adaptive learning (continuous retraining)
- [ ] Custom metrics for domain-specific optimization
- [ ] Integration with prompt versioning system

## References

- [DSPy Documentation](https://dspy-docs.vercel.app/)
- [DSPy Paper](https://arxiv.org/abs/2310.03714)
- [COMPREHENSIVE_ARCHITECTURE.md](../../COMPREHENSIVE_ARCHITECTURE.md)

## Support

For issues or questions:
1. Check test suite: `pytest tests/test_dspy_optimizer.py -v`
2. Review examples: `python scripts/optimize_dspy_example.py --help`
3. Check logs for detailed error messages

---

**Status**: ✅ Implementation Complete - All 24 Tests Passing
