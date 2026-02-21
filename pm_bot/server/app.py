"""v1 orchestration application surface without external web dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_bot.server.changesets import ChangesetService
from pm_bot.server.context_pack import build_context_pack
from pm_bot.server.db import OrchestratorDB
from pm_bot.server.github_connector import GitHubConnector


class ServerApp:
    """Thin callable facade mirroring intended API endpoints."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db = OrchestratorDB(db_path)
        self.connector = GitHubConnector(
            allowed_repos={"phys-sims/.github", "phys-sims/phys-pipeline"}
        )
        self.changesets = ChangesetService(db=self.db, connector=self.connector)

    def draft(
        self, item_type: str, title: str, body_fields: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        work_item = {
            "title": title,
            "type": item_type,
            "fields": body_fields or {},
            "relationships": {"children_refs": []},
        }
        issue_ref = f"draft:{item_type}:{title.lower().replace(' ', '-')}"
        self.db.upsert_work_item(issue_ref, work_item)
        return {"issue_ref": issue_ref, "work_item": work_item}

    def link_work_items(self, parent_ref: str, child_ref: str) -> None:
        self.db.add_relationship(parent_ref=parent_ref, child_ref=child_ref)

    def propose_changeset(
        self, operation: str, repo: str, payload: dict[str, Any], target_ref: str = ""
    ) -> dict[str, Any]:
        return self.changesets.propose(
            operation=operation,
            repo=repo,
            payload=payload,
            target_ref=target_ref,
        )

    def approve_changeset(self, changeset_id: int, approved_by: str) -> dict[str, Any]:
        return self.changesets.approve(changeset_id, approved_by)

    def get_work_item(self, issue_ref: str) -> dict[str, Any] | None:
        return self.db.get_work_item(issue_ref)

    def context_pack(
        self, issue_ref: str, profile: str = "pm-drafting", budget: int = 4000
    ) -> dict[str, Any]:
        return build_context_pack(
            db=self.db, issue_ref=issue_ref, profile=profile, char_budget=budget
        )

    def fetch_issue(self, repo: str, issue_ref: str) -> dict[str, Any] | None:
        return self.connector.fetch_issue(repo=repo, issue_ref=issue_ref)

    def list_issues(self, repo: str, **filters: str) -> list[dict[str, Any]]:
        return self.connector.list_issues(repo=repo, **filters)

    def ingest_webhook(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.db.append_audit_event(
            "webhook_received",
            {"event_type": event_type, "payload": payload},
        )
        if event_type != "issues":
            return {"status": "ignored"}

        issue = payload.get("issue") or {}
        repo = (payload.get("repository") or {}).get("full_name", "")
        number = issue.get("number")
        issue_ref = f"#{number}" if number else ""
        if not repo or not issue_ref:
            return {"status": "ignored"}

        normalized = {
            "issue_ref": issue_ref,
            "title": issue.get("title", ""),
            "state": issue.get("state", "open"),
            "labels": [label.get("name", "") for label in issue.get("labels", [])],
            "area": issue.get("area", ""),
        }
        self.connector.issues[(repo, issue_ref)] = normalized
        self.db.upsert_work_item(
            f"{repo}{issue_ref}",
            {
                "title": normalized["title"],
                "type": "issue",
                "fields": normalized,
                "relationships": self.db.get_related(f"{repo}{issue_ref}"),
            },
        )
        return {"status": "ingested", "issue_ref": f"{repo}{issue_ref}"}


def create_app(db_path: str | Path = ":memory:") -> ServerApp:
    return ServerApp(db_path=db_path)
