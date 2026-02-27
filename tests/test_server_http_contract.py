import asyncio
import json
import subprocess
import pytest
import sys

import pm_bot.server.app as app_module
from pm_bot.server.app import ASGIServer, ServerApp


def _asgi_request(
    app: ASGIServer,
    method: str,
    path: str,
    body: bytes = b"",
    query_string: bytes = b"",
) -> tuple[int, dict]:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
    }
    sent: list[dict] = []
    received = False

    async def receive() -> dict:
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))

    status = next(msg["status"] for msg in sent if msg["type"] == "http.response.start")
    payload = b"".join(msg.get("body", b"") for msg in sent if msg["type"] == "http.response.body")
    return status, json.loads(payload.decode("utf-8"))


def test_documented_server_startup_command_is_available():
    result = subprocess.run(
        [sys.executable, "-m", "pm_bot.server.app", "--print-startup"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000" in result.stdout


def test_http_health_and_changesets_routes_for_ui():
    service = ServerApp()
    app = ASGIServer(service=service)

    health_status, health_payload = _asgi_request(app, "GET", "/health")
    assert health_status == 200
    assert health_payload == {"status": "ok"}

    propose_body = {
        "operation": "create_issue",
        "repo": "phys-sims/phys-pipeline",
        "payload": {"issue_ref": "#120", "title": "HTTP flow"},
    }
    status, payload = _asgi_request(
        app,
        "POST",
        "/changesets/propose",
        body=json.dumps(propose_body).encode("utf-8"),
    )
    assert status == 200
    assert payload["status"] == "pending"
    assert payload["operation"] == "create_issue"

    pending_status, pending_payload = _asgi_request(app, "GET", "/changesets/pending")
    assert pending_status == 200
    assert pending_payload["summary"]["count"] == 1
    assert pending_payload["items"][0]["id"] == payload["id"]

    approve_status, approve_payload = _asgi_request(
        app,
        "POST",
        f"/changesets/{payload['id']}/approve",
        body=json.dumps({"approved_by": "human"}).encode("utf-8"),
    )
    assert approve_status == 200
    assert approve_payload["status"] == "applied"


def test_approval_denials_are_reason_coded_for_http_clients():
    service = ServerApp()
    app = ASGIServer(service=service)

    status, payload = _asgi_request(
        app,
        "POST",
        "/changesets/propose",
        body=json.dumps(
            {
                "operation": "create_issue",
                "repo": "outside/repo",
                "payload": {"title": "Denied"},
            }
        ).encode("utf-8"),
    )

    assert status == 403
    assert payload["reason_code"] == "repo_not_allowlisted"


def test_graph_estimator_and_report_routes_for_ui():
    service = ServerApp()
    app = ASGIServer(service=service)

    service.draft("epic", "Root")
    service.draft("task", "Child")
    service.link_work_items("draft:epic:root", "draft:task:child", source="sub_issue")

    tree_status, tree_payload = _asgi_request(
        app,
        "GET",
        "/graph/tree",
        query_string=b"root=draft:epic:root",
    )
    assert tree_status == 200
    assert tree_payload["root"]["issue_ref"] == "draft:epic:root"
    assert tree_payload["root"]["children"][0]["provenance"] == "sub_issue"

    deps_status, deps_payload = _asgi_request(app, "GET", "/graph/deps")
    assert deps_status == 200
    assert "summary" in deps_payload

    estimator_status, estimator_payload = _asgi_request(app, "GET", "/estimator/snapshot")
    assert estimator_status == 200
    assert estimator_payload["summary"]["count"] == len(estimator_payload["items"])

    no_report_status, no_report_payload = _asgi_request(app, "GET", "/reports/weekly/latest")
    assert no_report_status == 404
    assert no_report_payload["error"] == "report_not_found"

    service.generate_weekly_report(report_name="weekly-ui.md")
    latest_status, latest_payload = _asgi_request(app, "GET", "/reports/weekly/latest")
    assert latest_status == 200
    assert latest_payload["report_type"] == "weekly"


def test_graph_ingest_route_requires_repo_and_returns_diagnostics():
    service = ServerApp()
    app = ASGIServer(service=service)

    missing_status, missing_payload = _asgi_request(
        app,
        "POST",
        "/graph/ingest",
        body=json.dumps({}).encode("utf-8"),
    )
    assert missing_status == 400
    assert missing_payload["error"] == "missing_repo"

    service.db.upsert_work_item(
        "phys-sims/phys-pipeline#77",
        {
            "title": "Edge source",
            "type": "task",
            "area": "platform",
            "fields": {"issue_ref": "#77"},
            "relationships": {"children_refs": []},
        },
    )
    service.connector.sub_issues[("phys-sims/phys-pipeline", "#77")] = [{"issue_ref": "#78"}]
    service.connector.dependencies[("phys-sims/phys-pipeline", "#77")] = [{"issue_ref": "#76"}]

    ok_status, ok_payload = _asgi_request(
        app,
        "POST",
        "/graph/ingest",
        body=json.dumps({"repo": "phys-sims/phys-pipeline"}).encode("utf-8"),
    )
    assert ok_status == 200
    assert ok_payload["partial"] is False
    assert ok_payload["calls"] >= 1


def test_agent_run_routes_cover_propose_transition_claim_execute():
    service = ServerApp()
    app = ASGIServer(service=service)

    propose_status, propose_payload = _asgi_request(
        app,
        "POST",
        "/agent-runs/propose",
        body=json.dumps(
            {
                "created_by": "alice",
                "spec": {
                    "run_id": "http-run-1",
                    "model": "gpt-5",
                    "intent": "HTTP runner",
                    "adapter": "manual",
                    "requires_approval": True,
                },
            }
        ).encode("utf-8"),
    )
    assert propose_status == 200
    assert propose_payload["status"] == "proposed"

    transition_status, transition_payload = _asgi_request(
        app,
        "POST",
        "/agent-runs/transition",
        body=json.dumps(
            {
                "run_id": "http-run-1",
                "to_status": "approved",
                "reason_code": "human_approved",
                "actor": "reviewer",
            }
        ).encode("utf-8"),
    )
    assert transition_status == 200
    assert transition_payload["status"] == "approved"

    claim_status, claim_payload = _asgi_request(
        app,
        "POST",
        "/agent-runs/claim",
        body=json.dumps({"worker_id": "worker-1", "limit": 1, "lease_seconds": 30}).encode("utf-8"),
    )
    assert claim_status == 200
    assert claim_payload["summary"]["count"] == 1

    execute_status, execute_payload = _asgi_request(
        app,
        "POST",
        "/agent-runs/execute",
        body=json.dumps({"run_id": "http-run-1", "worker_id": "worker-1"}).encode("utf-8"),
    )
    assert execute_status == 200
    assert execute_payload["status"] == "completed"
    assert len(execute_payload["artifact_paths"]) == 1
    assert execute_payload["artifact_paths"][0].startswith("file://")
    assert execute_payload["artifact_paths"][0].endswith("/http-run-1.txt")

    transitions_status, transitions_payload = _asgi_request(
        app,
        "GET",
        "/agent-runs/transitions",
        query_string=b"run_id=http-run-1",
    )
    assert transitions_status == 200
    assert transitions_payload["summary"]["count"] >= 2


def test_unified_inbox_route_merges_pm_bot_and_github_items() -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    proposed = service.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"title": "Needs approval"},
    )
    assert proposed["status"] == "pending"

    service.connector.issues[("phys-sims/phys-pipeline", "#21")] = {
        "issue_ref": "#21",
        "title": "Review me",
        "url": "https://github.com/phys-sims/phys-pipeline/issues/21",
        "state": "open",
        "labels": ["needs-human"],
    }

    status, payload = _asgi_request(
        app,
        "GET",
        "/inbox",
        query_string=b"labels=needs-human&repos=phys-sims/phys-pipeline",
    )

    assert status == 200
    assert payload["schema_version"] == "inbox/v1"
    assert payload["summary"]["pm_bot_count"] == 1
    assert payload["summary"]["github_count"] == 1
    assert payload["items"][0]["source"] == "pm_bot"
    assert payload["diagnostics"]["cache"]["hit"] is False


def test_onboarding_readiness_and_dry_run_routes() -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    readiness_status, readiness_payload = _asgi_request(app, "GET", "/onboarding/readiness")
    assert readiness_status == 200
    assert "readiness_state" in readiness_payload

    dry_run_status, dry_run_payload = _asgi_request(
        app,
        "POST",
        "/onboarding/dry-run",
        body=json.dumps({}).encode("utf-8"),
    )
    assert dry_run_status == 200
    assert dry_run_payload["reason_code"] in {
        "missing_org_context",
        "single_tenant_mode",
        "org_installation_ready",
    }


def test_report_ir_intake_confirm_preview_and_propose_routes() -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    intake_status, intake_payload = _asgi_request(
        app,
        "POST",
        "/report-ir/intake",
        body=json.dumps(
            {
                "natural_text": "- Build v6 intake flow\n- Add approval handoff",
                "org": "phys-sims",
                "repos": ["phys-sims/phys-pipeline", "phys-sims/pm-bot"],
                "run_id": "v6-b-flow",
                "requested_by": "operator",
                "generated_at": "2026-02-25",
            }
        ).encode("utf-8"),
    )
    assert intake_status == 200
    assert intake_payload["schema_version"] == "report_ir_draft/v1"
    report_ir = intake_payload["draft"]
    assert report_ir["schema_version"] == "report_ir/v1"
    assert intake_payload["validation"]["errors"] == []

    chain_status, chain_payload = _asgi_request(
        app,
        "GET",
        "/audit/chain",
        query_string=b"run_id=v6-b-flow&event_type=report_ir_draft_generated",
    )
    assert chain_status == 200
    assert chain_payload["summary"]["total"] == 1
    llm_metadata = chain_payload["items"][0]["payload"]["llm_metadata"]
    assert llm_metadata["capability_id"] == "report_ir_draft"
    assert llm_metadata["prompt_version"] == "v1"
    assert llm_metadata["schema_version"] == "report_ir_draft/v1"
    assert llm_metadata["run_id"] == "v6-b-flow"
    assert llm_metadata["input_hash"]

    confirm_status, confirm_payload = _asgi_request(
        app,
        "POST",
        "/report-ir/confirm",
        body=json.dumps(
            {
                "run_id": "v6-b-flow",
                "confirmed_by": "human-reviewer",
                "draft": report_ir,
                "report_ir": report_ir,
            }
        ).encode("utf-8"),
    )
    assert confirm_status == 200
    assert confirm_payload["status"] == "confirmed"

    preview_status, preview_payload = _asgi_request(
        app,
        "POST",
        "/report-ir/preview",
        body=json.dumps({"run_id": "v6-b-flow", "report_ir": report_ir}).encode("utf-8"),
    )
    assert preview_status == 200
    assert preview_payload["schema_version"] == "changeset_preview/v1"
    assert preview_payload["summary"]["count"] >= 1
    assert "dependency_preview" in preview_payload
    assert isinstance(preview_payload["dependency_preview"]["repos"], list)
    first_repo_preview = preview_payload["dependency_preview"]["repos"][0]
    assert "nodes" in first_repo_preview
    assert "edges" in first_repo_preview

    propose_status, propose_payload = _asgi_request(
        app,
        "POST",
        "/report-ir/propose",
        body=json.dumps(
            {
                "run_id": "v6-b-flow",
                "requested_by": "operator",
                "report_ir": report_ir,
            }
        ).encode("utf-8"),
    )
    assert propose_status == 200
    assert propose_payload["schema_version"] == "report_ir_proposal/v1"
    assert propose_payload["summary"]["count"] == preview_payload["summary"]["count"]

    repeat_status, repeat_payload = _asgi_request(
        app,
        "POST",
        "/report-ir/propose",
        body=json.dumps(
            {
                "run_id": "v6-b-flow-repeat",
                "requested_by": "operator",
                "report_ir": report_ir,
            }
        ).encode("utf-8"),
    )
    assert repeat_status == 200
    assert repeat_payload["summary"]["count"] == propose_payload["summary"]["count"]
    assert [row["changeset"]["id"] for row in repeat_payload["items"]] == [
        row["changeset"]["id"] for row in propose_payload["items"]
    ]


def test_report_ir_intake_structured_mode_extracts_hierarchy_and_tokens() -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    structured_markdown = """# Epic: Platform Reliability area=platform priority=P1
## Feature: Queue hardening estimate=8 depends on feat:retry-policy
- [ ] Task: Add retry backoff area=platform priority=P1 est=3 blocked by task:db-migration
- [x] Task: Add dead letter queue area=platform priority=P1 estimate=2
"""

    intake_status, intake_payload = _asgi_request(
        app,
        "POST",
        "/report-ir/intake",
        body=json.dumps(
            {
                "natural_text": structured_markdown,
                "org": "phys-sims",
                "repos": ["phys-sims/pm-bot"],
                "mode": "structured",
                "generated_at": "2026-02-26",
            }
        ).encode("utf-8"),
    )

    assert intake_status == 200
    draft = intake_payload["draft"]
    assert draft["epics"] == [
        {
            "stable_id": "epic:platform-reliability",
            "title": "Platform Reliability",
            "objective": "Platform Reliability",
            "area": "platform",
            "priority": "P1",
        }
    ]
    assert draft["features"] == [
        {
            "stable_id": "feat:queue-hardening",
            "title": "Queue hardening",
            "goal": "Queue hardening",
            "area": "triage",
            "priority": "Triage",
            "epic_id": "epic:platform-reliability",
            "estimate_hrs": 8,
            "depends_on": ["feat:retry-policy"],
        }
    ]
    assert draft["tasks"] == [
        {
            "stable_id": "task:add-retry-backoff",
            "title": "Add retry backoff",
            "area": "platform",
            "priority": "P1",
            "type": "task",
            "feature_id": "feat:queue-hardening",
            "estimate_hrs": 3,
            "blocked_by": ["task:db-migration"],
        },
        {
            "stable_id": "task:add-dead-letter-queue",
            "title": "Add dead letter queue",
            "area": "platform",
            "priority": "P1",
            "type": "task",
            "feature_id": "feat:queue-hardening",
            "estimate_hrs": 2,
        },
    ]
    assert intake_payload["validation"]["errors"] == []


def test_audit_chain_rollups_and_incident_bundle_routes() -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    service.db.append_audit_event(
        "agent_run_completed",
        {"run_id": "run-audit-1", "repo": "phys-sims/pm-bot", "actor": "alice"},
    )
    service.db.append_audit_event(
        "agent_run_retry_scheduled",
        {
            "run_id": "run-audit-1",
            "repo": "phys-sims/pm-bot",
            "actor": "alice",
            "reason_code": "transient_provider_error",
            "queue_age_seconds": 12,
        },
    )
    service.db.append_audit_event(
        "changeset_denied",
        {
            "run_id": "run-audit-1",
            "repo": "phys-sims/pm-bot",
            "actor": "policy",
            "reason_code": "repo_not_allowlisted",
        },
    )
    service.db.append_audit_event(
        "report_ir_draft_generated",
        {
            "run_id": "run-audit-1",
            "llm_metadata": {
                "capability_id": "report_ir_draft",
                "prompt_version": "v1",
            },
        },
    )

    chain_status, chain_payload = _asgi_request(
        app,
        "GET",
        "/audit/chain",
        query_string=b"run_id=run-audit-1&repo=phys-sims%2Fpm-bot&actor=alice&limit=2&offset=0",
    )
    assert chain_status == 200
    assert chain_payload["schema_version"] == "audit_chain/v1"
    assert chain_payload["summary"]["count"] == 2
    assert chain_payload["summary"]["total"] == 2

    rollup_status, rollup_payload = _asgi_request(
        app,
        "GET",
        "/audit/rollups",
        query_string=b"run_id=run-audit-1",
    )
    assert rollup_status == 200
    assert rollup_payload["schema_version"] == "audit_rollups/v1"
    assert rollup_payload["summary"]["sample_size"] == 4
    assert rollup_payload["summary"]["retry_count"] == 1
    assert rollup_payload["summary"]["denial_count"] == 1
    assert rollup_payload["capability_concentration"] == [
        {"capability_id": "report_ir_draft", "count": 1}
    ]

    bundle_status, bundle_payload = _asgi_request(
        app,
        "GET",
        "/audit/incident-bundle",
        query_string=b"run_id=run-audit-1&actor=alice",
    )
    assert bundle_status == 200
    assert bundle_payload["schema_version"] == "incident_bundle/v1"
    assert bundle_payload["chain"]["summary"]["total"] == 2
    assert "retry_storm" in bundle_payload["runbook_hooks"]


def test_report_ir_intake_rejects_invalid_capability_output_before_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    called = {"propose": False}

    def _fake_propose(*args, **kwargs):
        called["propose"] = True
        raise AssertionError("propose path must not be reached")

    def _fake_run_capability(*args, **kwargs):
        raise app_module.CapabilityOutputValidationError(
            "report_ir_draft",
            errors=[
                {
                    "path": "$.draft",
                    "code": "SCHEMA_REQUIRED",
                    "message": "'draft' is a required property",
                }
            ],
            warnings=[
                {"path": "$", "code": "COERCION_DISABLED", "message": "no coercion attempted"}
            ],
        )

    monkeypatch.setattr(service, "propose_report_ir_changesets", _fake_propose)
    monkeypatch.setattr(app_module, "run_capability", _fake_run_capability)

    status, payload = _asgi_request(
        app,
        "POST",
        "/report-ir/intake",
        body=json.dumps(
            {
                "natural_text": "- plan item",
                "org": "phys-sims",
                "repos": ["phys-sims/pm-bot"],
            }
        ).encode("utf-8"),
    )

    assert status == 400
    assert payload["error"] == "capability_output_validation_failed:report_ir_draft"
    assert payload["validation"]["errors"][0]["code"] == "SCHEMA_REQUIRED"
    assert payload["validation"]["warnings"][0]["code"] == "COERCION_DISABLED"
    assert called["propose"] is False

    pending_status, pending_payload = _asgi_request(app, "GET", "/changesets/pending")
    assert pending_status == 200
    assert pending_payload["summary"]["count"] == 0
