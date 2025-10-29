# RAG System - Quick Reference

Production-ready RAG (Retrieval-Augmented Generation) system for TRIA AI chatbot.

## Quick Start

### 1. Build Knowledge Base (One-time Setup)

```bash
# Set OpenAI API key
export OPENAI_API_KEY="sk-..."  # Linux/Mac
# or
set OPENAI_API_KEY=sk-...       # Windows

# Build knowledge base from policy documents
python scripts/build_knowledge_base.py

# Verify collections
python scripts/build_knowledge_base.py --verify-only
```

### 2. Test Retrieval

```bash
python scripts/test_rag_retrieval.py
```

### 3. Use in Your Code

```python
from src.rag.knowledge_base import KnowledgeBase
import os

# Initialize
kb = KnowledgeBase(api_key=os.getenv("OPENAI_API_KEY"))

# Search policies
results = kb.search("What is the return policy?", collection="policies")

# Format for LLM
context = kb.format_for_llm(results, "POLICIES")

# Use in GPT-4 prompt
system_prompt = f"""
You are TRIA customer support.

{context}

Answer the customer's question.
"""
```

## API Reference

### KnowledgeBase Class

```python
class KnowledgeBase:
    def __init__(self, api_key: str)

    def search(
        self,
        query: str,
        collection: str = "all",  # "policies", "faqs", "escalation", "tone", "all"
        top_n: int = 5,
        min_similarity: float = None
    ) -> List[Dict]

    def format_for_llm(
        self,
        results: List[Dict],
        collection_type: str = "knowledge"
    ) -> str

    def retrieve_context(
        self,
        query: str,
        collections: List[str] = ["policies", "faqs"],
        top_n_per_collection: int = 3
    ) -> str  # LLM-ready context string
```

### Convenience Functions

```python
from src.rag.retrieval import (
    search_policies,
    search_faqs,
    search_escalation_rules,
    search_tone_guidelines,
    search_all_collections
)

# Search specific collection
results = search_policies("return policy", api_key="sk-...")

# Search all collections
all_results = search_all_collections("damaged product", api_key="sk-...")
```

## Collections

| Collection | Purpose | Source Document |
|------------|---------|-----------------|
| **policies_en** | Company rules & policies | TRIA_Rules_and_Policies_v1.0.docx |
| **faqs_en** | Product FAQs | TRIA_Product_FAQ_Handbook_v1.0.docx |
| **escalation_rules** | Escalation routing | TRIA_Escalation_Routing_Guide_v1.0.docx |
| **tone_personality** | Brand voice guidelines | TRIA_Tone_and_Personality_v1.0.docx |

## Common Use Cases

### 1. Answer Policy Questions

```python
kb = KnowledgeBase(api_key=os.getenv("OPENAI_API_KEY"))

# Customer asks: "What's your return policy?"
context = kb.retrieve_context(
    query="return policy for damaged items",
    collections=["policies", "faqs"]
)

# Add to LLM prompt
# GPT-4 will answer using retrieved policy information
```

### 2. Determine Escalation Rules

```python
# Customer is frustrated about delivery delay
escalation_context = kb.search(
    query="delivery delay customer frustrated",
    collection="escalation",
    top_n=3
)

# Check if escalation needed based on retrieved rules
```

### 3. Multi-Collection Search

```python
# Search all collections for comprehensive context
all_results = kb.search(
    query="damaged product return process",
    collection="all",
    top_n=2  # 2 results per collection
)

context = kb.format_for_llm(all_results)
# Result includes policies, FAQs, escalation rules, and tone guidelines
```

## Integration Patterns

### With Kailash SDK Workflow

```python
from kailash.workflow.builder import WorkflowBuilder
from src.rag.knowledge_base import KnowledgeBase

workflow = WorkflowBuilder()

# Add RAG retrieval node
workflow.add_node("PythonCodeNode", "rag_retrieval", {
    "code": """
from src.rag.knowledge_base import KnowledgeBase
import os

kb = KnowledgeBase(api_key=os.getenv('OPENAI_API_KEY'))
context = kb.retrieve_context(query=user_query, collections=['policies', 'faqs'])
result = {'rag_context': context}
"""
})

# Add LLM node
workflow.add_node("LLMAgentNode", "generate_response", {
    "system_prompt": "{{rag_context}}\n\nAnswer the question.",
    "model": "gpt-4-turbo-preview"
})

# Connect
workflow.add_connection("rag_retrieval", "rag_context", "generate_response", "context")
```

### With Custom Agent

```python
class CustomerServiceAgent:
    def __init__(self, api_key: str):
        self.kb = KnowledgeBase(api_key=api_key)
        self.llm = OpenAI(api_key=api_key)

    def answer(self, question: str) -> str:
        # Step 1: Retrieve relevant knowledge
        context = self.kb.retrieve_context(question)

        # Step 2: Generate response
        response = self.llm.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": f"You are TRIA support.\n\n{context}"},
                {"role": "user", "content": question}
            ]
        )

        return response.choices[0].message.content
```

## Maintenance

### Rebuild Knowledge Base

```bash
# WARNING: This deletes existing data
python scripts/build_knowledge_base.py --reset
```

### Add New Documents

1. Place new .docx file in `doc/policy/`
2. Ensure filename contains: `policy`, `faq`, `escalation`, or `tone`
3. Run rebuild:
   ```bash
   python scripts/build_knowledge_base.py --reset
   ```

### Check Collection Stats

```python
from src.rag.knowledge_base import KnowledgeBase

kb = KnowledgeBase(api_key="sk-...")
stats = kb.get_stats()

print(stats)
# {'policies_en': 1, 'faqs_en': 1, 'escalation_rules': 1, 'tone_personality': 1}
```

## Troubleshooting

### Issue: No results found

**Check**:
1. Knowledge base built? → `python scripts/build_knowledge_base.py --verify-only`
2. Collections not empty? → Should show `[OK]` status
3. Query too specific? → Try broader query

### Issue: Low similarity scores (<50%)

**Solutions**:
1. Use broader query terms
2. Check if query matches document content
3. Consider adding more relevant documents

### Issue: "Collection not found"

**Fix**: Rebuild knowledge base
```bash
python scripts/build_knowledge_base.py
```

## File Locations

- **Source Code**: `src/rag/`
  - `knowledge_base.py` - Main API
  - `retrieval.py` - Search functions
  - `document_processor.py` - Text extraction
  - `knowledge_indexer.py` - Embedding generation
  - `chroma_client.py` - ChromaDB management

- **Scripts**: `scripts/`
  - `build_knowledge_base.py` - Indexing
  - `test_rag_retrieval.py` - Testing

- **Data**:
  - `doc/policy/` - Source documents (.docx)
  - `data/chromadb/` - Vector database (persistent)

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (uses defaults if not set)
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7
```

## Performance Notes

- **Query time**: <1 second
- **Similarity scores**: 60-70% for relevant queries
- **Embedding model**: text-embedding-3-small (1536 dimensions)
- **Distance metric**: Cosine similarity
- **Storage**: ~2 MB for 4 documents

## Next Steps

1. **Integrate with chatbot**: Use RAG in customer service workflows
2. **Add multi-language**: Translate documents, create zh/ms collections
3. **Monitor usage**: Track query patterns and response quality
4. **Optimize**: Cache frequent queries, tune similarity thresholds

---

**For detailed documentation, see**: `RAG_IMPLEMENTATION_COMPLETE.md`
**For architecture details, see**: `doc/CHATBOT_ARCHITECTURE_PROPOSAL.md`
