# GitHub Projects field sync contract

pm-bot relies on a GitHub Projects v2 sync workflow that reads **issue-body headings** (and sometimes labels) and sets Project fields accordingly.

This document describes the **formatting contract** you MUST preserve.

## Canonical sources

The authoritative implementation lives in:

- `vendor/dotgithub/project-field-sync.yml`
- `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`

pm-bot must remain compatible with those files.

## The most important rule

> **The workflow reads headings and uses the first non-empty line after each heading as the field value.**

That means:

- The value MUST be on its own line immediately under the heading.
- Any bullets, extra prose, or blank lines *before* the value can break parsing.
- Multi-line values are usually ignored; only the first line is used.

## Required tracked headings

pm-bot MUST preserve these headings (exact spelling/case) in rendered issue bodies:

- `Area`
- `Priority`
- `Size`
- `Estimate (hrs)`
- `Risk`
- `Blocked by`
- `Actual (hrs)`

### Known compatibility note: `Size (Epic)`

The Epic template historically used `Size (Epic)` instead of `Size`.

Current compatibility behavior (as of the repo state described in `STATUS.md`):

- parser accepts `Size (Epic)`
- renderer normalizes output to `Size`

Do not remove this shim unless you have migrated templates and verified downstream behavior.

## Canonical formatting examples

### Good (parses correctly)

```markdown
### Area
cpa-sim

### Priority
P1

### Size
M

### Estimate (hrs)
12

### Risk
Low

### Blocked by
#123

### Actual (hrs)
8
```

Why this works:

- each heading is a `###` markdown heading
- each value is the first non-empty line after the heading
- values are simple and unambiguous

### Bad (often fails)

```markdown
### Area

- cpa-sim
```

The first non-empty line is `- cpa-sim`, which many parsers do not treat as a clean scalar value.

Also avoid:

```markdown
### Priority
P1
(extra commentary here)
```

If the sync script is strict, it may accept `P1`, but your own parser/renderer round-trip tests can drift.

## Allowed value conventions (recommended)

These are conventions; your org can choose others, but consistency is critical.

- `Area`: a short slug, e.g. `pm-bot`, `phys-pipeline`, `cpa-sim`
- `Priority`: `P0 | P1 | P2 | P3 | Triage`
- `Size`: `XS | S | M | L | XL`
- `Estimate (hrs)` / `Actual (hrs)`: numeric hours, no units
- `Risk`: `Low | Medium | High` or a short sentence if you prefer more nuance
- `Blocked by`: comma-separated issue refs or URLs (`#123`, full URL, etc.)

## Renderer rules (normative)

Any code that renders issue bodies MUST:

1. Emit headings in a stable order for the template type.
2. Emit each tracked heading as a `### <Heading>` block.
3. Ensure the value appears on the first non-empty line after that heading.
4. Avoid including extra help text between the heading and the value line.
5. Preserve template-required sections beyond the tracked headings (Goal, AC, Repro steps, etc.)

## Parser rules (normative)

Any code that parses issue bodies MUST:

- extract these headings reliably
- tolerate minor variations in whitespace
- treat missing or placeholder values as empty (don’t invent values)
- maintain compatibility with historical variants (`Size (Epic)`)

## How to test field sync safely

Use a sandbox repo connected to your org Project.

1. Draft an issue body (Feature/Task is fine).
2. Paste it into a new GitHub issue using the appropriate template.
3. Confirm the issue is added to the Project.
4. Confirm Project fields match the intended values.
5. Edit the issue body and re-check that fields update.

If this fails, the most common causes are:

- headings changed or weren’t rendered exactly
- value line is not the first non-empty line after the heading
- the workflow isn’t installed/enabled in the repo
- token/permissions for the workflow are missing/incorrect

## Change policy

Any change that affects Project field sync MUST be treated as a breaking change until proven otherwise.

When you change any of the following:

- templates (`vendor/dotgithub/ISSUE_TEMPLATE/*.yml`)
- the sync workflow (`vendor/dotgithub/project-field-sync.yml`)
- the renderer or parser logic

You MUST update:

- `STATUS.md` (canonical contract status + compatibility notes)
- parser/renderer compatibility tests
- `docs/github/projects-field-sync.md` (this file)

And you SHOULD run the First Human Test runbook again.

