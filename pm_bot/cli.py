"""pm-bot CLI v0."""

from __future__ import annotations

import json
from pathlib import Path

import requests
import typer

from pm_bot.github.body_parser import parse_child_refs
from pm_bot.github.parse_issue_body import parse_issue_body
from pm_bot.github.render_issue_body import FIELD_TO_HEADING, load_template_map, render_issue_body

CHILD_REF_HEADINGS = {
    "Child tasks",
    "Child Issues (link Features/Tasks/Tests/Benches/Docs)",
}


def _primary_context_heading(item_type: str) -> str:
    template_map = load_template_map()
    headings = template_map.get(item_type, {}).get("headings", [])
    reserved = set(FIELD_TO_HEADING.values()) | CHILD_REF_HEADINGS
    for heading in headings:
        if heading not in reserved:
            return heading
    return "Context"


app = typer.Typer(add_completion=False, help="pm-bot: agent-native PM orchestrator")


@app.command()
def status() -> None:
    """Print basic repo status and where to look next."""
    typer.echo("pm-bot is installed.")
    typer.echo("Roadmaps: docs/roadmaps/")
    typer.echo("Templates snapshot: vendor/dotgithub/ISSUE_TEMPLATE/")
    typer.echo("Schema: pm_bot/schema/work_item.schema.json")


@app.command()
def show_schema() -> None:
    """Print the WorkItem JSON schema."""
    schema_path = Path(__file__).parent / "schema" / "work_item.schema.json"
    typer.echo(schema_path.read_text())


@app.command()
def draft(
    item_type: str,
    title: str = typer.Option(..., "--title"),
    context: str = typer.Option("", "--context"),
    area: str = typer.Option("", "--area"),
    priority: str = typer.Option("", "--priority"),
    validate: bool = typer.Option(False, "--validate"),
) -> None:
    """Create a draft markdown body + JSON for an issue type."""
    item = {
        "title": title,
        "type": item_type,
        "fields": {},
        "relationships": {"children_refs": []},
    }
    if context:
        item["fields"][_primary_context_heading(item_type)] = context
    if area:
        item["area"] = area
    if priority:
        item["priority"] = priority

    markdown = render_issue_body(item)
    typer.echo("--- markdown ---")
    typer.echo(markdown)
    typer.echo("--- json ---")
    typer.echo(json.dumps(item, indent=2))

    if validate:
        parsed = parse_issue_body(markdown, item_type=item_type, title=title)
        if parsed.get("validation_errors"):
            raise typer.Exit(code=1)


@app.command()
def parse(
    file: Path = typer.Option(None, "--file"),
    url: str = typer.Option("", "--url"),
    issue_type: str = typer.Option(..., "--type"),
    title: str = typer.Option("", "--title"),
    validate: bool = typer.Option(False, "--validate"),
) -> None:
    """Parse an issue markdown file or URL into canonical JSON."""
    if file is None and not url:
        raise typer.BadParameter("Either --file or --url is required")
    if file is not None and url:
        raise typer.BadParameter("Use only one of --file or --url")

    if file is not None:
        markdown = file.read_text()
    else:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        markdown = response.text
    parsed = parse_issue_body(markdown, item_type=issue_type, title=title)
    typer.echo(json.dumps(parsed, indent=2))
    if validate and parsed.get("validation_errors"):
        raise typer.Exit(code=1)


@app.command()
def tree(file: Path = typer.Option(..., "--file")) -> None:
    """Print an ASCII tree of child issue refs parsed from checklists."""
    markdown = file.read_text()
    refs = parse_child_refs(markdown)
    typer.echo(file.name)
    for ref in refs:
        typer.echo(f"└── {ref}")


if __name__ == "__main__":
    app()
