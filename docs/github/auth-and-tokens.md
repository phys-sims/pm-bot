# GitHub auth and tokens

pm-bot supports multiple runtime modes, and each mode has different authentication needs.

This document is about:

- which token types to use
- what to avoid (common GitHub automation traps)
- how to keep the repo public-safe (no secrets in git)

## Summary: what to use when

### Local CLI, draft-only

- ✅ No GitHub token required if you are only drafting from templates and parsing local files.
- Optional: a **read-only** token if you want `pm parse --url ...`.

### Local server, approval-gated writes

Recommended:

- ✅ GitHub App installation token (preferred long-term)
- ✅ Fine-grained PAT scoped to specific repos (ok for personal use)

Avoid:

- ⚠️ GitHub Actions `GITHUB_TOKEN` for creating issues if you expect other workflows to run as a result.

## Token types

### Fine-grained PAT (personal access token)

Good for:

- personal, local-first usage
- fast setup

Risks/downsides:

- stored as a user secret (rotation/ownership is tied to your account)
- can be over-scoped if not careful

Guidance:

- scope to only the repos pm-bot should write to
- use the minimum permissions:
  - Issues: read/write
  - Metadata: read
  - Projects: read/write (only if pm-bot updates Projects directly)

### GitHub App installation token

Good for:

- org-scale usage
- least-privilege + separation from any single user
- easier future multi-user support

Operational notes:

- installation tokens expire (typically ~1 hour), so your connector must refresh them
- webhook signature validation becomes relevant if you ingest webhooks directly

### GitHub Actions `GITHUB_TOKEN`

`GITHUB_TOKEN` is convenient in workflows, but has a common gotcha:

- Events triggered by `GITHUB_TOKEN` often do not trigger other workflow runs (to prevent infinite loops).

Practical impact:

- If pm-bot runs inside Actions and creates an issue with `GITHUB_TOKEN`,
  your downstream “on issue opened/edited” workflows may not run.

Recommendation:

- If you need “create/update issue” actions to trigger other workflows, prefer:
  - GitHub App token, or
  - a PAT stored as a secret


## `pm parse --url` supported URL formats

The CLI supports two explicit URL source types:

1. **GitHub issue URL** (resolved via GitHub REST API and parsed from issue `body`)
   - Format: `https://github.com/<owner>/<repo>/issues/<number>`
   - Fetch path used by CLI: `https://api.github.com/repos/<owner>/<repo>/issues/<number>`

2. **Raw markdown URL** (fetched directly as markdown text)
   - Format: `https://.../*.md`
   - Common example: `https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>.md`

Unsupported URLs fail fast with an explicit error.

Auth notes for GitHub issue URLs:

- For public repos, unauthenticated reads may work but are still rate-limited.
- For private/restricted repos, provide `PM_BOT_GITHUB_TOKEN` (preferred) or `GITHUB_TOKEN`.
- Token should have read access to issues/metadata for the target repository.

## Secret handling

### Do

- use GitHub Actions secrets for workflow secrets
- use a local `.env` (gitignored) for local runs
- document required env vars in README/Quickstart

### Do not

- commit tokens to the repo
- put tokens in issue bodies, comments, or reports
- log tokens (scrub logs)

## Permissions model (recommended)

pm-bot should treat GitHub auth as layers:

1. **Read credential** (low risk)
   - fetch issue bodies, list issues, read project items
2. **Write credential** (high risk)
   - create/update issues
   - set sub-issues/dependencies
   - update Projects fields

Even if you use one token today, pm-bot’s connector SHOULD still model them separately so you can harden later.

## Repo allowlists

pm-bot SHOULD enforce an explicit allowlist of repos it can write to.

Current runtime behavior:

- Default allowlist is org-ready for phys-sims:
  - `phys-sims/.github`
  - `phys-sims/phys-pipeline`
  - `phys-sims/cpa-sim`
  - `phys-sims/fiber-link-sim`
  - `phys-sims/abcdef-sim`
  - `phys-sims/fiber-link-testbench`
  - `phys-sims/phys-sims-utils`
- Override allowlist for any org by setting `PM_BOT_ALLOWED_REPOS` as a comma-separated list.
  - Example: `PM_BOT_ALLOWED_REPOS="my-org/repo-a,my-org/repo-b"`
- When `PM_BOT_ALLOWED_REPOS` is set, it fully replaces the default list.
- Writes outside the active allowlist are denied with `repo_not_allowlisted`.

Why:

- prevents accidental writes to the wrong repo
- makes human approval review easier (“this bundle writes to repos A/B only”)
- gives a single deterministic switch for phys-sims org users vs other org users

## Inbox search and cache guidance

For unified inbox aggregation against GitHub:

- Decompose external queries into bounded chunks (labels/repo slices) to avoid large or brittle requests.
- Use short-lived TTL caching on normalized query signatures to reduce repeated API calls during operator refresh loops.
- Surface diagnostics (`cache.hit`, call counts, and rate-limit headers) to make throttling behavior observable.

This keeps inbox reads responsive while preserving rate-limit budget for higher-priority operations.

## Troubleshooting

### “pm parse --url …” fails

Common causes:

- token missing
- token has no access to that repo
- hitting rate limits (rare for single requests)

### “Project fields didn’t sync”

This is usually a workflow/config issue, not a token issue.

See: `docs/github/projects-field-sync.md`

### “My workflow didn’t run after pm-bot created an issue”

Likely cause: the issue was created by `GITHUB_TOKEN` in a workflow.

Mitigation: use a GitHub App token or PAT for that step.

## Connector runtime selection

pm-bot supports explicit connector selection through environment config:

- `PM_BOT_GITHUB_CONNECTOR=in_memory` (default): deterministic test connector, no live API calls.
- `PM_BOT_GITHUB_CONNECTOR=api`: GitHub REST API connector for real create/update/list/link operations.

Operational constraint:

- Production-like runs SHOULD set connector type explicitly; silent fallback to in-memory is intended only for local tests/dev.

## Environment variables and token split

Connector auth is loaded with read/write separation:

- `PM_BOT_GITHUB_READ_TOKEN`: read-only token for fetch/list operations.
- `PM_BOT_GITHUB_WRITE_TOKEN`: write-capable token for create/update/link operations.
- `PM_BOT_GITHUB_TOKEN` (or `GITHUB_TOKEN`) acts as shared fallback if split tokens are not configured.

Safety requirements:

- Write paths MUST fail closed when no write token is available (`missing_write_token`).
- Logs/audit records MUST never contain raw token values; only redacted fingerprints are allowed.
- Prefer separate credentials (or separate GitHub App installations) for read vs write privilege domains.

## Retry and rate-limit behavior

GitHub API connector retry behavior is bounded and deterministic at orchestration level:

- Retry only on retryable outcomes: GitHub 5xx or rate-limit responses (`429` and rate-limit flavored `403`).
- Backoff schedule uses bounded exponential timing (default 100ms, 200ms, 400ms; capped).
- `Retry-After` headers are respected as a lower-bound when present.
- Every attempt emits audit data with reason code and scheduled backoff (`changeset_attempt`).
- Exhausted retries produce dead-letter status with deterministic reason code (`retry_budget_exhausted`).
