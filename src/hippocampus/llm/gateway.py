"""Business-facing wrapper around the external llmgateway package."""

from __future__ import annotations

from llmgateway import Gateway

from ..config import HippoConfig
from .adapters import runtime_spec_from_hippo_config


class LLMGateway(Gateway):
    """Stable business-facing gateway built from HippoConfig."""

    def __init__(self, config: HippoConfig):
        self.config = config
        super().__init__(runtime_spec_from_hippo_config(config))


def create_llm_gateway(config: HippoConfig) -> LLMGateway:
    return LLMGateway(config)


__all__ = ["LLMGateway", "create_llm_gateway"]
