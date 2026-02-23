"""SQLite persistence for v1 orchestrator primitives."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class OrchestratorDB:
    """Small SQLite wrapper for work items, changesets, approvals, and audit events."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS work_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_ref TEXT UNIQUE,
                title TEXT NOT NULL,
                item_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_ref TEXT NOT NULL,
                child_ref TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'checklist',
                UNIQUE(parent_ref, child_ref, source)
            );

            CREATE TABLE IF NOT EXISTS changesets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                repo TEXT NOT NULL,
                target_ref TEXT,
                payload_json TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                UNIQUE(idempotency_key)
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                changeset_id INTEGER NOT NULL,
                approved_by TEXT NOT NULL,
                approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(changeset_id) REFERENCES changesets(id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_profile TEXT NOT NULL,
                model TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS estimate_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bucket_key TEXT NOT NULL,
                p50 REAL NOT NULL,
                p80 REAL NOT NULL,
                sample_count INTEGER NOT NULL,
                method TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                report_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_family TEXT NOT NULL,
                outcome TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                total_latency_ms REAL NOT NULL DEFAULT 0,
                UNIQUE(operation_family, outcome)
            )
            """
        )
        if not self._has_column("changesets", "idempotency_key"):
            self.conn.execute("ALTER TABLE changesets ADD COLUMN idempotency_key TEXT")
        if not self._has_column("changesets", "retry_count"):
            self.conn.execute(
                "ALTER TABLE changesets ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
            )
        if not self._has_column("changesets", "last_error"):
            self.conn.execute("ALTER TABLE changesets ADD COLUMN last_error TEXT")
        if not self._has_column("relationships", "source"):
            self.conn.execute(
                "ALTER TABLE relationships ADD COLUMN source TEXT NOT NULL DEFAULT 'checklist'"
            )
        self.conn.commit()

    def _has_column(self, table: str, column: str) -> bool:
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)

    def upsert_work_item(self, issue_ref: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO work_items (issue_ref, title, item_type, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(issue_ref) DO UPDATE SET
              title=excluded.title,
              item_type=excluded.item_type,
              payload_json=excluded.payload_json
            """,
            (issue_ref, payload.get("title", ""), payload.get("type", ""), json.dumps(payload)),
        )
        self.conn.commit()

    def get_work_item(self, issue_ref: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT payload_json FROM work_items WHERE issue_ref = ?", (issue_ref,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def create_changeset(
        self,
        operation: str,
        repo: str,
        payload: dict[str, Any],
        target_ref: str = "",
        idempotency_key: str = "",
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO changesets (operation, repo, target_ref, payload_json, idempotency_key)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                operation,
                repo,
                target_ref or None,
                json.dumps(payload),
                idempotency_key,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_changeset(self, changeset_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM changesets WHERE id = ?", (changeset_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "operation": row["operation"],
            "repo": row["repo"],
            "target_ref": row["target_ref"],
            "payload": json.loads(row["payload_json"]),
            "idempotency_key": row["idempotency_key"],
            "retry_count": row["retry_count"],
            "last_error": row["last_error"],
            "status": row["status"],
        }

    def get_changeset_by_idempotency_key(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT id FROM changesets WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        return self.get_changeset(int(row[0]))

    def set_changeset_status(self, changeset_id: int, status: str) -> None:
        self.conn.execute("UPDATE changesets SET status = ? WHERE id = ?", (status, changeset_id))
        self.conn.commit()

    def update_changeset_retry(self, changeset_id: int, retry_count: int, last_error: str) -> None:
        self.conn.execute(
            "UPDATE changesets SET retry_count = ?, last_error = ? WHERE id = ?",
            (retry_count, last_error, changeset_id),
        )
        self.conn.commit()

    def record_approval(self, changeset_id: int, approved_by: str) -> None:
        self.conn.execute(
            "INSERT INTO approvals (changeset_id, approved_by) VALUES (?, ?)",
            (changeset_id, approved_by),
        )
        self.conn.commit()

    def append_audit_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO audit_events (event_type, event_json) VALUES (?, ?)",
            (event_type, json.dumps(payload)),
        )
        self.conn.commit()

    def add_relationship(self, parent_ref: str, child_ref: str, source: str = "checklist") -> None:
        self.conn.execute(
            """
            INSERT INTO relationships (parent_ref, child_ref, source)
            VALUES (?, ?, ?)
            ON CONFLICT(parent_ref, child_ref, source) DO NOTHING
            """,
            (parent_ref, child_ref, source),
        )
        self.conn.commit()

    def get_related(self, issue_ref: str) -> dict[str, list[str]]:
        parent_rows = self.conn.execute(
            "SELECT parent_ref FROM relationships WHERE child_ref = ? ORDER BY parent_ref ASC",
            (issue_ref,),
        ).fetchall()
        child_rows = self.conn.execute(
            "SELECT child_ref FROM relationships WHERE parent_ref = ? ORDER BY child_ref ASC",
            (issue_ref,),
        ).fetchall()
        return {
            "parents": [row[0] for row in parent_rows],
            "children": [row[0] for row in child_rows],
        }

    def list_relationships(self) -> list[dict[str, str]]:
        rows = self.conn.execute(
            """
            SELECT parent_ref, child_ref, source
            FROM relationships
            ORDER BY parent_ref ASC, child_ref ASC, source ASC
            """
        ).fetchall()
        return [
            {
                "parent_ref": str(row["parent_ref"]),
                "child_ref": str(row["child_ref"]),
                "source": str(row["source"] or "checklist"),
            }
            for row in rows
        ]

    def list_work_items(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT payload_json FROM work_items ORDER BY issue_ref ASC")
        return [json.loads(row[0]) for row in rows]

    def list_work_item_records(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, payload_json FROM work_items ORDER BY id ASC"
        ).fetchall()
        return [{"id": int(row["id"]), "payload": json.loads(row["payload_json"])} for row in rows]

    def list_pending_changesets(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id FROM changesets WHERE status = 'pending' ORDER BY id ASC"
        )
        return [self.get_changeset(int(row[0])) for row in rows if row is not None]

    def list_audit_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        if event_type:
            rows = self.conn.execute(
                "SELECT id, event_type, event_json, created_at FROM audit_events WHERE event_type = ? ORDER BY id ASC",
                (event_type,),
            )
        else:
            rows = self.conn.execute(
                "SELECT id, event_type, event_json, created_at FROM audit_events ORDER BY id ASC"
            )
        return [
            {
                "id": int(row["id"]),
                "event_type": row["event_type"],
                "payload": json.loads(row["event_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def store_estimate_snapshot(
        self, bucket_key: str, p50: float, p80: float, sample_count: int, method: str
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO estimate_snapshots (bucket_key, p50, p80, sample_count, method)
            VALUES (?, ?, ?, ?, ?)
            """,
            (bucket_key, p50, p80, sample_count, method),
        )
        self.conn.commit()

    def latest_estimate_snapshots(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT s.id, s.bucket_key, s.p50, s.p80, s.sample_count, s.method
            FROM estimate_snapshots s
            INNER JOIN (
                SELECT bucket_key, MAX(id) AS max_id
                FROM estimate_snapshots
                GROUP BY bucket_key
            ) latest ON latest.max_id = s.id
            ORDER BY s.bucket_key ASC
            """
        )
        return [dict(row) for row in rows]

    def record_report(self, report_type: str, report_path: str) -> None:
        self.conn.execute(
            "INSERT INTO reports (report_type, report_path) VALUES (?, ?)",
            (report_type, report_path),
        )
        self.conn.commit()

    def latest_report(self, report_type: str = "weekly") -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, report_type, report_path, created_at
            FROM reports
            WHERE report_type = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (report_type,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "report_type": str(row["report_type"]),
            "report_path": str(row["report_path"]),
            "created_at": str(row["created_at"]),
        }

    def record_operation_metric(
        self, operation_family: str, outcome: str, latency_ms: float
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO operation_metrics (operation_family, outcome, count, total_latency_ms)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(operation_family, outcome) DO UPDATE SET
              count = count + 1,
              total_latency_ms = total_latency_ms + excluded.total_latency_ms
            """,
            (operation_family, outcome, float(latency_ms)),
        )
        self.conn.commit()

    def list_operation_metrics(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT operation_family, outcome, count, total_latency_ms
            FROM operation_metrics
            ORDER BY operation_family ASC, outcome ASC
            """
        )
        return [dict(row) for row in rows]
