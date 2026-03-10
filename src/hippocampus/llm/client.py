"""HippoLLM — async backend client without LiteLLM."""

from __future__ import annotations

import asyncio

from ..config import HippoConfig
from .runtime import (
    llm_provider,
    normalize_model_name,
    prefers_anthropic_messages,
    prefers_openai_chat,
    prefers_openai_responses,
    resolve_temperature,
)
from .transport import (
    anthropic_messages_completion,
    openai_chat_completion,
    openai_responses_completion,
)


class HippoLLM:
    """Async LLM client with retry and concurrency control."""

    def __init__(self, config: HippoConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.llm.max_concurrent)

    def _get_model(self, phase: str) -> str:
        models = self.config.llm.phase_models
        return getattr(models, phase, self.config.llm.fallback_model)

    def _get_temperature(self, phase: str) -> float:
        temps = self.config.llm.temperature
        return getattr(temps, phase, 0.0)

    async def _complete_once(
        self,
        *,
        provider: dict[str, object],
        model: str,
        messages: list[dict[str, str]],
        timeout: float,
        temperature: float,
    ) -> str:
        if prefers_openai_responses(provider):
            return await openai_responses_completion(
                provider=provider,
                model=model,
                messages=messages,
                max_tokens=4000,
                timeout=timeout,
                temperature=temperature,
            )
        if prefers_openai_chat(provider):
            return await openai_chat_completion(
                provider=provider,
                model=model,
                messages=messages,
                max_tokens=4000,
                timeout=timeout,
                temperature=temperature,
            )
        if prefers_anthropic_messages(provider, model):
            return await anthropic_messages_completion(
                provider=provider,
                model=model,
                messages=messages,
                max_tokens=4000,
                timeout=timeout,
                temperature=temperature,
            )
        return await openai_responses_completion(
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=4000,
            timeout=timeout,
            temperature=temperature,
        )

    async def call(self, phase: str, messages: list[dict[str, str]]) -> str:
        model = self._get_model(phase)
        provider = llm_provider(self.config)
        normalized_model = normalize_model_name(provider, model)
        temperature = resolve_temperature(normalized_model, self._get_temperature(phase))

        async with self._semaphore:
            for attempt in range(5):
                try:
                    return await self._complete_once(
                        provider=provider,
                        model=normalized_model,
                        messages=messages,
                        timeout=float(self.config.llm.timeout),
                        temperature=temperature,
                    )
                except Exception:
                    if attempt == 4:
                        raise
                    await asyncio.sleep(2 ** attempt + 1)
        return ""

    async def call_with_retry(
        self,
        phase: str,
        messages: list[dict[str, str]],
        validator=None,
    ) -> tuple[str, list[str]]:
        max_retries = self.config.llm.retry_max
        errors: list[str] = []

        for attempt in range(max_retries + 1):
            text = await self.call(phase, messages)
            if validator is None:
                return text, []

            errors = validator(text)
            if not errors:
                return text, []

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
