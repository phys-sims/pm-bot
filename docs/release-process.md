# Release process

## Versioning
- Use semantic versioning (`MAJOR.MINOR.PATCH`).
- Bump in `pyproject.toml` before tagging a release.

## Changelog policy
- Every user-facing change must be recorded in `CHANGELOG.md` under `Unreleased`.
- Move `Unreleased` entries into a tagged version section during release.

## Release steps
1. Run `ruff check .`, `ruff format .`, and `pytest -q`.
2. Ensure `STATUS.md` reflects roadmap and test status.
3. Update `CHANGELOG.md` with grouped entries.
4. Bump `pyproject.toml` version.
5. Create tag and publish package/artifacts.
