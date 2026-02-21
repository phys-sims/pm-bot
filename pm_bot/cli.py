"""pm-bot CLI (v0 scaffold)

This is intentionally small: the roadmaps live in docs/roadmaps/.
Agents should implement commands incrementally.
"""

import json
from pathlib import Path
import typer

app = typer.Typer(add_completion=False, help="pm-bot: agent-native PM orchestrator (scaffold)")

@app.command()
def status():
    """Print basic repo status and where to look next."""
    typer.echo("pm-bot scaffold is installed.")
    typer.echo("Roadmaps: docs/roadmaps/")
    typer.echo("Templates snapshot: vendor/dotgithub/ISSUE_TEMPLATE/")
    typer.echo("Schema: pm_bot/schema/work_item.schema.json")

@app.command()
def show_schema():
    """Print the WorkItem JSON schema."""
    schema_path = Path(__file__).parent / "schema" / "work_item.schema.json"
    typer.echo(schema_path.read_text())

if __name__ == "__main__":
    app()
