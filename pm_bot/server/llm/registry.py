"""Capability registry mapping IDs to prompt templates, schemas, and guardrails."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pm_bot.server.llm.capabilities import (
    BOARD_STRATEGY_REVIEW,
    ISSUE_ADJUSTMENT_PROPOSAL,
    REPORT_IR_DRAFT,
)


_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema" / "llm"


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    prompt_template: str
    output_schema: dict[str, Any]
    guardrails: dict[str, Any]


def _load_schema(filename: str) -> dict[str, Any]:
    return json.loads((_SCHEMA_DIR / filename).read_text())


CAPABILITY_REGISTRY: dict[str, CapabilityDefinition] = {
    REPORT_IR_DRAFT: CapabilityDefinition(
        capability_id=REPORT_IR_DRAFT,
        prompt_template=(
            "Convert intake text into report_ir/v1 JSON with deterministic stable IDs and "
            "triage defaults for missing fields. Return JSON object only."
        ),
        output_schema=_load_schema("report_ir_draft.schema.json"),
        guardrails={
            "require_org": True,
            "require_natural_text": True,
            "disallow_repo_outside_scope": True,
        },
    ),
    BOARD_STRATEGY_REVIEW: CapabilityDefinition(
        capability_id=BOARD_STRATEGY_REVIEW,
        prompt_template=(
            "Review board strategy and return prioritized recommendations as JSON only."
        ),
        output_schema=_load_schema("board_strategy_review.schema.json"),
        guardrails={"read_only": True},
    ),
    ISSUE_ADJUSTMENT_PROPOSAL: CapabilityDefinition(
        capability_id=ISSUE_ADJUSTMENT_PROPOSAL,
        prompt_template=(
            "Propose issue adjustments with deterministic fields and return JSON object only."
        ),
        output_schema=_load_schema("issue_adjustment_proposal.schema.json"),
        guardrails={"read_only": True},
    ),
}


def get_capability_definition(capability_id: str) -> CapabilityDefinition:
    capability = CAPABILITY_REGISTRY.get(capability_id)
    if capability is None:
        raise ValueError(f"unknown_capability:{capability_id}")
    return capability
