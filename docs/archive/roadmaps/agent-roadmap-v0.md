# Agent Roadmap v0 — PM Bot MVP (Draft + Validate + CLI)
_Date: 2026-02-21_

## Mission
Ship a **usable tool immediately** for a single user:
- Draft issues in existing GitHub templates (Epic/Feature/Task/Bug/Benchmark/Spike/Test/Chore).
- Parse existing issue bodies into canonical JSON.
- Render canonical JSON back into deterministic markdown that preserves your headings.
- Provide a CLI (`pm`) with commands: `draft`, `parse`, `tree`.

You MUST keep compatibility with:
- template field names like `Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`
- the existing Projects field sync which reads headings and uses the first non-empty line as the value.

## Inputs you must use
- `.github/ISSUE_TEMPLATE/*.yml` templates (use them as fixtures)
- `project-field-sync.yml` behavior: headings + labels map to project fields

## Non-goals (v0)
- No server/webhooks
- No writes to GitHub required (draft output is enough)
- No estimator

---

## Deliverables
1) **Canonical WorkItem schema**
   - Add `/pm_bot/schema/work_item.schema.json` (derived from templates).
   - Add `/pm_bot/schema/template_map.json` that lists required headings per type.

2) **Parser**
   - `pm_bot/github/parse_issue_body.py`
   - Extracts:
     - metadata headings (Area/Priority/Size/Estimate/Risk/Blocked by/ADR link/etc)
     - template-specific fields (Goal, Acceptance, Repro steps, Scenario, etc)
     - child issue references from checklists in:
       - Epic: “Child Issues (link Features/Tasks/Tests/Benches/Docs)”
       - Feature: “Child tasks” section
   - Output: `WorkItem` JSON (validated).

3) **Renderer**
   - `pm_bot/github/render_issue_body.py`
   - Deterministically renders markdown headings so `project-field-sync.yml` can parse them.
   - Ensure value is on the first non-empty line after each heading.

4) **CLI**
   - `cli/pm` (python or node)
   - Commands:
     - `pm draft <type> --title ... --context ... [--area ... --priority ...]`
       - Produces markdown body + canonical JSON.
     - `pm parse --file issue.md` or `pm parse --url <github issue url>` (url optional if no API yet)
     - `pm tree --file epic.md` prints ASCII tree by parsing #links in checklists.
   - Include `--validate` option.

5) **Tests**
   - Snapshot tests for each template type using fixtures derived from the YAML templates.
   - Round-trip tests:
     - render(parse(body)) preserves headings + required sections.

---

## Implementation steps (split into Codex-sized tasks)
### Task A: repo skeleton + schema
- Create python package scaffolding.
- Write `work_item.schema.json` + `template_map.json`.
- Add `AGENTS.md` instructions for future agent runs (short).

### Task B: markdown heading parser
- Implement robust heading extraction for `### <Heading>` blocks.
- Must handle “no response” placeholders (treat as empty).
- Provide unit tests.

### Task C: checklist / child issue parser
- Parse `- [ ] #123` style links.
- Parse full URLs too.
- Return list of child refs.

### Task D: renderer
- Render sections in a fixed order per template type.
- Render checklists with placeholders when missing.

### Task E: CLI + packaging
- Add `pm` CLI and docs.
- Add examples for:
  - drafting a Feature with Goal + Acceptance + Child tasks and the required headings.

---

## Acceptance criteria
- `pm draft feature ...` outputs a body that, when pasted into GitHub, would sync the intended fields.
- Parser and renderer pass on fixtures for: feature.yml, task.yml, bug.yml, benchmark.yml, spike.yml, test.yml, chore.yml, epic.yml.
- Epic size mismatch is handled by either:
  - normalizing to `Size` in renderer, or
  - supporting both headings in parser and renderer.

---

## Notes on template ergonomics (implement as a PR, but do NOT block v0)
Recommend (but optional in v0):
- Rename Epic “Size (Epic)” -> “Size” and unify enum to XS..XL
- Add optional “Actual (hrs)” input to Feature/Task/Bug/Benchmark/Test/Chore
