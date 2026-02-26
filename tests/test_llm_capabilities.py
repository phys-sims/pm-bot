from __future__ import annotations

import pytest

from pm_bot.server.llm.capabilities import (
    BOARD_STRATEGY_REVIEW,
    ISSUE_ADJUSTMENT_PROPOSAL,
    ISSUE_REPLANNER,
    REPORT_IR_DRAFT,
)
from pm_bot.server.llm.providers.base import LLMRequest, LLMResponse
from pm_bot.server.llm.service import CapabilityOutputValidationError, run_capability


def test_run_capability_report_ir_draft_with_local_provider() -> None:
    result = run_capability(
        REPORT_IR_DRAFT,
        input_payload={
            "natural_text": "- Build queue hardening flow",
            "org": "phys-sims",
            "repos": ["phys-sims/pm-bot"],
            "generated_at": "2026-02-26",
            "mode": "basic",
        },
        context={"provider": "local", "run_id": "run-cap-1"},
        policy={"allow_external_llm": False},
    )

    assert result["capability_id"] == REPORT_IR_DRAFT
    assert result["provider"] == "local"
    assert result["prompt_version"] == "v1"
    assert result["schema_version"] == "report_ir_draft/v1"
    assert result["input_hash"]
    assert result["run_id"] == "run-cap-1"
    assert result["output"]["draft"]["schema_version"] == "report_ir/v1"


def test_run_capability_enforces_required_guardrails() -> None:
    with pytest.raises(ValueError, match="capability_guardrail_failed:report_ir_draft:missing_org"):
        run_capability(
            REPORT_IR_DRAFT,
            input_payload={"natural_text": "- something", "org": "", "repos": []},
            context={"provider": "local"},
            policy={},
        )


class _InvalidJSONProvider:
    name = "invalid-json"

    def run(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            output={},
            model="fake",
            provider=self.name,
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            raw_text="not-json",
        )


class _SchemaViolationProvider:
    name = "schema-violation"

    def run(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            output={},
            model="fake",
            provider=self.name,
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            raw_text='{"draft": {"schema_version": "wrong"}}',
        )


def test_run_capability_rejects_non_json_model_output() -> None:
    with pytest.raises(CapabilityOutputValidationError) as exc_info:
        run_capability(
            REPORT_IR_DRAFT,
            input_payload={"natural_text": "- item", "org": "phys-sims", "repos": []},
            context={"provider": "invalid-json"},
            policy={},
            providers={"invalid-json": _InvalidJSONProvider()},
        )

    error = exc_info.value.as_dict()
    assert error["validation"]["errors"][0]["code"] == "JSON_PARSE"


def test_run_capability_rejects_schema_non_conforming_output() -> None:
    with pytest.raises(CapabilityOutputValidationError) as exc_info:
        run_capability(
            REPORT_IR_DRAFT,
            input_payload={"natural_text": "- item", "org": "phys-sims", "repos": []},
            context={"provider": "schema-violation"},
            policy={},
            providers={"schema-violation": _SchemaViolationProvider()},
        )

    error_codes = [row["code"] for row in exc_info.value.as_dict()["validation"]["errors"]]
    assert "SCHEMA_ENUM" in error_codes


class _ReadOnlyAdviceProvider:
    name = "read-only-advice"

    def run(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            output={},
            model="fake",
            provider=self.name,
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            raw_text=(
                '{"summary":"s","recommendations":[{"id":"r1","title":"t","priority":"P1"}]}'
            ),
        )


class _MutationProposalProvider:
    name = "mutation-proposal"

    def run(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            output={},
            model="fake",
            provider=self.name,
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            raw_text=(
                '{"schema_version":"changeset_bundle_proposal/v1","bundle":{'
                '"bundle_id":"bundle-1","requires_human_approval":true,'
                '"changesets":[{"operation":"update_issue","repo":"phys-sims/pm-bot",'
                '"target_ref":"#1","idempotency_key":"k1","payload":{"body":"x"}}]}}'
            ),
        )


def test_read_only_capability_allows_low_approval_policy() -> None:
    result = run_capability(
        BOARD_STRATEGY_REVIEW,
        input_payload={"board_snapshot": []},
        context={"provider": "read-only-advice"},
        policy={"approval_level": "low"},
        providers={"read-only-advice": _ReadOnlyAdviceProvider()},
    )

    assert result["capability_class"] == "read_only_advice"
    assert result["policy_enforcement"]["approval_level"] == "low"


def test_mutation_capability_denies_without_changeset_bundle_policy_flag() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "capability_policy_denied:issue_adjustment_proposal:changeset_bundle_proposal_required"
        ),
    ):
        run_capability(
            ISSUE_ADJUSTMENT_PROPOSAL,
            input_payload={"issue_ref": "#1"},
            context={"provider": "mutation-proposal"},
            policy={"require_human_approval": True},
            providers={"mutation-proposal": _MutationProposalProvider()},
        )


def test_mutation_capability_denies_when_human_approval_is_disabled() -> None:
    with pytest.raises(
        ValueError,
        match="capability_policy_denied:issue_adjustment_proposal:human_approval_required",
    ):
        run_capability(
            ISSUE_ADJUSTMENT_PROPOSAL,
            input_payload={"issue_ref": "#1"},
            context={"provider": "mutation-proposal"},
            policy={
                "proposal_output_changeset_bundle": True,
                "require_human_approval": False,
            },
            providers={"mutation-proposal": _MutationProposalProvider()},
        )


def test_capability_policy_denies_direct_github_write_bypass_attempt() -> None:
    with pytest.raises(
        ValueError,
        match="capability_policy_denied:board_strategy_review:direct_github_writes_forbidden",
    ):
        run_capability(
            BOARD_STRATEGY_REVIEW,
            input_payload={"board_snapshot": []},
            context={"provider": "read-only-advice"},
            policy={"allow_direct_github_writes": True},
            providers={"read-only-advice": _ReadOnlyAdviceProvider()},
        )


def test_mutation_capability_accepts_changeset_bundle_contract_when_policy_allows() -> None:
    result = run_capability(
        ISSUE_ADJUSTMENT_PROPOSAL,
        input_payload={"issue_ref": "#1"},
        context={"provider": "mutation-proposal"},
        policy={
            "proposal_output_changeset_bundle": True,
            "require_human_approval": True,
        },
        providers={"mutation-proposal": _MutationProposalProvider()},
    )

    assert result["capability_class"] == "mutation_proposal"
    assert result["policy_enforcement"]["requires_human_approval"] is True
    assert result["output"]["schema_version"] == "changeset_bundle_proposal/v1"


def test_issue_replanner_requires_mutation_policy_gates() -> None:
    with pytest.raises(
        ValueError,
        match="capability_policy_denied:issue_replanner:changeset_bundle_proposal_required",
    ):
        run_capability(
            ISSUE_REPLANNER,
            input_payload={"repo": "phys-sims/pm-bot", "diff": {}},
            context={"provider": "mutation-proposal"},
            policy={"require_human_approval": True},
            providers={"mutation-proposal": _MutationProposalProvider()},
        )
