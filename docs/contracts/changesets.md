# Changesets and approvals

Changesets are pm-bot’s **only** mechanism for mutating external systems (GitHub Issues, Projects, PRs, etc.).

This is the core safety guarantee:

> **No writes without an approved changeset.**

A changeset is also the unit of review: it can be previewed, edited, approved, rejected, and audited.

## Definitions

### ChangesetBundle

A ChangesetBundle is a group of changesets produced from a single planning event, typically:

- ingesting a ReportIR
- refreshing a WorkGraph from GitHub and reconciling drift
- an agent proposal run

A bundle MAY include changesets that target multiple repositories, but a bundle SHOULD be scoped to a coherent intent (one “plan apply” event).

### Changeset

A Changeset is a single operation on an external target.

Examples:

- create an issue
- update an issue body
- add/remove labels
- set a parent/child relationship (sub-issue)
- set a dependency edge (blocked-by)
- add an issue to a Project and set fields
- propose an agent run (token spend) (often represented as AgentRunSpec + approval, but can be coupled)

### Approval

An Approval is a recorded human decision that authorizes execution of:

- a changeset
- a bundle
- an agent run

Approvals MUST be auditable: who approved what, when, and under which policy.

### Execution log / audit event

Every attempted execution MUST produce an immutable log entry:

- success
- failure
- denial (blocked by policy or missing approval)

This is essential for “trusting” automation.

## Safety model

### Hard rule: approval-gated writes

Operations that mutate GitHub MUST require approval.

This includes:

- issue create/update
- label changes
- relationship edits (sub-issues / dependencies)
- Project item creation/field updates
- PR creation (if implemented)

Read-only operations MUST NOT require approval.

### Default-deny

pm-bot SHOULD treat new or unknown operation types as **denied by default** until explicitly allowed.

### Allowlist and denylist

Connectors SHOULD enforce:

- an allowlist of repositories the tool can write to
- a denylist of dangerous operations (e.g., modifying workflow files) if you ever expand beyond issues/projects

## Idempotency

Changesets MUST be idempotent.

### Idempotency key

Each changeset MUST include an `idempotency_key` that uniquely identifies its intent.

Recommended format:

```
<op>:<org>/<repo>:<stable_id or binding>:<intent-hash?>
```

Examples:

- `create_issue:phys-sims/pm-bot:feat:contracts`
- `set_parent:phys-sims/pm-bot:feat:contracts->epic:docs`
- `add_to_project:phys-sims/pm-bot:issue#123:project#42`

Rules:

- Re-running a bundle MUST not create duplicates if idempotency keys match previously applied changesets.
- If the “intent” changes (e.g., title changed), the idempotency key SHOULD change (or include an intent hash) so the system can propose an update rather than silently no-op.

## Changeset schema (suggested)

A changeset SHOULD have these fields:

- `changeset_id` (string): unique identifier for this changeset
- `bundle_id` (string): ID of the bundle that produced it
- `idempotency_key` (string): stable across retries for the same intent
- `operation` (string): operation type (see below)
- `target` (object): where to apply it (repo, issue binding, project binding)
- `payload` (object): operation-specific payload
- `requires_approval` (bool): true for all mutating ops
- `status` (enum): `proposed | approved | rejected | applying | applied | failed | superseded`
- `created_at` (string datetime)
- `created_by` (string): user/agent identifier
- `approved_at` (string datetime, optional)
- `approved_by` (string, optional)

### Operation types (recommended baseline)

Issue operations:

- `create_issue`
- `update_issue_title`
- `update_issue_body`
- `add_labels`
- `remove_labels`
- `set_assignees` (optional)

Relationship operations:

- `set_parent` / `clear_parent` (sub-issues)
- `add_dependency` / `remove_dependency` (blocked-by)

Project operations:

- `add_to_project`
- `set_project_field`

Agent operations:

- `propose_agent_run` (often points to an AgentRunSpec payload)

If you add new operation types, document them in this file and add tests.

## Preview and diff

Every bundle MUST be previewable.

Recommended preview fields:

- operation summary
- target repo + issue binding
- “before” (if updating an existing issue) and “after”
- any edges created/removed
- any Project field changes

For issue-body updates, previews SHOULD include:

- a rendered markdown diff (human-friendly)
- the underlying patch representation (machine-friendly)

## Patch representations

pm-bot MAY represent updates as:

- JSON Patch (RFC 6902) when strict atomic edits are needed
- JSON Merge Patch (RFC 7396) when replacing fields is sufficient

Internally, it’s often simplest to represent issue edits as “replace full body markdown”, but you still want a good diff preview.

## Execution semantics

### Apply order

Bundles SHOULD execute changesets in a stable order to reduce flakiness:

1. create issues (so bindings exist)
2. update issues (title/body/labels)
3. set relationships (parent/child, dependencies)
4. add to project + set fields

### Failure handling

If a bundle partially fails:

- already-applied changesets remain applied (do not attempt “best effort rollback” unless you have strong guarantees)
- the bundle remains in a failed state
- re-running MUST converge (idempotency) and only apply what’s missing or drifted

### Concurrency

pm-bot SHOULD bound concurrency:

- to avoid GitHub secondary rate limits
- to keep operations reviewable

## Audit requirements

pm-bot MUST record:

- all proposed changesets
- approvals and rejections
- all execution attempts
- all policy denials (e.g., `changeset_denied`)

Audit entries MUST include:

- timestamp
- actor (human/agent)
- target
- operation type
- result (success/failure/denied)
- error message (if any)

## Example: bundle with create + relationship + project fields

```json
{
  "bundle_id": "bundle_2026-02-22_0001",
  "source": {"kind": "report_ir", "ref": "report:pm-bot-docs"},
  "status": "proposed",
  "changesets": [
    {
      "changeset_id": "cs_0001",
      "idempotency_key": "create_issue:phys-sims/pm-bot:feat:contracts",
      "operation": "create_issue",
      "target": {"org": "phys-sims", "repo": "pm-bot"},
      "payload": {
        "type": "feature",
        "title": "[feat] Contract-first docs",
        "body_markdown": "### Goal\n...\n\n### Area\npm-bot\n\n### Priority\nP1\n",
        "labels": ["type:feature", "area:pm-bot", "prio:P1"]
      },
      "requires_approval": true,
      "status": "proposed"
    }
  ]
}
```

