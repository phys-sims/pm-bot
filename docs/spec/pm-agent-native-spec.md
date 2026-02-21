# Agent-native PM spec (derived from your current GitHub templates)

This spec turns your existing issue templates + project-field sync workflow into a consistent, agent-friendly system of record.

It is **not** a replatforming plan. It’s a thin layer that:
1) validates/generates issues in your existing templates
2) builds a per-issue **Context Pack**
3) learns time estimates from outcomes

---

## 1) What you already have (and what to fix)

### Issue templates (source of truth for structure)
You have 8 issue types: Epic, Feature, Task, Bug, Benchmark, Spike, Test, Chore/Infra.
Each template already encodes required fields and a stable set of metadata fields:
- **Area** (single select)
- **Priority** (P0/P1/P2)
- **Size** (XS–XL on most types)
- **Estimate (hrs)** (freeform number)
- **Risk** (Low/Med/High)
- **Blocked by** (text)
- ADR links/impact on Feature, ADR link(s) on Epic

### Project-field sync workflow (labels/body -> Project fields)
Your workflow parses issue/PR **markdown headings** like `### Area` and takes the *first non-empty line* of the section as the value.
It then writes to Project fields:
- Status, Priority, Size, Estimate (hrs), Area, Actual (hrs), Risk, Blocked By, Deliverable (optional)

**Key implication:** anything agents write must preserve the `### Heading` structure and keep the desired value on the first non-empty line in that section.

### Gaps / inconsistencies to fix ASAP
1) **Epic “Size (Epic)” won’t sync to Project Size** because the field parser looks for `### Size`.
   - Fix A: rename Epic label to `Size`
   - Fix B: update workflow to read `Size (Epic)` as a fallback.
2) **Actual (hrs) is supported by the workflow but not present in templates**, so it will almost always stay empty.
   - Add an optional `Actual (hrs)` input to templates (or at least to Feature/Task/Test/Benchmark).
3) **Epic does not have a “Blocked by” section**, so the Project “Blocked By” field won’t populate from epics unless you add it.

---

## 2) Canonical WorkItem schema (platform-agnostic)

Store WorkItems with a uniform core so agents can operate without special casing trackers.

### Enumerations
- `type`: epic | feature | task | bug | bench | spike | test | chore
- `area`: phys-pipeline | abcdef-sim | research-utils | cpa-sim | infra/docs
- `priority`: P0 | P1 | P2
- `size`: XS | S | M | L | XL (epic may omit XS)

### Canonical fields
All WorkItems:
- `id` (internal UUID)
- `external_ref` (e.g., GitHub issue node_id + URL)
- `title`
- `type`
- `area`
- `priority`
- `size` (optional for spikes/bugs if you want)
- `estimate_hrs` (optional numeric)
- `actual_hrs` (optional numeric)
- `risk` (Low/Med/High; optional)
- `blocked_by` (string list or text; optional)
- `status` (Backlog/Ready/In progress/In review/Done)
- `labels` (raw tracker labels)
- `created_at`, `updated_at`, `closed_at`

Type-specific fields:
- Epic: `objective`, `scope_in`, `scope_out`, `success_metrics[]`, `milestones[]`, `child_issue_links[]`, `adr_links[]`
- Feature: `goal`, `acceptance_criteria[]`, `child_tasks[]`, `adr_impact`, `adr_link`
- Task: `parent_feature_url`, `acceptance_criteria[]`
- Bug: `repro_steps`, `expected_vs_actual`, `logs`
- Benchmark: `scenario`, `metrics[]`
- Spike: `question`, `plan`, `exit_criteria[]`
- Test: `test_type`, `reference_contract`, `protocol`, `expected_artifacts[]`
- Chore: `scope_current_pain`, `scope_change`, `scope_acceptance`

Relationships (graph):
- `parent_id` / `children_ids[]`
- `depends_on_ids[]` / `blocks_ids[]`
- `related_ids[]`
- `adr_ids[]`

---

## 3) Context Pack spec (what every agent run consumes)

A Context Pack is a cached JSON blob, built per WorkItem, containing only what the agent needs.

### Context Pack JSON (v0)
```json
{
  "work_item": { "url": "...", "type": "feature", "title": "...", "area": "cpa-sim" },
  "requirements": {
    "acceptance_criteria": ["..."],
    "constraints": ["..."],
    "definition_of_done": ["..."]
  },
  "links": {
    "parent": "…",
    "children": ["…"],
    "blocked_by": ["…"],
    "blocks": ["…"],
    "adrs": ["docs/adr/0006-....md"]
  },
  "repo_context": {
    "repos_in_scope": ["cpa-sim", "research-utils"],
    "codeowners_or_contacts": [],
    "key_paths": []
  },
  "recent_activity": {
    "related_prs": [],
    "recent_commits": []
  },
  "pm_rules": {
    "templates": "issue-templates-guide.md",
    "field_sync_rules": "project-field-sync.yml",
    "required_headings": ["Area", "Priority", "Size", "Estimate (hrs)", "Risk", "Blocked by"]
  }
}
```

### Build rules
- Always include: WorkItem summary + acceptance/DoD + blockers + ADR links.
- Only include files/PRs that touch the same area/scope.
- Prefer parent + sibling WorkItems over “everything in the repo”.

---

## 4) Agent tool contract (minimum viable)

Agents should have tools that operate on the canonical schema, then sync to trackers.

### Tools (read)
- `get_work_item(url)` -> parses issue body into canonical fields
- `get_context_pack(url)` -> returns cached Context Pack (build if missing)
- `search_related_work(query, area, type)` -> find duplicates/related

### Tools (write, approval-gated)
- `draft_work_items(epic_prompt, constraints)` -> returns proposed Epic + children (structured JSON)
- `render_issue_body(work_item_json, template_type)` -> produces markdown body consistent with your issue form headings
- `publish_issue(repo, title, body, labels)` -> creates GitHub issue
- `update_issue(url, patch)` -> edits title/body/labels
- `link_parent_child(parent_url, child_urls[])` -> checklists + references
- `set_project_fields(url, fields)` -> optional direct sync (you already have GH Action for this)

**Policy:** default to “draft only”; human approves publish + any edits to existing items.

---

## 5) Dynamic estimation (learns from outcomes)

You already have `Estimate (hrs)` and `Actual (hrs)` as Project fields. Use them.

### Data you can gather without extra apps
- Status transition timestamps (Backlog → Done)
- Estimate (hrs), Size, Type, Area
- PR lead/cycle time as additional signals (optional)

### Estimator v0 (good enough)
Maintain rolling medians per bucket:
- bucket = (type, area, size)
Predict:
- `p50` = median(actual_hrs)
- `p80` = 80th percentile(actual_hrs)

Update buckets every time an item closes with an `actual_hrs`.

### Scheduling
Instead of “you have 10h today”, do:
- choose top items whose **p80 sum** fits your time window
- keep 20% slack

---

## 6) Implementation roadmap (personal tool -> SaaS)

Personal v1 (1–2 repos first):
1) Parser: GitHub issue body -> canonical fields (must respect your headings)
2) Context Pack builder: pulls parent/child, ADR paths, and recent PRs
3) Drafting agent: prompt -> Epic + child issues rendered to templates
4) Publish flow with approval + audit log
5) Estimator v0 using `estimate_hrs/actual_hrs`

SaaS adds:
- multi-tenant auth (GitHub App)
- durable webhook processing
- org-level graph + search
- per-org policies + permissions
- billing + token metering

---
