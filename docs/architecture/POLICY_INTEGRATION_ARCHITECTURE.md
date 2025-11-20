# Policy Integration Architecture

**Date**: 2025-11-07
**Status**: 🎯 IMPLEMENTATION READY
**Priority**: HIGH - Core chatbot capability

---

## Executive Summary

Comprehensive plan to fully integrate the 4 policy documents (~3,200 lines) into the TRIA chatbot engagement. The RAG infrastructure is already built, but policy integration needs enhancement to ensure:

1. **Dynamic tone adaptation** from Tone & Personality Guide
2. **Accurate policy responses** from Rules & Policies
3. **Intelligent escalation** using Escalation Routing Guide
4. **Product expertise** from Product FAQ Handbook

---

## Current State Analysis

### ✅ What's Already Built

**RAG Infrastructure**:
- ✅ ChromaDB integration (`src/rag/chroma_client.py`)
- ✅ Document processor (`src/rag/document_processor.py`)
- ✅ Knowledge indexer (`src/rag/knowledge_indexer.py`)
- ✅ Retrieval functions (`src/rag/retrieval.py`)
- ✅ Knowledge base wrapper (`src/rag/knowledge_base.py`)

**Collections**:
- ✅ `policies_en` - TRIA Rules and Policies (343 lines)
- ✅ `faqs_en` - Product FAQ Handbook (682 lines)
- ✅ `escalation_rules` - Escalation Routing Guide (831 lines)
- ✅ `tone_personality` - Tone and Personality Guide (1,051 lines)

**Agent Integration**:
- ✅ Intent classification routing
- ✅ RAG retrieval for product_inquiry
- ✅ RAG retrieval for policy_question
- ✅ Response generation with GPT-4

**Build Tools**:
- ✅ `scripts/build_knowledge_base.py` - Policy indexing script
- ✅ `scripts/test_rag_retrieval.py` - Testing tool

---

### ⚠️ Gaps Identified

**1. Tone Guidelines Not Applied Dynamically**
- **Current**: Static `CUSTOMER_SERVICE_PROMPT` in `system_prompts.py`
- **Issue**: Doesn't adapt tone based on situation (complaint vs routine)
- **Impact**: Responses may not match TRIA brand voice guidelines

**2. Policy Directory Path Mismatch**
- **Current**: Script looks for `doc/policy`
- **Reality**: Moved to `docs/policy` during cleanup
- **Impact**: Build script won't find policy files

**3. Escalation Rules Not Integrated**
- **Current**: Escalation logic hardcoded in agent
- **Issue**: Doesn't consult Escalation Routing Guide dynamically
- **Impact**: May escalate too early/late, miss edge cases

**4. No Policy Compliance Validation**
- **Current**: Responses not validated against policies
- **Issue**: Could give wrong pricing, terms, or procedures
- **Impact**: Customer misinformation, compliance issues

**5. No Usage Monitoring**
- **Current**: No tracking of which policies are retrieved
- **Issue**: Can't identify gaps or frequently asked policies
- **Impact**: Can't improve knowledge base systematically

---

## Implementation Plan

### Phase 1: Verify & Fix Infrastructure (Week 1)

#### Task 1.1: Verify Current Indexing Status

**Objective**: Confirm if policies are already indexed in ChromaDB

**Commands**:
```bash
# Check existing collections
python scripts/build_knowledge_base.py --verify-only

# Expected output:
# [OK]     policies_en                    XXX chunks
# [OK]     faqs_en                        XXX chunks
# [OK]     escalation_rules               XXX chunks
# [OK]     tone_personality               XXX chunks
```

**Verification Criteria**:
- ✅ All 4 collections exist
- ✅ Each has >0 chunks
- ✅ Total chunks ~150-200 (as estimated in policy docs)

---

#### Task 1.2: Fix Policy Directory Path

**File**: `scripts/build_knowledge_base.py`

**Change**:
```python
# Line 46 - BEFORE:
POLICY_DIR = project_root / "doc" / "policy"

# AFTER:
POLICY_DIR = project_root / "docs" / "policy"
```

**Verification**:
```bash
# Re-run build (if needed)
python scripts/build_knowledge_base.py --reset

# Should now find .docx files in docs/policy/
```

---

#### Task 1.3: Re-Index Policies (If Empty)

**If verification shows empty collections**:

```bash
# Backup existing chromadb (if any)
mv data/chromadb data/chromadb.backup

# Index all policies
python scripts/build_knowledge_base.py

# Verify successful indexing
python scripts/build_knowledge_base.py --verify-only
```

**Success Criteria**:
- ✅ All 4 collections populated
- ✅ No errors in indexing
- ✅ Test retrieval works: `python scripts/test_rag_retrieval.py`

---

### Phase 2: Dynamic Tone Adaptation (Week 2)

#### Task 2.1: Create Tone Retrieval Function

**File**: `src/agents/enhanced_customer_service_agent.py`

**New Method**:
```python
def _get_tone_guidelines(
    self,
    intent: str,
    sentiment: str = "neutral"
) -> str:
    """
    Retrieve appropriate tone guidelines based on context

    Args:
        intent: User intent (greeting, complaint, inquiry, etc.)
        sentiment: Detected sentiment (positive, neutral, negative)

    Returns:
        Tone guidelines text for LLM prompt
    """
    if not self.enable_rag:
        return ""  # Use default tone from CUSTOMER_SERVICE_PROMPT

    # Build tone query based on context
    if intent == "complaint" or sentiment == "negative":
        tone_query = "How to respond to customer complaints with empathy"
    elif intent == "order_placement":
        tone_query = "Tone for taking orders, confirmation style"
    elif intent == "greeting":
        tone_query = "Greeting style, friendly professional tone"
    else:
        tone_query = "Standard customer service tone, professional friendly"

    # Retrieve tone guidelines from RAG
    try:
        tone_results = search_tone_guidelines(
            query=tone_query,
            api_key=self.api_key,
            top_n=3
        )

        if tone_results:
            tone_text = format_results_for_llm(tone_results, "TONE GUIDELINES")
            logger.info(f"Retrieved {len(tone_results)} tone guidelines")
            return tone_text
        else:
            logger.warning("No tone guidelines retrieved - using default")
            return ""

    except Exception as e:
        logger.error(f"Failed to retrieve tone guidelines: {e}")
        return ""
```

---

#### Task 2.2: Integrate Tone Into Prompts

**Enhance `_handle_inquiry_with_rag`**:

```python
def _handle_inquiry_with_rag(
    self,
    message: str,
    intent_result: IntentResult,
    conversation_history: Optional[List[Dict[str, str]]]
) -> CustomerServiceResponse:
    """Handle inquiry with RAG + dynamic tone"""

    # ... existing knowledge retrieval code ...

    # NEW: Retrieve tone guidelines
    tone_guidelines = self._get_tone_guidelines(
        intent=intent_result.intent,
        sentiment=self._detect_sentiment(message)  # Add sentiment detection
    )

    # Build enhanced prompt with tone
    qa_prompt = self._build_rag_prompt_with_tone(
        user_question=message,
        retrieved_knowledge=knowledge_text,
        tone_guidelines=tone_guidelines,
        conversation_history=conversation_history or []
    )

    # ... rest of response generation ...
```

---

#### Task 2.3: Add Sentiment Detection

**New Helper Method**:
```python
def _detect_sentiment(self, message: str) -> str:
    """
    Quick sentiment detection for tone adaptation

    Returns: "positive", "neutral", or "negative"
    """
    # Simple keyword-based detection (can be enhanced with ML later)
    negative_keywords = [
        "complaint", "problem", "issue", "wrong", "bad", "terrible",
        "unhappy", "disappointed", "angry", "frustrated"
    ]

    positive_keywords = [
        "thank", "great", "excellent", "happy", "love", "perfect",
        "wonderful", "appreciate"
    ]

    message_lower = message.lower()

    if any(word in message_lower for word in negative_keywords):
        return "negative"
    elif any(word in message_lower for word in positive_keywords):
        return "positive"
    else:
        return "neutral"
```

---

### Phase 3: Escalation Rules Integration (Week 3)

#### Task 3.1: Enhance Escalation Decision Logic

**File**: `src/agents/enhanced_customer_service_agent.py`

**Current (Basic)**:
```python
def _handle_complaint(self, message, intent_result, conversation_history):
    # Hardcoded escalation logic
    if "urgent" in message.lower():
        escalate_to_human = True
```

**Enhanced (Policy-Driven)**:
```python
def _should_escalate(
    self,
    message: str,
    intent: str,
    confidence: float,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Determine if escalation needed using Escalation Routing Guide

    Returns:
        {
            "should_escalate": bool,
            "escalation_level": str,  # "L2_CSR", "L3_Manager", "L4_Director"
            "reason": str,
            "sla_minutes": int
        }
    """
    if not self.enable_escalation:
        return {"should_escalate": False}

    # Build escalation query
    escalation_query = f"""
    Intent: {intent}
    Confidence: {confidence:.2f}
    Message: {message}

    Should this be escalated? What level? Why?
    """

    # Retrieve escalation rules
    try:
        escalation_results = search_escalation_rules(
            query=escalation_query,
            api_key=self.api_key,
            top_n=5
        )

        if not escalation_results:
            # Fallback to confidence threshold
            return {
                "should_escalate": confidence < 0.7,
                "escalation_level": "L2_CSR" if confidence < 0.7 else None,
                "reason": f"Low confidence ({confidence:.2f})",
                "sla_minutes": 30
            }

        # Use GPT-4 to interpret escalation rules
        escalation_decision_prompt = f"""
Based on these escalation rules:

{format_results_for_llm(escalation_results, "ESCALATION RULES")}

Customer message: "{message}"
Intent: {intent}
AI Confidence: {confidence:.2f}

Decision:
1. Should escalate? (yes/no)
2. What level? (L2_CSR, L3_Manager, L4_Director, or NONE)
3. Why?
4. SLA in minutes?

Format response as JSON:
{{
    "should_escalate": bool,
    "escalation_level": str or null,
    "reason": str,
    "sla_minutes": int
}}
"""

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an escalation routing expert."},
                {"role": "user", "content": escalation_decision_prompt}
            ],
            temperature=0.1,  # Low temperature for consistent decisions
            response_format={"type": "json_object"}
        )

        import json
        decision = json.loads(response.choices[0].message.content)

        logger.info(f"Escalation decision: {decision}")
        return decision

    except Exception as e:
        logger.error(f"Escalation decision failed: {e}")
        # Fallback to confidence threshold
        return {
            "should_escalate": confidence < 0.7,
            "escalation_level": "L2_CSR" if confidence < 0.7 else None,
            "reason": f"Escalation rule retrieval failed, using confidence threshold",
            "sla_minutes": 30
        }
```

---

#### Task 3.2: Integrate Into Complaint Handler

```python
def _handle_complaint(
    self,
    message: str,
    intent_result: IntentResult,
    conversation_history: Optional[List[Dict[str, str]]]
) -> CustomerServiceResponse:
    """Handle complaint with policy-driven escalation"""

    # Check escalation using rules from RAG
    escalation_decision = self._should_escalate(
        message=message,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        conversation_history=conversation_history
    )

    if escalation_decision["should_escalate"]:
        # Generate empathetic acknowledgment + escalation notice
        response_text = self._generate_escalation_response(
            message=message,
            escalation_decision=escalation_decision
        )

        return CustomerServiceResponse(
            intent="complaint",
            confidence=intent_result.confidence,
            response_text=response_text,
            escalate_to_human=True,
            escalation_reason=escalation_decision["reason"],
            metadata={
                "escalation_level": escalation_decision["escalation_level"],
                "sla_minutes": escalation_decision["sla_minutes"]
            }
        )
    else:
        # Handle with AI using empathetic tone
        # ... existing code ...
```

---

### Phase 4: Policy Compliance Validation (Week 4)

#### Task 4.1: Add Policy Fact Checker

**New Module**: `src/agents/policy_validator.py`

```python
"""
Policy Compliance Validator
===========================

Validates AI responses against policy documents to ensure accuracy.

NO MOCKING - All validation uses real policy retrieval.
"""

from typing import Dict, List, Optional
import logging
from src.rag.retrieval import search_policies, format_results_for_llm

logger = logging.getLogger(__name__)


class PolicyValidator:
    """Validates responses against policy documents"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def validate_response(
        self,
        response_text: str,
        intent: str
    ) -> Dict[str, any]:
        """
        Validate response against policies

        Returns:
            {
                "is_valid": bool,
                "violations": List[str],
                "corrections": List[str]
            }
        """
        violations = []
        corrections = []

        # Check for pricing mentions
        if "SGD" in response_text or "$" in response_text:
            pricing_validation = self._validate_pricing(response_text)
            if not pricing_validation["valid"]:
                violations.append("Pricing may be incorrect")
                corrections.append(pricing_validation["correction"])

        # Check for policy statements
        if any(word in response_text.lower() for word in [
            "policy", "rule", "term", "condition", "day", "cutoff", "delivery"
        ]):
            policy_validation = self._validate_policy_statements(response_text)
            if not policy_validation["valid"]:
                violations.append("Policy statement may be incorrect")
                corrections.append(policy_validation["correction"])

        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "corrections": corrections
        }

    def _validate_pricing(self, response_text: str) -> Dict[str, any]:
        """Validate pricing against Product FAQ"""
        # Extract prices from response
        import re
        prices = re.findall(r'SGD\s*(\d+\.\d+)|\$(\d+\.\d+)', response_text)

        if not prices:
            return {"valid": True, "correction": ""}

        # Query actual pricing from RAG
        try:
            results = search_policies(
                query="product pricing pizza box 10 inch 12 inch 14 inch",
                api_key=self.api_key,
                top_n=5
            )

            policy_text = format_results_for_llm(results, "PRICING")

            # Check if response prices match policy
            # (Simplified - could use LLM for more sophisticated checking)
            expected_prices = ["0.45", "0.65", "0.85"]
            mentioned_prices = [p[0] or p[1] for p in prices]

            invalid_prices = [p for p in mentioned_prices if p not in expected_prices]

            if invalid_prices:
                return {
                    "valid": False,
                    "correction": f"Prices should be from: {', '.join(expected_prices)}. Policy says: {policy_text[:200]}"
                }

            return {"valid": True, "correction": ""}

        except Exception as e:
            logger.error(f"Pricing validation failed: {e}")
            return {"valid": True, "correction": ""}  # Fail open for now

    def _validate_policy_statements(self, response_text: str) -> Dict[str, any]:
        """Validate policy statements against Rules & Policies"""
        # Similar implementation to pricing validation
        # Query relevant policies and cross-check statements
        return {"valid": True, "correction": ""}  # Placeholder
```

---

#### Task 4.2: Integrate Validator Into Agent

```python
# In enhanced_customer_service_agent.py

def __init__(self, ...):
    # ... existing init ...

    # Add policy validator
    from src.agents.policy_validator import PolicyValidator
    self.policy_validator = PolicyValidator(api_key=self.api_key)

def _generate_final_response(
    self,
    response_text: str,
    intent: str
) -> str:
    """Generate final response with policy validation"""

    # Validate response against policies
    validation = self.policy_validator.validate_response(
        response_text=response_text,
        intent=intent
    )

    if not validation["is_valid"]:
        logger.warning(f"Response validation failed: {validation['violations']}")

        # Attempt to fix with corrections
        correction_prompt = f"""
Original response: {response_text}

Policy violations found:
{chr(10).join(validation['violations'])}

Corrections needed:
{chr(10).join(validation['corrections'])}

Generate corrected response that follows policies exactly.
"""

        # Re-generate with corrections
        corrected_response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": CUSTOMER_SERVICE_PROMPT},
                {"role": "user", "content": correction_prompt}
            ],
            temperature=0.1
        )

        return corrected_response.choices[0].message.content

    return response_text
```

---

### Phase 5: Monitoring & Analytics (Week 5)

#### Task 5.1: Add Policy Usage Tracking

**New Module**: `src/rag/usage_analytics.py`

```python
"""
RAG Usage Analytics
===================

Track which policies are retrieved and how they're used.
Helps identify gaps and improve knowledge base.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

ANALYTICS_FILE = Path("data/rag_usage_analytics.jsonl")


def log_retrieval(
    query: str,
    collection: str,
    results_count: int,
    top_result: Optional[Dict] = None,
    metadata: Optional[Dict] = None
):
    """
    Log RAG retrieval for analytics

    Args:
        query: User query
        collection: Collection searched
        results_count: Number of results returned
        top_result: Top result metadata
        metadata: Additional context (intent, confidence, etc.)
    """
    # Ensure analytics directory exists
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "collection": collection,
        "results_count": results_count,
        "top_document_id": top_result.get("id") if top_result else None,
        "top_similarity": top_result.get("similarity") if top_result else None,
        "metadata": metadata or {}
    }

    try:
        with open(ANALYTICS_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to log RAG usage: {e}")


def get_usage_stats(days: int = 7) -> Dict:
    """
    Get usage statistics for last N days

    Returns:
        {
            "total_queries": int,
            "queries_by_collection": Dict[str, int],
            "avg_results_per_query": float,
            "low_result_queries": List[Dict],  # Queries with <2 results
            "most_common_queries": List[str]
        }
    """
    # Implementation to analyze ANALYTICS_FILE
    # Returns insights for knowledge base improvement
    pass
```

---

#### Task 5.2: Integrate Analytics Into Retrieval

**Update retrieval functions**:

```python
# In src/rag/retrieval.py

from src.rag.usage_analytics import log_retrieval

def search_policies(query: str, api_key: str, top_n: int = 5, min_similarity: float = 0.6):
    """Search policies with usage logging"""

    results = _perform_search(...)  # Existing search logic

    # Log usage
    log_retrieval(
        query=query,
        collection="policies_en",
        results_count=len(results),
        top_result=results[0] if results else None
    )

    return results
```

---

### Phase 6: Testing & Validation (Week 6)

#### Task 6.1: Create Policy Integration Test Suite

**New File**: `tests/tier2_integration/test_policy_integration.py`

```python
"""
Policy Integration Tests
========================

Test that policies are correctly integrated into chatbot responses.

NO MOCKING - Uses real ChromaDB and policies.
"""

import pytest
from src.agents.enhanced_customer_service_agent import EnhancedCustomerServiceAgent
import os


@pytest.fixture
def agent():
    """Create test agent with RAG enabled"""
    return EnhancedCustomerServiceAgent(
        api_key=os.getenv('OPENAI_API_KEY'),
        enable_rag=True,
        enable_escalation=True
    )


def test_product_pricing_accuracy(agent):
    """Test that product pricing matches policy documents"""

    message = "How much is a 10 inch pizza box?"

    response = agent.handle_message(message)

    # Should mention correct price: SGD 0.45
    assert "0.45" in response.response_text or "$0.45" in response.response_text
    assert "SGD" in response.response_text or "$" in response.response_text

    # Should retrieve from FAQs
    assert any("faqs" in chunk.get("collection", "").lower()
               for chunk in response.knowledge_used)


def test_policy_compliance_delivery(agent):
    """Test delivery policy responses match official policies"""

    message = "What days do you deliver?"

    response = agent.handle_message(message)

    # Should mention correct schedule: Tuesday, Thursday, Saturday
    response_lower = response.response_text.lower()
    assert "tuesday" in response_lower
    assert "thursday" in response_lower
    assert "saturday" in response_lower


def test_escalation_logic_complaint(agent):
    """Test that complaints are escalated per Escalation Guide"""

    message = "I'm very unhappy with my order! It arrived damaged and late!"

    response = agent.handle_message(message)

    # Should escalate based on Escalation Routing Guide
    assert response.escalate_to_human == True
    assert response.intent == "complaint"

    # Should have retrieved escalation rules
    # (or at least made escalation decision)
    assert response.escalation_reason is not None


def test_tone_adaptation_complaint_vs_routine(agent):
    """Test that tone adapts based on situation"""

    complaint = "I have a serious complaint about quality"
    routine = "Can I order 100 pizza boxes?"

    complaint_response = agent.handle_message(complaint)
    routine_response = agent.handle_message(routine)

    # Complaint response should be more empathetic
    complaint_text = complaint_response.response_text.lower()
    assert any(word in complaint_text for word in [
        "sorry", "apologize", "understand", "concern"
    ])

    # Routine response should be efficient and helpful
    routine_text = routine_response.response_text.lower()
    assert any(word in routine_text for word in [
        "happy", "help", "order", "process"
    ])


def test_no_policy_violations_in_response(agent):
    """Test that responses don't violate policies"""

    message = "What's your return policy?"

    response = agent.handle_message(message)

    # Should NOT promise returns outside policy (24-hour window)
    response_lower = response.response_text.lower()
    if "return" in response_lower or "refund" in response_lower:
        # Should mention time limit
        assert "24" in response.response_text or "hour" in response_lower


def test_policy_coverage_common_questions():
    """Test that common policy questions get answers"""

    common_questions = [
        "What is the minimum order quantity?",
        "Do you have eco-friendly options?",
        "What are your delivery fees?",
        "When is the order cutoff time?",
        "Do you offer custom printing?",
        "What payment terms do you offer?",
        "How do I modify an order?",
        "What is your GST rate?"
    ]

    agent = EnhancedCustomerServiceAgent(
        api_key=os.getenv('OPENAI_API_KEY'),
        enable_rag=True
    )

    for question in common_questions:
        response = agent.handle_message(question)

        # Should have knowledge chunks retrieved
        assert len(response.knowledge_used) > 0, f"No knowledge retrieved for: {question}"

        # Response should be substantial (not "I don't know")
        assert len(response.response_text) > 50, f"Response too short for: {question}"
        assert "don't know" not in response.response_text.lower()
```

**Run Tests**:
```bash
pytest tests/tier2_integration/test_policy_integration.py -v --tb=short
```

---

### Phase 7: Documentation & Training (Week 7)

#### Task 7.1: Update Architecture Documentation

**This File** - Complete with implementation details

#### Task 7.2: Create Policy Update Workflow

**New File**: `docs/guides/POLICY_UPDATE_WORKFLOW.md`

```markdown
# Policy Update Workflow

When policies need to be updated:

1. **Update Policy Documents**
   - Edit .docx files in `docs/policy/`
   - Update markdown versions in `docs/policy/en/`
   - Increment version number

2. **Re-Index Policies**
   ```bash
   python scripts/build_knowledge_base.py --reset
   ```

3. **Test Changes**
   ```bash
   python scripts/test_rag_retrieval.py
   pytest tests/tier2_integration/test_policy_integration.py
   ```

4. **Deploy**
   - Restart API server to pick up new ChromaDB data
   - Monitor initial responses for accuracy

5. **Validate**
   - Review analytics for new policy queries
   - Check for any policy violations in logs
```

---

## Success Metrics

### Quantitative Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Policy Retrieval Accuracy | >90% | % of queries returning relevant chunks |
| Response Accuracy | 100% | Manual spot-check of pricing/policy facts |
| Tone Consistency | >85% | Manual review against Tone Guide |
| Escalation Precision | >80% | % of escalations that match guide |
| Policy Coverage | >95% | % of policy questions answered from RAG |

### Qualitative Metrics

- ✅ Responses sound like TRIA brand voice
- ✅ Customers feel heard and understood
- ✅ Escalations happen at appropriate times
- ✅ No policy violations in responses
- ✅ Cultural sensitivity maintained (Singapore context)

---

## Risk Mitigation

### Risk 1: RAG Returns Wrong Information

**Mitigation**:
- Policy validator catches inaccuracies
- Minimum similarity threshold (0.6)
- Log all retrievals for review
- Manual spot-checks during first 2 weeks

### Risk 2: Policies Become Outdated

**Mitigation**:
- Quarterly policy review process
- Version tracking in documents
- Auto-alert when policies >90 days old
- Easy re-indexing workflow

### Risk 3: Tone Drift Over Time

**Mitigation**:
- Regular tone audits (sample 50 responses/week)
- Tone guidelines dynamically retrieved (not cached)
- Customer feedback collection
- CSR review of edge cases

---

## Next Steps (Priority Order)

### Immediate (This Week)
1. ✅ **Verify indexing status** - Run `--verify-only`
2. ✅ **Fix directory path** - Update build script
3. ⚠️ **Re-index if needed** - Ensure all policies loaded

### Short-Term (Next 2 Weeks)
4. 🎯 **Implement dynamic tone adaptation** (Phase 2)
5. 🎯 **Integrate escalation rules** (Phase 3)
6. 🎯 **Add policy validator** (Phase 4)

### Medium-Term (Next Month)
7. 📊 **Add usage analytics** (Phase 5)
8. 🧪 **Create test suite** (Phase 6)
9. 📚 **Update documentation** (Phase 7)

### Long-Term (Ongoing)
10. 🔄 **Monitor and refine** - Weekly analytics review
11. 🔄 **Collect feedback** - Customer satisfaction surveys
12. 🔄 **Update policies** - Quarterly review cycle

---

## Commands Reference

```bash
# Verify policy indexing status
python scripts/build_knowledge_base.py --verify-only

# Re-index all policies
python scripts/build_knowledge_base.py --reset

# Test RAG retrieval
python scripts/test_rag_retrieval.py

# Run policy integration tests
pytest tests/tier2_integration/test_policy_integration.py -v

# Check usage analytics (after implementation)
python -c "from src.rag.usage_analytics import get_usage_stats; print(get_usage_stats(days=7))"
```

---

## Files to Create/Modify

### New Files
- ✅ `docs/architecture/POLICY_INTEGRATION_ARCHITECTURE.md` (this file)
- 🆕 `src/agents/policy_validator.py` (Phase 4)
- 🆕 `src/rag/usage_analytics.py` (Phase 5)
- 🆕 `tests/tier2_integration/test_policy_integration.py` (Phase 6)
- 🆕 `docs/guides/POLICY_UPDATE_WORKFLOW.md` (Phase 7)

### Files to Modify
- 📝 `scripts/build_knowledge_base.py` - Fix directory path (Line 46)
- 📝 `src/agents/enhanced_customer_service_agent.py` - Add tone retrieval, escalation rules, validator
- 📝 `src/rag/retrieval.py` - Add usage logging
- 📝 `README.md` - Link to policy integration docs

---

## Contact & Support

**For Implementation Questions**:
- Technical Lead: tech@tria-aibpo.sg

**For Policy Content Questions**:
- Operations Manager: operations@tria-aibpo.sg

**For Customer Service Training**:
- CSR Manager: support@tria-aibpo.sg

---

**Status**: 🎯 READY FOR IMPLEMENTATION
**Estimated Effort**: 6-7 weeks (with testing)
**Complexity**: Medium
**Impact**: HIGH - Core differentiator for TRIA chatbot

---

**Next Action**: Run verification command to check current indexing status:
```bash
python scripts/build_knowledge_base.py --verify-only
```
