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
        self.issues: dict[tuple[str, str], dict[str, Any]] = {}

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
        if request.operation == "create_issue":
            issue_ref = request.payload.get("issue_ref", "")
            if issue_ref:
                self.issues[(request.repo, issue_ref)] = dict(request.payload)
        elif request.operation == "update_issue":
            issue_ref = request.target_ref
            issue = self.issues.get((request.repo, issue_ref), {})
            issue.update(request.payload)
            self.issues[(request.repo, issue_ref)] = issue

        return {
            "repo": request.repo,
            "operation": request.operation,
            "target_ref": request.target_ref,
            "status": "applied",
        }

    def fetch_issue(self, repo: str, issue_ref: str) -> dict[str, Any] | None:
        return self.issues.get((repo, issue_ref))

    def list_issues(self, repo: str, **filters: str) -> list[dict[str, Any]]:
        issues = [issue for (issue_repo, _), issue in self.issues.items() if issue_repo == repo]
        if not filters:
            return issues

        matched: list[dict[str, Any]] = []
        for issue in issues:
            if all(str(issue.get(key, "")) == value for key, value in filters.items()):
                matched.append(issue)
        return matched
