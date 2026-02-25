import asyncio
import json
import subprocess
import sys

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
