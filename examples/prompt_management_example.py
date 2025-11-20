"""
Prompt Management System - Usage Examples
==========================================

Demonstrates how to use the unified prompt management system with A/B testing.

Run this script to see the system in action:
    python examples/prompt_management_example.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prompts.prompt_manager import get_prompt_manager


# ============================================================================
# EXAMPLE 1: Basic Usage
# ============================================================================

async def example_basic_usage():
    """Example 1: Get prompt with automatic A/B testing"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Usage")
    print("="*70)

    manager = get_prompt_manager()

    # Get prompt for user
    prompt = await manager.get_prompt(
        prompt_type="intent_classification",
        user_id="user_123"
    )

    print(f"\n✓ Got prompt for user_123:")
    print(f"  - Version: {prompt.version}")
    print(f"  - Source: {prompt.source.value}")
    print(f"  - Type: {prompt.type.value}")
    print(f"  - Content preview: {prompt.content[:100]}...")


# ============================================================================
# EXAMPLE 2: A/B Testing
# ============================================================================

async def example_ab_testing():
    """Example 2: Demonstrate A/B testing with multiple users"""
    print("\n" + "="*70)
    print("EXAMPLE 2: A/B Testing Distribution")
    print("="*70)

    manager = get_prompt_manager()

    # Test 100 users
    num_users = 100
    assignments = {"dspy": 0, "manual": 0}

    for i in range(num_users):
        user_id = f"user_{i}"
        group = manager.assign_ab_group(user_id, "intent_classification")
        assignments[group] += 1

    # Calculate percentages
    dspy_pct = (assignments["dspy"] / num_users) * 100
    manual_pct = (assignments["manual"] / num_users) * 100

    print(f"\n✓ Tested {num_users} users:")
    print(f"  - DSPy: {assignments['dspy']} users ({dspy_pct:.1f}%)")
    print(f"  - Manual: {assignments['manual']} users ({manual_pct:.1f}%)")
    print(f"  - Expected: ~90% DSPy, ~10% Manual")


# ============================================================================
# EXAMPLE 3: Performance Tracking
# ============================================================================

async def example_performance_tracking():
    """Example 3: Track and retrieve performance metrics"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Performance Tracking")
    print("="*70)

    manager = get_prompt_manager()

    # Simulate 10 requests with metrics
    prompt_id = "intent_classification_dspy_v1"

    for i in range(10):
        await manager.track_performance(
            prompt_id=prompt_id,
            metrics={
                "accuracy": 0.90 + (i * 0.01),  # 0.90 to 0.99
                "latency_ms": 100 + (i * 10),   # 100 to 190ms
                "token_count": 200 + (i * 5)    # 200 to 245 tokens
            }
        )

    # Get metrics
    metrics = manager.get_metrics(prompt_id)

    print(f"\n✓ Tracked 10 requests for {prompt_id}:")
    print(f"  - Average accuracy: {metrics['avg_accuracy']:.2%}")
    print(f"  - Average latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"  - Average tokens: {metrics['avg_tokens']:.0f}")
    print(f"  - Accuracy samples: {metrics['accuracy_samples']}")


# ============================================================================
# EXAMPLE 4: Version Promotion
# ============================================================================

async def example_version_promotion():
    """Example 4: Gradual rollout with version promotion"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Version Promotion (Gradual Rollout)")
    print("="*70)

    manager = get_prompt_manager()

    # Phase 1: 10% rollout
    await manager.promote_version(
        prompt_type="rag_qa",
        version="dspy_v1",
        rollout_pct=10
    )

    config = manager.get_ab_config("rag_qa")
    print(f"\n✓ Phase 1 (10% rollout):")
    print(f"  - Current version: {config['current_version']}")
    print(f"  - Rollout: {config['rollout_percentage']}%")
    print(f"  - Control: {config['control_percentage']}%")

    # Phase 2: 50% rollout
    await manager.promote_version(
        prompt_type="rag_qa",
        version="dspy_v1",
        rollout_pct=50
    )

    config = manager.get_ab_config("rag_qa")
    print(f"\n✓ Phase 2 (50% rollout):")
    print(f"  - Rollout: {config['rollout_percentage']}%")
    print(f"  - Control: {config['control_percentage']}%")

    # Phase 3: 100% rollout
    await manager.promote_version(
        prompt_type="rag_qa",
        version="dspy_v1",
        rollout_pct=100
    )

    config = manager.get_ab_config("rag_qa")
    print(f"\n✓ Phase 3 (100% rollout):")
    print(f"  - Rollout: {config['rollout_percentage']}%")
    print(f"  - Control: {config['control_percentage']}%")
    print(f"  - Status: Fully deployed!")


# ============================================================================
# EXAMPLE 5: Intent Prompt Helper
# ============================================================================

async def example_intent_prompt():
    """Example 5: Use intent classification helper"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Intent Classification Helper")
    print("="*70)

    manager = get_prompt_manager()

    # Get formatted intent prompt
    formatted_prompt = await manager.get_intent_prompt(
        user_message="I want to order 50 boxes",
        conversation_history=[
            {"role": "user", "content": "Hello, I'm from ABC Corp"},
            {"role": "assistant", "content": "Hello! How can I help you?"}
        ],
        user_id="user_demo"
    )

    print(f"\n✓ Generated intent classification prompt:")
    print(f"\n{formatted_prompt[:300]}...")
    print(f"\n  (Total length: {len(formatted_prompt)} characters)")


# ============================================================================
# EXAMPLE 6: RAG Prompt Helper
# ============================================================================

async def example_rag_prompt():
    """Example 6: Use RAG QA helper"""
    print("\n" + "="*70)
    print("EXAMPLE 6: RAG Question Answering Helper")
    print("="*70)

    manager = get_prompt_manager()

    # Get formatted RAG prompt
    formatted_prompt = await manager.get_rag_prompt(
        user_question="What is your return policy?",
        retrieved_knowledge="We accept returns within 30 days of purchase for unopened items. Returns require original receipt.",
        conversation_history=[],
        user_id="user_demo"
    )

    print(f"\n✓ Generated RAG QA prompt:")
    print(f"\n{formatted_prompt[:300]}...")
    print(f"\n  (Total length: {len(formatted_prompt)} characters)")


# ============================================================================
# EXAMPLE 7: Compare All Prompt Versions
# ============================================================================

async def example_compare_versions():
    """Example 7: Compare metrics across all prompt versions"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Compare All Prompt Versions")
    print("="*70)

    manager = get_prompt_manager()

    # Simulate metrics for multiple versions
    versions = [
        "intent_classification_dspy_v1",
        "intent_classification_manual_v1",
        "rag_qa_dspy_v1",
        "rag_qa_manual_v1"
    ]

    for version in versions:
        for i in range(5):
            await manager.track_performance(
                prompt_id=version,
                metrics={
                    "accuracy": 0.85 + (hash(version) % 15) * 0.01,
                    "latency_ms": 100 + (hash(version) % 100),
                    "token_count": 150 + (hash(version) % 150)
                }
            )

    # Get and display all metrics
    all_metrics = manager.get_metrics()

    print("\n✓ Metrics comparison:")
    print(f"\n{'Prompt ID':<40} {'Accuracy':<12} {'Latency':<12} {'Tokens':<10}")
    print("-" * 74)

    for prompt_id, metrics in all_metrics.items():
        if metrics['avg_accuracy'] > 0:  # Only show if we have accuracy data
            print(f"{prompt_id:<40} {metrics['avg_accuracy']:<12.2%} "
                  f"{metrics['avg_latency_ms']:<12.0f}ms {metrics['avg_tokens']:<10.0f}")


# ============================================================================
# EXAMPLE 8: Configuration Management
# ============================================================================

async def example_configuration():
    """Example 8: View and manage A/B test configuration"""
    print("\n" + "="*70)
    print("EXAMPLE 8: Configuration Management")
    print("="*70)

    manager = get_prompt_manager()

    # Get all configurations
    all_configs = manager.get_ab_config()

    print("\n✓ Current A/B test configurations:")
    print()

    for prompt_type, config in all_configs.items():
        print(f"  {prompt_type}:")
        print(f"    - Current: {config['current_version']} ({config['rollout_percentage']}%)")
        print(f"    - Control: {config['control_version']} ({config['control_percentage']}%)")
        print(f"    - Enabled: {config['enabled']}")
        print()


# ============================================================================
# EXAMPLE 9: Deterministic Assignment
# ============================================================================

async def example_deterministic_assignment():
    """Example 9: Verify deterministic A/B assignment"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Deterministic Assignment Verification")
    print("="*70)

    manager = get_prompt_manager()

    # Test same user multiple times
    user_id = "test_user_deterministic"
    assignments = set()

    for _ in range(10):
        group = manager.assign_ab_group(user_id, "intent_classification")
        assignments.add(group)

    print(f"\n✓ Tested user '{user_id}' 10 times:")
    print(f"  - Unique assignments: {len(assignments)}")
    print(f"  - Assignment: {assignments.pop()}")
    print(f"  - Deterministic: {'✓ YES' if len(assignments) == 0 else '✗ NO'}")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("PROMPT MANAGEMENT SYSTEM - USAGE EXAMPLES")
    print("="*70)
    print("\nDemonstrating unified prompt management with A/B testing...")

    try:
        await example_basic_usage()
        await example_ab_testing()
        await example_performance_tracking()
        await example_version_promotion()
        await example_intent_prompt()
        await example_rag_prompt()
        await example_compare_versions()
        await example_configuration()
        await example_deterministic_assignment()

        print("\n" + "="*70)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Review src/prompts/README.md for detailed documentation")
        print("  2. Run tests: pytest tests/test_prompt_manager.py -v")
        print("  3. Integrate with EnhancedCustomerServiceAgent")
        print("  4. Set up metrics dashboard")
        print()

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
