"""Repository registry and incremental GitHub cache sync service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from pm_bot.control_plane.db.db import OrchestratorDB
from pm_bot.control_plane.github.github_connector import GitHubConnector


@dataclass(frozen=True)
class SyncResult:
    repo_id: int
    full_name: str
    issues_upserted: int
    prs_upserted: int
    last_sync_at: str


class GitHubCacheSyncService:
    def __init__(
        self,
        *,
        db: OrchestratorDB,
        connector: GitHubConnector,
    ) -> None:
        self.db = db
        self.connector = connector

    def add_repo(self, *, full_name: str, since_days: int | None = None) -> dict[str, Any]:
        normalized_full_name = full_name.strip()
        if not normalized_full_name or "/" not in normalized_full_name:
            raise ValueError("invalid_full_name")

        repo = self.db.add_repo_registry_entry(full_name=normalized_full_name)
        self.sync_repo(repo_id=int(repo["id"]), initial_import=True, since_days=since_days)
        refreshed = self.db.get_repo_registry_entry(int(repo["id"]))
        if refreshed is None:
            raise RuntimeError("repo_registry_missing_after_add")
        return refreshed

    def sync_repo(
        self,
        *,
        repo_id: int,
        initial_import: bool = False,
        since_days: int | None = None,
    ) -> SyncResult:
        repo = self.db.get_repo_registry_entry(repo_id)
        if repo is None:
            raise ValueError("repo_not_found")

        cursor = self.db.get_sync_cursor(repo_id)
        now_iso = _utc_now_iso()

        if initial_import:
            issues_filters: dict[str, str] = {"state": "open", "per_page": "100"}
            prs_filters: dict[str, str] = {"state": "open", "per_page": "100", "sort": "updated"}
            if since_days is not None and since_days >= 0:
                since_iso = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
                issues_filters["since"] = since_iso
                prs_filters["sort"] = "updated"
                prs_filters["direction"] = "desc"
        else:
            issues_filters = {"state": "all", "per_page": "100"}
            prs_filters = {"state": "all", "per_page": "100", "sort": "updated"}
            if cursor and cursor.get("last_issues_sync"):
                issues_filters["since"] = str(cursor["last_issues_sync"])
            if cursor and cursor.get("last_prs_sync"):
                prs_filters["since"] = str(cursor["last_prs_sync"])

        issues_upserted = 0
        prs_upserted = 0
        try:
            issue_rows = self.connector.list_issues(repo["full_name"], **issues_filters)
            for issue in issue_rows:
                if not isinstance(issue, dict) or issue.get("pull_request"):
                    continue
                number = _coerce_number(issue.get("number"))
                if number is None:
                    continue
                self.db.upsert_issue_cache(
                    repo_id=repo_id,
                    issue_number=number,
                    state=str(issue.get("state", "")),
                    title=str(issue.get("title", "")),
                    updated_at=str(issue.get("updated_at", "")) or now_iso,
                    raw_json=issue,
                )
                issues_upserted += 1

            pr_rows = self.connector.list_pull_requests(repo["full_name"], **prs_filters)
            for pr in pr_rows:
                if not isinstance(pr, dict):
                    continue
                number = _coerce_number(pr.get("number"))
                if number is None:
                    continue
                self.db.upsert_pr_cache(
                    repo_id=repo_id,
                    pr_number=number,
                    state=str(pr.get("state", "")),
                    title=str(pr.get("title", "")),
                    updated_at=str(pr.get("updated_at", "")) or now_iso,
                    raw_json=pr,
                )
                prs_upserted += 1

            self.db.upsert_sync_cursor(
                repo_id=repo_id,
                last_issues_sync=now_iso,
                last_prs_sync=now_iso,
                issues_etag=None,
                prs_etag=None,
            )
            self.db.update_repo_registry_sync_status(
                repo_id=repo_id, last_sync_at=now_iso, last_error=""
            )
        except Exception as exc:
            self.db.update_repo_registry_sync_status(
                repo_id=repo_id, last_sync_at=repo.get("last_sync_at", ""), last_error=str(exc)
            )
            raise

        return SyncResult(
            repo_id=repo_id,
            full_name=repo["full_name"],
            issues_upserted=issues_upserted,
            prs_upserted=prs_upserted,
            last_sync_at=now_iso,
        )

    def refresh_all_repos(self) -> list[SyncResult]:
        results: list[SyncResult] = []
        for repo in self.db.list_repo_registry_entries():
            results.append(self.sync_repo(repo_id=int(repo["id"]), initial_import=False))
        return results


def _coerce_number(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
