# Unified Prompt Management System

**Comprehensive prompt management with A/B testing, version control, and DSPy integration**

---

## 📋 Overview

The Prompt Management System provides a unified interface for managing both manual and DSPy-optimized prompts with built-in A/B testing, version control, and performance tracking.

### Key Features

✅ **Unified Interface**: Single API for manual and DSPy prompts
✅ **A/B Testing**: Hash-based deterministic assignment (90% DSPy, 10% manual)
✅ **Version Control**: Full history tracking in `versions/` directory
✅ **Performance Tracking**: Per-prompt metrics (accuracy, latency, tokens)
✅ **Gradual Rollout**: Safe deployment (10% → 50% → 100%)
✅ **Metrics Integration**: Track which prompt used for each request

---

## 🏗️ Architecture

```
src/prompts/
├── prompt_manager.py         # Main PromptManager class
├── dspy_serialization.py     # DSPy model serialization utilities
├── optimized_prompts.py      # Legacy manual prompts (fallback)
├── manual/                   # Manual prompt text files
│   ├── intent_v1.txt
│   ├── rag_qa_v1.txt
│   ├── customer_service_v1.txt
│   └── tone_v1.txt
├── dspy/                     # DSPy optimized prompts (JSON)
│   ├── intent_dspy_v1.json
│   └── rag_qa_dspy_v1.json
├── config/                   # Configuration files
│   └── ab_test_config.yaml   # A/B test configuration
└── versions/                 # Archived versions (auto-managed)
    └── intent_classification_dspy_v1_20251107_123456.json
```

---

## 🚀 Quick Start

### Basic Usage

```python
from src.prompts.prompt_manager import get_prompt_manager

# Get global instance
manager = get_prompt_manager()

# Get prompt with automatic A/B testing
prompt = await manager.get_prompt(
    prompt_type="intent_classification",
    user_id="user_123"
)

print(f"Using: {prompt.version} ({prompt.source})")
print(f"Content: {prompt.content}")
```

### Intent Classification

```python
# Get formatted intent prompt
formatted_prompt = await manager.get_intent_prompt(
    user_message="I want to order supplies",
    conversation_history=[
        {"role": "user", "content": "Hello, I'm from ABC Corp"}
    ],
    user_id="user_123"
)

# Use with OpenAI
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": formatted_prompt}]
)
```

### RAG Question Answering

```python
# Get formatted RAG prompt
formatted_prompt = await manager.get_rag_prompt(
    user_question="What is your return policy?",
    retrieved_knowledge="We accept returns within 30 days...",
    conversation_history=[],
    user_id="user_123"
)
```

---

## 📊 A/B Testing

### How It Works

1. **Deterministic Assignment**: Same user always gets same version (hash-based)
2. **Configurable Split**: Default 90% DSPy, 10% manual
3. **Metrics Tracking**: Track performance per version
4. **Automatic Winner**: Promote based on metrics

### Check User's Group

```python
group = manager.assign_ab_group(
    user_id="user_123",
    prompt_type="intent_classification"
)

print(f"User is in: {group}")  # "dspy" or "manual"
```

### Configuration

Edit `config/ab_test_config.yaml`:

```yaml
intent_classification:
  current_version: "dspy_v1"
  rollout_percentage: 90
  control_version: "manual_v1"
  control_percentage: 10
  enabled: true
```

---

## 📈 Performance Tracking

### Track Metrics

```python
await manager.track_performance(
    prompt_id="intent_classification_dspy_v1",
    metrics={
        "accuracy": 0.95,
        "latency_ms": 150,
        "token_count": 200
    }
)
```

### Get Metrics

```python
# Get metrics for specific prompt
metrics = manager.get_metrics("intent_classification_dspy_v1")
print(f"Avg accuracy: {metrics['avg_accuracy']:.2f}")
print(f"Avg latency: {metrics['avg_latency_ms']:.0f}ms")
print(f"Avg tokens: {metrics['avg_tokens']:.0f}")

# Get all metrics
all_metrics = manager.get_metrics()
for prompt_id, m in all_metrics.items():
    print(f"{prompt_id}: {m['avg_accuracy']:.2f}")
```

---

## 🔄 Version Management

### Gradual Rollout

```python
# Phase 1: Test with 10% traffic
await manager.promote_version(
    prompt_type="intent_classification",
    version="dspy_v2",
    rollout_pct=10
)

# Phase 2: After validation, increase to 50%
await manager.promote_version(
    prompt_type="intent_classification",
    version="dspy_v2",
    rollout_pct=50
)

# Phase 3: Full rollout
await manager.promote_version(
    prompt_type="intent_classification",
    version="dspy_v2",
    rollout_pct=100
)
```

### Version History

All promoted versions are automatically archived to `versions/` with timestamps:

```
versions/intent_classification_dspy_v1_20251107_123456.json
versions/intent_classification_manual_v1_20251107_130000.json
```

---

## 🧪 DSPy Integration

### Save Optimized Model

```python
from src.prompts.dspy_serialization import save_dspy_model

# After DSPy optimization
optimized_classifier = optimizer.compile(IntentClassifier(), ...)

# Save to JSON
save_dspy_model(
    model=optimized_classifier,
    prompt_type="intent_classification",
    version="dspy_v2",
    output_path="src/prompts/dspy/",
    metadata={
        "optimizer": "BootstrapFewShot",
        "validation_accuracy": 0.94,
        "avg_latency_ms": 180,
        "training_examples": 50
    }
)
```

### Load Optimized Model

```python
from src.prompts.dspy_serialization import load_dspy_model

model_data = load_dspy_model(
    prompt_type="intent_classification",
    version="dspy_v2",
    input_path="src/prompts/dspy/"
)

print(f"Accuracy: {model_data['metadata']['validation_accuracy']}")
```

### Compare Models

```python
from src.prompts.dspy_serialization import compare_dspy_models

model1 = load_dspy_model("intent_classification", "dspy_v1", "src/prompts/dspy/")
model2 = load_dspy_model("intent_classification", "dspy_v2", "src/prompts/dspy/")

comparison = compare_dspy_models(model1, model2)
print(f"Accuracy improvement: {comparison['metrics_comparison']['validation_accuracy']['pct_change']:.1f}%")
```

---

## 📝 Adding New Prompts

### Manual Prompt

1. Create text file in `manual/`:

```bash
echo "Your prompt here" > src/prompts/manual/my_prompt_v1.txt
```

2. Add to `PromptType` enum in `prompt_manager.py`:

```python
class PromptType(str, Enum):
    MY_PROMPT = "my_prompt"
```

3. Add to configuration:

```yaml
# config/ab_test_config.yaml
my_prompt:
  current_version: "manual_v1"
  rollout_percentage: 100
  control_version: "manual_v1"
  control_percentage: 0
  enabled: false
```

### DSPy Prompt

1. Optimize with DSPy
2. Save using `save_dspy_model()`
3. Update `ab_test_config.yaml`
4. Promote with gradual rollout

---

## 🧪 Testing

Run comprehensive tests:

```bash
pytest tests/test_prompt_manager.py -v
```

Test coverage:
- ✅ A/B assignment determinism
- ✅ 90/10 split distribution
- ✅ Prompt loading (manual + DSPy)
- ✅ Version promotion
- ✅ Metrics tracking
- ✅ Configuration management
- ✅ Error handling
- ✅ Concurrent requests

---

## 📊 Metrics & Monitoring

### Tracked Metrics

For each prompt version:
- **Usage**: Total requests
- **Accuracy**: Average classification/QA accuracy
- **Latency**: Average response time (ms)
- **Tokens**: Average token count (input + output)

### Prometheus Integration

```python
# Metrics are automatically tracked:
# - prompt_used{type="intent", version="dspy_v1"}: counter
# - prompt_latency{type="intent", version="dspy_v1"}: histogram
# - prompt_accuracy{type="intent", version="dspy_v1"}: gauge
```

---

## 🎯 Best Practices

### 1. Start with Manual Prompts

Always create a manual baseline before DSPy optimization:

```yaml
intent_classification:
  current_version: "manual_v1"
  rollout_percentage: 100
```

### 2. Use Gradual Rollout

Never go directly to 100%:

```
Phase 1: 10%  (validate no regressions)
Phase 2: 50%  (gather statistical significance)
Phase 3: 100% (full deployment)
```

### 3. Track Comprehensive Metrics

Track all dimensions:

```python
await manager.track_performance(
    prompt_id=prompt.id,
    metrics={
        "accuracy": 0.95,
        "latency_ms": 150,
        "token_count": 200,
        "user_satisfaction": 4.5  # Custom metrics
    }
)
```

### 4. Monitor A/B Tests

Check metrics regularly:

```python
# Compare DSPy vs Manual
dspy_metrics = manager.get_metrics("intent_classification_dspy_v1")
manual_metrics = manager.get_metrics("intent_classification_manual_v1")

print(f"DSPy accuracy: {dspy_metrics['avg_accuracy']:.2%}")
print(f"Manual accuracy: {manual_metrics['avg_accuracy']:.2%}")
```

### 5. Archive Old Versions

Versions are auto-archived on promotion, but you can manually archive:

```python
# Versions automatically saved to versions/ on promote_version()
# Format: {prompt_type}_{version}_{timestamp}.json
```

---

## 🔧 Configuration Reference

### A/B Test Config (`config/ab_test_config.yaml`)

```yaml
prompt_type_name:
  current_version: str      # Primary version being tested
  rollout_percentage: int   # 0-100
  control_version: str      # Baseline version
  control_percentage: int   # 0-100 (must sum to 100 with rollout)
  enabled: bool             # Enable/disable A/B test
```

### DSPy Model JSON (`dspy/*.json`)

```json
{
  "version": "dspy_v1",
  "prompt_type": "intent_classification",
  "created_at": "2025-11-07T00:00:00Z",
  "content": "Prompt text...",
  "metadata": {
    "optimizer": "BootstrapFewShot",
    "validation_accuracy": 0.94,
    "avg_latency_ms": 180,
    "few_shot_examples": [...]
  }
}
```

---

## 🐛 Troubleshooting

### Prompt Not Found

If `get_prompt()` fails:
1. Check file exists in `manual/` or `dspy/`
2. Check filename matches pattern: `{prompt_type}_v1.txt` or `{prompt_type}_dspy_v1.json`
3. Fallback to `optimized_prompts.py` if file missing

### A/B Test Not Working

1. Check `enabled: true` in `ab_test_config.yaml`
2. Verify percentages sum to 100
3. Check user_id is consistent across requests

### Metrics Not Updating

```python
# Ensure you're tracking after each request
await manager.track_performance(prompt_id, metrics)

# Get metrics to verify
metrics = manager.get_metrics(prompt_id)
print(f"Total uses: {metrics['total_uses']}")
```

---

## 📚 Additional Resources

- **COMPREHENSIVE_ARCHITECTURE.md**: Full system architecture
- **tests/test_prompt_manager.py**: Complete test suite
- **src/prompts/dspy_serialization.py**: DSPy utilities

---

## 🎓 Example: Complete Workflow

```python
import asyncio
from src.prompts.prompt_manager import get_prompt_manager

async def main():
    manager = get_prompt_manager()

    # 1. Get prompt for user
    prompt = await manager.get_prompt(
        prompt_type="intent_classification",
        user_id="user_123"
    )

    print(f"Using {prompt.version} ({prompt.source})")

    # 2. Use prompt with LLM
    # ... call OpenAI ...

    # 3. Track performance
    await manager.track_performance(
        prompt_id=prompt.id,
        metrics={
            "accuracy": 0.95,
            "latency_ms": 150,
            "token_count": 200
        }
    )

    # 4. Check metrics
    metrics = manager.get_metrics(prompt.id)
    print(f"Average accuracy: {metrics['avg_accuracy']:.2%}")

    # 5. Promote better version (after validation)
    if metrics['avg_accuracy'] > 0.93:
        await manager.promote_version(
            prompt_type="intent_classification",
            version="dspy_v2",
            rollout_pct=50  # Gradual rollout
        )

asyncio.run(main())
```

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-11-07
**Version**: 1.0.0
