"""Filesystem + metadata checkpointer bridge for LangGraph-style runner state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class CheckpointMetadataStore(Protocol):
    def upsert_checkpoint_metadata(
        self,
        run_id: str,
        thread_id: str,
        status: str,
        current_node_id: str,
        checkpoint_path: str,
    ) -> None: ...


@dataclass
class CheckpointWriteResult:
    checkpoint_path: str
    sequence: int


class FsDbCheckpointer:
    """Persists checkpoint blobs to filesystem and metadata via injected store."""

    def __init__(
        self,
        metadata_store: CheckpointMetadataStore,
        base_dir: Path | str = Path("data/checkpoints"),
    ) -> None:
        self._metadata_store = metadata_store
        self._base_dir = Path(base_dir)

    def write(
        self,
        run_id: str,
        thread_id: str,
        status: str,
        current_node_id: str,
        payload: dict[str, Any],
    ) -> CheckpointWriteResult:
        thread_dir = self._base_dir / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        sequence = len(list(thread_dir.glob("checkpoint-*.json"))) + 1
        checkpoint_path = thread_dir / f"checkpoint-{sequence:05d}.json"
        envelope = {
            "run_id": run_id,
            "thread_id": thread_id,
            "status": status,
            "current_node_id": current_node_id,
            "written_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        checkpoint_path.write_text(json.dumps(envelope, sort_keys=True, indent=2), encoding="utf-8")
        self._metadata_store.upsert_checkpoint_metadata(
            run_id=run_id,
            thread_id=thread_id,
            status=status,
            current_node_id=current_node_id,
            checkpoint_path=str(checkpoint_path),
        )
        return CheckpointWriteResult(checkpoint_path=str(checkpoint_path), sequence=sequence)
