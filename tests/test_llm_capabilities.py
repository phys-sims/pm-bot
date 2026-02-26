from __future__ import annotations

import pytest

from pm_bot.server.llm.capabilities import REPORT_IR_DRAFT
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
