"""GitHub REST API connector implementation."""

from __future__ import annotations

import time
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
        cache_ttl_s: int = 30,
    ) -> None:
        self.allowed_repos = allowed_repos or set()
        self.auth = auth or GitHubAuth(read_token=None, write_token=None)
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.cache_ttl_s = max(1, int(cache_ttl_s))
        self._inbox_cache: dict[str, tuple[float, list[dict[str, Any]], dict[str, Any]]] = {}

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

    def list_sub_issues(self, repo: str, issue_ref: str) -> list[dict[str, Any]]:
        number = _issue_number_from_ref(issue_ref)
        response = self._request(
            "GET",
            f"/repos/{repo}/issues/{number}/sub_issues",
            token=self.auth.read_token,
        )
        return _normalize_graph_edge_rows(response, edge_kind="sub_issue")

    def list_issue_dependencies(self, repo: str, issue_ref: str) -> list[dict[str, Any]]:
        number = _issue_number_from_ref(issue_ref)
        response = self._request(
            "GET",
            f"/repos/{repo}/issues/{number}/dependencies",
            token=self.auth.read_token,
        )
        return _normalize_graph_edge_rows(response, edge_kind="dependency_api")

    def list_inbox_items(
        self,
        actor: str,
        labels: list[str] | None = None,
        repos: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        normalized_actor = actor.strip()
        normalized_labels = sorted({label.strip() for label in (labels or []) if label.strip()})
        normalized_repos = sorted({repo.strip() for repo in (repos or []) if repo.strip()})
        if not normalized_repos:
            normalized_repos = sorted(self.allowed_repos)

        cache_key = "|".join(
            [normalized_actor, ",".join(normalized_labels), ",".join(normalized_repos)]
        )
        now = time.time()
        cached = self._inbox_cache.get(cache_key)
        if cached and cached[0] > now:
            cached_items, cached_diag = cached[1], dict(cached[2])
            diag = dict(cached_diag)
            diag["cache"] = {"hit": True, "ttl_seconds": self.cache_ttl_s, "key": cache_key}
            return [dict(item) for item in cached_items], diag

        calls = 0
        all_rows: list[dict[str, Any]] = []
        last_headers: dict[str, Any] = {}
        chunk_size = 5
        label_chunks = [
            normalized_labels[i : i + chunk_size]
            for i in range(0, len(normalized_labels), chunk_size)
        ] or [[]]
        query_chunks: list[dict[str, Any]] = []

        for repo in normalized_repos:
            for chunk in label_chunks:
                params: dict[str, str] = {"state": "open", "per_page": "100"}
                query = f"repo:{repo}"
                if normalized_actor:
                    query = f"{query} involves:{normalized_actor}"
                if chunk:
                    labels_expr = " ".join([f"label:{label}" for label in chunk])
                    query = f"{query} {labels_expr}"
                    params["q"] = query
                query_chunks.append({"repo": repo, "labels": list(chunk), "q": query})
                rows, headers = self._request_with_headers(
                    "GET",
                    f"/repos/{repo}/issues",
                    token=self.auth.read_token,
                    params=params,
                )
                calls += 1
                last_headers = headers
                if isinstance(rows, list):
                    for row in rows:
                        normalized = self._normalize_inbox_row(
                            row=row, repo=repo, actor=normalized_actor
                        )
                        if normalized is not None:
                            all_rows.append(normalized)

        dedup: dict[str, dict[str, Any]] = {item["id"]: item for item in all_rows}
        items = sorted(
            dedup.values(),
            key=lambda item: (
                item.get("source", ""),
                item.get("item_type", ""),
                item.get("priority", ""),
                float(item.get("age_hours", 0.0)),
                item.get("repo", ""),
                item.get("id", ""),
            ),
        )
        diagnostics = {
            "cache": {"hit": False, "ttl_seconds": self.cache_ttl_s, "key": cache_key},
            "rate_limit": {
                "remaining": int(last_headers.get("X-RateLimit-Remaining", 0) or 0),
                "reset_at": str(last_headers.get("X-RateLimit-Reset", "")),
                "source": "github",
            },
            "queries": {"calls": calls, "chunks": query_chunks, "chunk_size": chunk_size},
        }
        self._inbox_cache[cache_key] = (
            now + self.cache_ttl_s,
            [dict(item) for item in items],
            dict(diagnostics),
        )
        return items, diagnostics

    def _normalize_inbox_row(self, row: Any, repo: str, actor: str) -> dict[str, Any] | None:
        if not isinstance(row, dict):
            return None
        if "pull_request" in row and row.get("state") != "open":
            return None
        issue_number = row.get("number")
        if not issue_number:
            return None
        labels = [
            str(label.get("name", "")) for label in row.get("labels", []) if isinstance(label, dict)
        ]
        is_pr = "pull_request" in row
        requested_reviewers = (
            row.get("requested_reviewers", [])
            if isinstance(row.get("requested_reviewers"), list)
            else []
        )
        actor_requested = any(
            isinstance(reviewer, dict) and str(reviewer.get("login", "")).strip() == actor
            for reviewer in requested_reviewers
        )
        item_type = "pr_review" if is_pr and actor_requested else "triage"
        action = "review" if item_type == "pr_review" else "triage"
        return {
            "source": "github",
            "item_type": item_type,
            "id": f"github:{repo}#{issue_number}",
            "title": str(row.get("title", "")),
            "repo": repo,
            "url": str(row.get("html_url", "")),
            "state": str(row.get("state", "open")),
            "priority": "",
            "age_hours": 0.0,
            "action": action,
            "requires_internal_approval": False,
            "stale": False,
            "stale_reason": "",
            "metadata": {
                "labels": labels,
                "requested_reviewer": actor if actor_requested else "",
                "query_actor": actor,
            },
        }

    def _request_with_headers(
        self,
        method: str,
        path: str,
        token: str | None,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
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
                retry_after_s=_parse_retry_after((response.headers or {}).get("Retry-After")),
            )
        if response.status_code in {500, 502, 503, 504}:
            raise RetryableGitHubError(
                "GitHub API 5xx response",
                reason_code=_reason_code_for_status(response.status_code),
            )

        response.raise_for_status()
        if not response.content:
            return {}, dict(response.headers or {})
        return response.json(), dict(response.headers or {})

    def _request(
        self,
        method: str,
        path: str,
        token: str | None,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        payload, _headers = self._request_with_headers(
            method=method,
            path=path,
            token=token,
            json=json,
            params=params,
        )
        return payload


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


def _normalize_graph_edge_rows(response: Any, edge_kind: str) -> list[dict[str, Any]]:
    if not isinstance(response, list):
        return []
    normalized: list[dict[str, Any]] = []
    for row in response:
        if not isinstance(row, dict):
            continue
        issue_ref = row.get("issue_ref") or row.get("number")
        if isinstance(issue_ref, int):
            issue_ref = f"#{issue_ref}"
        if not issue_ref:
            continue
        normalized.append(
            {
                "issue_ref": str(issue_ref),
                "source": edge_kind,
                "observed_at": str(row.get("observed_at", "")),
            }
        )
    normalized.sort(key=lambda item: item["issue_ref"])
    return normalized
