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

            CREATE TABLE IF NOT EXISTS graph_nodes (
                node_key TEXT PRIMARY KEY,
                org TEXT NOT NULL,
                repo TEXT NOT NULL,
                node_id TEXT NOT NULL,
                issue_ref TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(org, repo, node_id)
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_node_key TEXT NOT NULL,
                to_node_key TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                source TEXT NOT NULL,
                observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                partial INTEGER NOT NULL DEFAULT 0,
                diagnostic_json TEXT NOT NULL DEFAULT '{}',
                UNIQUE(from_node_key, to_node_key, edge_type, source),
                FOREIGN KEY(from_node_key) REFERENCES graph_nodes(node_key),
                FOREIGN KEY(to_node_key) REFERENCES graph_nodes(node_key)
            );

            CREATE TABLE IF NOT EXISTS graph_ingestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                calls INTEGER NOT NULL DEFAULT 0,
                failures INTEGER NOT NULL DEFAULT 0,
                partial INTEGER NOT NULL DEFAULT 0,
                diagnostics_json TEXT NOT NULL DEFAULT '{}',
                observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS changesets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                repo TEXT NOT NULL,
                target_ref TEXT,
                payload_json TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                tenant_context_json TEXT NOT NULL DEFAULT '{}',
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                UNIQUE(idempotency_key)
            );

            CREATE TABLE IF NOT EXISTS approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                changeset_id INTEGER NOT NULL,
                approved_by TEXT NOT NULL,
                tenant_context_json TEXT NOT NULL DEFAULT '{}',
                approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(changeset_id) REFERENCES changesets(id)
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_json TEXT NOT NULL,
                tenant_context_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS onboarding_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                readiness_state TEXT NOT NULL DEFAULT 'pending_context',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_profile TEXT NOT NULL,
                model TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS agent_run_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                reason_code TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        if not self._has_column("changesets", "tenant_context_json"):
            self.conn.execute(
                "ALTER TABLE changesets ADD COLUMN tenant_context_json TEXT NOT NULL DEFAULT '{}'"
            )
        if not self._has_column("changesets", "retry_count"):
            self.conn.execute(
                "ALTER TABLE changesets ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"
            )
        if not self._has_column("changesets", "last_error"):
            self.conn.execute("ALTER TABLE changesets ADD COLUMN last_error TEXT")
        if not self._has_column("approvals", "tenant_context_json"):
            self.conn.execute(
                "ALTER TABLE approvals ADD COLUMN tenant_context_json TEXT NOT NULL DEFAULT '{}'"
            )
        if not self._has_column("audit_events", "tenant_context_json"):
            self.conn.execute(
                "ALTER TABLE audit_events ADD COLUMN tenant_context_json TEXT NOT NULL DEFAULT '{}'"
            )
        if not self._has_column("agent_runs", "run_id"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN run_id TEXT")
        if not self._has_column("agent_runs", "created_by"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN created_by TEXT DEFAULT ''")
        if not self._has_column("agent_runs", "status"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN status TEXT DEFAULT 'proposed'")
        if not self._has_column("agent_runs", "status_reason"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN status_reason TEXT DEFAULT ''")
        if not self._has_column("agent_runs", "requires_approval"):
            self.conn.execute(
                "ALTER TABLE agent_runs ADD COLUMN requires_approval INTEGER DEFAULT 1"
            )
        if not self._has_column("agent_runs", "intent"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN intent TEXT DEFAULT ''")
        if not self._has_column("agent_runs", "spec_json"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN spec_json TEXT DEFAULT '{}'")
        if not self._has_column("agent_runs", "adapter_name"):
            self.conn.execute(
                "ALTER TABLE agent_runs ADD COLUMN adapter_name TEXT DEFAULT 'manual'"
            )
        if not self._has_column("agent_runs", "claimed_by"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN claimed_by TEXT")
        if not self._has_column("agent_runs", "claim_expires_at"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN claim_expires_at TEXT")
        if not self._has_column("agent_runs", "retry_count"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN retry_count INTEGER DEFAULT 0")
        if not self._has_column("agent_runs", "max_retries"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN max_retries INTEGER DEFAULT 2")
        if not self._has_column("agent_runs", "next_attempt_at"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN next_attempt_at TEXT")
        if not self._has_column("agent_runs", "last_error"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN last_error TEXT")
        if not self._has_column("agent_runs", "job_id"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN job_id TEXT")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_source_type ON graph_edges(source, edge_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_from_to ON graph_edges(from_node_key, to_node_key)"
        )
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_runs_run_id ON agent_runs(run_id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_agent_runs_queue ON agent_runs(status, next_attempt_at, id)"
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
        tenant_context: dict[str, Any] | None = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO changesets (
              operation, repo, target_ref, payload_json, idempotency_key, tenant_context_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                operation,
                repo,
                target_ref or None,
                json.dumps(payload),
                idempotency_key,
                json.dumps(self._normalize_tenant_context(tenant_context), sort_keys=True),
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
            "tenant_context": json.loads(row["tenant_context_json"] or "{}"),
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

    def record_approval(
        self,
        changeset_id: int,
        approved_by: str,
        tenant_context: dict[str, Any] | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO approvals (changeset_id, approved_by, tenant_context_json) VALUES (?, ?, ?)",
            (
                changeset_id,
                approved_by,
                json.dumps(self._normalize_tenant_context(tenant_context), sort_keys=True),
            ),
        )
        self.conn.commit()

    def append_audit_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        tenant_context: dict[str, Any] | None = None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO audit_events (event_type, event_json, tenant_context_json) VALUES (?, ?, ?)",
            (
                event_type,
                json.dumps(payload),
                json.dumps(self._normalize_tenant_context(tenant_context), sort_keys=True),
            ),
        )
        self.conn.commit()

    def add_relationship(self, parent_ref: str, child_ref: str, source: str = "checklist") -> None:
        self.add_graph_edge(
            from_issue_ref=parent_ref,
            to_issue_ref=child_ref,
            edge_type="parent_child",
            source=source,
        )
        self.conn.commit()

    def _parse_graph_identity(self, issue_ref: str) -> tuple[str, str, str]:
        if "#" in issue_ref and not issue_ref.startswith("draft:"):
            repo_path, number = issue_ref.split("#", 1)
            if "/" in repo_path:
                org, repo = repo_path.split("/", 1)
                node_id = number.strip() or issue_ref
                return org.strip(), repo.strip(), node_id
        return "", "", issue_ref

    def upsert_graph_node(self, issue_ref: str) -> str:
        org, repo, node_id = self._parse_graph_identity(issue_ref)
        node_key = f"{org}/{repo}#{node_id}" if org and repo else issue_ref
        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_key, org, repo, node_id, issue_ref)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(issue_ref) DO UPDATE SET
              org=excluded.org,
              repo=excluded.repo,
              node_id=excluded.node_id
            """,
            (node_key, org, repo, node_id, issue_ref),
        )
        return node_key

    def add_graph_edge(
        self,
        from_issue_ref: str,
        to_issue_ref: str,
        edge_type: str,
        source: str,
        observed_at: str = "",
        partial: bool = False,
        diagnostic: dict[str, Any] | None = None,
    ) -> None:
        from_key = self.upsert_graph_node(from_issue_ref)
        to_key = self.upsert_graph_node(to_issue_ref)
        self.conn.execute(
            """
            INSERT INTO graph_edges (
              from_node_key,
              to_node_key,
              edge_type,
              source,
              observed_at,
              partial,
              diagnostic_json
            )
            VALUES (?, ?, ?, ?, COALESCE(NULLIF(?, ''), CURRENT_TIMESTAMP), ?, ?)
            ON CONFLICT(from_node_key, to_node_key, edge_type, source) DO UPDATE SET
              observed_at=excluded.observed_at,
              partial=excluded.partial,
              diagnostic_json=excluded.diagnostic_json
            """,
            (
                from_key,
                to_key,
                edge_type,
                source,
                observed_at,
                1 if partial else 0,
                json.dumps(diagnostic or {}, sort_keys=True),
            ),
        )

    def list_graph_edges(self, edge_type: str = "") -> list[dict[str, Any]]:
        params: tuple[Any, ...] = ()
        where_clause = ""
        if edge_type:
            where_clause = "WHERE ge.edge_type = ?"
            params = (edge_type,)
        rows = self.conn.execute(
            f"""
            SELECT
              pn.issue_ref AS from_issue_ref,
              cn.issue_ref AS to_issue_ref,
              ge.edge_type,
              ge.source,
              ge.observed_at,
              ge.partial,
              ge.diagnostic_json
            FROM graph_edges ge
            INNER JOIN graph_nodes pn ON pn.node_key = ge.from_node_key
            INNER JOIN graph_nodes cn ON cn.node_key = ge.to_node_key
            {where_clause}
            ORDER BY
              pn.issue_ref ASC,
              cn.issue_ref ASC,
              ge.edge_type ASC,
              ge.source ASC
            """,
            params,
        ).fetchall()
        return [
            {
                "from_issue_ref": str(row["from_issue_ref"]),
                "to_issue_ref": str(row["to_issue_ref"]),
                "edge_type": str(row["edge_type"]),
                "source": str(row["source"]),
                "observed_at": str(row["observed_at"]),
                "partial": bool(row["partial"]),
                "diagnostic": json.loads(row["diagnostic_json"]),
            }
            for row in rows
        ]

    def record_graph_ingestion(
        self,
        repo: str,
        calls: int,
        failures: int,
        partial: bool,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO graph_ingestions (repo, calls, failures, partial, diagnostics_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                repo,
                calls,
                failures,
                1 if partial else 0,
                json.dumps(diagnostics or {}, sort_keys=True),
            ),
        )
        self.conn.commit()

    def latest_graph_ingestions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT gi.repo, gi.calls, gi.failures, gi.partial, gi.diagnostics_json, gi.observed_at
            FROM graph_ingestions gi
            INNER JOIN (
                SELECT repo, MAX(id) AS max_id
                FROM graph_ingestions
                GROUP BY repo
            ) latest ON latest.max_id = gi.id
            ORDER BY gi.repo ASC
            """
        ).fetchall()
        return [
            {
                "repo": str(row["repo"]),
                "calls": int(row["calls"]),
                "failures": int(row["failures"]),
                "partial": bool(row["partial"]),
                "diagnostics": json.loads(row["diagnostics_json"]),
                "observed_at": str(row["observed_at"]),
            }
            for row in rows
        ]

    def get_related(self, issue_ref: str) -> dict[str, list[str]]:
        parent_rows = self.conn.execute(
            """
            SELECT pn.issue_ref AS parent_ref
            FROM graph_edges ge
            INNER JOIN graph_nodes pn ON pn.node_key = ge.from_node_key
            INNER JOIN graph_nodes cn ON cn.node_key = ge.to_node_key
            WHERE ge.edge_type = 'parent_child' AND cn.issue_ref = ?
            ORDER BY pn.issue_ref ASC
            """,
            (issue_ref,),
        ).fetchall()
        child_rows = self.conn.execute(
            """
            SELECT cn.issue_ref AS child_ref
            FROM graph_edges ge
            INNER JOIN graph_nodes pn ON pn.node_key = ge.from_node_key
            INNER JOIN graph_nodes cn ON cn.node_key = ge.to_node_key
            WHERE ge.edge_type = 'parent_child' AND pn.issue_ref = ?
            ORDER BY cn.issue_ref ASC
            """,
            (issue_ref,),
        ).fetchall()
        return {
            "parents": [row[0] for row in parent_rows],
            "children": [row[0] for row in child_rows],
        }

    def list_relationships(self) -> list[dict[str, str]]:
        rows = self.conn.execute(
            """
            SELECT
              pn.issue_ref AS parent_ref,
              cn.issue_ref AS child_ref,
              ge.source AS source
            FROM graph_edges ge
            INNER JOIN graph_nodes pn ON pn.node_key = ge.from_node_key
            INNER JOIN graph_nodes cn ON cn.node_key = ge.to_node_key
            WHERE ge.edge_type = 'parent_child'
            ORDER BY pn.issue_ref ASC, cn.issue_ref ASC, ge.source ASC
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

    def _normalize_tenant_context(self, tenant_context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(tenant_context or {})
        tenant_mode = str(context.get("tenant_mode", "single_tenant")).strip() or "single_tenant"
        context["tenant_mode"] = tenant_mode
        context["org"] = str(context.get("org", "")).strip()
        context["installation_id"] = str(context.get("installation_id", "")).strip()
        return context

    def get_onboarding_state(self) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT readiness_state, updated_at FROM onboarding_state WHERE id = 1"
        ).fetchone()
        if row is None:
            return {"readiness_state": "pending_context", "updated_at": ""}
        return {
            "readiness_state": str(row["readiness_state"]),
            "updated_at": str(row["updated_at"]),
        }

    def set_onboarding_state(self, readiness_state: str) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO onboarding_state (id, readiness_state, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
              readiness_state=excluded.readiness_state,
              updated_at=CURRENT_TIMESTAMP
            """,
            (readiness_state,),
        )
        self.conn.commit()
        return self.get_onboarding_state()

    def list_pending_changesets(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id FROM changesets WHERE status = 'pending' ORDER BY id ASC"
        )
        return [self.get_changeset(int(row[0])) for row in rows if row is not None]

    def list_audit_events(
        self,
        event_type: str | None = None,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if event_type and run_id:
            rows = self.conn.execute(
                "SELECT id, event_type, event_json, tenant_context_json, created_at FROM audit_events WHERE event_type = ? AND json_extract(event_json, '$.run_id') = ? ORDER BY id ASC",
                (event_type, run_id),
            )
        elif event_type:
            rows = self.conn.execute(
                "SELECT id, event_type, event_json, tenant_context_json, created_at FROM audit_events WHERE event_type = ? ORDER BY id ASC",
                (event_type,),
            )
        elif run_id:
            rows = self.conn.execute(
                "SELECT id, event_type, event_json, tenant_context_json, created_at FROM audit_events WHERE json_extract(event_json, '$.run_id') = ? ORDER BY id ASC",
                (run_id,),
            )
        else:
            rows = self.conn.execute(
                "SELECT id, event_type, event_json, tenant_context_json, created_at FROM audit_events ORDER BY id ASC"
            )
        return [
            {
                "id": int(row["id"]),
                "event_type": row["event_type"],
                "payload": json.loads(row["event_json"]),
                "tenant_context": json.loads(row["tenant_context_json"] or "{}"),
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

    def create_agent_run(
        self,
        run_id: str,
        spec: dict[str, Any],
        created_by: str,
        adapter_name: str = "manual",
        max_retries: int = 2,
    ) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO agent_runs (
              run_id, prompt_profile, model, created_by, status, status_reason,
              requires_approval, intent, spec_json, adapter_name, max_retries,
              next_attempt_at
            )
            VALUES (?, ?, ?, ?, 'proposed', 'run_created', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                run_id,
                str(spec.get("prompt_profile", "default")),
                str(spec.get("model", "")),
                created_by,
                1 if spec.get("requires_approval", True) else 0,
                str(spec.get("intent", "")),
                json.dumps(spec, sort_keys=True),
                adapter_name,
                int(max_retries),
            ),
        )
        self.conn.commit()
        return self.get_agent_run(run_id) or {}

    def get_agent_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "run_id": str(row["run_id"]),
            "prompt_profile": str(row["prompt_profile"]),
            "model": str(row["model"]),
            "created_by": str(row["created_by"]),
            "status": str(row["status"]),
            "status_reason": str(row["status_reason"] or ""),
            "requires_approval": bool(row["requires_approval"]),
            "intent": str(row["intent"] or ""),
            "spec": json.loads(row["spec_json"] or "{}"),
            "adapter_name": str(row["adapter_name"] or "manual"),
            "claimed_by": str(row["claimed_by"] or ""),
            "claim_expires_at": str(row["claim_expires_at"] or ""),
            "retry_count": int(row["retry_count"] or 0),
            "max_retries": int(row["max_retries"] or 0),
            "next_attempt_at": str(row["next_attempt_at"] or ""),
            "last_error": str(row["last_error"] or ""),
            "job_id": str(row["job_id"] or ""),
            "started_at": str(row["started_at"]),
            "completed_at": str(row["completed_at"] or ""),
        }

    def update_agent_run_status(
        self,
        run_id: str,
        to_status: str,
        reason_code: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        row = self.conn.execute(
            "SELECT status FROM agent_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Unknown agent run")
        from_status = str(row["status"])
        completed_at_expr = (
            "CURRENT_TIMESTAMP"
            if to_status in {"completed", "failed", "cancelled", "rejected"}
            else "NULL"
        )
        self.conn.execute(
            f"""
            UPDATE agent_runs
            SET status = ?, status_reason = ?, completed_at = {completed_at_expr}
            WHERE run_id = ?
            """,
            (to_status, reason_code, run_id),
        )
        self.conn.execute(
            """
            INSERT INTO agent_run_transitions (run_id, from_status, to_status, reason_code, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                from_status,
                to_status,
                reason_code,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        self.conn.commit()

    def list_agent_run_transitions(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT run_id, from_status, to_status, reason_code, metadata_json, created_at
            FROM agent_run_transitions
            WHERE run_id = ?
            ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()
        return [
            {
                "run_id": str(row["run_id"]),
                "from_status": str(row["from_status"] or ""),
                "to_status": str(row["to_status"]),
                "reason_code": str(row["reason_code"]),
                "metadata": json.loads(row["metadata_json"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def claim_agent_runs(
        self, worker_id: str, limit: int = 1, lease_seconds: int = 30
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT run_id
            FROM agent_runs
            WHERE status = 'approved'
              AND COALESCE(next_attempt_at, CURRENT_TIMESTAMP) <= CURRENT_TIMESTAMP
              AND (
                claimed_by IS NULL OR claimed_by = '' OR claim_expires_at IS NULL
                OR claim_expires_at <= CURRENT_TIMESTAMP
                OR claimed_by = ?
              )
            ORDER BY id ASC
            LIMIT ?
            """,
            (worker_id, limit),
        ).fetchall()
        claimed_runs: list[dict[str, Any]] = []
        for row in rows:
            run_id = str(row["run_id"])
            self.conn.execute(
                """
                UPDATE agent_runs
                SET claimed_by = ?,
                    claim_expires_at = datetime(CURRENT_TIMESTAMP, '+' || ? || ' seconds')
                WHERE run_id = ?
                """,
                (worker_id, int(lease_seconds), run_id),
            )
            fetched = self.get_agent_run(run_id)
            if fetched is not None:
                claimed_runs.append(fetched)
        self.conn.commit()
        return claimed_runs

    def clear_agent_run_claim(self, run_id: str) -> None:
        self.conn.execute(
            "UPDATE agent_runs SET claimed_by = NULL, claim_expires_at = NULL WHERE run_id = ?",
            (run_id,),
        )
        self.conn.commit()

    def set_agent_run_execution(
        self,
        run_id: str,
        *,
        job_id: str = "",
        retry_count: int | None = None,
        next_attempt_seconds: int | None = None,
        last_error: str = "",
    ) -> None:
        if retry_count is not None:
            self.conn.execute(
                "UPDATE agent_runs SET retry_count = ? WHERE run_id = ?",
                (retry_count, run_id),
            )
        if next_attempt_seconds is not None:
            self.conn.execute(
                "UPDATE agent_runs SET next_attempt_at = datetime(CURRENT_TIMESTAMP, '+' || ? || ' seconds') WHERE run_id = ?",
                (int(next_attempt_seconds), run_id),
            )
        if job_id:
            self.conn.execute("UPDATE agent_runs SET job_id = ? WHERE run_id = ?", (job_id, run_id))
        if last_error:
            self.conn.execute(
                "UPDATE agent_runs SET last_error = ? WHERE run_id = ?",
                (last_error, run_id),
            )
        self.conn.commit()
