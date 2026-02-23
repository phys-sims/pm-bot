"""pm-bot CLI v0."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import requests
import typer

from pm_bot.github.body_parser import parse_child_refs
from pm_bot.github.parse_issue_body import parse_issue_body
from pm_bot.github.render_issue_body import FIELD_TO_HEADING, load_template_map, render_issue_body
from pm_bot.validation import validate_work_item

CHILD_REF_HEADINGS = {
    "Child tasks",
    "Child Issues (link Features/Tasks/Tests/Benches/Docs)",
}

GITHUB_ISSUE_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)(?:[/?#].*)?$"
)
RAW_MARKDOWN_URL_RE = re.compile(r"^https://.+\.md(?:[?#].*)?$", re.IGNORECASE)


def _load_raw_markdown_url(url: str) -> str:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def _load_github_issue_url(url: str) -> str:
    match = GITHUB_ISSUE_URL_RE.match(url)
    if not match:
        raise typer.BadParameter(
            "Unsupported GitHub issue URL format. Expected: "
            "https://github.com/<owner>/<repo>/issues/<number>"
        )
    owner = match.group("owner")
    repo = match.group("repo")
    number = match.group("number")
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"

    token = os.getenv("PM_BOT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(api_url, headers=headers, timeout=10)
    if response.status_code in {401, 403, 404}:
        raise typer.BadParameter(
            "Failed to fetch GitHub issue body. Provide a token via PM_BOT_GITHUB_TOKEN "
            "(preferred) or GITHUB_TOKEN with read access to the target repo."
        )
    response.raise_for_status()
    body = response.json().get("body") or ""
    return body


def _load_markdown_from_url(url: str) -> str:
    if GITHUB_ISSUE_URL_RE.match(url):
        return _load_github_issue_url(url)
    if RAW_MARKDOWN_URL_RE.match(url) or "raw.githubusercontent.com" in url:
        return _load_raw_markdown_url(url)
    raise typer.BadParameter(
        "Unsupported --url value. Supported formats: "
        "https://github.com/<owner>/<repo>/issues/<number> (GitHub issue URL) or "
        "https://.../*.md (raw markdown URL)."
    )


def _primary_context_heading(item_type: str) -> str:
    template_map = load_template_map()
    headings = template_map.get(item_type, {}).get("headings", [])
    reserved = set(FIELD_TO_HEADING.values()) | CHILD_REF_HEADINGS
    for heading in headings:
        if heading not in reserved:
            return heading
    return "Context"


app = typer.Typer(add_completion=False, help="pm-bot: agent-native PM orchestrator")


def _emit_validation_errors(errors: list[dict[str, str]]) -> None:
    typer.echo(json.dumps({"errors": errors}, indent=2))


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
        errors = validate_work_item(item)
        if errors:
            _emit_validation_errors(errors)
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
        try:
            markdown = _load_markdown_from_url(url)
        except typer.BadParameter as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=2) from exc
    parsed = parse_issue_body(markdown, item_type=issue_type, title=title)
    typer.echo(json.dumps(parsed, indent=2))
    if validate:
        errors = parsed.get("validation_errors", [])
        if errors:
            _emit_validation_errors(errors)
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
