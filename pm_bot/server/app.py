"""v1 orchestration application surface with a minimal ASGI HTTP layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs
from typing import Any

from pm_bot.server.changesets import ChangesetService
from pm_bot.server.context_pack import build_context_pack
from pm_bot.server.db import OrchestratorDB
from pm_bot.server.estimator import EstimatorService
from pm_bot.server.github_connector import build_connector_from_env
from pm_bot.server.graph import GraphService
from pm_bot.server.reporting import ReportingService


class ServerApp:
    """Thin callable facade mirroring intended API endpoints."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db = OrchestratorDB(db_path)
        self.connector = build_connector_from_env(
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

    def link_work_items(self, parent_ref: str, child_ref: str, source: str = "checklist") -> None:
        self.db.add_relationship(parent_ref=parent_ref, child_ref=child_ref, source=source)

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
        self._cache_issue_if_supported(repo=repo, issue_ref=issue_ref, issue=normalized)
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

    def _cache_issue_if_supported(self, repo: str, issue_ref: str, issue: dict[str, Any]) -> None:
        """Mirror webhook payload into connector-local cache when available.

        The in-memory connector keeps an `issues` map for deterministic reads in tests.
        API-backed connectors do not expose this cache and should simply skip this step.
        """

        issues_store = getattr(self.connector, "issues", None)
        if isinstance(issues_store, dict):
            issues_store[(repo, issue_ref)] = issue

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


class ASGIServer:
    """Minimal ASGI adapter exposing a safe subset of ServerApp methods."""

    def __init__(self, service: ServerApp | None = None) -> None:
        self.service = service or create_app()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._send_json(send, 500, {"error": "unsupported_scope"})
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        query_params = self._parse_query_params(scope.get("query_string", b""))
        body = await self._read_body(receive)

        try:
            if method == "GET" and path == "/health":
                await self._send_json(send, 200, {"status": "ok"})
                return

            if method == "GET" and path == "/changesets/pending":
                await self._send_json(
                    send,
                    200,
                    {
                        "items": self.service.db.list_pending_changesets(),
                        "summary": {
                            "count": len(self.service.db.list_pending_changesets()),
                        },
                    },
                )
                return

            if method == "POST" and path == "/changesets/propose":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                required = {"operation", "repo", "payload"}
                if not required.issubset(payload):
                    await self._send_json(send, 400, {"error": "missing_required_fields"})
                    return
                result = self.service.propose_changeset(
                    operation=payload["operation"],
                    repo=payload["repo"],
                    payload=payload["payload"],
                    target_ref=payload.get("target_ref", ""),
                    idempotency_key=payload.get("idempotency_key", ""),
                    run_id=payload.get("run_id", ""),
                )
                await self._send_json(send, 200, result)
                return

            if method == "POST" and path.startswith("/changesets/") and path.endswith("/approve"):
                changeset_id = self._parse_changeset_approve_path(path)
                if changeset_id is None:
                    await self._send_json(send, 404, {"error": "not_found"})
                    return
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                approved_by = str(payload.get("approved_by", "")).strip()
                if not approved_by:
                    await self._send_json(send, 400, {"error": "missing_approved_by"})
                    return
                result = self.service.approve_changeset(
                    changeset_id,
                    approved_by=approved_by,
                    run_id=str(payload.get("run_id", "")),
                )
                await self._send_json(send, 200, result)
                return

            if method == "GET" and path == "/graph/tree":
                root_ref = query_params.get("root", "")
                if not root_ref:
                    await self._send_json(send, 400, {"error": "missing_root"})
                    return
                await self._send_json(send, 200, self.service.graph_tree(root_ref=root_ref))
                return

            if method == "GET" and path == "/graph/deps":
                area = query_params.get("area", "")
                await self._send_json(send, 200, self.service.graph_deps(area=area))
                return

            if method == "GET" and path == "/estimator/snapshot":
                snapshots = self.service.estimator_snapshot()
                await self._send_json(
                    send,
                    200,
                    {
                        "items": snapshots,
                        "summary": {
                            "count": len(snapshots),
                        },
                    },
                )
                return

            if method == "GET" and path == "/reports/weekly/latest":
                latest = self.service.db.latest_report("weekly")
                if latest is None:
                    await self._send_json(send, 404, {"error": "report_not_found"})
                    return
                await self._send_json(send, 200, latest)
                return

            await self._send_json(send, 404, {"error": "not_found"})
        except PermissionError as exc:
            reason_code = "unknown"
            message = str(exc)
            prefix = "Changeset rejected by guardrails: "
            if message.startswith(prefix):
                reason_code = message[len(prefix) :]
            await self._send_json(send, 403, {"error": message, "reason_code": reason_code})
        except ValueError as exc:
            await self._send_json(send, 400, {"error": str(exc)})
        except RuntimeError as exc:
            await self._send_json(send, 409, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive response mapping
            await self._send_json(send, 500, {"error": str(exc)})

    async def _read_body(self, receive: Any) -> bytes:
        chunks: list[bytes] = []
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    def _parse_query_params(self, raw_query: bytes) -> dict[str, str]:
        if not raw_query:
            return {}
        parsed = parse_qs(raw_query.decode("utf-8"), keep_blank_values=False)
        return {key: values[-1] for key, values in parsed.items() if values}

    def _parse_changeset_approve_path(self, path: str) -> int | None:
        parts = [part for part in path.split("/") if part]
        if len(parts) != 3 or parts[0] != "changesets" or parts[2] != "approve":
            return None
        try:
            return int(parts[1])
        except ValueError:
            return None

    def _parse_json(self, body: bytes) -> dict[str, Any] | None:
        if not body:
            return {}
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    async def _send_json(self, send: Any, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


def create_app(db_path: str | Path = ":memory:") -> ServerApp:
    return ServerApp(db_path=db_path)


app = ASGIServer()


def main() -> int:
    parser = argparse.ArgumentParser(description="pm-bot ASGI server entrypoint")
    parser.add_argument(
        "--print-startup",
        action="store_true",
        help="print the supported uvicorn startup command and exit",
    )
    args = parser.parse_args()

    if args.print_startup:
        print("uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
