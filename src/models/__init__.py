"""
TRIA AI-BPO DataFlow Models

This module contains all DataFlow model definitions.
Each model automatically generates 9 CRUD nodes.
"""

from .dataflow_models import initialize_dataflow_models

__all__ = ["initialize_dataflow_models"]
