"""LangGraph runner adapter with lightweight policy checks and interrupt/resume support."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pm_bot.execution_plane.langgraph.checkpointer import FsDbCheckpointer
from pm_bot.execution_plane.llm import ISSUE_REPLANNER, run_capability
from pm_bot.shared.settings import get_storage_settings


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
    context_pack: dict[str, Any] | None = None
    retrieval: dict[str, Any] | None = None
    changeset_bundle: dict[str, Any] | None = None
    artifact_uris: list[str] = field(default_factory=list)


class LangGraphRunnerAdapter:
    name = "langgraph"
    _GRAPH_REPO_CHANGE_PROPOSER_V1 = "repo_change_proposer/v1"
    _EXPENSIVE_EXTERNAL_ACTIONS = {"repo_checkout", "run_tests"}

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

        spec = run.get("spec") or {}
        budget = (spec.get("execution") or {}).get("budget") or {}
        if self._wall_seconds(runtime) > int(budget.get("max_wall_seconds", 1_000_000)):
            return self._violation(run, runtime, "budget.wall_seconds")

        graph_id = str((spec.get("execution") or {}).get("graph_id", "")).strip()
        if graph_id == self._GRAPH_REPO_CHANGE_PROPOSER_V1 and not spec.get("simulated_steps"):
            return self._poll_repo_change_proposer_v1(run, runtime)

        steps = list(spec.get("simulated_steps", []))
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
        runtime = self._threads.get(run["run_id"])
        if runtime is not None and runtime.artifact_uris:
            return list(runtime.artifact_uris)
        return [entry["uri"] for entry in self._artifacts.list_run_artifacts(run["run_id"])]

    def _poll_repo_change_proposer_v1(
        self, run: dict[str, Any], runtime: _ThreadRuntime
    ) -> RunnerPollResult:
        spec = run.get("spec") or {}
        if runtime.step_index == 0:
            runtime.node_id = "load_context_pack"
            runtime.context_pack = self._load_context_pack(spec=spec)
            runtime.step_index += 1
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")

        if runtime.step_index == 1:
            runtime.node_id = "planner_decide_retrieval"
            should_retrieve = self._planner_should_retrieve(spec=spec)
            runtime.retrieval = {
                "enabled": should_retrieve,
                "query": str((spec.get("inputs") or {}).get("retrieval_query") or ""),
                "results": [],
                "chunk_ids": [],
                "token_usage": 0,
                "budget_tokens": int(
                    (
                        ((spec.get("execution") or {}).get("budget") or {}).get(
                            "max_retrieval_tokens", 0
                        )
                    )
                    or 0
                ),
            }
            runtime.step_index += 1
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")

        if runtime.step_index == 2:
            runtime.node_id = "retrieve_context"
            runtime.retrieval = self._retrieve_context(run=run, runtime=runtime)
            runtime.step_index += 1
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")

        if runtime.step_index == 3:
            runtime.node_id = "propose_changeset_bundle"
            expensive = self._requested_expensive_actions(spec=spec)
            if expensive and not bool(
                (spec.get("inputs") or {}).get("allow_expensive_actions", False)
            ):
                return self._violation(
                    run,
                    runtime,
                    "policy.expensive_external_action_requires_interrupt",
                    {"actions": expensive},
                )
            runtime.changeset_bundle = self._propose_changeset_bundle(run=run, runtime=runtime)
            runtime.step_index += 1
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")

        if runtime.step_index == 4:
            runtime.node_id = "emit_artifact"
            if runtime.changeset_bundle is None:
                return RunnerPollResult(state="failed", reason_code="missing_changeset_bundle")
            artifact_uri = self._emit_artifact(run=run, runtime=runtime)
            runtime.artifact_uris = [artifact_uri]
            runtime.step_index += 1
            self._checkpoint(run, runtime)
            return RunnerPollResult(state="running")

        runtime.status = "completed"
        runtime.node_id = "done"
        self._checkpoint(run, runtime)
        return RunnerPollResult(state="completed")

    def _load_context_pack(self, *, spec: dict[str, Any]) -> dict[str, Any]:
        inputs = spec.get("inputs") or {}
        context_pack = inputs.get("context_pack")
        if isinstance(context_pack, dict):
            return context_pack
        return {
            "schema_version": "context_pack/v2",
            "source": "cache_fallback",
            "inputs": inputs,
        }

    def _planner_should_retrieve(self, *, spec: dict[str, Any]) -> bool:
        query = str((spec.get("inputs") or {}).get("retrieval_query") or "").strip()
        return bool(query)

    def _retrieve_context(self, *, run: dict[str, Any], runtime: _ThreadRuntime) -> dict[str, Any]:
        retrieval = dict(runtime.retrieval or {})
        if not retrieval.get("enabled"):
            return retrieval

        spec = run.get("spec") or {}
        inputs = spec.get("inputs") or {}
        budget = (spec.get("execution") or {}).get("budget") or {}
        configured_cap = int(retrieval.get("budget_tokens") or 0)
        default_cap = max(0, int(budget.get("max_total_tokens", 0)) - runtime.tokens_used)
        token_cap = configured_cap if configured_cap > 0 else default_cap
        retrieval["budget_tokens"] = token_cap

        chunks = inputs.get("retrieval_chunks")
        if not isinstance(chunks, list):
            chunks = []

        used = 0
        selected: list[dict[str, Any]] = []
        chunk_ids: list[str] = []
        for raw in chunks:
            if not isinstance(raw, dict):
                continue
            chunk_id = str(raw.get("chunk_id") or "").strip()
            if not chunk_id:
                continue
            text = str(raw.get("text") or "")
            estimated_tokens = max(1, len(text) // 4)
            if used + estimated_tokens > token_cap:
                continue
            used += estimated_tokens
            selected.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "source_path": raw.get("source_path"),
                    "line_start": raw.get("line_start"),
                    "line_end": raw.get("line_end"),
                    "doc_type": raw.get("doc_type"),
                    "revision_sha": raw.get("revision_sha"),
                    "score": raw.get("score"),
                }
            )
            chunk_ids.append(chunk_id)

        retrieval["results"] = selected
        retrieval["chunk_ids"] = chunk_ids
        retrieval["token_usage"] = used
        if isinstance(runtime.context_pack, dict):
            self._attach_retrieval_to_context_pack(runtime.context_pack, retrieval)
        self._audit.append_audit_event(
            "langgraph_retrieval_query",
            {
                "run_id": run["run_id"],
                "thread_id": runtime.thread_id,
                "node_id": runtime.node_id,
                "query": retrieval.get("query") or "",
                "chunk_ids": chunk_ids,
                "token_usage": used,
                "budget_tokens": token_cap,
            },
        )
        return retrieval

    def _attach_retrieval_to_context_pack(
        self, context_pack: dict[str, Any], retrieval: dict[str, Any]
    ) -> None:
        sections = context_pack.get("sections")
        if not isinstance(sections, list):
            sections = []
            context_pack["sections"] = sections
        for result in retrieval.get("results", []):
            sections.append(
                {
                    "id": f"retrieved:{result.get('chunk_id')}",
                    "kind": "retrieved",
                    "content": result.get("text", ""),
                    "provenance": {
                        "chunk_id": result.get("chunk_id"),
                        "source_path": result.get("source_path"),
                        "line_start": result.get("line_start"),
                        "line_end": result.get("line_end"),
                        "doc_type": result.get("doc_type"),
                        "revision_sha": result.get("revision_sha"),
                        "score": result.get("score"),
                    },
                }
            )

        manifest = context_pack.get("manifest")
        if not isinstance(manifest, dict):
            manifest = {}
            context_pack["manifest"] = manifest
        manifest["retrieval"] = {
            "query": retrieval.get("query") or "",
            "chunk_ids": list(retrieval.get("chunk_ids") or []),
        }

    def _requested_expensive_actions(self, *, spec: dict[str, Any]) -> list[str]:
        requested = (spec.get("inputs") or {}).get("external_actions", [])
        if not isinstance(requested, list):
            return []
        normalized = [str(item).strip() for item in requested]
        return [item for item in normalized if item in self._EXPENSIVE_EXTERNAL_ACTIONS]

    def _propose_changeset_bundle(
        self,
        *,
        run: dict[str, Any],
        runtime: _ThreadRuntime,
    ) -> dict[str, Any]:
        spec = run.get("spec") or {}
        inputs = spec.get("inputs") or {}
        execution = spec.get("execution") or {}
        repo = str((execution.get("scopes") or {}).get("repo", "")).strip()
        capability_input = {
            "repo": repo,
            "current_snapshot_id": str(inputs.get("context_pack_id") or run["run_id"]),
            "diff": inputs.get("diff")
            or {
                "status_changes": [
                    {
                        "issue_ref": str(inputs.get("issue_ref") or "#0"),
                        "before": "unknown",
                        "after": "planned",
                    }
                ],
                "blocker_changes": [],
            },
        }
        result = run_capability(
            ISSUE_REPLANNER,
            input_payload=capability_input,
            context={"provider": str(inputs.get("llm_provider") or "local")},
            policy={
                "require_human_approval": True,
                "proposal_output_changeset_bundle": True,
                "allow_direct_github_writes": False,
            },
        )
        usage = result.get("usage") if isinstance(result, dict) else {}
        self._audit.append_audit_event(
            "langgraph_model_call",
            {
                "run_id": run["run_id"],
                "thread_id": runtime.thread_id,
                "node_id": runtime.node_id,
                "capability_id": ISSUE_REPLANNER,
                "tokens": int((usage or {}).get("total_tokens", 0)),
            },
        )
        output = result.get("output")
        if not isinstance(output, dict):
            raise ValueError("invalid_changeset_bundle_output")
        return output

    def _emit_artifact(self, *, run: dict[str, Any], runtime: _ThreadRuntime) -> str:
        settings = get_storage_settings()
        artifact_path = Path(settings.artifact_dir) / f"{run['run_id']}.changeset_bundle.json"
        payload = {
            "run_id": run["run_id"],
            "thread_id": runtime.thread_id,
            "graph_id": self._GRAPH_REPO_CHANGE_PROPOSER_V1,
            "context_pack": runtime.context_pack,
            "retrieval": runtime.retrieval,
            "changeset_bundle": runtime.changeset_bundle,
        }
        artifact_path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        artifact_uri = artifact_path.resolve().as_uri()
        self._audit.append_audit_event(
            "langgraph_artifact_emitted",
            {
                "run_id": run["run_id"],
                "thread_id": runtime.thread_id,
                "node_id": runtime.node_id,
                "kind": "changeset_bundle",
                "uri": artifact_uri,
            },
        )
        return artifact_uri

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
