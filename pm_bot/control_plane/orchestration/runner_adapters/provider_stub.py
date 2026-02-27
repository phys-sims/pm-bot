"""Provider-style adapter used for portable contract and failure-mapping coverage."""

from __future__ import annotations

from typing import Any

from pm_bot.control_plane.orchestration.runner import RunnerPollResult, RunnerSubmitResult

_NORMALIZED_FAILURE_CODES: dict[str, str] = {
    "timeout": "provider_timeout",
    "rate_limit": "provider_rate_limited",
    "auth": "provider_auth_denied",
    "validation": "provider_invalid_request",
    "internal": "provider_unavailable",
}


def normalize_provider_failure(reason_code: str) -> str:
    """Map provider-native failure reasons to deterministic policy-safe codes."""

    normalized = _NORMALIZED_FAILURE_CODES.get(reason_code.strip().lower())
    if normalized:
        return normalized
    return "provider_failed"


class ProviderStubRunnerAdapter:
    """Deterministic provider adapter for feature-flagged runs and tests."""

    name = "provider_stub"

    def submit(self, run: dict[str, Any]) -> RunnerSubmitResult:
        return RunnerSubmitResult(job_id=f"provider:{run['run_id']}", state="running")

    def poll(self, run: dict[str, Any]) -> RunnerPollResult:
        spec = run.get("spec") or {}
        state = str(spec.get("provider_poll_state", "completed")).strip() or "completed"
        if state == "failed":
            provider_reason = str(spec.get("provider_failure_reason", "internal"))
            return RunnerPollResult(
                state="failed",
                reason_code=normalize_provider_failure(provider_reason),
            )
        return RunnerPollResult(state=state)

    def fetch_artifacts(self, run: dict[str, Any]) -> list[str]:
        return [f"provider-artifacts/{run['run_id']}.json"]

    def cancel(self, run: dict[str, Any]) -> RunnerPollResult:
        return RunnerPollResult(state="cancelled", reason_code="provider_cancelled")
