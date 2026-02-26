"""Capability identifiers for uniform LLM-backed server features."""

from __future__ import annotations

REPORT_IR_DRAFT = "report_ir_draft"
BOARD_STRATEGY_REVIEW = "board_strategy_review"
ISSUE_REPLANNER = "issue_replanner"
ISSUE_ADJUSTMENT_PROPOSAL = "issue_adjustment_proposal"

ALL_CAPABILITIES = {
    REPORT_IR_DRAFT,
    BOARD_STRATEGY_REVIEW,
    ISSUE_ADJUSTMENT_PROPOSAL,
}
