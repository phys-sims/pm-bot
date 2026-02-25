# Triage inbox specification

The “inbox” is a unified review queue intended to reduce cognitive load.

It aggregates:

1. **pm-bot approvals**
   - pending ChangesetBundles (writes needing approval)
   - pending AgentRunSpecs (token spend needing approval)
2. **GitHub PR review requests**
   - PRs where you are a requested reviewer
3. **Issues/PRs needing human attention**
   - labeled `needs-human`, `needs-triage`, `status:review`, etc.

## Why an inbox?

Without a unified view, you have to:

- check GitHub notifications
- check Projects
- check pm-bot’s pending approvals
- remember what the automation is waiting on

The inbox should answer:

> “What do I need to review today, in priority order?”

## Data sources

### pm-bot internal

- DB tables: changesets, approvals, audit events, agent runs
- Filter: `status == proposed` or `status == pending_approval`

### GitHub

- PR review requests (requested_reviewer == you)
- Issues/PRs with `needs-human` labels
- Optional: recently opened issues in triage area

## Sorting and grouping (recommended)

Group by queue:

1. Safety-critical approvals (writes, token spend)
2. PR reviews
3. Triage items

Within a queue:

- sort by priority (if present)
- then by age (oldest first)

## Minimal UI/CLI shape

- CLI: `pm inbox`
- Server UI: a simple page listing inbox entries with:
  - title + link
  - why it’s in the inbox
  - what action is needed (approve/reject/review/triage)

## Safety invariants

Inbox is read-only. Any “approve” action must still:

- record an approval
- apply the approved bundle via the changeset engine
- write an audit event

## References

- `docs/contracts/changesets.md` (approval + audit)
- `docs/contracts/agent_run_spec.md` (agent approvals)
- `docs/spec/product.md` (workflow goal)



## Unified API contract (`/inbox`)

The server exposes a unified inbox payload with deterministic ordering and typed source items.

### Query params

- `actor` (optional): GitHub login used when mapping review-request items.
- `labels` (optional): comma-separated label filters (for example `needs-human,needs-triage,status:review`).
- `repos` (optional): comma-separated repo list to bound external queries.

### Response shape (`inbox/v1`)

- `schema_version`: fixed `inbox/v1`
- `items`: merged list of
  - `source=pm_bot` / `item_type=approval` (internal changeset approvals)
  - `source=github` / `item_type=pr_review|triage` (external inbox)
- `diagnostics`:
  - `cache`: hit/miss + TTL + normalized key
  - `queries`: call-count + chunk metadata
  - `rate_limit`: remaining/reset telemetry snapshot
- `summary`: total count + per-source counts

### Determinism rules

Merged ordering is deterministic by source-group then stable tie-breakers (`item_type`, `priority`, `age_hours`, `repo`, `id`).

### Safety constraints

- External GitHub items are always read-only inbox entries.
- Approval actions remain available only for `source=pm_bot` entries and continue through the existing approval/audit pipeline.
