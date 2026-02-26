# Release process

## Versioning
- Use semantic versioning (`MAJOR.MINOR.PATCH`).
- Bump in `pyproject.toml` before tagging a release.

## Changelog policy
- Every user-facing change must be recorded in `CHANGELOG.md` under `Unreleased`.
- Move `Unreleased` entries into a tagged version section during release.

## Release steps
1. Run `ruff check .`, `ruff format .`, and `pytest -q`.
2. Confirm CI `release-gate` is green (requires contract, reliability, regression fixtures, and docs-command validation checks from `docs/qa-matrix.md`).
3. Ensure `STATUS.md` reflects current CI health, compatibility notes, and active scope bullets only (no roadmap narrative).
4. Update `CHANGELOG.md` with grouped entries.
5. Bump `pyproject.toml` version.
6. Create tag and publish package/artifacts.
