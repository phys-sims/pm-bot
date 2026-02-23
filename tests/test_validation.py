import json
from pathlib import Path

from typer.testing import CliRunner

from pm_bot.cli import app
from pm_bot.github.parse_issue_body import parse_issue_body
from pm_bot.validation import validate_work_item

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_schema_and_rule_validation_codes_are_deterministic():
    work_item = _load_json("invalid_work_item_schema_and_rules.json")
    errors = validate_work_item(work_item)

    assert [e["code"] for e in errors] == [
        "RULE_CHILD_REF_INVALID",
        "RULE_CHILD_REF_INVALID",
        "SCHEMA_ENUM",
        "SCHEMA_MINIMUM",
        "SCHEMA_REQUIRED",
    ]
    assert errors[0]["path"] == "$.relationships.children_refs[0]"
    assert errors[-1]["path"] == "$.priority"


def test_parse_includes_required_heading_rule_errors():
    md = "### Goal\n_No response_\n\n### Area\nphys-pipeline\n\n### Priority\nP1\n"
    parsed = parse_issue_body(md, item_type="feature", title="missing-goal")

    assert parsed["validation_errors"] == [
        {
            "code": "RULE_REQUIRED_HEADING_EMPTY",
            "path": "$.fields[Goal]",
            "message": "Missing required heading content: Goal",
        }
    ]


def test_parse_validate_cli_returns_machine_readable_errors():
    runner = CliRunner()
    with runner.isolated_filesystem():
        md_path = Path("issue.md")
        md_path.write_text(
            "### Parent Feature URL\n_No response_\n\n### Area\nphys-pipeline\n\n### Priority\nP1\n"
        )
        result = runner.invoke(
            app,
            ["parse", "--file", str(md_path), "--type", "task", "--title", "x", "--validate"],
        )

    assert result.exit_code == 1
    payload = result.stdout.split('\n{\n  "errors":', 1)[1]
    errors_json = json.loads('{\n  "errors":' + payload)
    assert errors_json["errors"] == [
        {
            "code": "RULE_TASK_PARENT_FEATURE_URL_REQUIRED",
            "path": "$.fields[Parent Feature URL]",
            "message": "Task items require a non-empty 'Parent Feature URL' heading.",
        }
    ]


def test_draft_validate_cli_returns_machine_readable_errors():
    runner = CliRunner()
    result = runner.invoke(app, ["draft", "feature", "--title", "x", "--validate"])

    assert result.exit_code == 1
    payload = result.stdout.split('\n{\n  "errors":', 1)[1]
    errors_json = json.loads('{\n  "errors":' + payload)
    assert errors_json["errors"] == [
        {
            "code": "SCHEMA_REQUIRED",
            "path": "$.area",
            "message": "'area' is a required property",
        },
        {
            "code": "SCHEMA_REQUIRED",
            "path": "$.priority",
            "message": "'priority' is a required property",
        },
    ]
