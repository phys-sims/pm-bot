# PM Bot / Agent-native Work Orchestrator — Human Roadmap (v0→v3)
_Date: 2026-02-21_

You already have the hard part: a **structured PM framework** encoded as GitHub issue forms and a **Projects field sync** workflow.
- Templates cover Epic/Feature/Task/Bug/Benchmark/Spike/Test/Chore with consistent metadata like Area/Priority/Size/Estimate/Risk/Blocked-by.
- `project-field-sync.yml` maps labels + issue-body headings into Projects v2 fields, so any agent output must preserve the markdown heading layout.

This roadmap is written for **you (human)** and tells you what to do vs what you should delegate to **Codex agents**.

---

## TL;DR staged releases
- **v0 (today/this week):** Start using it immediately: codex drafts issues in *your existing templates*, plus a local CLI to parse/render issues deterministically.
- **v1:** “Safe write” orchestration: propose→approve→publish, context packs, and an audit trail.
- **v2:** Tree UI (graph view) + estimation baseline (P50/P80) + meta reports on agent usage quality.
- **v3 (later):** SaaS shape: multi-tenant, policy engine, vector retrieval, advanced estimator.

---

## 0) One-time setup (human-owned)
### 0.1 Choose the “system of record” for v0–v2
**Decision:** Keep GitHub Issues/Projects as the surface for now. Your system of record will be:
- **Canonical WorkItem JSON** (internal)
- A deterministic compiler to/from GitHub issue bodies (your headings)
- Sync to Projects v2 via your existing workflow

### 0.2 Repo layout (recommended)
Create a new repo (private or public): `phys-sims/pm-bot` with:
- `pm_bot/` (library: schema, parser, renderer)
- `cli/pm` (CLI entry)
- `server/` (v1+: webhook + API)
- `ui/` (v2+: tree/graph UI)
- `docs/` (specs, prompts, runbooks)
- `AGENTS.md` (Codex persistent instructions, see below)

### 0.3 Secrets & permissions (human-owned)
You need two separate credentials:
1) **GitHub** for reading/writing issues/projects across repos
   - v0: simplest is a fine-grained PAT
   - v1+: prefer a **GitHub App** installed on the org with least-privilege permissions:
     - Issues: read/write
     - Projects: read/write (if you want to set fields directly; otherwise keep your existing sync workflow)
     - Contents: read (for ADR files in `docs/adr/`)

2) **OpenAI/Codex** for agent runtime
   - If you use the “Codex Issue Generator” workflow, set `PM_BOT_KEY` as a repository secret where the workflow runs.
   - If you use Codex CLI / app, you authenticate via your ChatGPT account and point it at local clones.

### 0.4 Add “AGENTS.md” to each repo you want agents to work in (human-owned)
Create `AGENTS.md` in:
- `phys-sims/.github`
- `phys-sims/phys-pipeline`
- (later) other repos

Keep it short and evergreen:
- naming conventions (labels, headings, required sections)
- where templates live (`.github/ISSUE_TEMPLATE/*.yml`)
- how to create ADRs (`python scripts/adr_tools.py new ...`)
- safe rules (“never run destructive commands”, “never modify workflows without explicit approval”, etc.)

Codex’s own guidance is to use an `AGENTS.md` for persistent context and standards, and to keep tasks well-scoped (~1 hour) for best results.

---

## 1) Template ergonomics upgrades (do this early)
These are small edits that unlock everything else.

### 1.1 Fix Epic size label mismatch
Your Epic form currently uses **“Size (Epic)”**. Your Projects sync expects **“Size”**.
Pick one:
- **Preferred:** rename the Epic field label to `Size` and use XS–XL like the other templates.
- Alternative: update the sync parser to accept both headings.

### 1.2 Add `Actual (hrs)` to templates where you want learning
Your Projects sync already supports an `Actual (hrs)` field. Add an optional input to:
- Feature, Task, Bug, Benchmark, Test, Chore (at minimum)
This enables v2 estimation without needing an external time tracker.

### 1.3 Make “Blocked by” structured (optional but helpful)
Keep the freeform field, but ask for **issue links** first, then people tags.
Example placeholder: `#123, https://github.com/.../issues/456, @name`

### 1.4 Prefer sub-issues for hierarchy, keep checklists for cross-repo
In GitHub, sub-issues are now the native hierarchy primitive. In v0/v1 you can keep your checklists,
but in v2 you’ll want to migrate to sub-issues where possible for better rollups.

**Human action:** open a PR in `phys-sims/.github` implementing these template edits, then decide whether
`phys-sims/phys-pipeline` uses org defaults or has local overrides.

---

## 2) v0 — “Start using it right away”
### What you get
- A local `pm` CLI that:
  - parses a GitHub issue body into canonical JSON
  - renders canonical JSON back into *exact* template headings
  - prints a **tree view** (ASCII) from Epic → Feature → Task using your checklist links
- A Codex-driven “draft issues” flow that outputs valid bodies using your templates.

### Human tasks (v0)
1) Create `phys-sims/pm-bot` repo.
2) Decide where your “Codex Issue Generator” runs:
   - Option A: keep it in `phys-sims/phys-pipeline`
   - Option B (cleaner): run it in `phys-sims/.github` or `pm-bot` and let it create issues elsewhere.
3) Add secrets:
   - `PM_BOT_KEY` (for issue drafting + Codex workflows)
   - `ADD_TO_PROJECT_PAT` if you keep your existing sync action (already required by the workflow)
4) Merge template fixes (Section 1).

### AI tasks (v0) — what to tell Codex to implement
Give Codex the **Agent Roadmap v0** file (download below) and ask it to:
- implement schema + parser + renderer + CLI
- add unit tests using real template fixtures
- provide a small “issue drafting harness” that can be used by a GitHub Action or locally

### Success criteria (v0)
- You can run: `pm draft feature --title ... --context ...` and get a valid issue body.
- You can run: `pm parse <issue_url>` and get canonical JSON.
- Round-trip test passes: render(parse(issue_body)) == normalized(issue_body).

---

## 3) v1 — “Safe orchestration + Context Packs”
### What you get
- A small server with webhooks and an API that maintains a WorkItem graph (SQLite/Postgres).
- An approval flow:
  - agent produces a **changeset**
  - you approve
  - system writes to GitHub
- A Context Pack builder:
  - issue body + parent/children + referenced ADR snippets
  - token-bounded, cached

### Human tasks (v1)
- Create and install a GitHub App (recommended) for least-privilege org access.
- Pick a deployment target (simple: Fly.io/Render; or run locally).
- Define policies:
  - agents are **draft-only** by default
  - writes require manual approval
  - production repos allowlist

### AI tasks (v1)
- webhook ingestion (issues + PRs + edits)
- WorkItem store + audit log
- changeset system + approval UI (can be simple: local web UI)
- context pack builder (deterministic selection, cached)

---

## 4) v2 — “Tree UI + Estimator + Meta reports”
### What you get
- A web UI that shows:
  - tree (epic→feature→task)
  - dependencies (blocked-by edges)
  - roll-up progress
- Estimator v1:
  - uses historical `Actual (hrs)` to predict P50/P80 by (type, area, size)
- Meta reports:
  - how often agent drafts are accepted without edits
  - which templates fail validation most
  - estimate calibration coverage (does P80 contain ≥80% of actuals?)

### Human tasks (v2)
- Decide what “status transitions” mean (labels or project field) and stick to it.
- Start filling `Actual (hrs)` on completed tasks (even rough is fine).

### AI tasks (v2)
- build tree UI + graph view
- implement estimator baseline + dashboards
- implement agent quality scoring + report generator

---

## 5) v3 — “SaaS shape (later)”
Keep shape only:
- multi-tenant auth + isolation
- policy engine and admin controls
- vector retrieval across org docs/issues
- hierarchical Bayesian estimator (optional)
- billing/token metering

---

## How to run Codex effectively on this project (human playbook)
Use Codex in **small, testable tasks** (each ~1 hour of work):
- “Implement parser + unit tests for headings extraction”
- “Implement renderer that outputs the exact markdown headings”
- “Add GitHub webhook ingestion for issue edited events”
- “Add tree view endpoint + UI component”

Make Codex output:
- a PR per task (if using cloud/app), or a clean commit series (if using CLI).

---

## Downloads
- Agent Roadmap v0 / v1 / v2 / v3 (give these to Codex agents)
- Human Roadmap (this file)
