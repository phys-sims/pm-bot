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
_AUDIENCE_PATTERN = re.compile(r"^> \*\*Audience:\*\* .+")
_DEPTH_PATTERN = re.compile(r"^> \*\*Depth:\*\* (L[0-3])\b")
_SOT_PATTERN = re.compile(r"^> \*\*Source of truth:\*\* .+")


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
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme_text = (DOCS_DIR / "README.md").read_text(encoding="utf-8")
    status_text = STATUS_FILE.read_text(encoding="utf-8")

    required_commands = [
        "pytest -q",
        "ruff check .",
        "ruff format .",
        "python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates --check-depth-metadata --check-l0-bloat",
    ]
    for command in required_commands:
        if command not in status_text:
            errors.append(f"STATUS.md missing CI/operability command: {command}")

    required_status_headings = [
        "## Last updated",
        "## CI health checklist",
        "## Current compatibility notes",
        "## Active change scope bullets",
    ]
    for heading in required_status_headings:
        if heading not in status_text:
            errors.append(f"STATUS.md missing required section: {heading}")

    forbidden_status_sections = [
        "## Roadmap status",
        "## Canonical contract status",
        "## Current-state deltas",
        "Roadmap checklist",
        "Roadmap deliverables status",
        "Future roadmap",
        "Quickstart",
        "How to navigate",
    ]
    for section in forbidden_status_sections:
        if section in status_text:
            errors.append(f"STATUS.md contains non-operational guidance section: {section}")

    if re.search(r"^- Scope:", status_text, flags=re.MULTILINE):
        errors.append(
            "STATUS.md contains legacy Last updated scope bullets; keep scope bullets only in the active scope section."
        )

    if "## Active change scope bullets" in status_text and "superseded" not in status_text:
        errors.append(
            "STATUS.md active scope section missing explicit superseded/stale pruning guidance."
        )

    if "Template + stale content pruning instructions" not in status_text:
        errors.append(
            "STATUS.md missing stale content pruning instructions in active scope section."
        )

    if "## Documentation precedence (authoritative)" not in docs_readme_text:
        errors.append("docs/README.md missing authoritative documentation precedence section.")

    if "Documentation precedence" in readme_text:
        errors.append(
            "README.md must not define documentation precedence; link to docs/README.md instead."
        )

    if "Roadmap snapshot" in readme_text or "Core concepts" in readme_text:
        errors.append("README.md must stay concise and avoid deep narrative sections.")

    return errors


def _major_docs() -> list[tuple[Path, str]]:
    docs: list[tuple[Path, str]] = [
        (ROOT / "README.md", "L0"),
        (DOCS_DIR / "README.md", "L0"),
        (DOCS_DIR / "quickstart.md", "L1"),
    ]
    for path in sorted((DOCS_DIR / "runbooks").glob("*.md")):
        docs.append((path, "L1"))
    for path in sorted((DOCS_DIR / "spec").glob("*.md")):
        docs.append((path, "L2"))
    for path in sorted((DOCS_DIR / "github").glob("*.md")):
        docs.append((path, "L2"))
    for path in sorted((DOCS_DIR / "contracts").glob("*.md")):
        docs.append((path, "L3"))
    return docs


def check_doc_depth_metadata() -> list[str]:
    errors: list[str] = []
    for path, expected_depth in _major_docs():
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) < 4:
            errors.append(
                f"{path.relative_to(ROOT)} missing required audience/depth/source metadata block."
            )
            continue

        audience_line = lines[1] if len(lines) > 1 else ""
        depth_line = lines[2] if len(lines) > 2 else ""
        source_line = lines[3] if len(lines) > 3 else ""

        if not _AUDIENCE_PATTERN.match(audience_line):
            errors.append(f"{path.relative_to(ROOT)} missing '> **Audience:** ...' on line 2.")
        depth_match = _DEPTH_PATTERN.match(depth_line)
        if depth_match is None:
            errors.append(f"{path.relative_to(ROOT)} missing '> **Depth:** Lx ...' on line 3.")
        elif depth_match.group(1) != expected_depth:
            errors.append(
                f"{path.relative_to(ROOT)} has depth {depth_match.group(1)} but expected {expected_depth}."
            )
        if not _SOT_PATTERN.match(source_line):
            errors.append(
                f"{path.relative_to(ROOT)} missing '> **Source of truth:** ...' on line 4."
            )
    return errors


def check_l0_bloat() -> list[str]:
    errors: list[str] = []
    for path in (ROOT / "README.md", DOCS_DIR / "README.md"):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 200:
            errors.append(
                f"{path.relative_to(ROOT)} exceeds L0 size target (<~200 lines): {line_count} lines."
            )
    return errors


def run_checks(args: argparse.Namespace) -> int:
    errors: list[str] = []
    if args.check_links:
        errors.extend(check_markdown_links())
    if args.check_contradictions:
        errors.extend(check_contradiction_workflow_docs())
    if args.check_status_gates:
        errors.extend(check_status_operability_hygiene())
    if args.check_depth_metadata:
        errors.extend(check_doc_depth_metadata())
    if args.check_l0_bloat:
        errors.extend(check_l0_bloat())

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
    parser.add_argument(
        "--check-depth-metadata",
        action="store_true",
        help="Validate major docs include audience/depth/source metadata with expected tier.",
    )
    parser.add_argument(
        "--check-l0-bloat",
        action="store_true",
        help="Validate L0 docs remain under the target line-count budget.",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    ns = parser.parse_args()
    if not any(
        (
            ns.check_links,
            ns.check_contradictions,
            ns.check_status_gates,
            ns.check_depth_metadata,
            ns.check_l0_bloat,
        )
    ):
        ns.check_links = True
        ns.check_contradictions = True
        ns.check_status_gates = True
        ns.check_depth_metadata = True
        ns.check_l0_bloat = True
    raise SystemExit(run_checks(ns))
