from __future__ import annotations

from pathlib import Path


def _section_block(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    start = text.find(marker)
    assert start != -1, f"Missing heading: {heading}"
    start += len(marker)

    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:].strip()
    return text[start:next_heading].strip()


def _subsection_block(text: str, heading: str) -> str:
    marker = f"### {heading}\n"
    start = text.find(marker)
    assert start != -1, f"Missing subheading: {heading}"
    start += len(marker)

    next_subheading = text.find("\n### ", start)
    next_heading = text.find("\n## ", start)

    candidates = [idx for idx in (next_subheading, next_heading) if idx != -1]
    if not candidates:
        return text[start:].strip()
    return text[start : min(candidates)].strip()


def test_agent_docs_headings_and_trigger_matrix_are_synchronized() -> None:
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    docs_map = Path("docs/agents/README.md").read_text(encoding="utf-8")

    required_headings = ["Required first reads", "Trigger matrix", "Domain documentation links"]
    for heading in required_headings:
        assert f"## {heading}\n" in docs_map

    agents_matrix = _subsection_block(agents, "Trigger matrix")
    docs_matrix = _section_block(docs_map, "Trigger matrix")

    agents_lines = [line for line in agents_matrix.splitlines() if not line.startswith("> Sync note:")]
    docs_lines = [line for line in docs_matrix.splitlines() if not line.startswith("> Sync note:")]
    assert agents_lines == docs_lines
