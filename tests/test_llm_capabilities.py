from __future__ import annotations

import pytest

from pm_bot.server.llm.capabilities import REPORT_IR_DRAFT
from pm_bot.server.llm.service import run_capability


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
        context={"provider": "local"},
        policy={"allow_external_llm": False},
    )

    assert result["capability_id"] == REPORT_IR_DRAFT
    assert result["provider"] == "local"
    assert result["output"]["draft"]["schema_version"] == "report_ir/v1"


def test_run_capability_enforces_required_guardrails() -> None:
    with pytest.raises(ValueError, match="capability_guardrail_failed:report_ir_draft:missing_org"):
        run_capability(
            REPORT_IR_DRAFT,
            input_payload={"natural_text": "- something", "org": "", "repos": []},
            context={"provider": "local"},
            policy={},
        )
