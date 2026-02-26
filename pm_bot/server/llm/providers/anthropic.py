"""Anthropic provider adapter placeholder using normalized contracts."""

from __future__ import annotations

from pm_bot.server.llm.providers.base import LLMProvider, LLMRequest, LLMResponse


class AnthropicProvider(LLMProvider):
    """Stub provider that can be wired to Anthropic SDK later."""

    name = "anthropic"

    def run(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("anthropic_provider_not_configured")
