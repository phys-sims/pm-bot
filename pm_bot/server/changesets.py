"""Changeset propose/approve/publish flow."""

from __future__ import annotations

from typing import Any

from pm_bot.server.db import OrchestratorDB
from pm_bot.server.github_connector import GitHubConnector, WriteRequest


class ChangesetService:
    def __init__(self, db: OrchestratorDB, connector: GitHubConnector) -> None:
        self.db = db
        self.connector = connector

    def propose(
        self,
        operation: str,
        repo: str,
        payload: dict[str, Any],
        target_ref: str = "",
    ) -> dict[str, Any]:
        if not self.connector.can_write(repo, operation):
            self.db.append_audit_event(
                "changeset_denied",
                {"repo": repo, "operation": operation},
            )
            raise PermissionError("Changeset rejected by guardrails")

        changeset_id = self.db.create_changeset(
            operation=operation,
            repo=repo,
            payload=payload,
            target_ref=target_ref,
        )
        self.db.append_audit_event(
            "changeset_proposed",
            {"changeset_id": changeset_id, "repo": repo, "operation": operation},
        )
        return self.db.get_changeset(changeset_id) or {}

    def approve(self, changeset_id: int, approved_by: str) -> dict[str, Any]:
        changeset = self.db.get_changeset(changeset_id)
        if changeset is None:
            raise ValueError("Unknown changeset")

        if changeset["status"] != "pending":
            raise ValueError("Changeset is not pending")

        self.db.record_approval(changeset_id, approved_by)
        result = self.connector.execute_write(
            WriteRequest(
                operation=changeset["operation"],
                repo=changeset["repo"],
                target_ref=changeset.get("target_ref") or "",
                payload=changeset["payload"],
            )
        )
        self.db.set_changeset_status(changeset_id, "applied")
        self.db.append_audit_event(
            "changeset_applied",
            {"changeset_id": changeset_id, "approved_by": approved_by, "result": result},
        )
        return result
