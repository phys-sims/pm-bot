"""Changeset propose/approve/publish flow."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from pm_bot.server.db import OrchestratorDB
from pm_bot.server.github_connector import GitHubConnector, WriteRequest


class ChangesetService:
    def __init__(
        self,
        db: OrchestratorDB,
        connector: GitHubConnector,
        max_retries: int = 2,
    ) -> None:
        self.db = db
        self.connector = connector
        self.max_retries = max_retries

    def _build_idempotency_key(
        self,
        operation: str,
        repo: str,
        target_ref: str,
        payload: dict[str, Any],
    ) -> str:
        payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
        return f"{operation}:{repo}:{target_ref or '-'}:{payload_hash}"

    def propose(
        self,
        operation: str,
        repo: str,
        payload: dict[str, Any],
        target_ref: str = "",
        idempotency_key: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        decision = self.connector.evaluate_write(repo=repo, operation=operation)
        if not decision.allowed:
            self.db.append_audit_event(
                "changeset_denied",
                {
                    "repo": repo,
                    "operation": operation,
                    "reason_code": decision.reason_code,
                    "run_id": run_id,
                },
            )
            raise PermissionError(f"Changeset rejected by guardrails: {decision.reason_code}")

        resolved_key = idempotency_key or self._build_idempotency_key(
            operation=operation,
            repo=repo,
            target_ref=target_ref,
            payload=payload,
        )
        existing = self.db.get_changeset_by_idempotency_key(resolved_key)
        if existing is not None:
            self.db.append_audit_event(
                "changeset_idempotent_reuse",
                {
                    "changeset_id": existing["id"],
                    "idempotency_key": resolved_key,
                    "run_id": run_id,
                },
            )
            return existing

        changeset_id = self.db.create_changeset(
            operation=operation,
            repo=repo,
            payload=payload,
            target_ref=target_ref,
            idempotency_key=resolved_key,
        )
        self.db.append_audit_event(
            "changeset_proposed",
            {
                "changeset_id": changeset_id,
                "repo": repo,
                "operation": operation,
                "idempotency_key": resolved_key,
                "run_id": run_id,
            },
        )
        return self.db.get_changeset(changeset_id) or {}

    def approve(self, changeset_id: int, approved_by: str, run_id: str = "") -> dict[str, Any]:
        changeset = self.db.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError("Unknown changeset")

        if changeset["status"] != "pending":
            raise ValueError("Changeset is not pending")

        self.db.record_approval(changeset_id, approved_by)

        attempts = 0
        while attempts <= self.max_retries:
            attempts += 1
            started = time.perf_counter()
            try:
                result = self.connector.execute_write(
                    WriteRequest(
                        operation=changeset["operation"],
                        repo=changeset["repo"],
                        target_ref=changeset.get("target_ref") or "",
                        payload=changeset["payload"],
                    )
                )
                latency_ms = (time.perf_counter() - started) * 1000
                self.db.record_operation_metric("changeset_write", "success", latency_ms)
                self.db.append_audit_event(
                    "changeset_attempt",
                    {
                        "changeset_id": changeset_id,
                        "attempt": attempts,
                        "result": "success",
                        "latency_ms": round(latency_ms, 3),
                        "run_id": run_id,
                    },
                )
                self.db.set_changeset_status(changeset_id, "applied")
                self.db.append_audit_event(
                    "changeset_applied",
                    {
                        "changeset_id": changeset_id,
                        "approved_by": approved_by,
                        "result": result,
                        "attempts": attempts,
                        "run_id": run_id,
                    },
                )
                return result
            except RuntimeError as exc:
                latency_ms = (time.perf_counter() - started) * 1000
                self.db.record_operation_metric("changeset_write", "retryable_failure", latency_ms)
                self.db.update_changeset_retry(changeset_id, attempts, str(exc))
                self.db.append_audit_event(
                    "changeset_attempt",
                    {
                        "changeset_id": changeset_id,
                        "attempt": attempts,
                        "result": "retryable_failure",
                        "error": str(exc),
                        "latency_ms": round(latency_ms, 3),
                        "run_id": run_id,
                    },
                )
                if attempts > self.max_retries:
                    self.db.set_changeset_status(changeset_id, "failed")
                    self.db.append_audit_event(
                        "changeset_dead_lettered",
                        {
                            "changeset_id": changeset_id,
                            "attempts": attempts,
                            "error": str(exc),
                            "reason_code": "retry_budget_exhausted",
                            "run_id": run_id,
                        },
                    )
                    raise RuntimeError("Changeset failed: retry_budget_exhausted") from exc

        raise RuntimeError("Unreachable retry state")
