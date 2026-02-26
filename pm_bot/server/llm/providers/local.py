"""Deterministic local provider adapter used as safe default."""

from __future__ import annotations

import json
from typing import Any

from pm_bot.server.llm.capabilities import (
    ISSUE_ADJUSTMENT_PROPOSAL,
    ISSUE_REPLANNER,
    REPORT_IR_DRAFT,
)
from pm_bot.server.llm.providers.base import LLMProvider, LLMRequest, LLMResponse
from pm_bot.server.report_ir_intake import draft_report_ir_from_natural_text


class LocalLLMProvider(LLMProvider):
    """Routes known capabilities to deterministic local implementations."""

    name = "local"

    def run(self, request: LLMRequest) -> LLMResponse:
        if request.capability_id == REPORT_IR_DRAFT:
            output = self._run_report_ir_draft(request)
        elif request.capability_id in {ISSUE_ADJUSTMENT_PROPOSAL, ISSUE_REPLANNER}:
            output = self._run_issue_adjustment_proposal(request)
        else:
            raise ValueError(f"unsupported_local_capability:{request.capability_id}")
        return LLMResponse(
            output=output,
            model="deterministic-rule-engine",
            provider=self.name,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            raw_text=json.dumps(output, sort_keys=True),
        )

    def _run_report_ir_draft(self, request: LLMRequest) -> dict[str, Any]:
        natural_text = str(request.input_payload.get("natural_text", "")).strip()
        org = str(request.input_payload.get("org", "")).strip()
        repos = [
            str(repo).strip()
            for repo in request.input_payload.get("repos", [])
            if str(repo).strip()
        ]
        generated_at = str(request.input_payload.get("generated_at", "")).strip()
        mode = str(request.input_payload.get("mode", "basic")).strip() or "basic"

        draft = draft_report_ir_from_natural_text(
            natural_text=natural_text,
            org=org,
            repos=repos,
            generated_at=generated_at,
            mode=mode,
        )
        return {"draft": draft}

    def _run_issue_adjustment_proposal(self, request: LLMRequest) -> dict[str, Any]:
        repo = str(request.input_payload.get("repo", "")).strip()
        diff = request.input_payload.get("diff", {})
        status_changes = diff.get("status_changes", []) if isinstance(diff, dict) else []
        blocker_changes = diff.get("blocker_changes", []) if isinstance(diff, dict) else []

        changesets: list[dict[str, Any]] = []
        for row in [*status_changes, *blocker_changes]:
            if not isinstance(row, dict):
                continue
            issue_ref = str(row.get("issue_ref", "")).strip()
            if not issue_ref:
                continue
            idempotency_key = (
                f"issue-replanner:{repo}:{issue_ref}:"
                f"{str(request.input_payload.get('current_snapshot_id', ''))}"
            )
            changesets.append(
                {
                    "operation": "update_issue",
                    "repo": repo,
                    "target_ref": issue_ref,
                    "idempotency_key": idempotency_key,
                    "payload": {
                        "proposal_reason": "board_drift_replanner",
                        "suggested_action": "review_scope_and_dependencies",
                    },
                }
            )

        return {
            "schema_version": "changeset_bundle_proposal/v1",
            "bundle": {
                "bundle_id": f"issue-replanner-{request.input_payload.get('current_snapshot_id', '0')}",
                "requires_human_approval": True,
                "changesets": changesets,
            },
        }
