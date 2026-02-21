from pm_bot.github.template_loader import list_templates, load_template
from pm_bot.github.body_parser import parse_headings

def test_templates_load():
    names = list_templates()
    assert "epic" in names
    t = load_template("feature")
    assert t["name"].lower() == "feature"

def test_parse_headings():
    md = "### Area\nphys-pipeline\n\n### Priority\nP0\n"
    parsed = parse_headings(md)
    assert parsed.headings["Area"] == "phys-pipeline"
    assert parsed.headings["Priority"] == "P0"
