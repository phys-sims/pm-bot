"""Provider interface and normalized request/response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class LLMRequest:
    """Normalized provider request independent of vendor-specific SDKs."""

    capability_id: str
    prompt: str
    input_payload: dict[str, Any]
    context: dict[str, Any]
    policy: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    """Normalized provider response with structured output for downstream use."""

    output: dict[str, Any]
    model: str
    provider: str
    usage: dict[str, int]
    raw_text: str = ""


class LLMProvider(Protocol):
    """Provider adapter protocol for OpenAI/Anthropic/local implementations."""

    name: str

    def run(self, request: LLMRequest) -> LLMResponse:
        """Execute a normalized request and return normalized output."""
