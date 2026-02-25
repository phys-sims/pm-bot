from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from pm_bot.server.github_auth import load_github_auth_from_env
from pm_bot.server.github_connector import (
    RetryableGitHubError,
    WriteRequest,
    build_connector_from_env,
)
from pm_bot.server.github_connector_api import GitHubAPIConnector
from pm_bot.server.github_connector_inmemory import InMemoryGitHubConnector


@dataclass
class FakeResponse:
    status_code: int
    payload: Any
    headers: dict[str, str] | None = None

    @property
    def content(self) -> bytes:
        if self.payload is None:
            return b""
        return b"json"

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        if not self.responses:
            raise RuntimeError("No fake response left")
        return self.responses.pop(0)


def test_build_connector_from_env_defaults_to_inmemory() -> None:
    connector = build_connector_from_env(env={})
    assert isinstance(connector, InMemoryGitHubConnector)


def test_build_connector_from_env_explicit_empty_env_ignores_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PM_BOT_GITHUB_CONNECTOR", "api")
    connector = build_connector_from_env(env={})
    assert isinstance(connector, InMemoryGitHubConnector)


def test_build_connector_from_env_preserves_explicit_empty_allowed_repos() -> None:
    connector = build_connector_from_env(env={}, allowed_repos=set())
    assert connector.allowed_repos == set()


def test_auth_loads_read_write_tokens_with_shared_fallback() -> None:
    auth = load_github_auth_from_env(
        {
            "PM_BOT_GITHUB_READ_TOKEN": "read-token",
            "PM_BOT_GITHUB_TOKEN": "shared-token",
        }
    )
    assert auth.read_token == "read-token"
    assert auth.write_token == "shared-token"


def test_api_connector_create_update_list_and_link() -> None:
    session = FakeSession(
        [
            FakeResponse(200, [{"number": 1, "title": "One"}]),
            FakeResponse(200, {"number": 1, "title": "One"}),
            FakeResponse(201, {"number": 2, "title": "Two"}),
            FakeResponse(200, {"number": 2, "title": "Two+"}),
            FakeResponse(201, {"id": 55}),
        ]
    )
    connector = GitHubAPIConnector(
        allowed_repos={"phys-sims/phys-pipeline"},
        auth=load_github_auth_from_env(
            {
                "PM_BOT_GITHUB_READ_TOKEN": "read-token",
                "PM_BOT_GITHUB_WRITE_TOKEN": "write-token",
            }
        ),
        session=session,
    )

    listed = connector.list_issues("phys-sims/phys-pipeline", state="open")
    assert listed[0]["title"] == "One"

    fetched = connector.fetch_issue("phys-sims/phys-pipeline", "#1")
    assert fetched["number"] == 1

    created = connector.execute_write(
        WriteRequest(
            operation="create_issue",
            repo="phys-sims/phys-pipeline",
            target_ref="",
            payload={"title": "Two"},
        )
    )
    assert created["status"] == "applied"

    updated = connector.execute_write(
        WriteRequest(
            operation="update_issue",
            repo="phys-sims/phys-pipeline",
            target_ref="#2",
            payload={"title": "Two+"},
        )
    )
    assert updated["issue"]["title"] == "Two+"

    linked = connector.execute_write(
        WriteRequest(
            operation="link_issue",
            repo="phys-sims/phys-pipeline",
            target_ref="#2",
            payload={"linked_issue_ref": "#1", "relationship": "blocked_by"},
        )
    )
    assert linked["comment"]["id"] == 55

    auth_headers = [call["headers"].get("Authorization") for call in session.calls]
    assert auth_headers[0] == "Bearer read-token"
    assert auth_headers[2] == "Bearer write-token"


def test_api_connector_raises_retryable_for_rate_limit_and_5xx() -> None:
    connector = GitHubAPIConnector(
        allowed_repos={"phys-sims/phys-pipeline"},
        auth=load_github_auth_from_env({"PM_BOT_GITHUB_WRITE_TOKEN": "write-token"}),
        session=FakeSession(
            [
                FakeResponse(403, {"message": "API rate limit exceeded"}, {"Retry-After": "2"}),
            ]
        ),
    )

    with pytest.raises(RetryableGitHubError) as exc_info:
        connector.execute_write(
            WriteRequest(
                operation="create_issue",
                repo="phys-sims/phys-pipeline",
                target_ref="",
                payload={"title": "limited"},
            )
        )

    assert exc_info.value.reason_code == "github_rate_limited"
    assert exc_info.value.retry_after_s == 2.0

    connector_5xx = GitHubAPIConnector(
        allowed_repos={"phys-sims/phys-pipeline"},
        auth=load_github_auth_from_env({"PM_BOT_GITHUB_WRITE_TOKEN": "write-token"}),
        session=FakeSession([FakeResponse(503, {"message": "unavailable"})]),
    )
    with pytest.raises(RetryableGitHubError) as exc_5xx:
        connector_5xx.execute_write(
            WriteRequest(
                operation="create_issue",
                repo="phys-sims/phys-pipeline",
                target_ref="",
                payload={"title": "down"},
            )
        )
    assert exc_5xx.value.reason_code == "github_503"


def test_api_connector_normalizes_sub_issues_and_dependencies() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                [
                    {"number": 3, "observed_at": "2026-02-24T00:00:00Z"},
                    {"issue_ref": "#2", "observed_at": "2026-02-24T00:00:01Z"},
                    "ignore-me",
                ],
            ),
            FakeResponse(
                200,
                [
                    {"number": 7, "observed_at": "2026-02-24T00:00:02Z"},
                    {"issue_ref": "#6", "observed_at": "2026-02-24T00:00:03Z"},
                ],
            ),
        ]
    )
    connector = GitHubAPIConnector(
        allowed_repos={"phys-sims/phys-pipeline"},
        auth=load_github_auth_from_env({"PM_BOT_GITHUB_READ_TOKEN": "read-token"}),
        session=session,
    )

    sub_issues = connector.list_sub_issues("phys-sims/phys-pipeline", "#1")
    deps = connector.list_issue_dependencies("phys-sims/phys-pipeline", "#1")

    assert sub_issues == [
        {"issue_ref": "#2", "source": "sub_issue", "observed_at": "2026-02-24T00:00:01Z"},
        {"issue_ref": "#3", "source": "sub_issue", "observed_at": "2026-02-24T00:00:00Z"},
    ]
    assert deps == [
        {
            "issue_ref": "#6",
            "source": "dependency_api",
            "observed_at": "2026-02-24T00:00:03Z",
        },
        {
            "issue_ref": "#7",
            "source": "dependency_api",
            "observed_at": "2026-02-24T00:00:02Z",
        },
    ]


def test_api_connector_inbox_items_are_cached_and_deterministic() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                [
                    {
                        "number": 10,
                        "title": "Needs review",
                        "state": "open",
                        "html_url": "https://github.com/phys-sims/phys-pipeline/pull/10",
                        "pull_request": {"url": "x"},
                        "requested_reviewers": [{"login": "octo"}],
                        "labels": [{"name": "needs-human"}],
                    }
                ],
                {"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "1700000000"},
            )
        ]
    )
    connector = GitHubAPIConnector(
        allowed_repos={"phys-sims/phys-pipeline"},
        auth=load_github_auth_from_env({"PM_BOT_GITHUB_READ_TOKEN": "read-token"}),
        session=session,
        cache_ttl_s=60,
    )

    items_1, diag_1 = connector.list_inbox_items(
        actor="octo", labels=["needs-human"], repos=["phys-sims/phys-pipeline"]
    )
    items_2, diag_2 = connector.list_inbox_items(
        actor="octo", labels=["needs-human"], repos=["phys-sims/phys-pipeline"]
    )

    assert len(items_1) == 1
    assert items_1[0]["id"] == "github:phys-sims/phys-pipeline#10"
    assert items_1 == items_2
    assert diag_1["cache"]["hit"] is False
    assert diag_2["cache"]["hit"] is True
    assert len(session.calls) == 1
