"""Runner lifecycle + adapter contract for approval-gated agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pm_bot.server.db import OrchestratorDB


TERMINAL_STATUSES = {"completed", "failed", "cancelled", "rejected"}
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "proposed": {"approved", "rejected", "cancelled"},
    "approved": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled", "approved"},
    "failed": {"approved", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "rejected": set(),
}


@dataclass(frozen=True)
class RunnerSubmitResult:
    job_id: str
    state: str


@dataclass(frozen=True)
class RunnerPollResult:
    state: str
    reason_code: str = ""


class RunnerAdapter(Protocol):
    name: str

    def submit(self, run: dict[str, Any]) -> RunnerSubmitResult: ...

    def poll(self, run: dict[str, Any]) -> RunnerPollResult: ...

    def fetch_artifacts(self, run: dict[str, Any]) -> list[str]: ...

    def cancel(self, run: dict[str, Any]) -> RunnerPollResult: ...


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
        return [f"artifacts/{run['run_id']}.txt"]

    def cancel(self, run: dict[str, Any]) -> RunnerPollResult:
        return RunnerPollResult(state="cancelled", reason_code="cancelled_by_user")


class RunnerService:
    def __init__(
        self,
        db: OrchestratorDB,
        adapters: dict[str, RunnerAdapter] | None = None,
    ) -> None:
        self.db = db
        registered = adapters or {ManualRunnerAdapter.name: ManualRunnerAdapter()}
        self.adapters = dict(sorted(registered.items(), key=lambda kv: kv[0]))

    def _assert_transition(self, run: dict[str, Any], to_status: str) -> None:
        from_status = run["status"]
        if from_status in TERMINAL_STATUSES:
            raise ValueError("invalid_transition:terminal_state")
        allowed = ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise ValueError("invalid_transition:not_allowed")

    def create_run(self, spec: dict[str, Any], created_by: str) -> dict[str, Any]:
        run_id = str(spec.get("run_id", "")).strip()
        if not run_id:
            raise ValueError("missing_run_id")
        adapter_name = str(spec.get("adapter", ManualRunnerAdapter.name))
        if adapter_name not in self.adapters:
            raise ValueError("unknown_adapter")
        run = self.db.create_agent_run(
            run_id=run_id,
            spec=spec,
            created_by=created_by,
            adapter_name=adapter_name,
            max_retries=int(spec.get("max_retries", 2)),
        )
        self.db.append_audit_event(
            "agent_run_proposed",
            {
                "run_id": run_id,
                "status": run.get("status", "proposed"),
                "reason_code": "run_created",
                "adapter": adapter_name,
            },
        )
        return run

    def transition(
        self, run_id: str, to_status: str, reason_code: str, actor: str = ""
    ) -> dict[str, Any]:
        run = self.db.get_agent_run(run_id)
        if run is None:
            raise ValueError("unknown_run")
        self._assert_transition(run, to_status)
        self.db.update_agent_run_status(
            run_id,
            to_status,
            reason_code=reason_code,
            metadata={"actor": actor},
        )
        updated = self.db.get_agent_run(run_id) or {}
        self.db.append_audit_event(
            "agent_run_transitioned",
            {
                "run_id": run_id,
                "from_status": run["status"],
                "to_status": to_status,
                "reason_code": reason_code,
                "actor": actor,
            },
        )
        return updated

    def claim_ready_runs(
        self, worker_id: str, limit: int = 1, lease_seconds: int = 30
    ) -> list[dict[str, Any]]:
        return self.db.claim_agent_runs(
            worker_id=worker_id, limit=limit, lease_seconds=lease_seconds
        )

    def execute_claimed_run(self, run_id: str, worker_id: str) -> dict[str, Any]:
        run = self.db.get_agent_run(run_id)
        if run is None:
            raise ValueError("unknown_run")
        if run.get("claimed_by") != worker_id:
            raise ValueError("run_not_claimed_by_worker")

        adapter_name = run.get("adapter_name") or ManualRunnerAdapter.name
        adapter = self.adapters.get(adapter_name)
        if adapter is None:
            raise ValueError("unknown_adapter")

        if run["status"] == "approved":
            submit_result = adapter.submit(run)
            self.db.set_agent_run_execution(run_id, job_id=submit_result.job_id)
            run = self.transition(
                run_id, "running", reason_code="adapter_submitted", actor=worker_id
            )

        poll = adapter.poll(run)
        if poll.state == "running":
            self.db.clear_agent_run_claim(run_id)
            return self.db.get_agent_run(run_id) or {}

        if poll.state == "completed":
            artifacts = adapter.fetch_artifacts(run)
            completed = self.transition(
                run_id,
                "completed",
                reason_code="adapter_completed",
                actor=worker_id,
            )
            self.db.append_audit_event(
                "agent_run_artifacts",
                {"run_id": run_id, "artifacts": artifacts, "worker_id": worker_id},
            )
            self.db.clear_agent_run_claim(run_id)
            return completed

        retry_count = int(run.get("retry_count", 0)) + 1
        max_retries = int(run.get("max_retries", 0))
        self.db.set_agent_run_execution(
            run_id,
            retry_count=retry_count,
            next_attempt_seconds=min(60, 5 * retry_count),
            last_error=poll.reason_code or "adapter_failed",
        )
        if retry_count > max_retries:
            failed = self.transition(
                run_id,
                "failed",
                reason_code="retry_budget_exhausted",
                actor=worker_id,
            )
            self.db.append_audit_event(
                "agent_run_dead_lettered",
                {
                    "run_id": run_id,
                    "worker_id": worker_id,
                    "retry_count": retry_count,
                    "reason_code": "retry_budget_exhausted",
                },
            )
            self.db.clear_agent_run_claim(run_id)
            return failed

        reapproved = self.transition(
            run_id,
            "approved",
            reason_code="retry_scheduled",
            actor=worker_id,
        )
        self.db.clear_agent_run_claim(run_id)
        return reapproved

    def cancel(self, run_id: str, actor: str = "") -> dict[str, Any]:
        run = self.db.get_agent_run(run_id)
        if run is None:
            raise ValueError("unknown_run")
        if run["status"] in TERMINAL_STATUSES:
            raise ValueError("invalid_transition:terminal_state")
        adapter_name = run.get("adapter_name") or ManualRunnerAdapter.name
        adapter = self.adapters.get(adapter_name)
        if adapter is None:
            raise ValueError("unknown_adapter")
        result = adapter.cancel(run)
        return self.transition(
            run_id, "cancelled", reason_code=result.reason_code or "cancelled", actor=actor
        )
