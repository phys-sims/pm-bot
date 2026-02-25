import asyncio
import json

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


def test_context_pack_v2_is_hash_stable_and_budgeted() -> None:
    app = ServerApp()
    parent = app.draft(item_type="epic", title="Parent", body_fields={"Goal": "Big"})
    draft = app.draft(item_type="feature", title="Deterministic builder", body_fields={"Goal": "Ship"})
    child = app.draft(
        item_type="task",
        title="Very long child segment to force exclusion",
        body_fields={"Goal": "x" * 500},
    )
    app.link_work_items(parent["issue_ref"], draft["issue_ref"], source="sub_issue")
    app.link_work_items(draft["issue_ref"], child["issue_ref"], source="sub_issue")

    first = app.context_pack(draft["issue_ref"], budget=500, run_id="run-cp", requested_by="agent")
    second = app.context_pack(draft["issue_ref"], budget=500, run_id="run-cp", requested_by="agent")

    assert first["schema_version"] == "context_pack/v2"
    assert first["hash"] == second["hash"]
    assert first["budget"]["used_chars"] <= first["budget"]["max_chars"]
    assert first["manifest"]["excluded_segments"]
    assert first["manifest"]["exclusion_reasons"]["budget_exceeded"] >= 1


def test_context_pack_v2_redacts_secret_patterns() -> None:
    app = ServerApp()
    draft = app.draft(
        item_type="feature",
        title="Secret redaction",
        body_fields={"Goal": "Ship", "token": "ghp_abcdefghijklmnopqrstuvwxyz12345"},
    )

    pack = app.context_pack(draft["issue_ref"], budget=5000)

    assert pack["manifest"]["redaction_counts"]["total"] >= 1
    assert pack["manifest"]["redaction_counts"]["categories"]["github_pat"] >= 1


def test_context_pack_v1_compatibility_path() -> None:
    app = ServerApp()
    draft = app.draft(item_type="feature", title="Compat", body_fields={"Goal": "Keep v1"})

    v1 = app.context_pack(draft["issue_ref"], schema_version="context_pack/v1")
    assert v1["schema_version"] == "context_pack/v1"
    assert v1["content"]["fields"]["Goal"] == "Keep v1"


def test_context_pack_http_route_and_audit_run_filtering() -> None:
    service = ServerApp()
    asgi = ASGIServer(service=service)
    draft = service.draft(item_type="task", title="Route", body_fields={"Goal": "Test"})

    missing_status, missing_payload = _asgi_request(asgi, "GET", "/context-pack")
    assert missing_status == 400
    assert missing_payload["error"] == "missing_issue_ref"

    status, payload = _asgi_request(
        asgi,
        "GET",
        "/context-pack",
        query_string=(
            f"issue_ref={draft['issue_ref']}&budget=800&run_id=run-http&requested_by=ui".encode(
                "utf-8"
            )
        ),
    )
    assert status == 200
    assert payload["schema_version"] == "context_pack/v2"

    run_events = service.db.list_audit_events(event_type="context_pack_built", run_id="run-http")
    assert len(run_events) == 1
    assert run_events[0]["payload"]["requested_by"] == "ui"
