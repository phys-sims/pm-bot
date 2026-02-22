"""v1 orchestration application surface without external web dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_bot.server.changesets import ChangesetService
from pm_bot.server.context_pack import build_context_pack
from pm_bot.server.db import OrchestratorDB
from pm_bot.server.estimator import EstimatorService
from pm_bot.server.github_connector import GitHubConnector
from pm_bot.server.graph import GraphService
from pm_bot.server.reporting import ReportingService


class ServerApp:
    """Thin callable facade mirroring intended API endpoints."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db = OrchestratorDB(db_path)
        self.connector = GitHubConnector(
            allowed_repos={"phys-sims/.github", "phys-sims/phys-pipeline"}
        )
        self.changesets = ChangesetService(db=self.db, connector=self.connector)
        self.estimator = EstimatorService(db=self.db)
        self.graph = GraphService(db=self.db)
        self.reporting = ReportingService(db=self.db)

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
        self,
        operation: str,
        repo: str,
        payload: dict[str, Any],
        target_ref: str = "",
        idempotency_key: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        return self.changesets.propose(
            operation=operation,
            repo=repo,
            payload=payload,
            target_ref=target_ref,
            idempotency_key=idempotency_key,
            run_id=run_id,
        )

    def approve_changeset(
        self, changeset_id: int, approved_by: str, run_id: str = ""
    ) -> dict[str, Any]:
        return self.changesets.approve(changeset_id, approved_by, run_id=run_id)

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

    def ingest_webhook(
        self, event_type: str, payload: dict[str, Any], run_id: str = ""
    ) -> dict[str, Any]:
        self.db.append_audit_event(
            "webhook_received",
            {"event_type": event_type, "payload": payload, "run_id": run_id},
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

    def estimator_snapshot(self) -> list[dict[str, Any]]:
        return self.estimator.build_snapshots()

    def estimate(self, item_type: str, area: str = "", size: str = "") -> dict[str, Any]:
        return self.estimator.predict({"type": item_type, "area": area, "size": size})

    def graph_tree(self, root_ref: str) -> dict[str, Any]:
        return self.graph.tree(root_ref)

    def graph_deps(self, area: str = "") -> dict[str, list[dict[str, Any]]]:
        return self.graph.dependencies(area=area)

    def generate_weekly_report(
        self, report_name: str = "weekly.md", run_id: str = ""
    ) -> dict[str, str]:
        path = self.reporting.generate_weekly_report(report_name=report_name)
        self.db.append_audit_event(
            "report_generated",
            {"report_name": report_name, "report_path": str(path), "run_id": run_id},
        )
        return {"status": "generated", "report_path": str(path)}

    def observability_metrics(self) -> list[dict[str, Any]]:
        return self.db.list_operation_metrics()


def create_app(db_path: str | Path = ":memory:") -> ServerApp:
    return ServerApp(db_path=db_path)
