from __future__ import annotations

import json
from pathlib import Path

from pm_bot.github.parse_issue_body import parse_issue_body
from pm_bot.github.render_issue_body import render_issue_body

FIXTURES = Path(__file__).parent / "fixtures" / "golden_issue_flows"


def test_feature_issue_body_matches_golden_parse_fixture() -> None:
    markdown = (FIXTURES / "feature_issue_body.md").read_text(encoding="utf-8")
    expected = json.loads((FIXTURES / "feature_expected_parse.json").read_text(encoding="utf-8"))

    parsed = parse_issue_body(
        markdown, item_type="feature", title="Feature: deterministic parser fixtures"
    )

    assert parsed == expected


def test_feature_issue_body_matches_golden_render_fixture() -> None:
    parsed = json.loads((FIXTURES / "feature_expected_parse.json").read_text(encoding="utf-8"))
    expected = (FIXTURES / "feature_expected_render.md").read_text(encoding="utf-8")

    rendered = render_issue_body(parsed)

    assert rendered == expected
