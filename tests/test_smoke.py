from pm_bot.cli import _primary_context_heading
from pm_bot.github.body_parser import parse_child_refs, parse_headings
from pm_bot.github.parse_issue_body import parse_issue_body
from pm_bot.github.render_issue_body import render_issue_body
from pm_bot.github.template_loader import list_templates, load_template


def test_templates_load():
    names = list_templates()
    assert "epic" in names
    assert "feature" in names
    t = load_template("feature")
    assert t["name"].lower() == "feature"


def test_parse_headings_no_response_normalized():
    md = "### Area\nphys-pipeline\n\n### Priority\n_No response_\n"
    parsed = parse_headings(md)
    assert parsed.headings["Area"] == "phys-pipeline"
    assert parsed.headings["Priority"] == ""


def test_parse_child_refs_issue_numbers_and_urls():
    text = "- [ ] #123\n- [x] https://github.com/org/repo/issues/44\n- [ ] #123"
    assert parse_child_refs(text) == ["#123", "https://github.com/org/repo/issues/44"]


def test_parse_and_render_feature_roundtrip_headings_present():
    md = (
        "### Goal\nShip parser\n\n"
        "### Child tasks\n- [ ] #123\n\n"
        "### Area\nphys-pipeline\n\n"
        "### Priority\nP1\n"
    )
    parsed = parse_issue_body(md, item_type="feature", title="[feat] parser")
    rendered = render_issue_body(parsed)

    assert "### Goal" in rendered
    assert "### Area" in rendered
    assert "### Priority" in rendered
    assert "#123" in rendered


def test_epic_size_epic_heading_supported_by_parser():
    md = "### Area\nphys-pipeline\n\n### Size (Epic)\nL\n"
    parsed = parse_issue_body(md, item_type="epic", title="[epic] x")
    assert parsed["size"] == "L"


def test_primary_context_heading_prefers_first_non_project_heading():
    assert _primary_context_heading("feature") == "Goal"


def test_primary_context_heading_skips_child_headings_for_epic():
    assert _primary_context_heading("epic") == "Objective (North Star)"
