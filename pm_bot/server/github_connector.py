"""GitHub connector abstraction with approval and guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DENIED_OPERATIONS = {"delete_issue", "edit_workflow"}


@dataclass(frozen=True)
class WriteRequest:
    operation: str
    repo: str
    target_ref: str
    payload: dict[str, Any]


class GitHubConnector:
    """In-memory connector used for deterministic v1 workflow tests."""

    def __init__(self, allowed_repos: set[str] | None = None) -> None:
        self.allowed_repos = allowed_repos or set()
        self.executed_writes: list[WriteRequest] = []

    def can_write(self, repo: str, operation: str) -> bool:
        if self.allowed_repos and repo not in self.allowed_repos:
            return False
        if operation in DENIED_OPERATIONS:
            return False
        return True

    def execute_write(self, request: WriteRequest) -> dict[str, Any]:
        if not self.can_write(request.repo, request.operation):
            raise PermissionError("Write denied by guardrails")

        self.executed_writes.append(request)
        return {
            "repo": request.repo,
            "operation": request.operation,
            "target_ref": request.target_ref,
            "status": "applied",
        }
