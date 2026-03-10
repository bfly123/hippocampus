from __future__ import annotations

from typing import Any


def build_openai_chat_url(provider: dict[str, Any]) -> str:
    base_url = str(provider.get("base_url", "") or "").strip().rstrip("/")
    if not base_url:
        return ""
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def build_openai_responses_url(provider: dict[str, Any]) -> str:
    base_url = str(provider.get("base_url", "") or "").strip().rstrip("/")
    if not base_url:
        return ""
    if base_url.endswith("/responses"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/responses"
    return f"{base_url}/v1/responses"


def build_openai_headers(provider: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"content-type": "application/json"}
    api_key = str(provider.get("api_key", "") or "").strip()
    if api_key:
        headers["authorization"] = f"Bearer {api_key}"
    raw_headers = provider.get("headers", {}) or {}
    if isinstance(raw_headers, dict):
        for key, value in raw_headers.items():
            if isinstance(key, str) and isinstance(value, str) and key.strip():
                headers[key] = value
    return headers


def build_anthropic_headers(provider: dict[str, Any]) -> dict[str, str]:
    headers = build_openai_headers(provider)
    api_key = str(provider.get("api_key", "") or "").strip()
    lowered = {key.lower() for key in headers}
    if api_key and "x-api-key" not in lowered:
        headers["x-api-key"] = api_key
    if "anthropic-version" not in lowered:
        headers["anthropic-version"] = "2023-06-01"
    return headers


def build_openai_responses_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    instructions_parts: list[str] = []
    input_items: list[dict[str, Any]] = []
    for msg in messages:
        role = str(msg.get("role", "user") or "user").strip().lower()
        content = str(msg.get("content", "") or "")
        if role == "system":
            if content:
                instructions_parts.append(content)
            continue
        normalized = role if role in {"user", "assistant", "developer"} else "user"
        input_items.append(
            {
                "role": normalized,
                "content": [{"type": "input_text", "text": content}],
            }
        )
    payload: dict[str, Any] = {
        "model": model,
        "input": input_items or [{"role": "user", "content": [{"type": "input_text", "text": ""}]}],
        "max_output_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    instructions = "\n\n".join(x for x in instructions_parts if x.strip()).strip()
    if instructions:
        payload["instructions"] = instructions
    return payload


def build_anthropic_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    system_parts: list[str] = []
    convo: list[dict[str, str]] = []
    for msg in messages:
        role = str(msg.get("role", "user") or "user")
        content = str(msg.get("content", "") or "")
        if role == "system":
            system_parts.append(content)
            continue
        convo.append({"role": role, "content": content})
    payload: dict[str, Any] = {
        "model": model,
        "messages": convo or [{"role": "user", "content": ""}],
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    system_text = "\n".join(system_parts).strip()
    if system_text:
        payload["system"] = system_text
    return payload


__all__ = [
    "build_anthropic_headers",
    "build_anthropic_payload",
    "build_openai_chat_url",
    "build_openai_headers",
    "build_openai_responses_payload",
    "build_openai_responses_url",
]
