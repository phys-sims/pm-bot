"""Shared runtime settings for local-first disk-backed storage."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StorageSettings:
    """Filesystem and SQLite locations used by local-first deployments."""

    data_dir: Path
    sqlite_path: Path
    artifact_dir: Path
    checkpoint_dir: Path
    repos_dir: Path

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "StorageSettings":
        source = env or os.environ
        data_dir = Path(source.get("PMBOT_DATA_DIR", "./data"))
        sqlite_path = Path(
            source.get("PMBOT_SQLITE_PATH", str(data_dir / "control_plane" / "pm_bot.sqlite"))
        )
        artifact_dir = Path(source.get("PMBOT_ARTIFACT_DIR", str(data_dir / "artifacts")))
        checkpoint_dir = Path(source.get("PMBOT_CHECKPOINT_DIR", str(data_dir / "checkpoints")))
        repos_dir = Path(source.get("PMBOT_REPOS_DIR", str(data_dir / "repos")))
        return cls(
            data_dir=data_dir,
            sqlite_path=sqlite_path,
            artifact_dir=artifact_dir,
            checkpoint_dir=checkpoint_dir,
            repos_dir=repos_dir,
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)


def get_storage_settings(env: dict[str, str] | None = None) -> StorageSettings:
    """Build and hydrate storage settings from environment variables."""

    settings = StorageSettings.from_env(env)
    settings.ensure_directories()
    return settings


def default_artifact_uri(run_id: str, suffix: str = ".txt") -> str:
    """Build a local filesystem URI for a run artifact."""

    settings = get_storage_settings()
    artifact_path = (settings.artifact_dir / f"{run_id}{suffix}").resolve()
    return artifact_path.as_uri()
