import json

from pm_bot.server.app import ASGIServer, ServerApp
from pm_bot.server.github_auth import (
    REASON_INSTALLATION_MISMATCH,
    REASON_ORG_MISMATCH,
    REASON_REPO_ORG_MISMATCH,
    GitHubTenantContext,
    validate_org_and_installation_context,
)


def _asgi_request(app: ASGIServer, method: str, path: str, body: bytes = b"") -> tuple[int, dict]:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
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

    import asyncio

    asyncio.run(app(scope, receive, send))
    status = next(msg["status"] for msg in sent if msg["type"] == "http.response.start")
    payload = b"".join(msg.get("body", b"") for msg in sent if msg["type"] == "http.response.body")
    return status, json.loads(payload.decode("utf-8"))


def test_validate_org_and_installation_context_reason_codes() -> None:
    tenant = GitHubTenantContext(
        tenant_mode="single_tenant", org="phys-sims", installation_id="1234"
    )
    allowed, reason = validate_org_and_installation_context(
        tenant=tenant,
        repo="other/repo",
    )
    assert allowed is False
    assert reason == REASON_REPO_ORG_MISMATCH

    allowed, reason = validate_org_and_installation_context(
        tenant=tenant,
        repo="phys-sims/phys-pipeline",
        request_org="other",
    )
    assert allowed is False
    assert reason == REASON_ORG_MISMATCH

    allowed, reason = validate_org_and_installation_context(
        tenant=tenant,
        repo="phys-sims/phys-pipeline",
        request_installation_id="999",
    )
    assert allowed is False
    assert reason == REASON_INSTALLATION_MISMATCH


def test_onboarding_state_machine_and_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("PM_BOT_ORG", "")
    monkeypatch.setenv("PM_BOT_GITHUB_APP_INSTALLATION_ID", "")
    pending = ServerApp()
    assert pending.onboarding_dry_run()["readiness_state"] == "pending_context"

    monkeypatch.setenv("PM_BOT_ORG", "phys-sims")
    monkeypatch.setenv("PM_BOT_GITHUB_APP_INSTALLATION_ID", "")
    single = ServerApp()
    assert single.onboarding_dry_run()["readiness_state"] == "single_tenant_ready"

    monkeypatch.setenv("PM_BOT_ORG", "phys-sims")
    monkeypatch.setenv("PM_BOT_GITHUB_APP_INSTALLATION_ID", "42")
    org_ready = ServerApp()
    assert org_ready.onboarding_dry_run()["readiness_state"] == "org_ready"


def test_http_request_context_denial_is_reason_coded(monkeypatch) -> None:
    monkeypatch.setenv("PM_BOT_ORG", "phys-sims")
    service = ServerApp()
    app = ASGIServer(service=service)

    status, payload = _asgi_request(
        app,
        "POST",
        "/changesets/propose",
        body=json.dumps(
            {
                "operation": "create_issue",
                "repo": "phys-sims/phys-pipeline",
                "payload": {"title": "Denied context"},
                "org": "other-org",
            }
        ).encode("utf-8"),
    )
    assert status == 403
    assert payload["reason_code"] == "org_mismatch"

    denied = service.db.list_audit_events("auth_context_denied")
    assert denied
    assert denied[0]["payload"]["reason_code"] == "org_mismatch"
