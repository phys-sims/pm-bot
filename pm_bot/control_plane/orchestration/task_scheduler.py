"""TaskRun scheduler loop with quotas, leases, and deterministic retries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pm_bot.control_plane.db.db import OrchestratorDB
from pm_bot.control_plane.orchestration.runner import RunnerService


@dataclass(frozen=True)
class SchedulerQuotas:
    max_parallel_per_repo: int = 2
    max_parallel_per_tool: int = 4
    max_parallel_per_provider: int = 4


class TaskScheduler:
    def __init__(
        self,
        *,
        db: OrchestratorDB,
        runner: RunnerService,
        worker_id: str,
        quotas: SchedulerQuotas | None = None,
        lease_seconds: int = 30,
        max_task_retries: int = 2,
    ) -> None:
        self.db = db
        self.runner = runner
        self.worker_id = worker_id
        self.quotas = quotas or SchedulerQuotas()
        self.lease_seconds = max(1, int(lease_seconds))
        self.max_task_retries = max(0, int(max_task_retries))

    def run_once(self) -> dict[str, int]:
        claimed = 0
        dispatched = 0
        reserved = {"repo": {}, "tool": {}, "provider": {}}
        for task_run in self._runnable_candidates():
            if not self._within_quotas(task_run, reserved=reserved):
                continue
            if not self.db.claim_task_run(
                task_run["task_run_id"], self.worker_id, self.lease_seconds
            ):
                continue
            claimed += 1
            self.db.append_audit_event(
                "task_run_claimed",
                {
                    "task_run_id": task_run["task_run_id"],
                    "plan_id": task_run["plan_id"],
                    "worker_id": self.worker_id,
                },
            )
            metadata = self._task_metadata(task_run)
            reserved["repo"][metadata["repo"]] = reserved["repo"].get(metadata["repo"], 0) + 1
            reserved["tool"][metadata["tool"]] = reserved["tool"].get(metadata["tool"], 0) + 1
            reserved["provider"][metadata["provider"]] = (
                reserved["provider"].get(metadata["provider"], 0) + 1
            )
            self._dispatch_task(task_run_id=task_run["task_run_id"])
            dispatched += 1
        return {"claimed": claimed, "dispatched": dispatched}

    def _runnable_candidates(self) -> list[dict[str, Any]]:
        rows = self.db.conn.execute(
            """
            SELECT task_run_id, plan_id, task_id, status, deps_json, retries,
                   COALESCE(next_attempt_at, CURRENT_TIMESTAMP) AS next_attempt_at,
                   COALESCE(claimed_by, '') AS claimed_by,
                   COALESCE(claim_expires_at, '') AS claim_expires_at
            FROM task_runs
            WHERE status IN ('pending', 'running')
            ORDER BY task_id ASC
            """
        ).fetchall()
        status_map = {str(row["task_id"]): str(row["status"]) for row in rows}
        candidates: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            claim_expires_at = str(item["claim_expires_at"] or "")
            if str(item["claimed_by"]).strip() and str(item["claimed_by"]) != self.worker_id:
                if not claim_expires_at:
                    continue
                is_expired = bool(
                    self.db.conn.execute(
                        "SELECT (? <= CURRENT_TIMESTAMP)", (claim_expires_at,)
                    ).fetchone()[0]
                )
                if not is_expired:
                    continue
            if str(item["status"]) == "pending":
                deps = self.db.get_task_run(str(item["task_run_id"]))["deps"]
                if any(status_map.get(dep_task_id) != "succeeded" for dep_task_id in deps):
                    continue
            is_due = bool(
                self.db.conn.execute(
                    "SELECT (? <= CURRENT_TIMESTAMP)", (item["next_attempt_at"],)
                ).fetchone()[0]
            )
            if is_due:
                candidates.append(self.db.get_task_run(str(item["task_run_id"])) or {})
        return candidates

    def _task_metadata(self, task_run: dict[str, Any]) -> dict[str, str]:
        plan = self.db.get_orchestration_plan(task_run["plan_id"]) or {}
        payload = plan.get("payload") or {}
        tasks = payload.get("payload", {}).get("tasks") or payload.get("tasks") or []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            if str(task.get("task_id") or task.get("id") or "").strip() == task_run["task_id"]:
                inputs = task.get("inputs") if isinstance(task.get("inputs"), dict) else {}
                return {
                    "repo": str(inputs.get("repo", "default/repo")),
                    "tool": str(inputs.get("tool", "github_read")),
                    "provider": str(inputs.get("provider", "langgraph")),
                }
        inputs = payload.get("inputs") if isinstance(payload.get("inputs"), dict) else {}
        return {
            "repo": str(inputs.get("repo", "default/repo")),
            "tool": str(inputs.get("tool", "github_read")),
            "provider": str(inputs.get("provider", "langgraph")),
        }

    def _within_quotas(
        self, candidate: dict[str, Any], *, reserved: dict[str, dict[str, int]]
    ) -> bool:
        metadata = self._task_metadata(candidate)
        running = self.db.conn.execute(
            """
            SELECT task_run_id, plan_id FROM task_runs
            WHERE status = 'running'
              AND claim_expires_at > CURRENT_TIMESTAMP
            """
        ).fetchall()
        repo_count = 0
        tool_count = 0
        provider_count = 0
        for row in running:
            task = self.db.get_task_run(str(row["task_run_id"]))
            if task is None:
                continue
            entry = self._task_metadata(task)
            repo_count += int(entry["repo"] == metadata["repo"])
            tool_count += int(entry["tool"] == metadata["tool"])
            provider_count += int(entry["provider"] == metadata["provider"])
        repo_count += int(reserved["repo"].get(metadata["repo"], 0))
        tool_count += int(reserved["tool"].get(metadata["tool"], 0))
        provider_count += int(reserved["provider"].get(metadata["provider"], 0))
        return (
            repo_count < self.quotas.max_parallel_per_repo
            and tool_count < self.quotas.max_parallel_per_tool
            and provider_count < self.quotas.max_parallel_per_provider
        )

    def _dispatch_task(self, *, task_run_id: str) -> None:
        task_run = self.db.get_task_run(task_run_id)
        if task_run is None:
            return
        run_id = task_run["run_id"] or f"{task_run_id}:attempt:{task_run['retries'] + 1}"
        spec = {
            "schema_version": "agent_run_spec/v2",
            "run_id": run_id,
            "goal": f"Execute task {task_run['task_id']}",
            "inputs": {"task_run_id": task_run_id},
            "execution": {
                "engine": "langgraph",
                "graph_id": "repo_change_proposer/v1",
                "thread_id": None,
                "budget": {
                    "max_total_tokens": 500,
                    "max_tool_calls": 5,
                    "max_wall_seconds": 60,
                },
                "tools_allowed": ["github_read"],
                "scopes": {"repo": self._task_metadata(task_run)["repo"]},
            },
            "model": "gpt-5",
            "intent": "task_scheduler_dispatch",
            "requires_approval": True,
            "adapter": "langgraph",
            "simulated_steps": [{"type": "model_call", "tokens": 1, "node_id": "task-start"}],
        }
        existing = self.db.get_agent_run(run_id)
        if existing is None:
            self.runner.create_run(spec=spec, created_by=self.worker_id)
            self.runner.transition(
                run_id,
                to_status="approved",
                reason_code="task_scheduler_approved",
                actor=self.worker_id,
            )
        claimed = self.runner.claim_ready_runs(
            worker_id=f"task-worker:{task_run_id}",
            limit=1,
            lease_seconds=self.lease_seconds,
        )
        if not claimed:
            return
        outcome = self.runner.execute_claimed_run(
            run_id=run_id, worker_id=f"task-worker:{task_run_id}"
        )
        persisted = self.db.get_agent_run(run_id) or outcome
        status = str(persisted.get("status", "running"))
        reason_code = str(persisted.get("status_reason") or persisted.get("last_error") or "")
        thread_id = str(persisted.get("thread_id", ""))
        if status == "completed":
            self.db.update_task_run_result(
                task_run_id,
                status="succeeded",
                run_id=run_id,
                thread_id=thread_id,
                clear_claim=True,
            )
            self.db.append_audit_event(
                "task_run_succeeded",
                {
                    "task_run_id": task_run_id,
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "reason_code": "task_completed",
                },
            )
            return

        if status in {"failed", "cancelled", "rejected"}:
            retries = int(task_run["retries"]) + 1
            if retries > self.max_task_retries:
                self.db.update_task_run_result(
                    task_run_id,
                    status="failed",
                    retries=retries,
                    run_id=run_id,
                    thread_id=thread_id,
                    reason_code=reason_code or "retry_budget_exhausted",
                    clear_claim=True,
                )
                self.db.append_audit_event(
                    "task_run_failed",
                    {
                        "task_run_id": task_run_id,
                        "run_id": run_id,
                        "thread_id": thread_id,
                        "retries": retries,
                        "reason_code": reason_code or "retry_budget_exhausted",
                    },
                )
                return
            delay_seconds = 5 * retries
            self.db.update_task_run_result(
                task_run_id,
                status="pending",
                retries=retries,
                next_attempt_seconds=delay_seconds,
                run_id=run_id,
                thread_id=thread_id,
                reason_code=reason_code or "task_retry_scheduled",
                clear_claim=True,
            )
            self.db.append_audit_event(
                "task_run_retry_scheduled",
                {
                    "task_run_id": task_run_id,
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "retries": retries,
                    "next_attempt_in_seconds": delay_seconds,
                    "reason_code": reason_code or "task_retry_scheduled",
                },
            )
            return

        self.db.update_task_run_result(
            task_run_id,
            status="running",
            run_id=run_id,
            thread_id=thread_id,
            clear_claim=True,
        )
        self.db.append_audit_event(
            "task_run_running",
            {
                "task_run_id": task_run_id,
                "run_id": run_id,
                "thread_id": thread_id,
                "reason_code": "task_in_progress",
            },
        )
