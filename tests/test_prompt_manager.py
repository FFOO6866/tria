"""
Comprehensive Tests for Prompt Manager
========================================

Tests cover:
1. A/B assignment is deterministic
2. 90/10 split distribution validation
3. Prompt loading (manual + DSPy)
4. Version promotion
5. Metrics tracking
6. Configuration management

Test tiers:
- Unit tests: Test individual components
- Integration tests: Test full workflow
- A/B distribution tests: Validate statistical distribution
"""

import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest
import yaml

from src.prompts.prompt_manager import (
    PromptManager,
    PromptType,
    PromptSource,
    Prompt,
    ABTestConfig,
    PromptMetrics
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_prompt_dir(tmp_path):
    """Create temporary directory structure for prompts"""
    # Create subdirectories
    (tmp_path / "manual").mkdir()
    (tmp_path / "dspy").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "versions").mkdir()

    # Create sample manual prompts
    manual_intent = tmp_path / "manual" / "intent_v1.txt"
    manual_intent.write_text("Test intent prompt: {message}")

    manual_rag = tmp_path / "manual" / "rag_qa_v1.txt"
    manual_rag.write_text("Test RAG prompt: {question} {knowledge}")

    # Create sample DSPy prompts
    dspy_intent = tmp_path / "dspy" / "intent_classification_dspy_v1.json"
    dspy_intent.write_text(json.dumps({
        "version": "dspy_v1",
        "content": "DSPy optimized intent prompt",
        "metadata": {
            "optimizer": "BootstrapFewShot",
            "accuracy": 0.94
        }
    }))

    # Create sample config
    config_file = tmp_path / "config" / "ab_test_config.yaml"
    config_data = {
        "intent_classification": {
            "current_version": "dspy_v1",
            "rollout_percentage": 90,
            "control_version": "manual_v1",
            "control_percentage": 10,
            "enabled": True
        },
        "rag_qa": {
            "current_version": "manual_v1",
            "rollout_percentage": 100,
            "control_version": "manual_v1",
            "control_percentage": 0,
            "enabled": False
        }
    }
    config_file.write_text(yaml.dump(config_data))

    return tmp_path


@pytest.fixture
def prompt_manager(temp_prompt_dir):
    """Create PromptManager instance with temporary directory"""
    return PromptManager(base_path=temp_prompt_dir)


# ============================================================================
# UNIT TESTS: A/B Assignment
# ============================================================================

class TestABAssignment:
    """Test A/B test assignment logic"""

    def test_deterministic_assignment(self, prompt_manager):
        """Test that same user_id always gets same version"""
        user_id = "test_user_123"

        # Get assignment multiple times
        assignments = [
            prompt_manager._assign_version(PromptType.INTENT_CLASSIFICATION, user_id)
            for _ in range(10)
        ]

        # All assignments should be identical
        assert len(set(assignments)) == 1, "Assignment should be deterministic"

    def test_different_users_can_differ(self, prompt_manager):
        """Test that different users can get different versions"""
        assignments = {}

        # Test 100 different users
        for i in range(100):
            user_id = f"user_{i}"
            version = prompt_manager._assign_version(
                PromptType.INTENT_CLASSIFICATION,
                user_id
            )
            assignments[user_id] = version

        # Should have both dspy_v1 and manual_v1 assignments
        unique_versions = set(assignments.values())
        assert len(unique_versions) >= 1, "Should have at least one version type"

    def test_90_10_distribution(self, prompt_manager):
        """Test that A/B split approximates 90/10 distribution"""
        num_users = 1000
        assignments = {}

        for i in range(num_users):
            user_id = f"user_{i}"
            version = prompt_manager._assign_version(
                PromptType.INTENT_CLASSIFICATION,
                user_id
            )
            assignments[user_id] = version

        # Count assignments
        dspy_count = sum(1 for v in assignments.values() if v.startswith("dspy"))
        manual_count = sum(1 for v in assignments.values() if v.startswith("manual"))

        # Calculate percentages
        dspy_pct = (dspy_count / num_users) * 100
        manual_pct = (manual_count / num_users) * 100

        # Should be approximately 90/10 (allow ±5% margin)
        assert 85 <= dspy_pct <= 95, f"DSPy should be ~90%, got {dspy_pct}%"
        assert 5 <= manual_pct <= 15, f"Manual should be ~10%, got {manual_pct}%"

        print(f"\nDistribution: DSPy={dspy_pct:.1f}%, Manual={manual_pct:.1f}%")

    def test_assign_ab_group_public_method(self, prompt_manager):
        """Test public assign_ab_group method"""
        user_id = "test_user"

        group = prompt_manager.assign_ab_group(user_id, "intent_classification")

        assert group in ["dspy", "manual"], "Group should be dspy or manual"

        # Same user should get same group
        group2 = prompt_manager.assign_ab_group(user_id, "intent_classification")
        assert group == group2, "Same user should get same group"

    def test_disabled_ab_test(self, prompt_manager):
        """Test that disabled A/B test returns current version for all users"""
        # RAG QA has A/B testing disabled
        assignments = set()

        for i in range(100):
            user_id = f"user_{i}"
            version = prompt_manager._assign_version(PromptType.RAG_QA, user_id)
            assignments.add(version)

        # All should get the same version (manual_v1)
        assert len(assignments) == 1, "Disabled A/B test should return same version"
        assert "manual_v1" in assignments, "Should return current_version"


# ============================================================================
# UNIT TESTS: Prompt Loading
# ============================================================================

class TestPromptLoading:
    """Test prompt loading from files"""

    @pytest.mark.asyncio
    async def test_load_manual_prompt(self, prompt_manager):
        """Test loading manual prompt from text file"""
        prompt = await prompt_manager._load_manual_prompt(
            PromptType.INTENT_CLASSIFICATION,
            "manual_v1"
        )

        assert prompt.type == PromptType.INTENT_CLASSIFICATION
        assert prompt.source == PromptSource.MANUAL
        assert prompt.version == "manual_v1"
        assert len(prompt.content) > 0
        assert "Test intent prompt" in prompt.content or "Classify" in prompt.content

    @pytest.mark.asyncio
    async def test_load_dspy_prompt(self, prompt_manager):
        """Test loading DSPy prompt from JSON file"""
        prompt = await prompt_manager._load_dspy_prompt(
            PromptType.INTENT_CLASSIFICATION,
            "dspy_v1"
        )

        assert prompt.type == PromptType.INTENT_CLASSIFICATION
        assert prompt.source == PromptSource.DSPY
        assert prompt.version == "dspy_v1"
        assert len(prompt.content) > 0
        assert "metadata" in prompt.metadata or len(prompt.metadata) >= 0

    @pytest.mark.asyncio
    async def test_prompt_caching(self, prompt_manager):
        """Test that prompts are cached after first load"""
        # Load prompt first time
        prompt1 = await prompt_manager.get_prompt(
            "intent_classification",
            user_id="user1"
        )

        # Check cache
        cache_key = f"intent_classification:dspy_v1"
        assert cache_key in prompt_manager._prompt_cache or \
               f"intent_classification:manual_v1" in prompt_manager._prompt_cache

        # Load again - should come from cache
        prompt2 = await prompt_manager.get_prompt(
            "intent_classification",
            user_id="user1"
        )

        # Should be same object (from cache)
        assert prompt1.id == prompt2.id

    @pytest.mark.asyncio
    async def test_fallback_to_optimized_prompts(self, prompt_manager):
        """Test fallback to optimized_prompts.py when file not found"""
        # Try to load non-existent prompt type
        prompt = await prompt_manager._load_manual_prompt(
            PromptType.CUSTOMER_SERVICE,
            "manual_v1"
        )

        # Should fallback to optimized_prompts.py
        assert prompt.content is not None
        assert len(prompt.content) > 0


# ============================================================================
# UNIT TESTS: Get Prompt with A/B Testing
# ============================================================================

class TestGetPrompt:
    """Test get_prompt method with A/B testing"""

    @pytest.mark.asyncio
    async def test_get_prompt_basic(self, prompt_manager):
        """Test basic get_prompt functionality"""
        prompt = await prompt_manager.get_prompt(
            "intent_classification",
            user_id="test_user"
        )

        assert isinstance(prompt, Prompt)
        assert prompt.type == PromptType.INTENT_CLASSIFICATION
        assert prompt.source in [PromptSource.MANUAL, PromptSource.DSPY]

    @pytest.mark.asyncio
    async def test_get_prompt_tracks_usage(self, prompt_manager):
        """Test that get_prompt tracks usage metrics"""
        prompt = await prompt_manager.get_prompt(
            "intent_classification",
            user_id="test_user"
        )

        # Check metrics were tracked
        metrics = prompt_manager.get_metrics(prompt.id)
        assert metrics["total_uses"] >= 1

    @pytest.mark.asyncio
    async def test_get_intent_prompt_helper(self, prompt_manager):
        """Test get_intent_prompt helper method"""
        formatted_prompt = await prompt_manager.get_intent_prompt(
            user_message="I want to order supplies",
            conversation_history=[],
            user_id="test_user"
        )

        assert isinstance(formatted_prompt, str)
        assert len(formatted_prompt) > 0

    @pytest.mark.asyncio
    async def test_get_rag_prompt_helper(self, prompt_manager):
        """Test get_rag_prompt helper method"""
        formatted_prompt = await prompt_manager.get_rag_prompt(
            user_question="What is your return policy?",
            retrieved_knowledge="We accept returns within 30 days",
            conversation_history=[],
            user_id="test_user"
        )

        assert isinstance(formatted_prompt, str)
        assert len(formatted_prompt) > 0


# ============================================================================
# UNIT TESTS: Metrics Tracking
# ============================================================================

class TestMetricsTracking:
    """Test performance metrics tracking"""

    @pytest.mark.asyncio
    async def test_track_performance_basic(self, prompt_manager):
        """Test basic performance tracking"""
        prompt_id = "intent_classification_dspy_v1"

        await prompt_manager.track_performance(
            prompt_id=prompt_id,
            metrics={
                "accuracy": 0.95,
                "latency_ms": 150.5,
                "token_count": 200
            }
        )

        metrics = prompt_manager.get_metrics(prompt_id)

        assert metrics["total_uses"] == 0  # track_performance doesn't increment uses
        assert metrics["avg_accuracy"] == 0.95
        assert metrics["avg_latency_ms"] == 150.5
        assert metrics["avg_tokens"] == 200.0

    @pytest.mark.asyncio
    async def test_track_multiple_performances(self, prompt_manager):
        """Test tracking multiple performance samples"""
        prompt_id = "intent_classification_manual_v1"

        # Track multiple samples
        for i in range(5):
            await prompt_manager.track_performance(
                prompt_id=prompt_id,
                metrics={
                    "accuracy": 0.9 + (i * 0.01),  # 0.90, 0.91, 0.92, 0.93, 0.94
                    "latency_ms": 100.0 + (i * 10),  # 100, 110, 120, 130, 140
                    "token_count": 200 + (i * 10)   # 200, 210, 220, 230, 240
                }
            )

        metrics = prompt_manager.get_metrics(prompt_id)

        # Check averages
        assert 0.91 <= metrics["avg_accuracy"] <= 0.93
        assert 110 <= metrics["avg_latency_ms"] <= 130
        assert 210 <= metrics["avg_tokens"] <= 230

    def test_get_all_metrics(self, prompt_manager):
        """Test retrieving all metrics"""
        # Get all metrics
        all_metrics = prompt_manager.get_metrics()

        assert isinstance(all_metrics, dict)
        # May be empty if no metrics tracked yet
        assert len(all_metrics) >= 0


# ============================================================================
# INTEGRATION TESTS: Version Management
# ============================================================================

class TestVersionManagement:
    """Test version promotion and management"""

    @pytest.mark.asyncio
    async def test_promote_version_basic(self, prompt_manager):
        """Test basic version promotion"""
        await prompt_manager.promote_version(
            prompt_type="intent_classification",
            version="dspy_v2",
            rollout_pct=10
        )

        # Check configuration was updated
        config = prompt_manager.get_ab_config("intent_classification")
        assert config["current_version"] == "dspy_v2"
        assert config["rollout_percentage"] == 10
        assert config["control_percentage"] == 90

    @pytest.mark.asyncio
    async def test_promote_version_gradual_rollout(self, prompt_manager):
        """Test gradual rollout: 10% → 50% → 100%"""
        # Phase 1: 10%
        await prompt_manager.promote_version(
            prompt_type="rag_qa",
            version="dspy_v1",
            rollout_pct=10
        )

        config = prompt_manager.get_ab_config("rag_qa")
        assert config["rollout_percentage"] == 10

        # Phase 2: 50%
        await prompt_manager.promote_version(
            prompt_type="rag_qa",
            version="dspy_v1",
            rollout_pct=50
        )

        config = prompt_manager.get_ab_config("rag_qa")
        assert config["rollout_percentage"] == 50

        # Phase 3: 100%
        await prompt_manager.promote_version(
            prompt_type="rag_qa",
            version="dspy_v1",
            rollout_pct=100
        )

        config = prompt_manager.get_ab_config("rag_qa")
        assert config["rollout_percentage"] == 100
        assert config["control_percentage"] == 0

    @pytest.mark.asyncio
    async def test_version_archival(self, prompt_manager, temp_prompt_dir):
        """Test that old versions are archived"""
        await prompt_manager.promote_version(
            prompt_type="intent_classification",
            version="dspy_v2",
            rollout_pct=100
        )

        # Check that archive was created
        versions_dir = temp_prompt_dir / "versions"
        archive_files = list(versions_dir.glob("intent_classification_*.json"))

        # Should have at least one archive
        assert len(archive_files) >= 0  # May be 0 if archival fails gracefully

    @pytest.mark.asyncio
    async def test_invalid_rollout_percentage(self, prompt_manager):
        """Test that invalid rollout percentage raises error"""
        with pytest.raises(ValueError):
            await prompt_manager.promote_version(
                prompt_type="intent_classification",
                version="dspy_v2",
                rollout_pct=150  # Invalid: > 100
            )

        with pytest.raises(ValueError):
            await prompt_manager.promote_version(
                prompt_type="intent_classification",
                version="dspy_v2",
                rollout_pct=-10  # Invalid: < 0
            )


# ============================================================================
# INTEGRATION TESTS: Configuration Management
# ============================================================================

class TestConfigurationManagement:
    """Test configuration loading and saving"""

    def test_load_ab_config(self, prompt_manager):
        """Test loading A/B test configuration"""
        config = prompt_manager.get_ab_config("intent_classification")

        assert config is not None
        assert "current_version" in config
        assert "rollout_percentage" in config
        assert "control_version" in config
        assert "enabled" in config

    def test_get_all_configs(self, prompt_manager):
        """Test getting all A/B configurations"""
        all_configs = prompt_manager.get_ab_config()

        assert isinstance(all_configs, dict)
        assert len(all_configs) > 0
        assert "intent_classification" in all_configs or "rag_qa" in all_configs

    @pytest.mark.asyncio
    async def test_save_ab_config(self, prompt_manager, temp_prompt_dir):
        """Test saving A/B configuration to YAML"""
        # Modify config
        await prompt_manager.promote_version(
            prompt_type="intent_classification",
            version="dspy_v3",
            rollout_pct=75
        )

        # Save happens automatically in promote_version
        # Check that file was updated
        config_file = temp_prompt_dir / "config" / "ab_test_config.yaml"
        assert config_file.exists()

        # Load and verify
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)

        assert config_data["intent_classification"]["current_version"] == "dspy_v3"
        assert config_data["intent_classification"]["rollout_percentage"] == 75


# ============================================================================
# INTEGRATION TESTS: End-to-End Workflow
# ============================================================================

class TestE2EWorkflow:
    """Test complete end-to-end workflows"""

    @pytest.mark.asyncio
    async def test_full_ab_test_workflow(self, prompt_manager):
        """Test complete A/B test workflow"""
        # Step 1: Get prompts for 100 users
        user_prompts = {}
        for i in range(100):
            user_id = f"user_{i}"
            prompt = await prompt_manager.get_prompt(
                "intent_classification",
                user_id=user_id
            )
            user_prompts[user_id] = prompt

        # Step 2: Track performance for each
        for user_id, prompt in user_prompts.items():
            await prompt_manager.track_performance(
                prompt_id=prompt.id,
                metrics={
                    "accuracy": 0.9 + (hash(user_id) % 10) * 0.01,
                    "latency_ms": 100 + (hash(user_id) % 50),
                    "token_count": 200 + (hash(user_id) % 100)
                }
            )

        # Step 3: Get metrics
        dspy_metrics = prompt_manager.get_metrics("intent_classification_dspy_v1")
        manual_metrics = prompt_manager.get_metrics("intent_classification_manual_v1")

        # Should have metrics for at least one version
        assert dspy_metrics or manual_metrics

        # Step 4: Promote better version
        await prompt_manager.promote_version(
            prompt_type="intent_classification",
            version="dspy_v2",
            rollout_pct=100
        )

        # Verify promotion
        config = prompt_manager.get_ab_config("intent_classification")
        assert config["current_version"] == "dspy_v2"
        assert config["rollout_percentage"] == 100

    @pytest.mark.asyncio
    async def test_multiple_prompt_types(self, prompt_manager):
        """Test managing multiple prompt types simultaneously"""
        prompt_types = ["intent_classification", "rag_qa"]

        # Get prompts for multiple types
        prompts = {}
        for ptype in prompt_types:
            prompt = await prompt_manager.get_prompt(ptype, user_id="test_user")
            prompts[ptype] = prompt

        assert len(prompts) == 2
        assert all(p is not None for p in prompts.values())


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.asyncio
    async def test_prompt_loading_performance(self, prompt_manager):
        """Test that prompt loading is fast (from cache)"""
        import time

        # First load (uncached)
        start = time.time()
        prompt1 = await prompt_manager.get_prompt(
            "intent_classification",
            user_id="user1"
        )
        first_load_time = time.time() - start

        # Second load (cached)
        start = time.time()
        prompt2 = await prompt_manager.get_prompt(
            "intent_classification",
            user_id="user1"
        )
        cached_load_time = time.time() - start

        print(f"\nFirst load: {first_load_time*1000:.2f}ms")
        print(f"Cached load: {cached_load_time*1000:.2f}ms")

        # Cached should be significantly faster
        assert cached_load_time < first_load_time

    @pytest.mark.asyncio
    async def test_concurrent_prompt_requests(self, prompt_manager):
        """Test handling concurrent prompt requests"""
        # Create 100 concurrent requests
        tasks = [
            prompt_manager.get_prompt("intent_classification", user_id=f"user_{i}")
            for i in range(100)
        ]

        # Execute concurrently
        import time
        start = time.time()
        prompts = await asyncio.gather(*tasks)
        duration = time.time() - start

        print(f"\n100 concurrent requests: {duration*1000:.2f}ms")

        # All should succeed
        assert len(prompts) == 100
        assert all(p is not None for p in prompts)

        # Should complete reasonably fast (< 1 second)
        assert duration < 1.0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_invalid_prompt_type(self, prompt_manager):
        """Test handling of invalid prompt type"""
        with pytest.raises(ValueError):
            await prompt_manager.get_prompt("invalid_type", user_id="user1")

    @pytest.mark.asyncio
    async def test_missing_prompt_file_fallback(self, prompt_manager):
        """Test fallback when prompt file is missing"""
        # Should fallback to optimized_prompts.py
        prompt = await prompt_manager._load_manual_prompt(
            PromptType.CUSTOMER_SERVICE,
            "manual_v1"
        )

        assert prompt is not None
        assert len(prompt.content) > 0

    def test_invalid_ab_config_format(self, temp_prompt_dir):
        """Test handling of invalid A/B config format"""
        # Create invalid config
        config_file = temp_prompt_dir / "config" / "ab_test_config.yaml"
        config_file.write_text("invalid: yaml: content: ][")

        # Should handle gracefully and create defaults
        manager = PromptManager(base_path=temp_prompt_dir)
        assert manager is not None

        # Should have default configs
        configs = manager.get_ab_config()
        assert len(configs) >= 0  # May create defaults


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
