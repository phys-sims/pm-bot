"""Sync the vendored template snapshot from phys-sims/.github.

Usage:
    python scripts/sync_dotgithub.py --ref main

Requires:
    - PM_BOT_GITHUB_TOKEN env var (recommended) OR GITHUB_TOKEN env var
      (fine-grained PAT or GitHub App installation token)
    - access to phys-sims/.github

Notes:
    - This script is intentionally simple; it fetches raw files via GitHub REST API.
    - Pin the ref (tag/SHA) once you want reproducibility.
"""

from __future__ import annotations
import argparse
import base64
import os
from pathlib import Path
import requests

OWNER = "phys-sims"
REPO = ".github"

FILES = [
    ".github/ISSUE_TEMPLATE/epic.yml",
    ".github/ISSUE_TEMPLATE/feature.yml",
    ".github/ISSUE_TEMPLATE/task.yml",
    ".github/ISSUE_TEMPLATE/bug.yml",
    ".github/ISSUE_TEMPLATE/benchmark.yml",
    ".github/ISSUE_TEMPLATE/spike.yml",
    ".github/ISSUE_TEMPLATE/test.yml",
    ".github/ISSUE_TEMPLATE/chore.yml",
    "issue-templates-guide.md",
    "project-field-sync.yml",
]


def gh_get_contents(path: str, ref: str, token: str) -> bytes:
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=headers, params={"ref": ref}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("encoding") == "base64":
        return base64.b64decode(data["content"])
    raise RuntimeError(f"Unexpected response for {path}: {data}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="main", help="branch, tag, or SHA to fetch from")
    ap.add_argument("--dest", default="vendor/dotgithub", help="destination directory")
    args = ap.parse_args()

    token = os.environ.get("PM_BOT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Missing PM_BOT_GITHUB_TOKEN (or GITHUB_TOKEN) in environment.")

    dest = Path(args.dest)
    (dest / "ISSUE_TEMPLATE").mkdir(parents=True, exist_ok=True)

    for f in FILES:
        content = gh_get_contents(f, args.ref, token)
        out_path = dest / f.replace(".github/ISSUE_TEMPLATE/", "ISSUE_TEMPLATE/")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(content)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
