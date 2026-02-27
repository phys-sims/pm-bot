"""GitHub connector contracts, policy primitives, and factory helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

from pm_bot.control_plane.github.github_auth import GitHubAuth, load_github_auth_from_env


DENIED_OPERATIONS = {"delete_issue", "edit_workflow"}

DEFAULT_ALLOWED_REPOS = {
    "phys-sims/.github",
    "phys-sims/phys-pipeline",
    "phys-sims/cpa-sim",
    "phys-sims/fiber-link-sim",
    "phys-sims/abcdef-sim",
    "phys-sims/fiber-link-testbench",
    "phys-sims/phys-sims-utils",
}


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

    def list_pull_requests(self, repo: str, **filters: str) -> list[dict[str, Any]]: ...

    def list_sub_issues(self, repo: str, issue_ref: str) -> list[dict[str, Any]]: ...

    def list_issue_dependencies(self, repo: str, issue_ref: str) -> list[dict[str, Any]]: ...

    def list_inbox_items(
        self,
        actor: str,
        labels: list[str] | None = None,
        repos: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]: ...


def _parse_allowed_repos_from_env(env: dict[str, str]) -> set[str] | None:
    configured = (env.get("PM_BOT_ALLOWED_REPOS") or "").strip()
    if not configured:
        return None
    return {repo.strip() for repo in configured.split(",") if repo.strip()}


def build_connector_from_env(
    env: dict[str, str] | None = None,
    allowed_repos: set[str] | None = None,
) -> GitHubConnector:
    env_map = os.environ if env is None else env
    connector_type = (env_map.get("PM_BOT_GITHUB_CONNECTOR") or "in_memory").strip().lower()
    env_allowed_repos = _parse_allowed_repos_from_env(env_map)
    repos = (
        DEFAULT_ALLOWED_REPOS
        if allowed_repos is None and env_allowed_repos is None
        else (env_allowed_repos if allowed_repos is None else allowed_repos)
    )

    if connector_type == "api":
        from pm_bot.control_plane.github.github_connector_api import GitHubAPIConnector

        auth = load_github_auth_from_env(env_map)
        return GitHubAPIConnector(allowed_repos=repos, auth=auth)

    from pm_bot.control_plane.github.github_connector_inmemory import InMemoryGitHubConnector

    return InMemoryGitHubConnector(allowed_repos=repos)


__all__ = [
    "DEFAULT_ALLOWED_REPOS",
    "DENIED_OPERATIONS",
    "GitHubAuth",
    "GitHubConnector",
    "PolicyDecision",
    "RetryableGitHubError",
    "WriteRequest",
    "build_connector_from_env",
]
