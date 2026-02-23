"""GitHub REST API connector implementation."""

from __future__ import annotations

from typing import Any

import requests

from pm_bot.server.github_auth import GitHubAuth
from pm_bot.server.github_connector import (
    DENIED_OPERATIONS,
    PolicyDecision,
    RetryableGitHubError,
    WriteRequest,
)


class GitHubAPIConnector:
    def __init__(
        self,
        allowed_repos: set[str] | None = None,
        auth: GitHubAuth | None = None,
        base_url: str = "https://api.github.com",
        session: requests.Session | None = None,
    ) -> None:
        self.allowed_repos = allowed_repos or set()
        self.auth = auth or GitHubAuth(read_token=None, write_token=None)
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def evaluate_write(self, repo: str, operation: str) -> PolicyDecision:
        if self.allowed_repos and repo not in self.allowed_repos:
            return PolicyDecision(allowed=False, reason_code="repo_not_allowlisted")
        if operation in DENIED_OPERATIONS:
            return PolicyDecision(allowed=False, reason_code="operation_denylisted")
        if not self.auth.write_token:
            return PolicyDecision(allowed=False, reason_code="missing_write_token")
        return PolicyDecision(allowed=True, reason_code="allowed")

    def can_write(self, repo: str, operation: str) -> bool:
        return self.evaluate_write(repo=repo, operation=operation).allowed

    def execute_write(self, request: WriteRequest) -> dict[str, Any]:
        decision = self.evaluate_write(repo=request.repo, operation=request.operation)
        if not decision.allowed:
            raise PermissionError(f"Write denied by guardrails: {decision.reason_code}")

        if request.operation == "create_issue":
            response = self._request(
                "POST",
                f"/repos/{request.repo}/issues",
                token=self.auth.write_token,
                json=request.payload,
            )
            return {
                "repo": request.repo,
                "operation": request.operation,
                "status": "applied",
                "issue": response,
            }

        if request.operation == "update_issue":
            number = _issue_number_from_ref(request.target_ref)
            response = self._request(
                "PATCH",
                f"/repos/{request.repo}/issues/{number}",
                token=self.auth.write_token,
                json=request.payload,
            )
            return {
                "repo": request.repo,
                "operation": request.operation,
                "status": "applied",
                "issue": response,
            }

        if request.operation == "link_issue":
            number = _issue_number_from_ref(request.target_ref)
            linked_issue_ref = str(request.payload.get("linked_issue_ref", "")).strip()
            relationship = str(request.payload.get("relationship", "relates_to")).strip()
            comment = f"pm-bot link ({relationship}): {linked_issue_ref}"
            response = self._request(
                "POST",
                f"/repos/{request.repo}/issues/{number}/comments",
                token=self.auth.write_token,
                json={"body": comment},
            )
            return {
                "repo": request.repo,
                "operation": request.operation,
                "status": "applied",
                "comment": response,
            }

        raise ValueError(f"Unsupported write operation: {request.operation}")

    def fetch_issue(self, repo: str, issue_ref: str) -> dict[str, Any] | None:
        number = _issue_number_from_ref(issue_ref)
        return self._request("GET", f"/repos/{repo}/issues/{number}", token=self.auth.read_token)

    def list_issues(self, repo: str, **filters: str) -> list[dict[str, Any]]:
        params = {key: value for key, value in filters.items() if value != ""}
        response = self._request(
            "GET", f"/repos/{repo}/issues", token=self.auth.read_token, params=params
        )
        if isinstance(response, list):
            return response
        return []

    def _request(
        self,
        method: str,
        path: str,
        token: str | None,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=headers,
            json=json,
            params=params,
            timeout=15,
        )

        if response.status_code in {429, 500, 502, 503, 504, 403} and _looks_like_rate_limit(
            response
        ):
            raise RetryableGitHubError(
                "GitHub API retryable failure",
                reason_code=_reason_code_for_status(response.status_code),
                retry_after_s=_parse_retry_after(response.headers.get("Retry-After")),
            )
        if response.status_code in {500, 502, 503, 504}:
            raise RetryableGitHubError(
                "GitHub API 5xx response",
                reason_code=_reason_code_for_status(response.status_code),
            )

        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


def _issue_number_from_ref(issue_ref: str) -> int:
    ref = issue_ref.strip()
    if ref.startswith("#"):
        ref = ref[1:]
    try:
        return int(ref)
    except ValueError as exc:
        raise ValueError(f"Unsupported issue ref: {issue_ref}") from exc


def _looks_like_rate_limit(response: requests.Response) -> bool:
    if response.status_code == 429:
        return True
    if response.status_code != 403:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    message = str(payload.get("message", "")).lower()
    return "rate limit" in message


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _reason_code_for_status(status: int) -> str:
    if status in {429, 403}:
        return "github_rate_limited"
    return f"github_{status}"
