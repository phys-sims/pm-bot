"""v1 orchestration application surface with a minimal ASGI HTTP layer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from urllib.parse import parse_qs
from typing import Any

from pm_bot.server.changesets import ChangesetService
from pm_bot.server.context_pack import build_context_pack
from pm_bot.server.db import OrchestratorDB
from pm_bot.server.estimator import EstimatorService
from pm_bot.server.github_auth import (
    load_tenant_context_from_env,
    validate_org_and_installation_context,
)
from pm_bot.server.github_connector import build_connector_from_env
from pm_bot.server.graph import GraphService
from pm_bot.server.llm.capabilities import REPORT_IR_DRAFT
from pm_bot.server.llm.service import CapabilityOutputValidationError, run_capability
from pm_bot.server.reporting import ReportingService
from pm_bot.server.report_ir_intake import (
    build_changeset_preview,
    validate_report_ir,
)
from pm_bot.server.runner import RunnerService
from pm_bot.server.runner_adapters import (
    build_runner_adapters_from_env,
    default_runner_adapter_name,
)


class ServerApp:
    """Thin callable facade mirroring intended API endpoints."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db = OrchestratorDB(db_path)
        self.tenant = load_tenant_context_from_env(os.environ)
        self.connector = build_connector_from_env()
        self.changesets = ChangesetService(db=self.db, connector=self.connector)
        self.estimator = EstimatorService(db=self.db)
        self.graph = GraphService(db=self.db)
        self.reporting = ReportingService(db=self.db)
        self._sync_onboarding_readiness()
        runner_adapters = build_runner_adapters_from_env(os.environ)
        self.runner = RunnerService(
            db=self.db,
            adapters=runner_adapters,
            default_adapter_name=default_runner_adapter_name(
                os.environ,
                adapters=runner_adapters,
            ),
        )

    def _request_tenant_context(
        self,
        repo: str,
        org: str = "",
        installation_id: str = "",
    ) -> dict[str, str]:
        return {
            "tenant_mode": self.tenant.tenant_mode or "single_tenant",
            "org": org.strip() or (repo.split("/", 1)[0].strip() if "/" in repo else ""),
            "installation_id": installation_id.strip(),
        }

    def _sync_onboarding_readiness(self) -> dict[str, Any]:
        readiness = self.onboarding_dry_run()
        return self.db.set_onboarding_state(readiness["readiness_state"])

    def onboarding_readiness(self) -> dict[str, Any]:
        return self.db.get_onboarding_state()

    def onboarding_dry_run(self) -> dict[str, Any]:
        if not self.tenant.org.strip():
            return {
                "readiness_state": "pending_context",
                "reason_code": "missing_org_context",
                "checks": {
                    "org": False,
                    "installation": not bool(self.tenant.installation_id.strip()),
                },
            }
        if not self.tenant.installation_id.strip():
            return {
                "readiness_state": "single_tenant_ready",
                "reason_code": "single_tenant_mode",
                "checks": {"org": True, "installation": False},
            }
        return {
            "readiness_state": "org_ready",
            "reason_code": "org_installation_ready",
            "checks": {"org": True, "installation": True},
        }

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
        tenant_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resolved_tenant_context = tenant_context or self._request_tenant_context(repo=repo)
        return self.changesets.propose(
            operation=operation,
            repo=repo,
            payload=payload,
            target_ref=target_ref,
            idempotency_key=idempotency_key,
            run_id=run_id,
            tenant_context=resolved_tenant_context,
        )

    def approve_changeset(
        self,
        changeset_id: int,
        approved_by: str,
        run_id: str = "",
        tenant_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.changesets.approve(
            changeset_id,
            approved_by,
            run_id=run_id,
            tenant_context=tenant_context,
        )

    def get_work_item(self, issue_ref: str) -> dict[str, Any] | None:
        return self.db.get_work_item(issue_ref)

    def context_pack(
        self,
        issue_ref: str,
        profile: str = "pm-drafting",
        budget: int = 4000,
        run_id: str = "",
        requested_by: str = "",
        schema_version: str = "context_pack/v2",
    ) -> dict[str, Any]:
        pack = build_context_pack(
            db=self.db,
            issue_ref=issue_ref,
            profile=profile,
            char_budget=budget,
            schema_version=schema_version,
        )
        tenant_context = self._request_tenant_context(
            repo=issue_ref.split("#", 1)[0] if "#" in issue_ref else ""
        )
        self.db.append_audit_event(
            "context_pack_built",
            {
                "issue_ref": issue_ref,
                "profile": profile,
                "schema_version": pack.get("schema_version", schema_version),
                "hash": pack.get("hash", ""),
                "budget": pack.get("budget", {"max_chars": budget, "used_chars": None}),
                "run_id": run_id,
                "requested_by": requested_by,
            },
            tenant_context=tenant_context,
        )
        return pack

    def fetch_issue(self, repo: str, issue_ref: str) -> dict[str, Any] | None:
        return self.connector.fetch_issue(repo=repo, issue_ref=issue_ref)

    def list_issues(self, repo: str, **filters: str) -> list[dict[str, Any]]:
        return self.connector.list_issues(repo=repo, **filters)

    def ingest_webhook(
        self, event_type: str, payload: dict[str, Any], run_id: str = ""
    ) -> dict[str, Any]:
        repo = str((payload.get("repository") or {}).get("full_name", "")).strip()
        tenant_context = self._request_tenant_context(
            repo=repo,
            org=str(payload.get("org", "")),
            installation_id=str(payload.get("installation_id", "")),
        )
        self.db.append_audit_event(
            "webhook_received",
            {"event_type": event_type, "payload": payload, "run_id": run_id},
            tenant_context=tenant_context,
        )
        if event_type != "issues":
            return {"status": "ignored"}

        issue = payload.get("issue") or {}
        repo = repo or (payload.get("repository") or {}).get("full_name", "")
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

    def ingest_graph(self, repo: str) -> dict[str, Any]:
        return self.graph.ingest_repo_graph(repo=repo, connector=self.connector)

    def generate_weekly_report(
        self, report_name: str = "weekly.md", run_id: str = ""
    ) -> dict[str, str]:
        path = self.reporting.generate_weekly_report(report_name=report_name)
        self.db.append_audit_event(
            "report_generated",
            {"report_name": report_name, "report_path": str(path), "run_id": run_id},
            tenant_context=self._request_tenant_context(repo=""),
        )
        return {"status": "generated", "report_path": str(path)}

    def propose_agent_run(self, spec: dict[str, Any], created_by: str) -> dict[str, Any]:
        return self.runner.create_run(spec=spec, created_by=created_by)

    def transition_agent_run(
        self,
        run_id: str,
        to_status: str,
        reason_code: str,
        actor: str = "",
    ) -> dict[str, Any]:
        return self.runner.transition(
            run_id=run_id, to_status=to_status, reason_code=reason_code, actor=actor
        )

    def claim_agent_runs(
        self, worker_id: str, limit: int = 1, lease_seconds: int = 30
    ) -> list[dict[str, Any]]:
        return self.runner.claim_ready_runs(
            worker_id=worker_id, limit=limit, lease_seconds=lease_seconds
        )

    def execute_claimed_agent_run(self, run_id: str, worker_id: str) -> dict[str, Any]:
        return self.runner.execute_claimed_run(run_id=run_id, worker_id=worker_id)

    def cancel_agent_run(self, run_id: str, actor: str = "") -> dict[str, Any]:
        return self.runner.cancel(run_id=run_id, actor=actor)

    def list_agent_run_transitions(self, run_id: str) -> list[dict[str, Any]]:
        return self.db.list_agent_run_transitions(run_id=run_id)

    def intake_natural_text(
        self,
        natural_text: str,
        org: str,
        repos: list[str],
        run_id: str = "",
        requested_by: str = "",
        generated_at: str = "",
        mode: str = "basic",
    ) -> dict[str, Any]:
        capability_result = run_capability(
            REPORT_IR_DRAFT,
            input_payload={
                "natural_text": natural_text,
                "org": org,
                "repos": repos,
                "generated_at": generated_at,
                "mode": mode,
            },
            context={"provider": "local", "run_id": run_id, "requested_by": requested_by},
            policy={"allow_external_llm": False},
        )
        draft = capability_result.get("output", {}).get("draft")
        if not isinstance(draft, dict):
            raise RuntimeError("invalid_capability_output")
        validation = validate_report_ir(draft)
        draft_id = draft.get("report", {}).get("source", {}).get("prompt_hash", "")
        self.db.append_audit_event(
            "report_ir_draft_generated",
            {
                "run_id": run_id,
                "requested_by": requested_by,
                "draft_id": draft_id,
                "llm_metadata": {
                    "capability_id": capability_result.get("capability_id", ""),
                    "prompt_version": capability_result.get("prompt_version", ""),
                    "model": capability_result.get("model", ""),
                    "provider": capability_result.get("provider", ""),
                    "model_provider": (
                        f"{capability_result.get('provider', '')}:{capability_result.get('model', '')}"
                    ).strip(":"),
                    "input_hash": capability_result.get("input_hash", ""),
                    "schema_version": capability_result.get("schema_version", ""),
                    "run_id": capability_result.get("run_id", run_id),
                },
                "input": {"natural_text": natural_text, "mode": mode},
                "validation": validation,
            },
            tenant_context=self._request_tenant_context(repo=repos[0] if repos else "", org=org),
        )
        return {
            "draft_id": draft_id,
            "schema_version": "report_ir_draft/v1",
            "draft": draft,
            "validation": validation,
        }

    def confirm_report_ir(
        self,
        report_ir: dict[str, Any],
        confirmed_by: str,
        run_id: str = "",
        draft: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        validation = validate_report_ir(report_ir)
        if validation["errors"]:
            raise ValueError("report_ir_validation_failed")
        report = report_ir.get("report") or {}
        scope = report.get("scope") or {}
        repos = [str(repo).strip() for repo in (scope.get("repos") or []) if str(repo).strip()]
        confirmation_id = (
            f"confirm-{str(report.get('generated_at', '')).strip()}-"
            f"{str(report.get('title', '')).strip().lower().replace(' ', '-')[:24]}"
        ).strip("-")
        self.db.append_audit_event(
            "report_ir_confirmed",
            {
                "run_id": run_id,
                "confirmed_by": confirmed_by,
                "confirmation_id": confirmation_id,
                "draft": draft or {},
                "confirmed": report_ir,
            },
            tenant_context=self._request_tenant_context(
                repo=repos[0] if repos else "",
                org=str(scope.get("org", "")),
            ),
        )
        return {
            "status": "confirmed",
            "confirmation_id": confirmation_id,
            "validation": validation,
            "report_ir": report_ir,
        }

    def preview_report_ir_changesets(
        self, report_ir: dict[str, Any], run_id: str = ""
    ) -> dict[str, Any]:
        validation = validate_report_ir(report_ir)
        if validation["errors"]:
            raise ValueError("report_ir_validation_failed")
        preview = build_changeset_preview(report_ir)
        report = report_ir.get("report") or {}
        scope = report.get("scope") or {}
        repos = [str(repo).strip() for repo in (scope.get("repos") or []) if str(repo).strip()]
        self.db.append_audit_event(
            "report_ir_preview_generated",
            {
                "run_id": run_id,
                "summary": preview["summary"],
            },
            tenant_context=self._request_tenant_context(
                repo=repos[0] if repos else "",
                org=str(scope.get("org", "")),
            ),
        )
        return preview

    def propose_report_ir_changesets(
        self,
        report_ir: dict[str, Any],
        run_id: str,
        requested_by: str,
    ) -> dict[str, Any]:
        preview = self.preview_report_ir_changesets(report_ir=report_ir, run_id=run_id)
        items: list[dict[str, Any]] = []
        for item in preview["items"]:
            proposed = self.propose_changeset(
                operation=item["operation"],
                repo=item["repo"],
                payload=item["payload"],
                target_ref=item.get("target_ref", ""),
                idempotency_key=item["idempotency_key"],
                run_id=run_id,
                tenant_context=self._request_tenant_context(repo=item["repo"]),
            )
            items.append(
                {
                    "stable_id": item["stable_id"],
                    "repo": item["repo"],
                    "idempotency_key": item["idempotency_key"],
                    "changeset": proposed,
                }
            )
        self.db.append_audit_event(
            "report_ir_changesets_proposed",
            {
                "run_id": run_id,
                "requested_by": requested_by,
                "count": len(items),
                "changeset_ids": [row["changeset"]["id"] for row in items],
            },
            tenant_context=self._request_tenant_context(repo=items[0]["repo"] if items else ""),
        )
        return {
            "schema_version": "report_ir_proposal/v1",
            "items": items,
            "summary": {"count": len(items)},
        }

    def observability_metrics(self) -> list[dict[str, Any]]:
        return self.db.list_operation_metrics()

    def unified_inbox(
        self, actor: str, labels: list[str] | None = None, repos: list[str] | None = None
    ) -> dict[str, Any]:
        pending = self.db.list_pending_changesets()
        internal_items: list[dict[str, Any]] = []
        for row in pending:
            internal_items.append(
                {
                    "source": "pm_bot",
                    "item_type": "approval",
                    "id": f"changeset:{row['id']}",
                    "title": f"Approve {row['operation']} for {row['repo']}",
                    "repo": row["repo"],
                    "url": "",
                    "state": row.get("status", "pending"),
                    "priority": "",
                    "age_hours": 0.0,
                    "action": "approve",
                    "requires_internal_approval": True,
                    "stale": False,
                    "stale_reason": "",
                    "metadata": {
                        "changeset_id": row["id"],
                        "operation": row["operation"],
                        "target_ref": row.get("target_ref", ""),
                    },
                }
            )

        github_items, diagnostics = self.connector.list_inbox_items(
            actor=actor, labels=labels or [], repos=repos or []
        )

        items = sorted(
            [*internal_items, *github_items],
            key=lambda item: (
                0 if item["source"] == "pm_bot" else 1,
                item.get("item_type", ""),
                item.get("priority", ""),
                float(item.get("age_hours", 0.0)),
                item.get("repo", ""),
                item.get("id", ""),
            ),
        )

        return {
            "schema_version": "inbox/v1",
            "items": items,
            "diagnostics": diagnostics,
            "summary": {
                "count": len(items),
                "pm_bot_count": len(internal_items),
                "github_count": len(github_items),
            },
        }

    def audit_chain(
        self,
        *,
        run_id: str = "",
        event_type: str = "",
        repo: str = "",
        actor: str = "",
        start_at: str = "",
        end_at: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        base = self.db.list_audit_events(
            event_type=event_type.strip() or None,
            run_id=run_id.strip() or None,
        )

        normalized_repo = repo.strip().lower()
        normalized_actor = actor.strip().lower()

        def _iso(value: str) -> datetime | None:
            if not value.strip():
                return None
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None

        start_dt = _iso(start_at)
        end_dt = _iso(end_at)

        filtered: list[dict[str, Any]] = []
        for item in base:
            payload = item.get("payload", {}) if isinstance(item.get("payload"), dict) else {}
            payload_repo = str(payload.get("repo", payload.get("target_repo", ""))).strip().lower()
            payload_actor = (
                str(
                    payload.get(
                        "actor",
                        payload.get(
                            "approved_by",
                            payload.get("requested_by", payload.get("created_by", "")),
                        ),
                    )
                )
                .strip()
                .lower()
            )

            if normalized_repo and payload_repo != normalized_repo:
                continue
            if normalized_actor and payload_actor != normalized_actor:
                continue

            created_at = str(item.get("created_at", ""))
            created_dt = _iso(created_at)
            if start_dt and created_dt and created_dt < start_dt:
                continue
            if end_dt and created_dt and created_dt > end_dt:
                continue

            filtered.append(item)

        filtered.sort(key=lambda row: int(row["id"]))
        bounded_limit = max(1, min(limit, 500))
        bounded_offset = max(0, offset)
        page = filtered[bounded_offset : bounded_offset + bounded_limit]
        next_offset = (
            bounded_offset + bounded_limit
            if bounded_offset + bounded_limit < len(filtered)
            else None
        )

        return {
            "schema_version": "audit_chain/v1",
            "items": page,
            "summary": {
                "count": len(page),
                "total": len(filtered),
                "next_offset": next_offset,
                "filters": {
                    "run_id": run_id,
                    "event_type": event_type,
                    "repo": repo,
                    "actor": actor,
                    "start_at": start_at,
                    "end_at": end_at,
                },
            },
        }

    def audit_rollups(self, *, run_id: str = "") -> dict[str, Any]:
        events = self.db.list_audit_events(run_id=run_id.strip() or None)
        total = len(events)
        completed = len([e for e in events if e["event_type"] == "agent_run_completed"])
        retried = len([e for e in events if e["event_type"] == "agent_run_retry_scheduled"])
        dead_lettered = len(
            [
                e
                for e in events
                if e["event_type"] in {"agent_run_dead_lettered", "changeset_dead_lettered"}
            ]
        )
        denied = len([e for e in events if "denied" in str(e["event_type"])])

        reason_counts: dict[str, int] = {}
        repo_counts: dict[str, int] = {}
        queue_ages: list[float] = []
        capability_counts: dict[str, int] = {}
        prompt_versions: dict[str, int] = {}

        for event in events:
            payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            reason = str(payload.get("reason_code", "")).strip()
            repo = str(payload.get("repo", payload.get("target_repo", ""))).strip()
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            if repo:
                repo_counts[repo] = repo_counts.get(repo, 0) + 1
            llm_metadata = payload.get("llm_metadata", {}) if isinstance(payload, dict) else {}
            if isinstance(llm_metadata, dict):
                capability_id = str(llm_metadata.get("capability_id", "")).strip()
                prompt_version = str(llm_metadata.get("prompt_version", "")).strip()
                if capability_id:
                    capability_counts[capability_id] = capability_counts.get(capability_id, 0) + 1
                if capability_id and prompt_version:
                    key = f"{capability_id}:{prompt_version}"
                    prompt_versions[key] = prompt_versions.get(key, 0) + 1

            if "queue_age_seconds" in payload:
                try:
                    queue_ages.append(float(payload.get("queue_age_seconds", 0.0)))
                except (TypeError, ValueError):
                    pass

        return {
            "schema_version": "audit_rollups/v1",
            "summary": {
                "sample_size": total,
                "completion_rate": round((completed / total), 4) if total else 0.0,
                "retry_count": retried,
                "dead_letter_count": dead_lettered,
                "denial_count": denied,
                "average_queue_age_seconds": round(sum(queue_ages) / len(queue_ages), 2)
                if queue_ages
                else 0.0,
            },
            "top_reason_codes": [
                {"reason_code": reason, "count": count}
                for reason, count in sorted(
                    reason_counts.items(), key=lambda item: (-item[1], item[0])
                )[:5]
            ],
            "repo_concentration": [
                {"repo": repo_name, "count": count}
                for repo_name, count in sorted(
                    repo_counts.items(), key=lambda item: (-item[1], item[0])
                )[:5]
            ],
            "capability_concentration": [
                {"capability_id": capability_id, "count": count}
                for capability_id, count in sorted(
                    capability_counts.items(), key=lambda item: (-item[1], item[0])
                )[:5]
            ],
            "prompt_version_concentration": [
                {"capability_prompt": capability_prompt, "count": count}
                for capability_prompt, count in sorted(
                    prompt_versions.items(), key=lambda item: (-item[1], item[0])
                )[:5]
            ],
        }

    def export_incident_bundle(self, *, run_id: str = "", actor: str = "") -> dict[str, Any]:
        chain = self.audit_chain(run_id=run_id, actor=actor, limit=500, offset=0)
        rollups = self.audit_rollups(run_id=run_id)
        hooks = {
            "retry_storm": "docs/runbooks/first-human-test.md",
            "denial_spike": "docs/runbooks/first-human-test.md",
            "webhook_drift": "docs/runbooks/first-human-test.md",
        }
        return {
            "schema_version": "incident_bundle/v1",
            "export": {
                "run_id": run_id,
                "actor": actor,
                "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            "runbook_hooks": hooks,
            "chain": chain,
            "rollups": rollups,
        }


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

            if method == "GET" and path == "/inbox":
                labels = [
                    value.strip()
                    for value in query_params.get("labels", "").split(",")
                    if value.strip()
                ]
                repos = [
                    value.strip()
                    for value in query_params.get("repos", "").split(",")
                    if value.strip()
                ]
                await self._send_json(
                    send,
                    200,
                    self.service.unified_inbox(
                        actor=query_params.get("actor", ""),
                        labels=labels,
                        repos=repos,
                    ),
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
                ok, tenant_context = await self._validate_request_context(
                    send,
                    repo=str(payload.get("repo", "")),
                    payload=payload,
                    query_params=query_params,
                )
                if not ok:
                    return
                result = self.service.propose_changeset(
                    operation=payload["operation"],
                    repo=payload["repo"],
                    payload=payload["payload"],
                    target_ref=payload.get("target_ref", ""),
                    idempotency_key=payload.get("idempotency_key", ""),
                    run_id=payload.get("run_id", ""),
                    tenant_context=tenant_context,
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
                changeset = self.service.db.get_changeset(changeset_id)
                if changeset is None:
                    await self._send_json(send, 404, {"error": "not_found"})
                    return
                ok, tenant_context = await self._validate_request_context(
                    send,
                    repo=str(changeset.get("repo", "")),
                    payload=payload,
                    query_params=query_params,
                )
                if not ok:
                    return
                result = self.service.approve_changeset(
                    changeset_id,
                    approved_by=approved_by,
                    run_id=str(payload.get("run_id", "")),
                    tenant_context=tenant_context,
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

            if method == "POST" and path == "/graph/ingest":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                repo = str(payload.get("repo", "")).strip()
                if not repo:
                    await self._send_json(send, 400, {"error": "missing_repo"})
                    return
                ok, _tenant_context = await self._validate_request_context(
                    send, repo=repo, payload=payload, query_params=query_params
                )
                if not ok:
                    return
                await self._send_json(send, 200, self.service.ingest_graph(repo=repo))
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

            if method == "GET" and path == "/context-pack":
                issue_ref = query_params.get("issue_ref", "")
                if not issue_ref:
                    await self._send_json(send, 400, {"error": "missing_issue_ref"})
                    return
                budget = int(query_params.get("budget", "4000"))
                result = self.service.context_pack(
                    issue_ref=issue_ref,
                    profile=query_params.get("profile", "pm-drafting"),
                    budget=budget,
                    schema_version=query_params.get("schema_version", "context_pack/v2"),
                    run_id=query_params.get("run_id", ""),
                    requested_by=query_params.get("requested_by", ""),
                )
                await self._send_json(send, 200, result)
                return

            if method == "POST" and path == "/agent-runs/propose":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                spec = payload.get("spec")
                if not isinstance(spec, dict):
                    await self._send_json(send, 400, {"error": "missing_spec"})
                    return
                created_by = str(payload.get("created_by", "")).strip()
                if not created_by:
                    await self._send_json(send, 400, {"error": "missing_created_by"})
                    return
                await self._send_json(
                    send, 200, self.service.propose_agent_run(spec=spec, created_by=created_by)
                )
                return

            if method == "POST" and path == "/agent-runs/transition":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                run_id = str(payload.get("run_id", "")).strip()
                to_status = str(payload.get("to_status", "")).strip()
                reason_code = str(payload.get("reason_code", "")).strip() or "status_updated"
                if not run_id or not to_status:
                    await self._send_json(send, 400, {"error": "missing_required_fields"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.transition_agent_run(
                        run_id=run_id,
                        to_status=to_status,
                        reason_code=reason_code,
                        actor=str(payload.get("actor", "")),
                    ),
                )
                return

            if method == "POST" and path == "/agent-runs/claim":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                worker_id = str(payload.get("worker_id", "")).strip()
                if not worker_id:
                    await self._send_json(send, 400, {"error": "missing_worker_id"})
                    return
                items = self.service.claim_agent_runs(
                    worker_id=worker_id,
                    limit=int(payload.get("limit", 1)),
                    lease_seconds=int(payload.get("lease_seconds", 30)),
                )
                await self._send_json(send, 200, {"items": items, "summary": {"count": len(items)}})
                return

            if method == "POST" and path == "/agent-runs/execute":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                run_id = str(payload.get("run_id", "")).strip()
                worker_id = str(payload.get("worker_id", "")).strip()
                if not run_id or not worker_id:
                    await self._send_json(send, 400, {"error": "missing_required_fields"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.execute_claimed_agent_run(run_id=run_id, worker_id=worker_id),
                )
                return

            if method == "GET" and path == "/onboarding/readiness":
                await self._send_json(send, 200, self.service.onboarding_readiness())
                return

            if method == "POST" and path == "/onboarding/dry-run":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                await self._send_json(send, 200, self.service.onboarding_dry_run())
                return

            if method == "GET" and path == "/audit/chain":
                raw_limit = query_params.get("limit", "100").strip()
                raw_offset = query_params.get("offset", "0").strip()
                try:
                    limit = int(raw_limit)
                    offset = int(raw_offset)
                except ValueError:
                    await self._send_json(send, 400, {"error": "invalid_pagination"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.audit_chain(
                        run_id=query_params.get("run_id", "").strip(),
                        event_type=query_params.get("event_type", "").strip(),
                        repo=query_params.get("repo", "").strip(),
                        actor=query_params.get("actor", "").strip(),
                        start_at=query_params.get("start_at", "").strip(),
                        end_at=query_params.get("end_at", "").strip(),
                        limit=limit,
                        offset=offset,
                    ),
                )
                return

            if method == "GET" and path == "/audit/rollups":
                await self._send_json(
                    send,
                    200,
                    self.service.audit_rollups(run_id=query_params.get("run_id", "").strip()),
                )
                return

            if method == "GET" and path == "/audit/incident-bundle":
                await self._send_json(
                    send,
                    200,
                    self.service.export_incident_bundle(
                        run_id=query_params.get("run_id", "").strip(),
                        actor=query_params.get("actor", "").strip(),
                    ),
                )
                return

            if method == "GET" and path == "/agent-runs/transitions":
                run_id = query_params.get("run_id", "").strip()
                if not run_id:
                    await self._send_json(send, 400, {"error": "missing_run_id"})
                    return
                items = self.service.list_agent_run_transitions(run_id=run_id)
                await self._send_json(
                    send,
                    200,
                    {"items": items, "summary": {"count": len(items)}},
                )
                return

            if method == "POST" and path == "/agent-runs/cancel":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                run_id = str(payload.get("run_id", "")).strip()
                if not run_id:
                    await self._send_json(send, 400, {"error": "missing_run_id"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.cancel_agent_run(
                        run_id=run_id, actor=str(payload.get("actor", ""))
                    ),
                )
                return

            if method == "POST" and path == "/report-ir/intake":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                natural_text = str(payload.get("natural_text", "")).strip()
                org = str(payload.get("org", "")).strip()
                repos = [
                    str(repo).strip() for repo in payload.get("repos", []) if str(repo).strip()
                ]
                if not natural_text or not org:
                    await self._send_json(send, 400, {"error": "missing_required_fields"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.intake_natural_text(
                        natural_text=natural_text,
                        org=org,
                        repos=repos,
                        run_id=str(payload.get("run_id", "")).strip(),
                        requested_by=str(payload.get("requested_by", "")).strip(),
                        generated_at=str(payload.get("generated_at", "")).strip(),
                        mode=str(payload.get("mode", "basic")).strip() or "basic",
                    ),
                )
                return

            if method == "POST" and path == "/report-ir/confirm":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                report_ir = payload.get("report_ir")
                confirmed_by = str(payload.get("confirmed_by", "")).strip()
                if not isinstance(report_ir, dict) or not confirmed_by:
                    await self._send_json(send, 400, {"error": "missing_required_fields"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.confirm_report_ir(
                        report_ir=report_ir,
                        confirmed_by=confirmed_by,
                        run_id=str(payload.get("run_id", "")).strip(),
                        draft=payload.get("draft")
                        if isinstance(payload.get("draft"), dict)
                        else None,
                    ),
                )
                return

            if method == "POST" and path == "/report-ir/preview":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                report_ir = payload.get("report_ir")
                if not isinstance(report_ir, dict):
                    await self._send_json(send, 400, {"error": "missing_report_ir"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.preview_report_ir_changesets(
                        report_ir=report_ir,
                        run_id=str(payload.get("run_id", "")).strip(),
                    ),
                )
                return

            if method == "POST" and path == "/report-ir/propose":
                payload = self._parse_json(body)
                if payload is None:
                    await self._send_json(send, 400, {"error": "invalid_json"})
                    return
                report_ir = payload.get("report_ir")
                run_id = str(payload.get("run_id", "")).strip()
                requested_by = str(payload.get("requested_by", "")).strip()
                if not isinstance(report_ir, dict) or not run_id or not requested_by:
                    await self._send_json(send, 400, {"error": "missing_required_fields"})
                    return
                await self._send_json(
                    send,
                    200,
                    self.service.propose_report_ir_changesets(
                        report_ir=report_ir,
                        run_id=run_id,
                        requested_by=requested_by,
                    ),
                )
                return

            await self._send_json(send, 404, {"error": "not_found"})
        except PermissionError as exc:
            reason_code = "unknown"
            message = str(exc)
            prefix = "Changeset rejected by guardrails: "
            if message.startswith(prefix):
                reason_code = message[len(prefix) :]
            await self._send_json(send, 403, {"error": message, "reason_code": reason_code})
        except CapabilityOutputValidationError as exc:
            await self._send_json(send, 400, exc.as_dict())
        except ValueError as exc:
            await self._send_json(send, 400, {"error": str(exc)})
        except RuntimeError as exc:
            await self._send_json(send, 409, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive response mapping
            await self._send_json(send, 500, {"error": str(exc)})

    def _extract_request_context(
        self, payload: dict[str, Any], query_params: dict[str, str]
    ) -> tuple[str, str]:
        org = str(payload.get("org", "") or query_params.get("org", "")).strip()
        installation_id = str(
            payload.get("installation_id", "") or query_params.get("installation_id", "")
        ).strip()
        return org, installation_id

    async def _validate_request_context(
        self,
        send: Any,
        *,
        repo: str,
        payload: dict[str, Any],
        query_params: dict[str, str],
    ) -> tuple[bool, dict[str, str]]:
        org, installation_id = self._extract_request_context(payload, query_params)
        tenant_context = self.service._request_tenant_context(
            repo=repo, org=org, installation_id=installation_id
        )
        allowed, reason_code = validate_org_and_installation_context(
            tenant=self.service.tenant,
            repo=repo,
            request_org=org,
            request_installation_id=installation_id,
        )
        if allowed:
            return True, tenant_context
        self.service.db.append_audit_event(
            "auth_context_denied",
            {"repo": repo, "reason_code": reason_code},
            tenant_context=tenant_context,
        )
        await self._send_json(
            send,
            403,
            {"error": "request_context_denied", "reason_code": reason_code},
        )
        return False, tenant_context

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
