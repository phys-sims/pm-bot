"""GitHub connector contracts, policy primitives, and factory helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

from pm_bot.server.github_auth import GitHubAuth, load_github_auth_from_env


DENIED_OPERATIONS = {"delete_issue", "edit_workflow"}


@dataclass(frozen=True)
class WriteRequest:
    operation: str
    repo: str
    target_ref: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str


class RetryableGitHubError(RuntimeError):
    def __init__(self, message: str, reason_code: str, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.retry_after_s = retry_after_s


class GitHubConnector(Protocol):
    """Connector contract for all GitHub integration implementations."""

    allowed_repos: set[str]

    def evaluate_write(self, repo: str, operation: str) -> PolicyDecision: ...

    def can_write(self, repo: str, operation: str) -> bool: ...

    def execute_write(self, request: WriteRequest) -> dict[str, Any]: ...

    def fetch_issue(self, repo: str, issue_ref: str) -> dict[str, Any] | None: ...

    def list_issues(self, repo: str, **filters: str) -> list[dict[str, Any]]: ...


def build_connector_from_env(
    env: dict[str, str] | None = None,
    allowed_repos: set[str] | None = None,
) -> GitHubConnector:
    env_map = os.environ if env is None else env
    connector_type = (env_map.get("PM_BOT_GITHUB_CONNECTOR") or "in_memory").strip().lower()
    repos = allowed_repos or {"phys-sims/.github", "phys-sims/phys-pipeline"}

    if connector_type == "api":
        from pm_bot.server.github_connector_api import GitHubAPIConnector

        auth = load_github_auth_from_env(env_map)
        return GitHubAPIConnector(allowed_repos=repos, auth=auth)

    from pm_bot.server.github_connector_inmemory import InMemoryGitHubConnector

    return InMemoryGitHubConnector(allowed_repos=repos)


__all__ = [
    "DENIED_OPERATIONS",
    "GitHubAuth",
    "GitHubConnector",
    "PolicyDecision",
    "RetryableGitHubError",
    "WriteRequest",
    "build_connector_from_env",
]
