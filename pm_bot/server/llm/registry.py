"""Capability registry mapping IDs to prompt templates, schemas, and guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pm_bot.server.llm.capabilities import BOARD_STRATEGY_REVIEW, ISSUE_REPLANNER, REPORT_IR_DRAFT


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    prompt_template: str
    output_schema: dict[str, Any]
    guardrails: dict[str, Any]


CAPABILITY_REGISTRY: dict[str, CapabilityDefinition] = {
    REPORT_IR_DRAFT: CapabilityDefinition(
        capability_id=REPORT_IR_DRAFT,
        prompt_template=(
            "Convert intake text into report_ir/v1 JSON with deterministic stable IDs and "
            "triage defaults for missing fields."
        ),
        output_schema={
            "type": "object",
            "required": ["draft"],
            "properties": {"draft": {"type": "object"}},
            "additionalProperties": True,
        },
        guardrails={
            "require_org": True,
            "require_natural_text": True,
            "disallow_repo_outside_scope": True,
        },
    ),
    BOARD_STRATEGY_REVIEW: CapabilityDefinition(
        capability_id=BOARD_STRATEGY_REVIEW,
        prompt_template="Review board strategy and return prioritized recommendations.",
        output_schema={"type": "object"},
        guardrails={"read_only": True},
    ),
    ISSUE_REPLANNER: CapabilityDefinition(
        capability_id=ISSUE_REPLANNER,
        prompt_template="Suggest deterministic issue replanning adjustments.",
        output_schema={"type": "object"},
        guardrails={"read_only": True},
    ),
}


def get_capability_definition(capability_id: str) -> CapabilityDefinition:
    capability = CAPABILITY_REGISTRY.get(capability_id)
    if capability is None:
        raise ValueError(f"unknown_capability:{capability_id}")
    return capability
