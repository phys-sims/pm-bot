"""GitHub auth loading with read/write token separation and safe handling."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class GitHubAuth:
    read_token: str | None
    write_token: str | None

    def redacted(self) -> dict[str, str]:
        return {
            "read_token": _redact_token(self.read_token),
            "write_token": _redact_token(self.write_token),
        }


def load_github_auth_from_env(env: dict[str, str] | None = None) -> GitHubAuth:
    env_map = env or os.environ

    shared_token = _clean(env_map.get("PM_BOT_GITHUB_TOKEN") or env_map.get("GITHUB_TOKEN"))
    read_token = _clean(env_map.get("PM_BOT_GITHUB_READ_TOKEN")) or shared_token
    write_token = _clean(env_map.get("PM_BOT_GITHUB_WRITE_TOKEN")) or shared_token
    return GitHubAuth(read_token=read_token, write_token=write_token)


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
