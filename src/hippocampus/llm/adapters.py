from __future__ import annotations

from llmgateway import ProviderSpec, RuntimeSpec, TaskSpec

from ..config import HippoConfig


def runtime_spec_from_hippo_config(config: HippoConfig) -> RuntimeSpec:
    llm = config.llm
    temperatures = config.llm.temperature.model_dump()
    phase_models = config.llm.phase_models.model_dump()
    phase_reasoning_effort = config.llm.phase_reasoning_effort.model_dump()

    tasks = {
        task_name: TaskSpec(
            model=str(model or "").strip(),
            temperature=float(temperatures.get(task_name, 0.0)),
            reasoning_effort=str(phase_reasoning_effort.get(task_name, "") or "").strip().lower(),
        )
        for task_name, model in phase_models.items()
    }

    return RuntimeSpec(
        provider=ProviderSpec(
            provider_type=str(getattr(llm, "provider_type", "") or "").strip(),
            api_style=str(getattr(llm, "api_style", "") or "").strip(),
            base_url=str(llm.base_url or llm.api_base or "").strip(),
            api_key=str(llm.api_key or "").strip(),
            headers=dict(llm.extra_headers or {}),
            model_map=dict(getattr(llm, "model_map", {}) or {}),
        ),
        fallback_model=str(config.llm.fallback_model or "").strip(),
        max_concurrent=max(1, int(config.llm.max_concurrent)),
        retry_max=max(0, int(config.llm.retry_max)),
        timeout=float(config.llm.timeout),
        tasks=tasks,
    )


__all__ = ["runtime_spec_from_hippo_config"]
