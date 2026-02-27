"""LangGraph runner adapter with lightweight policy checks and interrupt/resume support."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from pm_bot.execution_plane.langgraph.checkpointer import FsDbCheckpointer


@dataclass(frozen=True)
class RunnerSubmitResult:
    job_id: str
    state: str


@dataclass(frozen=True)
class RunnerPollResult:
    state: str
    reason_code: str = ""
    interrupt_id: str = ""
    interrupt_payload: dict[str, Any] | None = None


class AuditSink(Protocol):
    def append_audit_event(self, event_type: str, payload: dict[str, Any]) -> None: ...


class InterruptStore(Protocol):
    def create_run_interrupt(
        self,
        interrupt_id: str,
        run_id: str,
        thread_id: str,
        kind: str,
        risk: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...


class RunStore(Protocol):
    def set_agent_run_execution(
        self, run_id: str, job_id: str = "", thread_id: str = ""
    ) -> None: ...


class ArtifactStore(Protocol):
    def list_run_artifacts(self, run_id: str) -> list[dict[str, Any]]: ...


@dataclass
class _ThreadRuntime:
    run_id: str
    thread_id: str
    status: str = "running"
    started_monotonic: float = field(default_factory=time.monotonic)
    node_id: str = "start"
    step_index: int = 0
    tokens_used: int = 0
    tool_calls: int = 0
    last_interrupt_id: str = ""
    pending_interrupt_payload: dict[str, Any] | None = None


class LangGraphRunnerAdapter:
    name = "langgraph"

    def __init__(
        self,
        audit_sink: AuditSink,
        interrupt_store: InterruptStore,
        run_store: RunStore,
        artifact_store: ArtifactStore,
        checkpointer: FsDbCheckpointer,
    ) -> None:
        self._audit = audit_sink
        self._interrupts = interrupt_store
        self._run_store = run_store
        self._artifacts = artifact_store
        self._checkpointer = checkpointer
        self._threads: dict[str, _ThreadRuntime] = {}

    def submit(self, run: dict[str, Any]) -> RunnerSubmitResult:
        thread_id = str(uuid.uuid4())
        runtime = _ThreadRuntime(run_id=run["run_id"], thread_id=thread_id)
        self._threads[run["run_id"]] = runtime
        self._run_store.set_agent_run_execution(run["run_id"], thread_id=thread_id)
        self._checkpoint(run, runtime)
        return RunnerSubmitResult(job_id=f"langgraph:{thread_id}", state="running")

    def poll(self, run: dict[str, Any]) -> RunnerPollResult:
        runtime = self._threads.get(run["run_id"])
        if runtime is None:
            return RunnerPollResult(state="failed", reason_code="unknown_thread")
        if runtime.status == "blocked":
            return RunnerPollResult(
                state="blocked",
                reason_code="interrupt_pending",
                interrupt_id=runtime.last_interrupt_id,
                interrupt_payload=runtime.pending_interrupt_payload,
            )
        if runtime.status in {"cancelled", "completed", "failed"}:
            return RunnerPollResult(state=runtime.status)

        budget = ((run.get("spec") or {}).get("execution") or {}).get("budget") or {}
        if self._wall_seconds(runtime) > int(budget.get("max_wall_seconds", 1_000_000)):
            return self._violation(run, runtime, "budget.wall_seconds")

        steps = list((run.get("spec") or {}).get("simulated_steps", []))
        if runtime.step_index >= len(steps):
            runtime.status = "completed"
            runtime.node_id = "done"
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="completed")

        step = steps[runtime.step_index]
        runtime.node_id = str(step.get("node_id", f"step-{runtime.step_index}"))
        step_kind = str(step.get("type", "model_call"))
        if step_kind == "model_call":
            tokens = int(step.get("tokens", 0))
            runtime.tokens_used += tokens
            if runtime.tokens_used > int(budget.get("max_total_tokens", 1_000_000_000)):
                return self._violation(run, runtime, "budget.total_tokens")
            self._audit.append_audit_event(
                "langgraph_model_call",
                {
                    "run_id": run["run_id"],
                    "thread_id": runtime.thread_id,
                    "node_id": runtime.node_id,
                    "tokens": tokens,
                },
            )
        elif step_kind == "tool_call":
            tool_name = str(step.get("tool", ""))
            allowed_tools = list(
                (((run.get("spec") or {}).get("execution") or {}).get("tools_allowed") or [])
            )
            if tool_name not in allowed_tools:
                return self._violation(run, runtime, "policy.tool_not_allowed", {"tool": tool_name})
            runtime.tool_calls += 1
            if runtime.tool_calls > int(budget.get("max_tool_calls", 1_000_000_000)):
                return self._violation(run, runtime, "budget.tool_calls")
            self._audit.append_audit_event(
                "langgraph_tool_call",
                {
                    "run_id": run["run_id"],
                    "thread_id": runtime.thread_id,
                    "node_id": runtime.node_id,
                    "tool": tool_name,
                },
            )

        runtime.step_index += 1
        self._checkpoint(run, runtime)
        return RunnerPollResult(state="running")

    def resume(self, run: dict[str, Any], decision: dict[str, Any]) -> RunnerPollResult:
        runtime = self._threads.get(run["run_id"])
        if runtime is None:
            return RunnerPollResult(state="failed", reason_code="unknown_thread")
        action = str(decision.get("action", "reject"))
        self._audit.append_audit_event(
            "langgraph_interrupt_decision",
            {
                "run_id": run["run_id"],
                "thread_id": runtime.thread_id,
                "node_id": runtime.node_id,
                "action": action,
            },
        )
        if action == "approve":
            runtime.status = "running"
            runtime.pending_interrupt_payload = None
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")
        if action == "edit":
            edited = decision.get("edited_payload")
            runtime.pending_interrupt_payload = edited if isinstance(edited, dict) else {}
            runtime.status = "running"
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")
        runtime.status = "failed"
        self._checkpoint(run, runtime)
        return RunnerPollResult(state="failed", reason_code="interrupt_rejected")

    def cancel(self, run: dict[str, Any]) -> RunnerPollResult:
        runtime = self._threads.get(run["run_id"])
        if runtime is None:
            return RunnerPollResult(state="cancelled", reason_code="cancelled")
        runtime.status = "cancelled"
        self._checkpoint(run, runtime)
        return RunnerPollResult(state="cancelled", reason_code="cancelled_by_user")

    def fetch_artifacts(self, run: dict[str, Any]) -> list[str]:
        return [entry["uri"] for entry in self._artifacts.list_run_artifacts(run["run_id"])]

    def _wall_seconds(self, runtime: _ThreadRuntime) -> int:
        return int(time.monotonic() - runtime.started_monotonic)

    def _violation(
        self,
        run: dict[str, Any],
        runtime: _ThreadRuntime,
        reason_code: str,
        extra: dict[str, Any] | None = None,
    ) -> RunnerPollResult:
        spec = run.get("spec") or {}
        mode = str(spec.get("policy_violation_mode", "interrupt")).strip().lower() or "interrupt"
        if mode == "fail":
            runtime.status = "failed"
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="failed", reason_code=reason_code)
        interrupt_id = f"interrupt:{run['run_id']}:{uuid.uuid4()}"
        payload = {
            "reason_code": reason_code,
            "node_id": runtime.node_id,
            "thread_id": runtime.thread_id,
            **(extra or {}),
        }
        self._interrupts.create_run_interrupt(
            interrupt_id=interrupt_id,
            run_id=run["run_id"],
            thread_id=runtime.thread_id,
            kind="policy_violation",
            risk="medium",
            payload=payload,
        )
        self._audit.append_audit_event(
            "langgraph_interrupt_created",
            {
                "run_id": run["run_id"],
                "thread_id": runtime.thread_id,
                "node_id": runtime.node_id,
                "interrupt_id": interrupt_id,
                "payload": payload,
            },
        )
        runtime.status = "blocked"
        runtime.last_interrupt_id = interrupt_id
        runtime.pending_interrupt_payload = payload
        self._checkpoint(run, runtime)
        return RunnerPollResult(
            state="blocked",
            reason_code=reason_code,
            interrupt_id=interrupt_id,
            interrupt_payload=payload,
        )

    def _checkpoint(self, run: dict[str, Any], runtime: _ThreadRuntime) -> None:
        payload = {
            "step_index": runtime.step_index,
            "tokens_used": runtime.tokens_used,
            "tool_calls": runtime.tool_calls,
            "last_interrupt_id": runtime.last_interrupt_id,
        }
        self._checkpointer.write(
            run_id=run["run_id"],
            thread_id=runtime.thread_id,
            status=runtime.status,
            current_node_id=runtime.node_id,
            payload=payload,
        )
