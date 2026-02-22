# ContextPack v1

Context packs are deterministic bundles of information meant for downstream agents and humans.

They exist to solve two problems:

1. Give an agent enough context to do useful work (issue + surrounding graph + key docs)
2. Do it in a **deterministic, budgeted, auditable** way (no “grab random context”)

Context packs are especially important because pm-bot’s safety model is:

- agents propose changes (changesets / PRs)
- humans approve before publication

A good context pack makes agent outputs higher quality and easier to review.

## Design goals

ContextPack v1 MUST:

- be deterministic to build given the same inputs
- be bounded by an explicit budget (token/char/byte)
- be hashable and cacheable (content hash)
- include provenance (“why is this included?”)
- avoid secrets (redaction rules)

ContextPack v1 SHOULD:

- support multiple profiles (drafting vs coding vs review)
- include parent/child context and dependencies
- include referenced ADR excerpts when available

## Where context packs are built

Current repo layout indicates context packing exists at:

- `pm_bot/server/context_pack.py`

(See `STATUS.md` for the current module list.)

## Schema (recommended)

Top-level fields:

- `schema_version` (required): `context_pack/v1`
- `pack_id` (required): unique identifier
- `generated_at` (required): ISO datetime
- `profile` (required): `drafting | coding | review | other`
- `root` (required):
  - `work_item_id` (stable_id) OR `issue_url`
- `inputs` (required): what was used to build the pack
  - list of issue URLs, stable IDs, and file paths
- `budget` (required):
  - `max_chars` (int) OR `max_tokens` (int) OR both
  - `strategy` (string): `truncate_tail | drop_low_priority | both`
- `hash` (required): e.g. `sha256:<hex>`
- `sections` (required): ordered list of content blocks
- `redactions` (optional): what was removed and why

### Sections

Each section is an object like:

- `kind` (string): `issue`, `comment`, `work_item_json`, `edge_list`, `adr_excerpt`, `file_excerpt`, `instructions`
- `title` (string)
- `source` (object): where it came from (URL/path/id)
- `provenance` (string): why included (root, parent, child, dependency, adr_ref, etc.)
- `content` (string): actual content
- `metadata` (object): optional structured fields for downstream parsing

Sections MUST be ordered deterministically.

## Inclusion rules (recommended baseline)

Given a root work item:

1. Always include:
   - root issue body (rendered markdown)
   - canonical WorkItem JSON (if available)
2. Include one hop of graph context:
   - parent (if exists)
   - children (direct)
   - dependencies (blocked-by / depends-on)
3. Include referenced ADRs:
   - if the issue body references ADR files (or has an “ADR link” heading),
     include the first N lines or a targeted excerpt.
4. Include repo-local docs/excerpts ONLY if explicitly referenced or configured.
   - do not “crawl the whole repo” by default

## Determinism requirements

Given the same root + graph + files:

- sections MUST appear in a stable order
- truncation MUST be deterministic
- hashes MUST match across runs

Recommended ordering:

1. Instructions section (profile-specific)
2. Root item (markdown + json)
3. Parent (if any)
4. Children (sorted by stable_id or issue number)
5. Dependencies (sorted)
6. ADR excerpts (sorted by path)
7. Other file excerpts

## Redaction rules (minimum)

Context pack builder MUST:

- avoid including secrets from environment variables
- avoid including `.env` files or credential files
- optionally scrub lines matching common secret patterns

If redactions happen, record:

- what was removed (path/section)
- why (policy)
- what the user can do to include it safely (e.g., paste manually)

## Example ContextPack (abbreviated)

```json
{
  "schema_version": "context_pack/v1",
  "pack_id": "cp_2026-02-22_0001",
  "generated_at": "2026-02-22T01:20:00Z",
  "profile": "coding",
  "root": {"work_item_id": "feat:contracts-docs"},
  "budget": {"max_chars": 20000, "strategy": "drop_low_priority"},
  "hash": "sha256:example",
  "sections": [
    {
      "kind": "instructions",
      "title": "Agent instructions (coding)",
      "source": {"kind": "builtin"},
      "provenance": "profile",
      "content": "Make a PR that adds docs/contracts/*.md ..."
    },
    {
      "kind": "issue",
      "title": "Root issue body",
      "source": {"url": "https://github.com/org/repo/issues/123"},
      "provenance": "root",
      "content": "### Goal\n..."
    }
  ]
}
```

## Versioning

- breaking changes require a new `schema_version`
- optional fields can be added in-place

