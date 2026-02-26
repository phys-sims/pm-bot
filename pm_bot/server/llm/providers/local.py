"""Deterministic local provider adapter used as safe default."""

from __future__ import annotations

import json
from typing import Any

from pm_bot.server.llm.capabilities import REPORT_IR_DRAFT
from pm_bot.server.llm.providers.base import LLMProvider, LLMRequest, LLMResponse
from pm_bot.server.report_ir_intake import draft_report_ir_from_natural_text


class LocalLLMProvider(LLMProvider):
    """Routes known capabilities to deterministic local implementations."""

    name = "local"

    def run(self, request: LLMRequest) -> LLMResponse:
        if request.capability_id != REPORT_IR_DRAFT:
            raise ValueError(f"unsupported_local_capability:{request.capability_id}")

        output = self._run_report_ir_draft(request)
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
