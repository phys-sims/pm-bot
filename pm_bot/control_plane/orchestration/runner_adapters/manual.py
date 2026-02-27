"""Manual runner adapter baseline implementation."""

from __future__ import annotations

from typing import Any

from pm_bot.control_plane.orchestration.runner import RunnerPollResult, RunnerSubmitResult
from pm_bot.shared.settings import default_artifact_uri


class ManualRunnerAdapter:
    """Local deterministic adapter used as the baseline runner implementation."""

    name = "manual"

    def submit(self, run: dict[str, Any]) -> RunnerSubmitResult:
        return RunnerSubmitResult(job_id=f"manual:{run['run_id']}", state="running")

    def poll(self, run: dict[str, Any]) -> RunnerPollResult:
        state = str((run.get("spec") or {}).get("manual_poll_state", "completed"))
        if state == "failed":
            return RunnerPollResult(state="failed", reason_code="manual_failed")
        return RunnerPollResult(state=state)

    def fetch_artifacts(self, run: dict[str, Any]) -> list[str]:
        explicit = (run.get("spec") or {}).get("artifact_paths")
        if isinstance(explicit, list):
            return [str(path) for path in explicit]
        return [default_artifact_uri(run["run_id"], suffix=".txt")]

    def cancel(self, run: dict[str, Any]) -> RunnerPollResult:
        return RunnerPollResult(state="cancelled", reason_code="cancelled_by_user")
