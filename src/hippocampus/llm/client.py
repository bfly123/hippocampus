"""HippoLLM — async LLM client with retry and concurrency control."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from ..config import HippoConfig


class HippoLLM:
    """Async LLM client with retry and concurrency control."""

    def __init__(self, config: HippoConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(
            config.llm.max_concurrent
        )

    def _get_model(self, phase: str) -> str:
        """Get model name for a given phase."""
        models = self.config.llm.phase_models
        return getattr(models, phase, self.config.llm.fallback_model)

    def _get_temperature(self, phase: str) -> float:
        """Get temperature for a given phase."""
        temps = self.config.llm.temperature
        return getattr(temps, phase, 0.0)

    def _infer_provider(self, model: str) -> str | None:
        """Infer LiteLLM provider for non-prefixed model ids."""
        if "/" in model:
            return None
        configured = (self.config.llm.litellm_provider or "").strip()
        if configured:
            return configured
        # For anthropic-compatible gateways, provider can be inferred from base URL.
        base_url = (
            (self.config.llm.base_url or "")
            or (self.config.llm.api_base or "")
        ).strip().lower()
        if "/anthropic" in base_url:
            return "anthropic"
        lower = model.lower()
        if lower.startswith("claude"):
            return "anthropic"
        if lower.startswith("glm"):
            # GLM is routed via anthropic-compatible endpoints in llm-proxy.
            return "anthropic"
        if lower.startswith(("gpt", "o1", "o3", "o4")):
            return "openai"
        return None

    async def call(
        self,
        phase: str,
        messages: list[dict[str, str]],
    ) -> str:
        """Make a single LLM call with concurrency control and rate limit retry."""
        import litellm

        model = self._get_model(phase)
        temperature = self._get_temperature(phase)
        model_l = model.lower()

        async with self._semaphore:
            kwargs = dict(
                model=model,
                messages=messages,
                timeout=self.config.llm.timeout,
            )
            # OpenAI GPT-5 family only supports temperature=1; omit custom
            # temperature to let backend defaults apply.
            if not model_l.startswith("gpt-5"):
                kwargs["temperature"] = temperature
            provider = self._infer_provider(model)
            if provider:
                kwargs["custom_llm_provider"] = provider
            if self.config.llm.base_url:
                kwargs["base_url"] = self.config.llm.base_url
            elif self.config.llm.api_base:
                # Backward compatibility for old config key.
                kwargs["api_base"] = self.config.llm.api_base
            if self.config.llm.api_key:
                kwargs["api_key"] = self.config.llm.api_key
            if self.config.llm.extra_headers:
                kwargs["extra_headers"] = self.config.llm.extra_headers

            for attempt in range(5):
                try:
                    response = await litellm.acompletion(**kwargs)
                    return response.choices[0].message.content or ""
                except (
                    litellm.exceptions.RateLimitError,
                    litellm.exceptions.InternalServerError,
                    litellm.exceptions.APIConnectionError,
                    litellm.exceptions.Timeout,
                    litellm.Timeout,
                ):
                    wait = 2 ** attempt + 1
                    await asyncio.sleep(wait)
            # Final attempt, let exception propagate
            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content or ""

    async def call_with_retry(
        self,
        phase: str,
        messages: list[dict[str, str]],
        validator=None,
    ) -> tuple[str, list[str]]:
        """Call LLM with validation and retry logic.

        Returns (response_text, validation_errors).
        Empty errors list means success.
        """
        max_retries = self.config.llm.retry_max
        errors: list[str] = []

        for attempt in range(max_retries + 1):
            text = await self.call(phase, messages)

            if validator is None:
                return text, []

            errors = validator(text)
            if not errors:
                return text, []

            # Build retry message
            retry_msg = (
                "你上次的输出存在以下问题：\n"
                + "\n".join(f"- {e}" for e in errors)
                + "\n\n请修正后重新输出完整 JSON。仅输出 JSON，不要解释。"
            )
            if attempt < max_retries:
                messages = messages + [
                    {"role": "assistant", "content": text},
                    {"role": "user", "content": retry_msg},
                ]

        return text, errors
