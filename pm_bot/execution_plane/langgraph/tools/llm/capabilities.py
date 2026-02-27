"""Capability identifiers for uniform LLM-backed server features."""

from __future__ import annotations

REPORT_IR_DRAFT = "report_ir_draft"
BOARD_STRATEGY_REVIEW = "board_strategy_review"
ISSUE_REPLANNER = "issue_replanner"
ISSUE_ADJUSTMENT_PROPOSAL = "issue_adjustment_proposal"

READ_ONLY_ADVICE = "read_only_advice"
MUTATION_PROPOSAL = "mutation_proposal"

ALL_CAPABILITIES = {
    REPORT_IR_DRAFT,
    BOARD_STRATEGY_REVIEW,
    ISSUE_REPLANNER,
    ISSUE_ADJUSTMENT_PROPOSAL,
}

CAPABILITY_CLASSES = {
    REPORT_IR_DRAFT: READ_ONLY_ADVICE,
    BOARD_STRATEGY_REVIEW: READ_ONLY_ADVICE,
    ISSUE_REPLANNER: MUTATION_PROPOSAL,
    ISSUE_ADJUSTMENT_PROPOSAL: MUTATION_PROPOSAL,
}


def capability_class(capability_id: str) -> str:
    return CAPABILITY_CLASSES.get(capability_id, READ_ONLY_ADVICE)
