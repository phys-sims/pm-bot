"""Unified capability runner for LLM-backed and deterministic server features."""

from __future__ import annotations

from typing import Any

from pm_bot.server.llm.providers import LLMProvider, LLMRequest, LocalLLMProvider
from pm_bot.server.llm.registry import get_capability_definition


def _select_provider(context: dict[str, Any], providers: dict[str, LLMProvider]) -> LLMProvider:
    provider_name = str(context.get("provider", "local")).strip() or "local"
    provider = providers.get(provider_name)
    if provider is None:
        raise ValueError(f"unknown_provider:{provider_name}")
    return provider


def _enforce_guardrails(
    *, capability_id: str, input_payload: dict[str, Any], guardrails: dict[str, Any]
) -> None:
    if (
        guardrails.get("require_natural_text")
        and not str(input_payload.get("natural_text", "")).strip()
    ):
        raise ValueError(f"capability_guardrail_failed:{capability_id}:missing_natural_text")
    if guardrails.get("require_org") and not str(input_payload.get("org", "")).strip():
        raise ValueError(f"capability_guardrail_failed:{capability_id}:missing_org")


def run_capability(
    capability_id: str,
    input_payload: dict[str, Any],
    context: dict[str, Any],
    policy: dict[str, Any],
    providers: dict[str, LLMProvider] | None = None,
) -> dict[str, Any]:
    """Execute a named capability through a normalized provider interface."""

    provider_map = providers or {"local": LocalLLMProvider()}
    definition = get_capability_definition(capability_id)
    _enforce_guardrails(
        capability_id=capability_id,
        input_payload=input_payload,
        guardrails=definition.guardrails,
    )

    provider = _select_provider(context, provider_map)
    request = LLMRequest(
        capability_id=capability_id,
        prompt=definition.prompt_template,
        input_payload=input_payload,
        context=context,
        policy=policy,
    )
    response = provider.run(request)
    return {
        "capability_id": capability_id,
        "provider": response.provider,
        "model": response.model,
        "usage": response.usage,
        "output": response.output,
        "guardrails": definition.guardrails,
        "output_schema": definition.output_schema,
    }
