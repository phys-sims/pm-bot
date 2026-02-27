"""OpenAI provider adapter placeholder using normalized contracts."""

from __future__ import annotations

from pm_bot.execution_plane.langgraph.tools.llm.providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
)


class OpenAIProvider(LLMProvider):
    """Stub provider that can be wired to OpenAI SDK later."""

    name = "openai"

    def run(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("openai_provider_not_configured")
