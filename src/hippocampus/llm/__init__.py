"""Hippo-facing LLM entrypoints.

Generic runtime primitives live in the external ``llmgateway`` package.
"""

from .adapters import runtime_spec_from_hippo_config
from .gateway import LLMGateway, create_llm_gateway

__all__ = [
    "LLMGateway",
    "create_llm_gateway",
    "runtime_spec_from_hippo_config",
]
