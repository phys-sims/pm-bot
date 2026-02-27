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
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._configure_connection()
        self._init_schema()

    def _configure_connection(self) -> None:
        """Apply local-first SQLite settings for durability and concurrent reads."""

        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA temp_store=MEMORY")

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
                graph_id TEXT NOT NULL DEFAULT '',
                thread_id TEXT,
                budgets_json TEXT NOT NULL DEFAULT '{}',
                tools_allowed_json TEXT NOT NULL DEFAULT '[]',
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                artifact_paths_json TEXT NOT NULL DEFAULT "[]"
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

            CREATE TABLE IF NOT EXISTS run_interrupts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interrupt_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                risk TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                decision_json TEXT NOT NULL DEFAULT '{}',
                decision_actor TEXT NOT NULL DEFAULT '',
                decision_action TEXT NOT NULL DEFAULT '',
                resolved_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS run_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_id TEXT NOT NULL UNIQUE,
                run_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                uri TEXT NOT NULL,
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

            CREATE TABLE IF NOT EXISTS board_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                trigger_source TEXT NOT NULL,
                run_id TEXT NOT NULL DEFAULT '',
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS board_snapshot_diffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo TEXT NOT NULL,
                previous_snapshot_id INTEGER,
                current_snapshot_id INTEGER NOT NULL,
                drift_score REAL NOT NULL,
                significant_drift INTEGER NOT NULL,
                triggered_replanner INTEGER NOT NULL,
                proposal_count INTEGER NOT NULL DEFAULT 0,
                diff_json TEXT NOT NULL,
                run_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(previous_snapshot_id) REFERENCES board_snapshots(id),
                FOREIGN KEY(current_snapshot_id) REFERENCES board_snapshots(id)
            );

            CREATE TABLE IF NOT EXISTS orchestration_plan (
                plan_id TEXT PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'expanded',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS task_runs (
                task_run_id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                deps_json TEXT NOT NULL DEFAULT '[]',
                run_id TEXT NOT NULL DEFAULT '',
                thread_id TEXT NOT NULL DEFAULT '',
                retries INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                claimed_by TEXT,
                claim_expires_at TEXT,
                last_error_code TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(plan_id) REFERENCES orchestration_plan(plan_id)
            );

            CREATE TABLE IF NOT EXISTS task_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                from_task TEXT NOT NULL,
                to_task TEXT NOT NULL,
                UNIQUE(plan_id, from_task, to_task),
                FOREIGN KEY(plan_id) REFERENCES orchestration_plan(plan_id)
            );
            
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS repo_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                full_name TEXT NOT NULL UNIQUE,
                default_branch TEXT NOT NULL DEFAULT 'main',
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_sync_at TEXT,
                last_error TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(workspace_id) REFERENCES workspaces(id)
            );

            CREATE TABLE IF NOT EXISTS issue_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                issue_number INTEGER NOT NULL,
                state TEXT NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                FOREIGN KEY(repo_id) REFERENCES repo_registry(id),
                UNIQUE(repo_id, issue_number)
            );

            CREATE TABLE IF NOT EXISTS pr_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                pr_number INTEGER NOT NULL,
                state TEXT NOT NULL,
                title TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                FOREIGN KEY(repo_id) REFERENCES repo_registry(id),
                UNIQUE(repo_id, pr_number)
            );

            CREATE TABLE IF NOT EXISTS sync_cursors (
                repo_id INTEGER PRIMARY KEY,
                last_issues_sync TEXT,
                last_prs_sync TEXT,
                issues_etag TEXT,
                prs_etag TEXT,
                FOREIGN KEY(repo_id) REFERENCES repo_registry(id)
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_path_or_url TEXT NOT NULL,
                repo_id INTEGER,
                revision_sha TEXT NOT NULL DEFAULT '',
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(repo_id) REFERENCES repo_registry(id)
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT NOT NULL UNIQUE,
                doc_id INTEGER NOT NULL,
                offset_start INTEGER NOT NULL,
                offset_end INTEGER NOT NULL,
                text_hash TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(doc_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS embedding_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT NOT NULL,
                qdrant_point_id TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chunk_id) REFERENCES chunks(chunk_id),
                UNIQUE(chunk_id, embedding_model)
            );

            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id TEXT PRIMARY KEY,
                repo_id INTEGER,
                scope_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                stats_json TEXT NOT NULL DEFAULT '{}',
                error_text TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(repo_id) REFERENCES repo_registry(id)
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
        if not self._has_column("agent_runs", "artifact_paths_json"):
            self.conn.execute(
                "ALTER TABLE agent_runs ADD COLUMN artifact_paths_json TEXT DEFAULT '[]'"
            )
        if not self._has_column("agent_runs", "tools_allowed_json"):
            self.conn.execute(
                "ALTER TABLE agent_runs ADD COLUMN tools_allowed_json TEXT DEFAULT '[]'"
            )
        if not self._has_column("agent_runs", "budgets_json"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN budgets_json TEXT DEFAULT '{}'")
        if not self._has_column("agent_runs", "thread_id"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN thread_id TEXT")
        if not self._has_column("agent_runs", "graph_id"):
            self.conn.execute("ALTER TABLE agent_runs ADD COLUMN graph_id TEXT DEFAULT ''")
        self.conn.execute("INSERT OR IGNORE INTO workspaces (id, name) VALUES (1, 'default')")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_repo_registry_workspace ON repo_registry(workspace_id, full_name)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_issue_cache_repo_updated ON issue_cache(repo_id, updated_at)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pr_cache_repo_updated ON pr_cache(repo_id, updated_at)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_repo_source ON documents(repo_id, source_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id, chunk_id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_embedding_records_chunk_model ON embedding_records(chunk_id, embedding_model)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_repo_status ON ingestion_jobs(repo_id, status)"
        )
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
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS run_interrupts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "interrupt_id TEXT NOT NULL UNIQUE,"
            "run_id TEXT NOT NULL,"
            "thread_id TEXT NOT NULL,"
            "kind TEXT NOT NULL,"
            "risk TEXT NOT NULL,"
            "payload_json TEXT NOT NULL DEFAULT '{}',"
            "status TEXT NOT NULL DEFAULT 'pending',"
            "decision_json TEXT NOT NULL DEFAULT '{}',"
            "decision_actor TEXT NOT NULL DEFAULT '',"
            "decision_action TEXT NOT NULL DEFAULT '',"
            "resolved_at TEXT,"
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS run_artifacts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "artifact_id TEXT NOT NULL UNIQUE,"
            "run_id TEXT NOT NULL,"
            "kind TEXT NOT NULL,"
            "uri TEXT NOT NULL,"
            "metadata_json TEXT NOT NULL DEFAULT '{}',"
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS run_checkpoint_metadata ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "run_id TEXT NOT NULL UNIQUE,"
            "thread_id TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "current_node_id TEXT NOT NULL DEFAULT '',"
            "checkpoint_path TEXT NOT NULL DEFAULT '',"
            "last_checkpoint_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_interrupts_run_status ON run_interrupts(run_id, status, id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_artifacts_run_kind ON run_artifacts(run_id, kind, id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_runs_plan_status ON task_runs(plan_id, status, task_id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_runs_claims ON task_runs(status, next_attempt_at, claim_expires_at, task_id)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_edges_plan ON task_edges(plan_id, from_task, to_task)"
        )
        if not self._has_column("task_runs", "next_attempt_at"):
            self.conn.execute("ALTER TABLE task_runs ADD COLUMN next_attempt_at TEXT")
        if not self._has_column("task_runs", "claimed_by"):
            self.conn.execute("ALTER TABLE task_runs ADD COLUMN claimed_by TEXT")
        if not self._has_column("task_runs", "claim_expires_at"):
            self.conn.execute("ALTER TABLE task_runs ADD COLUMN claim_expires_at TEXT")
        if not self._has_column("task_runs", "last_error_code"):
            self.conn.execute(
                "ALTER TABLE task_runs ADD COLUMN last_error_code TEXT NOT NULL DEFAULT ''"
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

    def add_repo_registry_entry(
        self,
        *,
        full_name: str,
        workspace_id: int = 1,
        default_branch: str = "main",
    ) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO repo_registry (workspace_id, full_name, default_branch)
            VALUES (?, ?, ?)
            """,
            (workspace_id, full_name, default_branch),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM repo_registry WHERE full_name = ?",
            (full_name,),
        ).fetchone()
        if row is None:
            raise RuntimeError("repo_registry_insert_failed")
        return {
            "id": int(row["id"]),
            "workspace_id": int(row["workspace_id"]),
            "full_name": str(row["full_name"]),
            "default_branch": str(row["default_branch"]),
            "added_at": str(row["added_at"]),
            "last_sync_at": str(row["last_sync_at"] or ""),
            "last_error": str(row["last_error"] or ""),
        }

    def get_repo_registry_entry(self, repo_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM repo_registry WHERE id = ?", (repo_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "workspace_id": int(row["workspace_id"]),
            "full_name": str(row["full_name"]),
            "default_branch": str(row["default_branch"]),
            "added_at": str(row["added_at"]),
            "last_sync_at": str(row["last_sync_at"] or ""),
            "last_error": str(row["last_error"] or ""),
        }

    def list_repo_registry_entries(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM repo_registry ORDER BY id ASC").fetchall()
        return [
            {
                "id": int(row["id"]),
                "workspace_id": int(row["workspace_id"]),
                "full_name": str(row["full_name"]),
                "default_branch": str(row["default_branch"]),
                "added_at": str(row["added_at"]),
                "last_sync_at": str(row["last_sync_at"] or ""),
                "last_error": str(row["last_error"] or ""),
            }
            for row in rows
        ]

    def update_repo_registry_sync_status(
        self, *, repo_id: int, last_sync_at: str, last_error: str
    ) -> None:
        self.conn.execute(
            "UPDATE repo_registry SET last_sync_at = ?, last_error = ? WHERE id = ?",
            (last_sync_at or None, last_error, repo_id),
        )
        self.conn.commit()

    def upsert_issue_cache(
        self,
        *,
        repo_id: int,
        issue_number: int,
        state: str,
        title: str,
        updated_at: str,
        raw_json: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO issue_cache (repo_id, issue_number, state, title, updated_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, issue_number) DO UPDATE SET
              state=excluded.state,
              title=excluded.title,
              updated_at=excluded.updated_at,
              raw_json=excluded.raw_json
            """,
            (repo_id, issue_number, state, title, updated_at, json.dumps(raw_json, sort_keys=True)),
        )
        self.conn.commit()

    def list_issue_cache(self, *, repo_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT issue_number, state, title, updated_at, raw_json
            FROM issue_cache
            WHERE repo_id = ?
            ORDER BY issue_number ASC
            """,
            (repo_id,),
        ).fetchall()
        return [
            {
                "issue_number": int(row["issue_number"]),
                "state": str(row["state"]),
                "title": str(row["title"]),
                "updated_at": str(row["updated_at"]),
                "raw_json": json.loads(row["raw_json"]),
            }
            for row in rows
        ]

    def upsert_pr_cache(
        self,
        *,
        repo_id: int,
        pr_number: int,
        state: str,
        title: str,
        updated_at: str,
        raw_json: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO pr_cache (repo_id, pr_number, state, title, updated_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, pr_number) DO UPDATE SET
              state=excluded.state,
              title=excluded.title,
              updated_at=excluded.updated_at,
              raw_json=excluded.raw_json
            """,
            (repo_id, pr_number, state, title, updated_at, json.dumps(raw_json, sort_keys=True)),
        )
        self.conn.commit()

    def list_pr_cache(self, *, repo_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT pr_number, state, title, updated_at, raw_json
            FROM pr_cache
            WHERE repo_id = ?
            ORDER BY pr_number ASC
            """,
            (repo_id,),
        ).fetchall()
        return [
            {
                "pr_number": int(row["pr_number"]),
                "state": str(row["state"]),
                "title": str(row["title"]),
                "updated_at": str(row["updated_at"]),
                "raw_json": json.loads(row["raw_json"]),
            }
            for row in rows
        ]

    def upsert_sync_cursor(
        self,
        *,
        repo_id: int,
        last_issues_sync: str,
        last_prs_sync: str,
        issues_etag: str | None = None,
        prs_etag: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO sync_cursors (repo_id, last_issues_sync, last_prs_sync, issues_etag, prs_etag)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
              last_issues_sync=excluded.last_issues_sync,
              last_prs_sync=excluded.last_prs_sync,
              issues_etag=excluded.issues_etag,
              prs_etag=excluded.prs_etag
            """,
            (repo_id, last_issues_sync or None, last_prs_sync or None, issues_etag, prs_etag),
        )
        self.conn.commit()

    def get_sync_cursor(self, repo_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM sync_cursors WHERE repo_id = ?", (repo_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "repo_id": int(row["repo_id"]),
            "last_issues_sync": str(row["last_issues_sync"] or ""),
            "last_prs_sync": str(row["last_prs_sync"] or ""),
            "issues_etag": str(row["issues_etag"] or ""),
            "prs_etag": str(row["prs_etag"] or ""),
        }

    def _normalize_tenant_context(self, tenant_context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(tenant_context or {})
        tenant_mode = str(context.get("tenant_mode", "single_tenant")).strip() or "single_tenant"
        context["tenant_mode"] = tenant_mode
        context["org"] = str(context.get("org", "")).strip()
        context["installation_id"] = str(context.get("installation_id", "")).strip()
        return context

    def upsert_orchestration_plan(
        self,
        *,
        plan_id: str,
        repo_id: int,
        source: str,
        payload: dict[str, Any],
        status: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO orchestration_plan (plan_id, repo_id, source, payload_json, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(plan_id) DO UPDATE SET
              repo_id=excluded.repo_id,
              source=excluded.source,
              payload_json=excluded.payload_json,
              status=excluded.status,
              updated_at=CURRENT_TIMESTAMP
            """,
            (plan_id, repo_id, source, json.dumps(payload, sort_keys=True), status),
        )
        self.conn.commit()

    def replace_task_graph(
        self,
        *,
        plan_id: str,
        task_runs: list[dict[str, Any]],
        edges: list[dict[str, str]],
    ) -> None:
        self.conn.execute("DELETE FROM task_runs WHERE plan_id = ?", (plan_id,))
        self.conn.execute("DELETE FROM task_edges WHERE plan_id = ?", (plan_id,))
        for task_run in task_runs:
            self.conn.execute(
                """
                INSERT INTO task_runs (
                  task_run_id, plan_id, task_id, status, deps_json, run_id, thread_id, retries,
                  next_attempt_at, claimed_by, claim_expires_at, last_error_code
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(task_run["task_run_id"]),
                    plan_id,
                    str(task_run["task_id"]),
                    str(task_run.get("status", "pending")),
                    json.dumps(task_run.get("deps", []), sort_keys=True),
                    str(task_run.get("run_id", "")),
                    str(task_run.get("thread_id", "")),
                    int(task_run.get("retries", 0)),
                    str(task_run.get("next_attempt_at", "")) or None,
                    str(task_run.get("claimed_by", "")) or None,
                    str(task_run.get("claim_expires_at", "")) or None,
                    str(task_run.get("last_error_code", "")),
                ),
            )
        for edge in edges:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO task_edges (plan_id, from_task, to_task)
                VALUES (?, ?, ?)
                """,
                (plan_id, edge["from_task"], edge["to_task"]),
            )
        self.conn.commit()

    def get_orchestration_plan(self, plan_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT plan_id, repo_id, source, payload_json, status FROM orchestration_plan WHERE plan_id = ?",
            (plan_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "plan_id": str(row["plan_id"]),
            "repo_id": int(row["repo_id"]),
            "source": str(row["source"]),
            "payload": json.loads(row["payload_json"]),
            "status": str(row["status"]),
        }

    def list_task_runs(self, plan_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT task_run_id, task_id, status, deps_json, run_id, thread_id, retries,
                   next_attempt_at, claimed_by, claim_expires_at, last_error_code
            FROM task_runs
            WHERE plan_id = ?
            ORDER BY task_id ASC
            """,
            (plan_id,),
        ).fetchall()
        return [
            {
                "task_run_id": str(row["task_run_id"]),
                "task_id": str(row["task_id"]),
                "status": str(row["status"]),
                "deps": json.loads(row["deps_json"]),
                "run_id": str(row["run_id"] or ""),
                "thread_id": str(row["thread_id"] or ""),
                "retries": int(row["retries"]),
                "next_attempt_at": str(row["next_attempt_at"] or ""),
                "claimed_by": str(row["claimed_by"] or ""),
                "claim_expires_at": str(row["claim_expires_at"] or ""),
                "last_error_code": str(row["last_error_code"] or ""),
            }
            for row in rows
        ]

    def get_task_run(self, task_run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT task_run_id, plan_id, task_id, status, deps_json, run_id, thread_id, retries,
                   next_attempt_at, claimed_by, claim_expires_at, last_error_code
            FROM task_runs
            WHERE task_run_id = ?
            """,
            (task_run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "task_run_id": str(row["task_run_id"]),
            "plan_id": str(row["plan_id"]),
            "task_id": str(row["task_id"]),
            "status": str(row["status"]),
            "deps": json.loads(row["deps_json"]),
            "run_id": str(row["run_id"] or ""),
            "thread_id": str(row["thread_id"] or ""),
            "retries": int(row["retries"]),
            "next_attempt_at": str(row["next_attempt_at"] or ""),
            "claimed_by": str(row["claimed_by"] or ""),
            "claim_expires_at": str(row["claim_expires_at"] or ""),
            "last_error_code": str(row["last_error_code"] or ""),
        }

    def claim_task_run(self, task_run_id: str, worker_id: str, lease_seconds: int) -> bool:
        cur = self.conn.execute(
            """
            UPDATE task_runs
            SET claimed_by = ?,
                claim_expires_at = datetime(CURRENT_TIMESTAMP, '+' || ? || ' seconds'),
                status = CASE WHEN status = 'pending' THEN 'running' ELSE status END,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_run_id = ?
              AND status IN ('pending', 'running')
              AND (COALESCE(next_attempt_at, CURRENT_TIMESTAMP) <= CURRENT_TIMESTAMP)
              AND (
                claimed_by IS NULL OR claimed_by = '' OR claim_expires_at IS NULL
                OR claim_expires_at <= CURRENT_TIMESTAMP OR claimed_by = ?
              )
            """,
            (worker_id, int(lease_seconds), task_run_id, worker_id),
        )
        self.conn.commit()
        return int(cur.rowcount or 0) > 0

    def update_task_run_result(
        self,
        task_run_id: str,
        *,
        status: str,
        retries: int | None = None,
        next_attempt_seconds: int | None = None,
        run_id: str | None = None,
        thread_id: str | None = None,
        reason_code: str = "",
        clear_claim: bool = False,
    ) -> None:
        updates: list[str] = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        args: list[Any] = [status]
        if retries is not None:
            updates.append("retries = ?")
            args.append(int(retries))
        if next_attempt_seconds is not None:
            updates.append("next_attempt_at = datetime(CURRENT_TIMESTAMP, '+' || ? || ' seconds')")
            args.append(int(next_attempt_seconds))
        elif status in {"succeeded", "failed"}:
            updates.append("next_attempt_at = NULL")
        if run_id is not None:
            updates.append("run_id = ?")
            args.append(run_id)
        if thread_id is not None:
            updates.append("thread_id = ?")
            args.append(thread_id)
        if reason_code:
            updates.append("last_error_code = ?")
            args.append(reason_code)
        if clear_claim:
            updates.append("claimed_by = NULL")
            updates.append("claim_expires_at = NULL")
        args.append(task_run_id)
        self.conn.execute(f"UPDATE task_runs SET {', '.join(updates)} WHERE task_run_id = ?", args)
        self.conn.commit()

    def list_task_edges(self, plan_id: str) -> list[dict[str, str]]:
        rows = self.conn.execute(
            """
            SELECT from_task, to_task FROM task_edges
            WHERE plan_id = ?
            ORDER BY from_task ASC, to_task ASC
            """,
            (plan_id,),
        ).fetchall()
        return [
            {"from_task": str(row["from_task"]), "to_task": str(row["to_task"])} for row in rows
        ]

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

    def store_board_snapshot(
        self,
        *,
        repo: str,
        trigger_source: str,
        snapshot: dict[str, Any],
        run_id: str = "",
    ) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO board_snapshots (repo, trigger_source, run_id, snapshot_json)
            VALUES (?, ?, ?, ?)
            """,
            (repo, trigger_source, run_id, json.dumps(snapshot, sort_keys=True)),
        )
        self.conn.commit()
        snapshot_id = int(cur.lastrowid)
        return self.get_board_snapshot(snapshot_id) or {}

    def get_board_snapshot(self, snapshot_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id, repo, trigger_source, run_id, snapshot_json, created_at
            FROM board_snapshots
            WHERE id = ?
            """,
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "repo": str(row["repo"]),
            "trigger_source": str(row["trigger_source"]),
            "run_id": str(row["run_id"] or ""),
            "snapshot": json.loads(row["snapshot_json"]),
            "created_at": str(row["created_at"]),
        }

    def latest_board_snapshot(self, repo: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT id
            FROM board_snapshots
            WHERE repo = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (repo,),
        ).fetchone()
        if row is None:
            return None
        return self.get_board_snapshot(int(row["id"]))

    def store_board_snapshot_diff(
        self,
        *,
        repo: str,
        previous_snapshot_id: int | None,
        current_snapshot_id: int,
        drift_score: float,
        significant_drift: bool,
        triggered_replanner: bool,
        proposal_count: int,
        diff: dict[str, Any],
        run_id: str = "",
    ) -> dict[str, Any]:
        cur = self.conn.execute(
            """
            INSERT INTO board_snapshot_diffs (
              repo,
              previous_snapshot_id,
              current_snapshot_id,
              drift_score,
              significant_drift,
              triggered_replanner,
              proposal_count,
              diff_json,
              run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo,
                previous_snapshot_id,
                current_snapshot_id,
                float(drift_score),
                1 if significant_drift else 0,
                1 if triggered_replanner else 0,
                int(proposal_count),
                json.dumps(diff, sort_keys=True),
                run_id,
            ),
        )
        self.conn.commit()
        diff_id = int(cur.lastrowid)
        return self.get_board_snapshot_diff(diff_id) or {}

    def get_board_snapshot_diff(self, diff_id: int) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT
              id,
              repo,
              previous_snapshot_id,
              current_snapshot_id,
              drift_score,
              significant_drift,
              triggered_replanner,
              proposal_count,
              diff_json,
              run_id,
              created_at
            FROM board_snapshot_diffs
            WHERE id = ?
            """,
            (diff_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "id": int(row["id"]),
            "repo": str(row["repo"]),
            "previous_snapshot_id": (
                int(row["previous_snapshot_id"])
                if row["previous_snapshot_id"] is not None
                else None
            ),
            "current_snapshot_id": int(row["current_snapshot_id"]),
            "drift_score": float(row["drift_score"]),
            "significant_drift": bool(row["significant_drift"]),
            "triggered_replanner": bool(row["triggered_replanner"]),
            "proposal_count": int(row["proposal_count"]),
            "diff": json.loads(row["diff_json"]),
            "run_id": str(row["run_id"] or ""),
            "created_at": str(row["created_at"]),
        }

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
              run_id, prompt_profile, model, graph_id, thread_id, budgets_json, tools_allowed_json,
              created_by, status, status_reason,
              requires_approval, intent, spec_json, adapter_name, max_retries,
              next_attempt_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'proposed', 'run_created', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                run_id,
                str(spec.get("prompt_profile", "default")),
                str(spec.get("model", "")),
                str(spec.get("execution", {}).get("graph_id", spec.get("graph_id", ""))),
                spec.get("execution", {}).get("thread_id", spec.get("thread_id")),
                json.dumps(
                    spec.get("execution", {}).get("budget", spec.get("budgets", {})), sort_keys=True
                ),
                json.dumps(
                    spec.get("execution", {}).get("tools_allowed", spec.get("tools_allowed", [])),
                    sort_keys=True,
                ),
                created_by,
                1 if spec.get("requires_approval", True) else 0,
                str(spec.get("intent", spec.get("goal", ""))),
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
            "graph_id": str(row["graph_id"] or ""),
            "thread_id": str(row["thread_id"] or ""),
            "budgets": json.loads(row["budgets_json"] or "{}"),
            "tools_allowed": json.loads(row["tools_allowed_json"] or "[]"),
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
            "artifact_paths": json.loads(row["artifact_paths_json"] or "[]"),
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
        thread_id: str = "",
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
        if thread_id:
            self.conn.execute(
                "UPDATE agent_runs SET thread_id = ? WHERE run_id = ?",
                (thread_id, run_id),
            )
        self.conn.commit()

    def upsert_checkpoint_metadata(
        self,
        run_id: str,
        thread_id: str,
        status: str,
        current_node_id: str,
        checkpoint_path: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO run_checkpoint_metadata
              (run_id, thread_id, status, current_node_id, checkpoint_path, last_checkpoint_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(run_id) DO UPDATE SET
              thread_id = excluded.thread_id,
              status = excluded.status,
              current_node_id = excluded.current_node_id,
              checkpoint_path = excluded.checkpoint_path,
              last_checkpoint_at = CURRENT_TIMESTAMP
            """,
            (run_id, thread_id, status, current_node_id, checkpoint_path),
        )
        self.conn.commit()

    def get_checkpoint_metadata(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT run_id, thread_id, status, current_node_id, checkpoint_path, last_checkpoint_at
            FROM run_checkpoint_metadata WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": str(row["run_id"]),
            "thread_id": str(row["thread_id"]),
            "status": str(row["status"]),
            "current_node_id": str(row["current_node_id"]),
            "checkpoint_path": str(row["checkpoint_path"]),
            "last_checkpoint_at": str(row["last_checkpoint_at"]),
        }

    def set_agent_run_artifacts(self, run_id: str, artifact_paths: list[str]) -> None:
        normalized = [str(path) for path in artifact_paths]
        self.conn.execute(
            "UPDATE agent_runs SET artifact_paths_json = ? WHERE run_id = ?",
            (json.dumps(normalized, sort_keys=True), run_id),
        )
        for idx, path in enumerate(normalized):
            self.conn.execute(
                """
                INSERT OR REPLACE INTO run_artifacts (artifact_id, run_id, kind, uri, metadata_json)
                VALUES (?, ?, 'log', ?, '{}')
                """,
                (f"{run_id}:artifact:{idx}", run_id, path),
            )
        self.conn.commit()

    def list_run_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT artifact_id, run_id, kind, uri, metadata_json, created_at
            FROM run_artifacts WHERE run_id = ? ORDER BY id ASC
            """,
            (run_id,),
        ).fetchall()
        return [
            {
                "schema_version": "run_artifact/v1",
                "artifact_id": str(row["artifact_id"]),
                "run_id": str(row["run_id"]),
                "kind": str(row["kind"]),
                "uri": str(row["uri"]),
                "metadata": json.loads(row["metadata_json"] or "{}"),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def create_run_interrupt(
        self,
        interrupt_id: str,
        run_id: str,
        thread_id: str,
        kind: str,
        risk: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO run_interrupts (interrupt_id, run_id, thread_id, kind, risk, payload_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (interrupt_id, run_id, thread_id, kind, risk, json.dumps(payload, sort_keys=True)),
        )
        self.conn.commit()
        return self.get_run_interrupt(interrupt_id) or {}

    def get_run_interrupt(self, interrupt_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT interrupt_id, run_id, thread_id, kind, risk, payload_json, status,
                   decision_json, decision_actor, decision_action, created_at, resolved_at
            FROM run_interrupts WHERE interrupt_id = ?
            """,
            (interrupt_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "schema_version": "run_interrupt/v1",
            "interrupt_id": str(row["interrupt_id"]),
            "run_id": str(row["run_id"]),
            "thread_id": str(row["thread_id"]),
            "kind": str(row["kind"]),
            "risk": str(row["risk"]),
            "payload": json.loads(row["payload_json"] or "{}"),
            "status": str(row["status"]),
            "decision": json.loads(row["decision_json"] or "{}"),
            "decision_actor": str(row["decision_actor"] or ""),
            "decision_action": str(row["decision_action"] or ""),
            "created_at": str(row["created_at"]),
            "resolved_at": str(row["resolved_at"] or ""),
        }

    def resolve_run_interrupt(
        self,
        interrupt_id: str,
        action: str,
        actor: str,
        edited_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        interrupt = self.get_run_interrupt(interrupt_id)
        if interrupt is None:
            return None
        next_status = {"approve": "approved", "reject": "rejected", "edit": "edited"}.get(action)
        if next_status is None:
            raise ValueError("invalid_interrupt_action")
        payload = interrupt["payload"]
        if action == "edit" and isinstance(edited_payload, dict):
            payload = edited_payload
            self.conn.execute(
                "UPDATE run_interrupts SET payload_json = ? WHERE interrupt_id = ?",
                (json.dumps(edited_payload, sort_keys=True), interrupt_id),
            )
        self.conn.execute(
            """
            UPDATE run_interrupts
            SET status = ?, decision_json = ?, decision_actor = ?, decision_action = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE interrupt_id = ?
            """,
            (
                next_status,
                json.dumps({"action": action, "payload": payload}, sort_keys=True),
                actor,
                action,
                interrupt_id,
            ),
        )
        self.conn.commit()
        return self.get_run_interrupt(interrupt_id)

    def list_run_interrupts(self, run_id: str | None = None) -> list[dict[str, Any]]:
        if run_id:
            rows = self.conn.execute(
                """
                SELECT interrupt_id FROM run_interrupts WHERE run_id = ? ORDER BY id ASC
                """,
                (run_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT interrupt_id FROM run_interrupts ORDER BY id ASC"
            ).fetchall()
        return [self.get_run_interrupt(str(row[0])) for row in rows if row is not None]
