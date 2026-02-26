# ReportIR v1
> **Audience:** Contributors producing or validating ReportIR payloads.
> **Depth:** L3 (normative contract).
> **Source of truth:** Authoritative contract semantics for ReportIR v1; MUST-level terms are binding.


ReportIR (“Report Intermediate Representation”) is the **machine-readable plan format** that pm-bot ingests deterministically.

It exists to enable **Mode A** (“bring-your-own report”) workflows:

- a human (or external LLM) produces a Markdown report
- the report embeds a small structured block (JSON or YAML)
- pm-bot reads that block without calling an LLM
- pm-bot maps it into WorkGraph, then into proposed changesets

## Design goals

ReportIR v1 MUST:

- be easy for a human or LLM to generate
- be deterministic to parse (no heuristics required)
- support stable IDs so repeated runs are idempotent
- support enough metadata to populate GitHub templates and Projects fields

ReportIR v1 SHOULD:

- be minimal (don’t turn it into a full project management database)
- allow optional fields (risk, size, estimates) without forcing them everywhere
- allow partial plans (some tasks missing) while still producing useful diffs

## Non-goals

ReportIR is not:

- a GitHub API payload
- a canonical storage format (that’s WorkGraph/WorkItem)
- a free-form narrative report (the narrative remains in Markdown; ReportIR is just the structured core)

## Embedding format in Markdown

pm-bot MUST support deterministic extraction of the structured block from Markdown.

### Recommended embedding (canonical)

Embed a single fenced code block with an info string that explicitly names the schema:

```markdown
```pm-bot:report-ir/v1
{ ... JSON or YAML ... }
```
```

Extraction rules (normative):

1. pm-bot MUST scan the Markdown for fenced code blocks whose info string is exactly:
   - `pm-bot:report-ir/v1`
   - `pm-bot:report_ir/v1` (legacy alias)
2. If **exactly one** such block exists:
   - parse it as JSON if it starts with `{` or `[`
   - otherwise parse as YAML
3. If **zero** such blocks exist:
   - Mode A ingestion fails with a clear error
   - Mode B MAY be offered (LLM extraction) if configured
4. If **more than one** such block exists:
   - ingestion MUST fail (ambiguity)

### Allowed fallback embedding (best-effort)

If the canonical info string is absent, pm-bot MAY support a best-effort fallback:

- any fenced `json`/`yaml` block that contains a top-level `schema_version: report_ir/v1`

This fallback MUST NOT silently pick an arbitrary block if multiple candidates match.

## Top-level shape

ReportIR v1 is a JSON/YAML object with these top-level keys:

- `schema_version` (required): must equal `report_ir/v1`
- `report` (required): metadata about the report itself
- `epics` (optional): list of epic-level items
- `features` (optional): list of feature-level items
- `tasks` (optional): list of task-level items
- `notes` (optional): structured annotations / assumptions that aren’t work items

### `report`

Required fields:

- `title` (string, required)
- `generated_at` (string, required): ISO-8601 date or datetime
- `scope` (object, required):
  - `org` (string, required)
  - `repos` (array[string], optional): repos relevant to the plan
- `source` (object, optional):
  - `kind` (string): e.g. `human`, `gpt`, `claude`, `other`
  - `url` (string): permalink to source report, if any
  - `prompt_hash` (string): optional reproducibility hook

### Work item lists

All work items in ReportIR share a common required core:

- `stable_id` (string, required, unique across the entire document)
- `title` (string, required)
- `area` (string, recommended)
- `priority` (string, recommended)

Additional optional fields MAY appear, including:

- `status` (string): backlog / in-progress / done (or your org’s vocabulary)
- `size` (string): XS / S / M / L / XL (recommended alignment with templates)
- `estimate_hrs` (number): numeric hours estimate (do not include units)
- `risk` (string): short risk summary (1–2 sentences)
- `blocked_by` (array[string]): stable IDs or issue URLs
- `links` (array[string]): related URLs (issues, docs, designs)
- `acceptance_criteria` (array[string]): DoD bullets
- `owners` (array[string]): GitHub handles or emails

#### Epic fields

Epics MAY include:

- `objective` (string): the “why”
- `milestones` (array[object]):
  - `title` (string)
  - `target_date` (string, ISO date)
- `features` (array[string]): optional explicit feature stable_ids
  - If omitted, features can reference epics via `epic_id`

#### Feature fields

Features SHOULD include:

- `epic_id` (string): stable_id of parent epic (or `null` for standalone)
- `goal` (string): short description of what this feature delivers
- `depends_on` (array[string]): stable_ids of other features/tasks
- `tasks` (array[string]): optional explicit child task stable_ids

#### Task fields

Tasks SHOULD include:

- `feature_id` (string): stable_id of parent feature (or `null` for standalone)
- `type` (string): optional classification, e.g. `task`, `bug`, `spike`, `test`, `chore`

## Stable IDs

Stable IDs are the backbone of idempotency.

Requirements:

- `stable_id` MUST be unique across epics/features/tasks in the same ReportIR document.
- `stable_id` MUST be stable across repeated runs of the same plan (do not include timestamps).
- `stable_id` SHOULD be human-readable.

Recommended formats:

- `epic:<slug>`
- `feat:<slug>`
- `task:<slug>`
- For typed tasks:
  - `bug:<slug>`
  - `spike:<slug>`
  - `test:<slug>`
  - `chore:<slug>`

Where `<slug>` SHOULD be lowercase and URL-safe (`[a-z0-9-:_]+`).

## Validation rules

ReportIR v1 MUST be validated at two layers:

1. **Schema validation**
   - shape/type checks (strings, arrays, numbers)
2. **Rule validation**
   - business logic constraints

Minimum rule validation (recommended defaults):

- If a Feature has an `epic_id`, it MUST reference an existing epic stable_id.
- If a Task has a `feature_id`, it MUST reference an existing feature stable_id.
- Every `depends_on` entry MUST reference an existing stable_id, OR be a valid GitHub issue URL.
- Missing `area` or `priority` SHOULD be routed to triage (see below) rather than guessed.

### Triage policy for missing fields

pm-bot SHOULD implement a consistent policy for incomplete plans. Recommended:

- if `area` missing: set `area = "triage"` and attach `needs-human` label in downstream mapping
- if `priority` missing: set `priority = "Triage"` (or P? value) and attach `needs-human`
- never invent a priority based on wording without explicit configuration

## Mapping: ReportIR → WorkGraph

Mapping SHOULD be deterministic and mechanical.

Recommended mapping:

- Each epic/feature/task becomes a WorkItem node with the same `stable_id`.
- Parent-child edges:
  - Feature → Epic: create `parent_child` edge from epic → feature
  - Task → Feature: create `parent_child` edge from feature → task
- Dependency edges:
  - For each `depends_on`: create `depends_on` edge from item → dependency
- Blocked-by:
  - For each `blocked_by`: create `blocked_by` edge (direction item → blocker)

Provenance requirements:

- All edges created from ReportIR MUST be labeled `provenance = "report_ir"`.

## Example (minimal)

```json
{
  "schema_version": "report_ir/v1",
  "report": {
    "title": "pm-bot MVP plan",
    "generated_at": "2026-02-22",
    "scope": {"org": "phys-sims", "repos": ["pm-bot"]}
  },
  "features": [
    {
      "stable_id": "feat:docs-contracts",
      "title": "Add contract-first docs",
      "goal": "Document ReportIR/WorkGraph/Changesets/AgentRunSpec",
      "area": "pm-bot",
      "priority": "P1"
    }
  ]
}
```

## Versioning and evolution

- `schema_version` MUST be versioned.
- Backward incompatible changes require a new version (e.g. `report_ir/v2`).
- Backward compatible extensions MAY add optional fields.

If you extend v1 with org-specific fields, put them under a namespaced key:

```json
{
  "schema_version": "report_ir/v1",
  "x_org": {
    "my_custom_field": "..."
  }
}
```

