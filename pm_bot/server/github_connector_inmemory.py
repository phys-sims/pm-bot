"""In-memory GitHub connector for deterministic tests."""

from __future__ import annotations

from typing import Any

from pm_bot.server.github_connector import (
    DENIED_OPERATIONS,
    PolicyDecision,
    RetryableGitHubError,
    WriteRequest,
)


class InMemoryGitHubConnector:
    """In-memory connector used for deterministic v1 workflow tests."""

    def __init__(self, allowed_repos: set[str] | None = None) -> None:
        self.allowed_repos = allowed_repos or set()
        self.executed_writes: list[WriteRequest] = []
        self.issues: dict[tuple[str, str], dict[str, Any]] = {}
        self._transient_failures_seen: dict[tuple[str, str, str], int] = {}

    def evaluate_write(self, repo: str, operation: str) -> PolicyDecision:
        if self.allowed_repos and repo not in self.allowed_repos:
            return PolicyDecision(allowed=False, reason_code="repo_not_allowlisted")
        if operation in DENIED_OPERATIONS:
            return PolicyDecision(allowed=False, reason_code="operation_denylisted")
        return PolicyDecision(allowed=True, reason_code="allowed")

    def can_write(self, repo: str, operation: str) -> bool:
        return self.evaluate_write(repo=repo, operation=operation).allowed

    def execute_write(self, request: WriteRequest) -> dict[str, Any]:
        decision = self.evaluate_write(repo=request.repo, operation=request.operation)
        if not decision.allowed:
            raise PermissionError(f"Write denied by guardrails: {decision.reason_code}")

        fail_budget = int(request.payload.get("_transient_failures", 0) or 0)
        signature = (request.repo, request.operation, request.target_ref)
        seen = self._transient_failures_seen.get(signature, 0)
        if seen < fail_budget:
            self._transient_failures_seen[signature] = seen + 1
            raise RetryableGitHubError(
                "Transient connector failure", reason_code="transient_failure"
            )

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
        elif request.operation == "link_issue":
            issue_ref = request.target_ref
            issue = self.issues.get((request.repo, issue_ref), {"issue_ref": issue_ref})
            links = list(issue.get("linked_issues", []))
            linked_issue_ref = str(request.payload.get("linked_issue_ref", ""))
            if linked_issue_ref and linked_issue_ref not in links:
                links.append(linked_issue_ref)
            issue["linked_issues"] = links
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
