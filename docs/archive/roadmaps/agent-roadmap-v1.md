# Agent Roadmap v1 — Safe Write Orchestrator + Context Packs
_Date: 2026-02-21_

## Mission
Upgrade v0 into a tool you can trust across repos:
- Maintain a canonical WorkItem graph in a local DB.
- Ingest updates from GitHub (webhooks/polling).
- Add **propose → approve → publish** so agents never write directly.
- Generate per-issue **Context Packs** for downstream coding agents.

## Constraints
- Keep compatibility with existing templates and field sync behavior.
- Keep “draft-only” as the default; writes require approval.
- Limit scope initially to:
  - `phys-sims/.github`
  - `phys-sims/phys-pipeline`

---

## Deliverables
1) **Server + DB**
- `server/app.py` (FastAPI recommended)
- SQLite first (Postgres later)
- Tables:
  - work_items (canonical JSON + key fields)
  - relationships
  - agent_runs (prompt profile, model, timestamps)
  - changesets (diffs proposed by agents)
  - approvals
  - audit_events

2) **GitHub connector**
- Minimal endpoints:
  - fetch issue by URL/number
  - list issues by label/area/status
  - write issue (create/update) **only via approved changeset**
  - optional: add item to Project (or rely on existing action)
- Webhook ingestion:
  - issues: opened/edited/labeled
  - pull requests: optional, later
- Store raw webhook payloads for audit/debug.

3) **Changeset + approval workflow**
- Agent outputs a proposed changeset:
  - create issue, edit issue, link parent/child, etc
- Human approves in a local web UI (or CLI approval).
- Only then execute writes to GitHub.

4) **Context Pack builder**
- Deterministically assemble:
  - issue body + key comments (optional)
  - parent/child issues (one hop)
  - referenced ADR paths from templates
  - small excerpt of ADR files (first N lines or specific sections)
- Add caching with a content hash.

5) **Agent tool API (for Codex to call indirectly)**
Even if Codex can’t “call tools” directly, structure code so you *could* expose:
- `GET /work-items/<built-in function id>`
- `POST /draft` (returns JSON + markdown)
- `POST /changesets` (create proposal)
- `POST /approvals/<built-in function id>` (approve + execute)

---

## Implementation tasks (Codex-sized)
### Task A: DB + models + migrations
- Define tables + SQLAlchemy models
- Include migration tooling (alembic) if using Postgres later

### Task B: GitHub auth + connector
- Implement GitHub App auth or PAT
- Implement read endpoints + rate limiting
- Implement write endpoints behind changeset approval

### Task C: webhook receiver
- Validate signatures (if using GitHub App)
- Normalize events into audit_events
- Upsert work_items on changes

### Task D: changeset engine
- Define a JSON patch format for issue creation/update
- Render “diff previews” for UI review

### Task E: context pack builder
- “Pack profiles” (pm-drafting vs coding)
- Token budget enforcement (simple char budget in v1)
- Hashing + caching

### Task F: minimal UI for approvals
- A simple page listing pending changesets
- Diff preview and “Approve” button
- Show audit log entries per changeset

---

## Acceptance criteria
- An agent cannot write without a recorded approval.
- Given an issue URL, server can produce a context pack within a deterministic size budget.
- System can ingest issue edits and keep canonical fields in sync.

---

## Guardrails (must implement)
- Hard allowlist of repos the app can write to.
- Denylist of dangerous operations (deleting issues, editing workflows, etc).
- Record every action in audit log.
