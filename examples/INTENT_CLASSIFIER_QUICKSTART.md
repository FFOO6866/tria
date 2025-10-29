# TRIA Intent Classifier - Quick Start Guide

## 1. Installation

No additional packages needed - uses existing OpenAI integration.

```bash
# Ensure environment is set up
pip install -r requirements.txt
```

## 2. Set API Key

```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-..." >> .env
```

## 3. Quick Test

```python
from src.agents.intent_classifier import classify_intent

# Classify a message
result = classify_intent("I need 500 meal trays")

print(f"Intent: {result.intent}")          # order_placement
print(f"Confidence: {result.confidence}")  # 0.98
```

## 4. Full Customer Service Agent

```python
from src.agents.enhanced_customer_service_agent import handle_customer_message

# Handle any customer message
response = handle_customer_message("What's your refund policy?")

print(response.response_text)
```

## 5. Run Live Test

```bash
python examples/test_intent_classifier_live.py
```

Expected output: `ALL TESTS PASSED!`

## Common Use Cases

### Classify Intent Only
```python
from src.agents import IntentClassifier

classifier = IntentClassifier()
result = classifier.classify_intent("Where's my order?")
print(result.intent)  # "order_status"
```

### Get Full Response
```python
from src.agents import EnhancedCustomerServiceAgent

agent = EnhancedCustomerServiceAgent()
response = agent.handle_message("Do you have 10 inch boxes?")
print(response.response_text)  # Full response from agent
```

### With Conversation History
```python
conversation_history = [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello!"}
]

response = agent.handle_message(
    "I need supplies",
    conversation_history=conversation_history
)
```

## Supported Intents

- `order_placement` - Place new order
- `order_status` - Check order status
- `product_inquiry` - Product questions
- `policy_question` - Policy questions
- `complaint` - Issues/complaints
- `greeting` - Greetings
- `general_query` - Other questions

## Troubleshooting

**"OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY=sk-...
```

**Low confidence (<0.6)**
- Provide more context in the message
- Add conversation history

**RAG not working**
- Run `python scripts/build_knowledge_base.py` to populate ChromaDB
- Or disable RAG: `agent = EnhancedCustomerServiceAgent(enable_rag=False)`

## Full Documentation

See `INTENT_CLASSIFICATION_IMPLEMENTATION.md` for complete details.
