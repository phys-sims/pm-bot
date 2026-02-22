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

Why:

- prevents accidental writes to the wrong repo
- makes human approval review easier (“this bundle writes to repos A/B only”)

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

