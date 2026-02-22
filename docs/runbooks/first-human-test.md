# Runbook: First human test

This runbook is the minimum manual validation needed to trust pm-bot in real repos.

It is designed to answer:

- “Does Projects field sync still work with pm-bot’s rendered bodies?”
- “Are writes actually approval-gated?”
- “Do parse/render round-trips preserve headings?”
- “Can I build a tree view without nonsense?”
- “Do reruns avoid duplicates?”

## Safety rules

- Use a **sandbox repository** and/or a test Project first.
- Do not run write-capable credentials against production repos until this runbook passes.
- If anything feels unclear, fail closed: do not apply changes.

## Prerequisites

- You have a sandbox repo in your GitHub org (or personal account).
- The sandbox repo has:
  - issue templates (or inherits from your `.github` repo)
  - the Projects field sync workflow installed/configured for that repo
- You can run pm-bot locally.

## Step 0 — Local repo health

From the pm-bot repo root:

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
ruff format .
```

Expected: all pass.

If tests fail, fix that before proceeding — this runbook assumes a healthy baseline.

## Step 1 — Validate Projects sync formatting (the “hardest” dependency)

1. Use `pm draft` (or manually fill the template) to create a Feature issue body.
2. Ensure the body includes *all required tracked headings*:

   - Area
   - Priority
   - Size
   - Estimate (hrs)
   - Risk
   - Blocked by
   - Actual (hrs)

3. Verify formatting rules:
   - The first non-empty line after each heading is the value
   - No bullets or prose between heading and value

4. Create an issue in the sandbox repo:
   - Paste the drafted body into the issue body (or create using the template).

5. Wait for the workflow to run (or trigger it, depending on your setup).

6. Confirm in the Project UI:
   - the issue is added to the Project
   - fields populate correctly (Area, Priority, Size, etc.)

If this fails:

- read `docs/github/projects-field-sync.md`
- check if the workflow is installed/enabled
- check that headings match exactly
- check that the first non-empty line is the intended value

## Step 2 — Parse → render round-trip

1. Copy the issue body into a local file: `issue.md`
2. Run:

```bash
pm parse --file issue.md > work_item.json
```

3. Render back to markdown (via CLI or library; see Quickstart):

- If CLI supports it:

```bash
pm render --json work_item.json > issue.rendered.md
```

- Otherwise, use the renderer through whatever interface the repo provides.

4. Compare:

- `issue.md` vs `issue.rendered.md`

Expected:

- required headings are preserved
- values appear correctly under headings
- any template-required sections are present

Small whitespace differences are ok; semantic drift is not.

## Step 3 — Approval gate validation (server mode)

This step validates “no writes without approval”.

1. Start the pm-bot server locally:

```bash
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000
```

1a. Validate startup contract:

```bash
python -m pm_bot.server.app --print-startup
curl -s http://127.0.0.1:8000/health
```

2. Configure the server with:
   - repo allowlist (sandbox repo only)
   - GitHub credentials
   - write permissions disabled unless explicitly applying approved changesets

3. Create a trivial changeset proposal (one of):
   - update the title of the sandbox issue
   - add a label
   - update a non-critical section of the issue body

4. Attempt to apply the changeset **without approval**.

Expected:

- it is denied
- an audit event is recorded (denied)

5. Approve the changeset via the server UI/CLI.
6. Apply the changeset.

Expected:

- the GitHub issue updates
- an audit event is recorded (approved + applied)

If you can apply without approval, stop and fix immediately — this is a core invariant.

## Step 4 — Idempotency check (rerun should not duplicate)

1. Run the same proposal again:
   - same operation + same idempotency key

Expected:

- pm-bot recognizes it as already applied and no-ops (or proposes a safe “already applied” status)
- no duplicate issue, labels, or relationships appear

## Step 5 — Tree + dependencies smoke test

Goal: verify the tree view works and provenance is sensible.

1. Create a small work structure in the sandbox repo:

- Epic issue: `epic:demo`
- Feature issues: `feat:demo:a`, `feat:demo:b`
- Task issues under one feature: `task:demo:a1`, `task:demo:a2`

2. Create hierarchy using one method (preferably sub-issues if available).
3. Add one dependency (e.g., `task:demo:a2` blocked by `task:demo:a1`).

4. In pm-bot, render a tree view:

```bash
pm tree --url <epic issue url>
```

(or the equivalent CLI/UI flow)

Expected:

- hierarchy is correct
- dependency overlay is visible (if implemented)
- provenance labels align with how you created edges

If you used checklists, provenance should be `checklist`.
If you used sub-issues, provenance should be `sub_issue`.

## Step 6 — Regression notes

Once this runbook passes:

- record the sandbox repo + project IDs used
- keep one “golden” epic/feature/task structure as a regression fixture
- rerun this runbook after:
  - template changes
  - renderer/parser changes
  - workflow changes
  - GitHub auth changes

## Troubleshooting checklist

- Projects fields wrong:
  - headings mismatch
  - value line not first non-empty line
  - workflow not installed/enabled
  - workflow token/permissions missing
- Writes not blocked:
  - approval gate bypass bug
  - missing policy enforcement
- Duplicate issues created:
  - stable IDs not used
  - idempotency keys not stable
  - apply logic not recognizing prior runs
- Tree is wrong:
  - conflicting sources (sub-issues vs checklists)
  - cycles in parent/child edges
  - parser missing link formats



## Step 7 — Reliability incident drills (v4)

Use these drills to validate retry/idempotency/observability behavior before shipping.

### Drill A: Retry storm containment
1. Propose a changeset whose payload includes `_transient_failures: 9`.
2. Approve the changeset.
3. Confirm behavior:
   - changeset transitions to failed after bounded retries.
   - `changeset_dead_lettered` audit event is emitted with `reason_code=retry_budget_exhausted`.
   - metrics include `changeset_write` with `retryable_failure` outcome.

### Drill B: Webhook drift correlation
1. Call webhook ingest with explicit `run_id`.
2. Generate a weekly report with the same `run_id`.
3. Confirm both `webhook_received` and `report_generated` audit events carry that `run_id` for cross-signal triage.

### Drill C: Policy denial spikes
1. Propose writes to an unallowlisted repo and a denylisted operation.
2. Confirm each emits `changeset_denied` with deterministic reason codes.
3. If denial rate spikes, triage in this order:
   - repo allowlist config drift
   - unexpected operation type introduction
   - attempted writes outside approved scope

