#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
STATUS_FILE = ROOT / "STATUS.md"
CHECKLIST_FILE = DOCS_DIR / "ROADMAP_V4_CHECKLIST.md"

_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _iter_markdown_files() -> list[Path]:
    files = sorted(DOCS_DIR.rglob("*.md"))
    files.append(STATUS_FILE)
    return files


def _is_external_link(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https", "mailto"}


def check_markdown_links() -> list[str]:
    errors: list[str] = []
    for path in _iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        for target in _LINK_PATTERN.findall(text):
            clean_target = target.strip()
            if not clean_target or _is_external_link(clean_target):
                continue
            if clean_target.startswith("#"):
                continue
            rel_target = clean_target.split("#", 1)[0]
            if not rel_target:
                continue
            resolved = (path.parent / rel_target).resolve()
            if not resolved.exists():
                errors.append(
                    f"{path.relative_to(ROOT)} contains missing link target: {clean_target}"
                )
    return errors


def check_contradiction_workflow_docs() -> list[str]:
    errors: list[str] = []
    maintenance = (DOCS_DIR / "maintenance.md").read_text(encoding="utf-8")
    if "Contradiction-check workflow" not in maintenance:
        errors.append("docs/maintenance.md missing 'Contradiction-check workflow' section.")
    if "python scripts/docs_hygiene.py --check-contradictions" not in maintenance:
        errors.append("docs/maintenance.md missing contradiction-check command entry.")

    checklist = CHECKLIST_FILE.read_text(encoding="utf-8")
    for row_number in (11, 12, 13):
        row_match = re.search(rf"^\|\s*{row_number}\s*\|.*$", checklist, flags=re.MULTILINE)
        if row_match is None or "☑ done" not in row_match.group(0):
            errors.append("docs/ROADMAP_V4_CHECKLIST.md rows 11-13 must be marked ☑ done.")
            break
    return errors


def check_status_operability_hygiene() -> list[str]:
    errors: list[str] = []
    status_text = STATUS_FILE.read_text(encoding="utf-8")

    required_commands = [
        "pytest -q",
        "ruff check .",
        "ruff format .",
        "python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates",
    ]
    for command in required_commands:
        if command not in status_text:
            errors.append(f"STATUS.md missing CI/operability command: {command}")

    if "v3 near-term complete" not in status_text:
        errors.append("STATUS.md must explicitly state that v3 near-term scope is complete.")

    if re.search(r"v3[^\n]*in progress", status_text, flags=re.IGNORECASE):
        errors.append("STATUS.md contains stale v3 in-progress references.")

    return errors


def run_checks(args: argparse.Namespace) -> int:
    errors: list[str] = []
    if args.check_links:
        errors.extend(check_markdown_links())
    if args.check_contradictions:
        errors.extend(check_contradiction_workflow_docs())
    if args.check_status_gates:
        errors.extend(check_status_operability_hygiene())

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("Docs hygiene checks passed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run docs/status hygiene checks.")
    parser.add_argument("--check-links", action="store_true", help="Validate local markdown links.")
    parser.add_argument(
        "--check-contradictions",
        action="store_true",
        help="Validate contradiction-check workflow docs/checklist state.",
    )
    parser.add_argument(
        "--check-status-gates",
        action="store_true",
        help="Validate STATUS.md contains required operability gates.",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    ns = parser.parse_args()
    if not any((ns.check_links, ns.check_contradictions, ns.check_status_gates)):
        ns.check_links = True
        ns.check_contradictions = True
        ns.check_status_gates = True
    raise SystemExit(run_checks(ns))
