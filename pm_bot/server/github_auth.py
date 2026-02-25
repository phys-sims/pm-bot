"""GitHub auth loading with read/write token separation and safe handling."""

from __future__ import annotations

import os
from dataclasses import dataclass


REASON_INVALID_REPO = "invalid_repo"
REASON_REPO_ORG_MISMATCH = "repo_org_mismatch"
REASON_ORG_MISMATCH = "org_mismatch"
REASON_INSTALLATION_MISMATCH = "installation_mismatch"


@dataclass(frozen=True)
class GitHubAuth:
    read_token: str | None
    write_token: str | None

    def redacted(self) -> dict[str, str]:
        return {
            "read_token": _redact_token(self.read_token),
            "write_token": _redact_token(self.write_token),
        }


@dataclass(frozen=True)
class GitHubTenantContext:
    tenant_mode: str
    org: str
    installation_id: str


def load_github_auth_from_env(env: dict[str, str] | None = None) -> GitHubAuth:
    env_map = env or os.environ

    shared_token = _clean(env_map.get("PM_BOT_GITHUB_TOKEN") or env_map.get("GITHUB_TOKEN"))
    read_token = _clean(env_map.get("PM_BOT_GITHUB_READ_TOKEN")) or shared_token
    write_token = _clean(env_map.get("PM_BOT_GITHUB_WRITE_TOKEN")) or shared_token
    return GitHubAuth(read_token=read_token, write_token=write_token)


def load_tenant_context_from_env(env: dict[str, str] | None = None) -> GitHubTenantContext:
    env_map = env or os.environ
    mode = _clean(env_map.get("PM_BOT_TENANT_MODE")) or "single_tenant"
    org = _clean(env_map.get("PM_BOT_ORG")) or ""
    installation_id = _clean(env_map.get("PM_BOT_GITHUB_APP_INSTALLATION_ID")) or ""
    return GitHubTenantContext(tenant_mode=mode, org=org, installation_id=installation_id)


def validate_org_and_installation_context(
    *,
    tenant: GitHubTenantContext,
    repo: str,
    request_org: str = "",
    request_installation_id: str = "",
) -> tuple[bool, str]:
    if "/" not in repo:
        return False, REASON_INVALID_REPO

    repo_org = repo.split("/", 1)[0].strip()
    if not repo_org:
        return False, REASON_INVALID_REPO

    expected_org = tenant.org.strip()
    if expected_org and repo_org != expected_org:
        return False, REASON_REPO_ORG_MISMATCH

    normalized_request_org = request_org.strip()
    if expected_org and normalized_request_org and normalized_request_org != expected_org:
        return False, REASON_ORG_MISMATCH

    expected_install = tenant.installation_id.strip()
    normalized_request_install = request_installation_id.strip()
    if (
        expected_install
        and normalized_request_install
        and normalized_request_install != expected_install
    ):
        return False, REASON_INSTALLATION_MISMATCH

    return True, "allowed"


def _clean(token: str | None) -> str | None:
    if token is None:
        return None
    value = token.strip()
    return value or None


def _redact_token(token: str | None) -> str:
    if token is None:
        return "unset"
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"
