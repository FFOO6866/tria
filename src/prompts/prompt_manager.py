"""
Unified Prompt Management System with A/B Testing
==================================================

Features:
- Unified interface for manual and DSPy prompts
- Version control for prompts (store history)
- A/B testing framework (90% DSPy, 10% manual)
- Performance tracking per prompt version
- Gradual rollout support (10% → 50% → 100%)
- Prompt loading from files and DSPy models
- Metrics integration (track which prompt used for each request)

Architecture:
- Manual prompts: Text files in src/prompts/manual/
- DSPy prompts: Serialized JSON in src/prompts/dspy/
- Configuration: YAML in src/prompts/config/ab_test_config.yaml
- Versions: Historical versions in src/prompts/versions/

Usage:
    from src.prompts.prompt_manager import PromptManager

    manager = PromptManager()

    # Get prompt with A/B testing
    prompt = await manager.get_prompt("intent_classification", user_id="user123")

    # Track performance
    await manager.track_performance(
        prompt_id=prompt.id,
        metrics={
            "accuracy": 0.95,
            "latency_ms": 150,
            "token_count": 200
        }
    )

    # Promote version after validation
    await manager.promote_version(
        prompt_type="intent_classification",
        version="dspy_v2",
        rollout_pct=50  # Gradual rollout to 50%
    )
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class PromptType(str, Enum):
    """Supported prompt types"""
    INTENT_CLASSIFICATION = "intent_classification"
    RAG_QA = "rag_qa"
    CUSTOMER_SERVICE = "customer_service"
    TONE_GUIDELINES = "tone_guidelines"


class PromptSource(str, Enum):
    """Prompt source (manual vs DSPy)"""
    MANUAL = "manual"
    DSPY = "dspy"


@dataclass
class Prompt:
    """Prompt object with metadata"""
    id: str  # Unique identifier (e.g., "intent_v1_manual")
    type: PromptType
    source: PromptSource
    version: str
    content: str  # Actual prompt text
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source.value,
            "version": self.version,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ABTestConfig:
    """A/B test configuration for a prompt type"""
    prompt_type: PromptType
    current_version: str  # e.g., "dspy_v1"
    rollout_percentage: int  # 0-100
    control_version: str  # e.g., "manual_v1"
    control_percentage: int  # 0-100
    enabled: bool = True

    def __post_init__(self):
        """Validate percentages sum to 100"""
        if self.rollout_percentage + self.control_percentage != 100:
            raise ValueError(
                f"Percentages must sum to 100, got {self.rollout_percentage} + "
                f"{self.control_percentage} = {self.rollout_percentage + self.control_percentage}"
            )


@dataclass
class PromptMetrics:
    """Performance metrics for a prompt"""
    prompt_id: str
    total_uses: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    total_accuracy: float = 0.0
    accuracy_count: int = 0

    @property
    def avg_latency_ms(self) -> float:
        """Average latency"""
        return self.total_latency_ms / self.total_uses if self.total_uses > 0 else 0.0

    @property
    def avg_tokens(self) -> float:
        """Average token count"""
        return self.total_tokens / self.total_uses if self.total_uses > 0 else 0.0

    @property
    def avg_accuracy(self) -> float:
        """Average accuracy"""
        return self.total_accuracy / self.accuracy_count if self.accuracy_count > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "prompt_id": self.prompt_id,
            "total_uses": self.total_uses,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_tokens": self.avg_tokens,
            "avg_accuracy": self.avg_accuracy,
            "accuracy_samples": self.accuracy_count
        }


# ============================================================================
# PROMPT MANAGER
# ============================================================================

class PromptManager:
    """
    Unified prompt management with versioning and A/B testing

    Responsibilities:
    1. Load prompts from files (manual) and serialized models (DSPy)
    2. A/B test assignment (deterministic hash-based)
    3. Performance tracking per prompt version
    4. Version promotion with gradual rollout
    5. Metrics integration
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize prompt manager

        Args:
            base_path: Base path for prompts (defaults to src/prompts/)
        """
        if base_path is None:
            base_path = Path(__file__).parent

        self.base_path = Path(base_path)
        self.manual_path = self.base_path / "manual"
        self.dspy_path = self.base_path / "dspy"
        self.config_path = self.base_path / "config"
        self.versions_path = self.base_path / "versions"

        # Ensure directories exist
        for path in [self.manual_path, self.dspy_path, self.config_path, self.versions_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Cache for loaded prompts
        self._prompt_cache: Dict[str, Prompt] = {}

        # A/B test configurations
        self._ab_configs: Dict[PromptType, ABTestConfig] = {}

        # Performance metrics
        self._metrics: Dict[str, PromptMetrics] = {}

        # Load configuration
        self._load_ab_config()

        logger.info(f"PromptManager initialized with base_path={self.base_path}")

    # ========================================================================
    # CONFIGURATION LOADING
    # ========================================================================

    def _load_ab_config(self):
        """Load A/B test configuration from YAML"""
        config_file = self.config_path / "ab_test_config.yaml"

        if not config_file.exists():
            logger.warning(f"A/B config not found: {config_file}, using defaults")
            self._create_default_config()
            return

        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            # Parse each prompt type configuration
            for prompt_type_str, config in config_data.items():
                try:
                    prompt_type = PromptType(prompt_type_str)
                    ab_config = ABTestConfig(
                        prompt_type=prompt_type,
                        current_version=config.get("current_version", "manual_v1"),
                        rollout_percentage=config.get("rollout_percentage", 100),
                        control_version=config.get("control_version", "manual_v1"),
                        control_percentage=config.get("control_percentage", 0),
                        enabled=config.get("enabled", True)
                    )
                    self._ab_configs[prompt_type] = ab_config
                    logger.info(f"Loaded A/B config for {prompt_type.value}: {ab_config}")
                except (ValueError, KeyError) as e:
                    logger.error(f"Invalid A/B config for {prompt_type_str}: {e}")

        except Exception as e:
            logger.error(f"Failed to load A/B config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default A/B test configuration"""
        # Default: 100% manual prompts (safe default)
        for prompt_type in PromptType:
            self._ab_configs[prompt_type] = ABTestConfig(
                prompt_type=prompt_type,
                current_version="manual_v1",
                rollout_percentage=100,
                control_version="manual_v1",
                control_percentage=0,
                enabled=False  # Disabled by default
            )

        logger.info("Created default A/B test configuration")

    # ========================================================================
    # PROMPT LOADING
    # ========================================================================

    async def get_prompt(
        self,
        prompt_type: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Prompt:
        """
        Get prompt with A/B testing support

        Args:
            prompt_type: Type of prompt (intent_classification, rag_qa, etc.)
            user_id: User identifier for A/B assignment
            context: Optional context for prompt formatting

        Returns:
            Prompt object with content and metadata
        """
        # Convert string to enum
        try:
            ptype = PromptType(prompt_type)
        except ValueError:
            raise ValueError(f"Invalid prompt type: {prompt_type}")

        # Get A/B test assignment
        version = self._assign_version(ptype, user_id)

        # Load prompt
        prompt = await self._load_prompt(ptype, version)

        # Track usage
        self._track_usage(prompt.id)

        return prompt

    def _assign_version(self, prompt_type: PromptType, user_id: str) -> str:
        """
        Deterministic A/B test assignment

        Uses hash-based assignment to ensure same user always gets same version.

        Args:
            prompt_type: Type of prompt
            user_id: User identifier

        Returns:
            Version string (e.g., "dspy_v1" or "manual_v1")
        """
        # Get A/B config for this prompt type
        ab_config = self._ab_configs.get(prompt_type)

        if not ab_config or not ab_config.enabled:
            # No A/B test configured, return current version
            return ab_config.current_version if ab_config else "manual_v1"

        # Deterministic hash-based assignment
        hash_input = f"{prompt_type.value}:{user_id}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_val % 100  # 0-99

        # Assign based on rollout percentage
        if bucket < ab_config.rollout_percentage:
            return ab_config.current_version
        else:
            return ab_config.control_version

    def assign_ab_group(self, user_id: str, prompt_type: str = "intent_classification") -> str:
        """
        Public method to check which A/B group a user is in

        Args:
            user_id: User identifier
            prompt_type: Type of prompt (defaults to intent_classification)

        Returns:
            "dspy" or "manual"
        """
        try:
            ptype = PromptType(prompt_type)
        except ValueError:
            ptype = PromptType.INTENT_CLASSIFICATION

        version = self._assign_version(ptype, user_id)

        # Extract source from version (e.g., "dspy_v1" -> "dspy")
        if version.startswith("dspy"):
            return "dspy"
        else:
            return "manual"

    async def _load_prompt(self, prompt_type: PromptType, version: str) -> Prompt:
        """
        Load prompt from cache or file

        Args:
            prompt_type: Type of prompt
            version: Version string

        Returns:
            Prompt object
        """
        # Check cache
        cache_key = f"{prompt_type.value}:{version}"
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]

        # Determine source from version
        if version.startswith("dspy"):
            source = PromptSource.DSPY
            prompt = await self._load_dspy_prompt(prompt_type, version)
        else:
            source = PromptSource.MANUAL
            prompt = await self._load_manual_prompt(prompt_type, version)

        # Cache and return
        self._prompt_cache[cache_key] = prompt
        return prompt

    async def _load_manual_prompt(self, prompt_type: PromptType, version: str) -> Prompt:
        """Load manual prompt from text file"""
        # Map prompt type to filename
        filename_map = {
            PromptType.INTENT_CLASSIFICATION: "intent_v1.txt",
            PromptType.RAG_QA: "rag_qa_v1.txt",
            PromptType.CUSTOMER_SERVICE: "customer_service_v1.txt",
            PromptType.TONE_GUIDELINES: "tone_v1.txt"
        }

        filename = filename_map.get(prompt_type, f"{prompt_type.value}_v1.txt")
        filepath = self.manual_path / filename

        if not filepath.exists():
            # Fallback: try to import from optimized_prompts.py
            logger.warning(f"Manual prompt file not found: {filepath}, using fallback")
            content = self._get_fallback_prompt(prompt_type)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

        return Prompt(
            id=f"{prompt_type.value}_{version}",
            type=prompt_type,
            source=PromptSource.MANUAL,
            version=version,
            content=content,
            metadata={"file": str(filepath)}
        )

    async def _load_dspy_prompt(self, prompt_type: PromptType, version: str) -> Prompt:
        """Load DSPy prompt from serialized JSON"""
        filename = f"{prompt_type.value}_{version}.json"
        filepath = self.dspy_path / filename

        if not filepath.exists():
            logger.warning(f"DSPy prompt not found: {filepath}, falling back to manual")
            # Fallback to manual version
            return await self._load_manual_prompt(prompt_type, "manual_v1")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return Prompt(
                id=f"{prompt_type.value}_{version}",
                type=prompt_type,
                source=PromptSource.DSPY,
                version=version,
                content=data.get("content", ""),
                metadata=data.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Failed to load DSPy prompt {filepath}: {e}")
            # Fallback to manual
            return await self._load_manual_prompt(prompt_type, "manual_v1")

    def _get_fallback_prompt(self, prompt_type: PromptType) -> str:
        """Get fallback prompt from optimized_prompts.py"""
        try:
            from .optimized_prompts import (
                OPTIMIZED_INTENT_PROMPT,
                OPTIMIZED_RAG_QA_PROMPT,
                OPTIMIZED_CUSTOMER_SERVICE_PROMPT
            )

            fallback_map = {
                PromptType.INTENT_CLASSIFICATION: OPTIMIZED_INTENT_PROMPT,
                PromptType.RAG_QA: OPTIMIZED_RAG_QA_PROMPT,
                PromptType.CUSTOMER_SERVICE: OPTIMIZED_CUSTOMER_SERVICE_PROMPT
            }

            return fallback_map.get(prompt_type, "No prompt available")
        except ImportError:
            logger.error("Could not import optimized_prompts.py")
            return "No prompt available"

    # ========================================================================
    # PROMPT-SPECIFIC METHODS
    # ========================================================================

    async def get_intent_prompt(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: str = "default"
    ) -> str:
        """Get intent classification prompt with context"""
        prompt = await self.get_prompt("intent_classification", user_id)

        # Format prompt with context
        from .optimized_prompts import build_optimized_intent_prompt
        formatted = build_optimized_intent_prompt(user_message, conversation_history)

        return formatted

    async def get_rag_prompt(
        self,
        user_question: str,
        retrieved_knowledge: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: str = "default"
    ) -> str:
        """Get RAG QA prompt with context"""
        prompt = await self.get_prompt("rag_qa", user_id)

        # Format prompt with context
        from .optimized_prompts import build_optimized_rag_qa_prompt
        formatted = build_optimized_rag_qa_prompt(
            user_question,
            retrieved_knowledge,
            conversation_history
        )

        return formatted

    # ========================================================================
    # PERFORMANCE TRACKING
    # ========================================================================

    def _track_usage(self, prompt_id: str):
        """Track prompt usage"""
        if prompt_id not in self._metrics:
            self._metrics[prompt_id] = PromptMetrics(prompt_id=prompt_id)

        self._metrics[prompt_id].total_uses += 1

    async def track_performance(
        self,
        prompt_id: str,
        metrics: Dict[str, Any]
    ):
        """
        Track performance metrics for a prompt

        Args:
            prompt_id: Prompt identifier
            metrics: Dictionary with metrics:
                - accuracy: float (0.0-1.0)
                - latency_ms: float
                - token_count: int
        """
        if prompt_id not in self._metrics:
            self._metrics[prompt_id] = PromptMetrics(prompt_id=prompt_id)

        pm = self._metrics[prompt_id]

        # Update metrics
        if "latency_ms" in metrics:
            pm.total_latency_ms += metrics["latency_ms"]

        if "token_count" in metrics:
            pm.total_tokens += metrics["token_count"]

        if "accuracy" in metrics:
            pm.total_accuracy += metrics["accuracy"]
            pm.accuracy_count += 1

        logger.debug(f"Tracked performance for {prompt_id}: {metrics}")

    def get_metrics(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics

        Args:
            prompt_id: Optional prompt ID (returns all if None)

        Returns:
            Dictionary of metrics
        """
        if prompt_id:
            pm = self._metrics.get(prompt_id)
            return pm.to_dict() if pm else {}
        else:
            return {pid: pm.to_dict() for pid, pm in self._metrics.items()}

    # ========================================================================
    # VERSION MANAGEMENT
    # ========================================================================

    async def promote_version(
        self,
        prompt_type: str,
        version: str,
        rollout_pct: int
    ):
        """
        Promote a prompt version with gradual rollout

        Args:
            prompt_type: Type of prompt
            version: Version to promote (e.g., "dspy_v2")
            rollout_pct: Rollout percentage (10, 50, 100)

        Usage:
            # Initial rollout to 10%
            await manager.promote_version("intent_classification", "dspy_v2", 10)

            # After validation, increase to 50%
            await manager.promote_version("intent_classification", "dspy_v2", 50)

            # Full rollout
            await manager.promote_version("intent_classification", "dspy_v2", 100)
        """
        try:
            ptype = PromptType(prompt_type)
        except ValueError:
            raise ValueError(f"Invalid prompt type: {prompt_type}")

        if not 0 <= rollout_pct <= 100:
            raise ValueError(f"rollout_pct must be 0-100, got {rollout_pct}")

        # Get current config
        ab_config = self._ab_configs.get(ptype)
        if not ab_config:
            ab_config = ABTestConfig(
                prompt_type=ptype,
                current_version="manual_v1",
                rollout_percentage=100,
                control_version="manual_v1",
                control_percentage=0
            )
            self._ab_configs[ptype] = ab_config

        # Archive current version
        await self._archive_version(ptype, ab_config.current_version)

        # Update configuration
        old_version = ab_config.current_version
        ab_config.current_version = version
        ab_config.rollout_percentage = rollout_pct
        ab_config.control_percentage = 100 - rollout_pct
        ab_config.enabled = True

        # Save configuration
        await self._save_ab_config()

        logger.info(
            f"Promoted {prompt_type} from {old_version} to {version} "
            f"with {rollout_pct}% rollout"
        )

    async def _archive_version(self, prompt_type: PromptType, version: str):
        """Archive a prompt version to versions/ directory"""
        try:
            # Load the prompt
            prompt = await self._load_prompt(prompt_type, version)

            # Save to archive
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"{prompt_type.value}_{version}_{timestamp}.json"
            archive_path = self.versions_path / archive_filename

            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(prompt.to_dict(), f, indent=2)

            logger.info(f"Archived version to {archive_path}")
        except Exception as e:
            logger.error(f"Failed to archive version: {e}")

    async def _save_ab_config(self):
        """Save A/B test configuration to YAML"""
        config_file = self.config_path / "ab_test_config.yaml"

        config_data = {}
        for prompt_type, ab_config in self._ab_configs.items():
            config_data[prompt_type.value] = {
                "current_version": ab_config.current_version,
                "rollout_percentage": ab_config.rollout_percentage,
                "control_version": ab_config.control_version,
                "control_percentage": ab_config.control_percentage,
                "enabled": ab_config.enabled
            }

        try:
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)

            logger.info(f"Saved A/B config to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save A/B config: {e}")

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_ab_config(self, prompt_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get A/B test configuration

        Args:
            prompt_type: Optional prompt type (returns all if None)

        Returns:
            Dictionary of A/B test configurations
        """
        if prompt_type:
            try:
                ptype = PromptType(prompt_type)
                ab_config = self._ab_configs.get(ptype)
                if ab_config:
                    return {
                        "prompt_type": ab_config.prompt_type.value,
                        "current_version": ab_config.current_version,
                        "rollout_percentage": ab_config.rollout_percentage,
                        "control_version": ab_config.control_version,
                        "control_percentage": ab_config.control_percentage,
                        "enabled": ab_config.enabled
                    }
                return {}
            except ValueError:
                return {}
        else:
            return {
                pt.value: {
                    "current_version": cfg.current_version,
                    "rollout_percentage": cfg.rollout_percentage,
                    "control_version": cfg.control_version,
                    "control_percentage": cfg.control_percentage,
                    "enabled": cfg.enabled
                }
                for pt, cfg in self._ab_configs.items()
            }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Singleton instance for application-wide use
_prompt_manager_instance: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get or create global PromptManager instance"""
    global _prompt_manager_instance
    if _prompt_manager_instance is None:
        _prompt_manager_instance = PromptManager()
    return _prompt_manager_instance
