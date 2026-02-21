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


def create_app(db_path: str | Path = ":memory:") -> ServerApp:
    return ServerApp(db_path=db_path)
